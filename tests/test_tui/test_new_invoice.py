from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from textual.widgets import Button, Label, MaskedInput, Select

from emissor.tui.app import EmissorApp
from emissor.tui.screens.new_invoice import NewInvoiceScreen


@pytest.mark.asyncio
async def test_new_invoice_screen_starts_with_form(mock_config):
    app = EmissorApp(env="homologacao")
    async with app.run_test() as pilot:
        await pilot.press("n")
        screen = app.screen
        assert isinstance(screen, NewInvoiceScreen)
        assert screen.query_one("#form-container").display is True
        assert screen.query_one("#preview-container").display is False
        assert screen.query_one("#result-container").display is False


@pytest.mark.asyncio
async def test_new_invoice_screen_loads_clients_in_select(mock_config):
    app = EmissorApp(env="homologacao")
    async with app.run_test() as pilot:
        await pilot.press("n")
        await pilot.pause()
        sel = app.screen.query_one("#client-select", Select)
        assert len(sel._options) >= 2


@pytest.mark.asyncio
async def test_new_invoice_escape_goes_back(mock_config):
    from emissor.tui.screens.dashboard import DashboardScreen

    app = EmissorApp(env="homologacao")
    async with app.run_test() as pilot:
        await pilot.press("n")
        assert isinstance(app.screen, NewInvoiceScreen)
        await pilot.press("escape")
        assert isinstance(app.screen, DashboardScreen)


@pytest.mark.asyncio
async def test_prepare_shows_preview(mock_config):
    """Clicking Preparar with valid input transitions to preview phase."""
    mock_prepared = MagicMock()
    mock_prepared.emitter.razao_social = "ACME"
    mock_prepared.emitter.cnpj = "123"
    mock_prepared.client.nome = "Client X"
    mock_prepared.client.nif = "999"
    mock_prepared.intermediary = None
    mock_prepared.n_dps = 5
    mock_prepared.env = "homologacao"

    with patch("emissor.services.emission.prepare", return_value=mock_prepared):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.press("n")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, NewInvoiceScreen)

            # Fill form
            sel = screen.query_one("#client-select", Select)
            sel.value = "acme"

            from textual.widgets import Input

            screen.query_one("#valor-brl", Input).value = "1000.00"
            screen.query_one("#valor-usd", Input).value = "200.00"
            screen.query_one("#competencia", MaskedInput).value = "30/12/2025"

            # Click Preparar
            screen.query_one("#btn-preparar", Button).press()
            await pilot.pause()

            # Should show preview
            assert screen.query_one("#preview-container").display is True
            assert screen.query_one("#form-container").display is False


@pytest.mark.asyncio
async def test_prepare_validation_error_stays_on_form(mock_config):
    """Clicking Preparar with missing client shows error, stays on form."""
    app = EmissorApp(env="homologacao")
    async with app.run_test() as pilot:
        await pilot.press("n")
        await pilot.pause()

        screen = app.screen
        assert isinstance(screen, NewInvoiceScreen)

        # Don't fill anything, just click Preparar
        screen.query_one("#btn-preparar", Button).press()
        await pilot.pause()

        # Should stay on form with error
        assert screen.query_one("#form-container").display is True
        error_text = screen.query_one("#error-label", Label).render().plain
        assert "cliente" in error_text.lower()


@pytest.mark.asyncio
async def test_submit_disables_buttons(mock_config):
    """Enviar and Salvar buttons are disabled immediately when _do_submit is called."""
    mock_prepared = MagicMock()
    mock_prepared.emitter.razao_social = "ACME"
    mock_prepared.emitter.cnpj = "123"
    mock_prepared.client.nome = "Client"
    mock_prepared.client.nif = "999"
    mock_prepared.intermediary = None
    mock_prepared.n_dps = 5
    mock_prepared.env = "homologacao"

    with patch("emissor.services.emission.prepare", return_value=mock_prepared):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.press("n")
            await pilot.pause()

            screen = app.screen
            assert isinstance(screen, NewInvoiceScreen)

            # Fill and prepare
            sel = screen.query_one("#client-select", Select)
            sel.value = "acme"
            from textual.widgets import Input

            screen.query_one("#valor-brl", Input).value = "1000.00"
            screen.query_one("#valor-usd", Input).value = "200.00"
            screen.query_one("#competencia", MaskedInput).value = "30/12/2025"

            screen.query_one("#btn-preparar", Button).press()
            await pilot.pause()

            # Now on preview, buttons should be enabled
            btn_enviar = screen.query_one("#btn-enviar", Button)
            btn_salvar = screen.query_one("#btn-salvar", Button)
            assert btn_enviar.disabled is False
            assert btn_salvar.disabled is False

            # Patch _run_submit to prevent actual worker execution
            with patch.object(screen, "_run_submit"):
                screen._do_submit()
                # Buttons should be disabled synchronously by _do_submit
                assert btn_enviar.disabled is True
                assert btn_salvar.disabled is True


@pytest.mark.asyncio
async def test_submit_success_shows_result(mock_config):
    """Successful submit transitions to result phase."""
    mock_prepared = MagicMock()
    mock_prepared.emitter.razao_social = "ACME"
    mock_prepared.emitter.cnpj = "123"
    mock_prepared.client.nome = "Client"
    mock_prepared.client.nif = "999"
    mock_prepared.intermediary = None
    mock_prepared.n_dps = 5
    mock_prepared.env = "homologacao"

    submit_result = {
        "n_dps": 5,
        "response": {"chNFSe": "NFSe_test_123", "nNFSe": "42"},
    }

    with (
        patch("emissor.services.emission.prepare", return_value=mock_prepared),
        patch("emissor.services.emission.submit", return_value=submit_result),
    ):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.press("n")
            await pilot.pause()

            screen = app.screen
            sel = screen.query_one("#client-select", Select)
            sel.value = "acme"
            from textual.widgets import Input

            screen.query_one("#valor-brl", Input).value = "1000.00"
            screen.query_one("#valor-usd", Input).value = "200.00"
            screen.query_one("#competencia", MaskedInput).value = "30/12/2025"

            screen.query_one("#btn-preparar", Button).press()
            await pilot.pause()

            # Now submit
            screen.query_one("#btn-enviar", Button).press()
            await pilot.pause()

            # Should show result phase
            assert screen.query_one("#result-container").display is True
            result_text = screen.query_one("#result-info", Label).render().plain
            assert "NFSe_test_123" in result_text


@pytest.mark.asyncio
async def test_save_xml_success(mock_config):
    """Clicking Salvar XML saves and shows status."""
    mock_prepared = MagicMock()
    mock_prepared.emitter.razao_social = "ACME"
    mock_prepared.emitter.cnpj = "123"
    mock_prepared.client.nome = "Client"
    mock_prepared.client.nif = "999"
    mock_prepared.intermediary = None
    mock_prepared.n_dps = 5
    mock_prepared.env = "homologacao"

    with (
        patch("emissor.services.emission.prepare", return_value=mock_prepared),
        patch("emissor.services.emission.save_xml", return_value="/tmp/dry_run_dps_5.xml"),
    ):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.press("n")
            await pilot.pause()

            screen = app.screen
            sel = screen.query_one("#client-select", Select)
            sel.value = "acme"
            from textual.widgets import Input

            screen.query_one("#valor-brl", Input).value = "1000.00"
            screen.query_one("#valor-usd", Input).value = "200.00"
            screen.query_one("#competencia", MaskedInput).value = "30/12/2025"

            screen.query_one("#btn-preparar", Button).press()
            await pilot.pause()

            # Click save
            screen.query_one("#btn-salvar", Button).press()
            await pilot.pause()

            status_text = screen.query_one("#status-label", Label).render().plain
            assert "dry_run_dps_5" in status_text


@pytest.mark.asyncio
async def test_new_invoice_prefill_sets_values(mock_config):
    """Prefill dict pre-populates client and values."""
    prefill = {"client_slug": "acme", "valor_brl": "5000.00", "valor_usd": "1000.00"}
    app = EmissorApp(env="homologacao")
    async with app.run_test() as pilot:
        from textual.widgets import Input

        app.push_screen(NewInvoiceScreen(prefill=prefill))
        await pilot.pause()

        screen = app.screen
        assert isinstance(screen, NewInvoiceScreen)

        sel = screen.query_one("#client-select", Select)
        assert sel.value == "acme"
        assert screen.query_one("#valor-brl", Input).value == "5000.00"
        assert screen.query_one("#valor-usd", Input).value == "1000.00"
        # Date should NOT be pre-filled
        assert screen.query_one("#competencia", MaskedInput).value == ""


@pytest.mark.asyncio
async def test_new_invoice_no_prefill_default(mock_config):
    """Without prefill, form starts empty as before."""
    app = EmissorApp(env="homologacao")
    async with app.run_test() as pilot:
        from textual.widgets import Input

        await pilot.press("n")
        await pilot.pause()

        screen = app.screen
        assert isinstance(screen, NewInvoiceScreen)

        sel = screen.query_one("#client-select", Select)
        assert sel.value is Select.BLANK
        assert screen.query_one("#valor-brl", Input).value == ""
        assert screen.query_one("#valor-usd", Input).value == ""
