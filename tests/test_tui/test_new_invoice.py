from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from textual.widgets import Button, Input, Label, MaskedInput, Select, Static

from emissor.tui.app import EmissorApp
from emissor.tui.screens.new_invoice import NewInvoiceScreen

# --- Helpers ---


async def _fill_step1(screen, pilot, *, client="acme", competencia="30/12/2025"):
    """Fill Step 1 fields and advance to Step 2."""
    sel = screen.query_one("#client-select", Select)
    sel.value = client
    screen.query_one("#competencia", MaskedInput).value = competencia
    screen.query_one("#btn-step1-next", Button).press()
    await pilot.pause()
    assert screen._step == 2, f"Expected step 2, got {screen._step}"


async def _fill_step2(screen, pilot):
    """Fill required Step 2 fields (pre-filled by emitter defaults) and advance to Step 3."""
    # Ensure required fields have values (emitter defaults should already fill these)
    if not screen.query_one("#x-desc-serv", Input).value:
        screen.query_one("#x-desc-serv", Input).value = "Desenvolvimento de Software"
    if not screen.query_one("#c-trib-nac", Input).value:
        screen.query_one("#c-trib-nac", Input).value = "010101"
    screen.query_one("#btn-step2-next", Button).press()
    await pilot.pause()
    assert screen._step == 3, f"Expected step 3, got {screen._step}"


async def _fill_step3(screen, pilot, *, valor_brl="1000.00", valor_usd="200.00"):
    """Fill Step 3 monetary values and click Preparar."""
    screen.query_one("#valor-brl", Input).value = valor_brl
    screen.query_one("#valor-usd", Input).value = valor_usd
    screen.query_one("#btn-preparar", Button).press()
    await pilot.pause()
    assert screen._step == 4, f"Expected step 4, got {screen._step}"


async def _navigate_to_step4(screen, pilot, **kwargs):
    """Navigate through steps 1→2→3→4 (Preparar)."""
    step1_keys = ("client", "competencia")
    step3_keys = ("valor_brl", "valor_usd")
    await _fill_step1(screen, pilot, **{k: v for k, v in kwargs.items() if k in step1_keys})
    await _fill_step2(screen, pilot)
    await _fill_step3(screen, pilot, **{k: v for k, v in kwargs.items() if k in step3_keys})


def _make_mock_prepared(**overrides):
    """Create a mock PreparedDPS with sensible defaults."""
    mock = MagicMock()
    mock.emitter.razao_social = overrides.get("razao_social", "ACME")
    mock.emitter.cnpj = overrides.get("cnpj", "123")
    mock.emitter.x_desc_serv = "Dev"
    mock.emitter.c_trib_nac = "010101"
    mock.emitter.c_nbs = "115022000"
    mock.emitter.tp_moeda = "220"
    mock.emitter.c_pais_result = "US"
    mock.client.nome = overrides.get("client_nome", "Client")
    mock.client.nif = overrides.get("client_nif", "999")
    mock.intermediary = overrides.get("intermediary")
    mock.invoice.x_desc_serv = None
    mock.invoice.c_trib_nac = None
    mock.invoice.c_nbs = None
    mock.invoice.tp_moeda = None
    mock.invoice.trib_issqn = None
    mock.invoice.c_pais_result = None
    mock.n_dps = overrides.get("n_dps", 5)
    mock.env = overrides.get("env", "homologacao")
    return mock


# --- Step navigation tests ---


@pytest.mark.asyncio
async def test_new_invoice_screen_starts_with_step1(mock_config):
    app = EmissorApp(env="homologacao")
    async with app.run_test() as pilot:
        await pilot.press("n")
        screen = app.screen
        assert isinstance(screen, NewInvoiceScreen)
        assert screen.query_one("#step-1-pessoas").display is True
        assert screen.query_one("#step-2-servico").display is False
        assert screen.query_one("#step-3-valores").display is False
        assert screen.query_one("#step-4-revisao").display is False
        assert screen.query_one("#result-container").display is False


@pytest.mark.asyncio
async def test_step_indicator_shows_correct_label(mock_config):
    app = EmissorApp(env="homologacao")
    async with app.run_test() as pilot:
        await pilot.press("n")
        screen = app.screen
        assert isinstance(screen, NewInvoiceScreen)
        indicator = screen.query_one("#step-indicator", Static)
        assert "Passo 1/4" in indicator.render().plain


@pytest.mark.asyncio
async def test_step1_to_step2_navigation(mock_config):
    app = EmissorApp(env="homologacao")
    async with app.run_test() as pilot:
        await pilot.press("n")
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, NewInvoiceScreen)

        screen.query_one("#client-select", Select).value = "acme"
        screen.query_one("#competencia", MaskedInput).value = "30/12/2025"

        screen.query_one("#btn-step1-next", Button).press()
        await pilot.pause()

        assert screen._step == 2
        assert screen.query_one("#step-2-servico").display is True
        assert screen.query_one("#step-1-pessoas").display is False


@pytest.mark.asyncio
async def test_step2_back_returns_to_step1(mock_config):
    app = EmissorApp(env="homologacao")
    async with app.run_test() as pilot:
        await pilot.press("n")
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, NewInvoiceScreen)

        await _fill_step1(screen, pilot)
        assert screen._step == 2

        screen.query_one("#btn-step2-back", Button).press()
        await pilot.pause()

        assert screen._step == 1
        assert screen.query_one("#step-1-pessoas").display is True


@pytest.mark.asyncio
async def test_step3_back_returns_to_step2(mock_config):
    app = EmissorApp(env="homologacao")
    async with app.run_test() as pilot:
        await pilot.press("n")
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, NewInvoiceScreen)

        await _fill_step1(screen, pilot)
        await _fill_step2(screen, pilot)
        assert screen._step == 3

        screen.query_one("#btn-step3-back", Button).press()
        await pilot.pause()

        assert screen._step == 2
        assert screen.query_one("#step-2-servico").display is True


@pytest.mark.asyncio
async def test_new_invoice_screen_loads_clients_in_select(mock_config):
    app = EmissorApp(env="homologacao")
    async with app.run_test() as pilot:
        await pilot.press("n")
        await pilot.pause()
        sel = app.screen.query_one("#client-select", Select)
        assert len(sel._options) >= 2


@pytest.mark.asyncio
async def test_new_invoice_escape_from_step1_goes_back(mock_config):
    from emissor.tui.screens.dashboard import DashboardScreen

    app = EmissorApp(env="homologacao")
    async with app.run_test() as pilot:
        await pilot.press("n")
        assert isinstance(app.screen, NewInvoiceScreen)
        await pilot.press("escape")
        assert isinstance(app.screen, DashboardScreen)


@pytest.mark.asyncio
async def test_escape_in_step2_returns_to_step1(mock_config):
    app = EmissorApp(env="homologacao")
    async with app.run_test() as pilot:
        await pilot.press("n")
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, NewInvoiceScreen)

        await _fill_step1(screen, pilot)
        assert screen._step == 2

        await pilot.press("escape")
        assert screen._step == 1


@pytest.mark.asyncio
async def test_escape_in_step4_returns_to_step3(mock_config):
    mock_prepared = _make_mock_prepared()

    with patch("emissor.services.emission.prepare", return_value=mock_prepared):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.press("n")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, NewInvoiceScreen)

            await _navigate_to_step4(screen, pilot)
            assert screen._step == 4

            await pilot.press("escape")
            assert screen._step == 3


# --- Validation tests ---


@pytest.mark.asyncio
async def test_step1_validation_error_missing_client(mock_config):
    app = EmissorApp(env="homologacao")
    async with app.run_test() as pilot:
        await pilot.press("n")
        await pilot.pause()

        screen = app.screen
        assert isinstance(screen, NewInvoiceScreen)

        # Don't fill anything, just click Next
        screen.query_one("#btn-step1-next", Button).press()
        await pilot.pause()

        assert screen.query_one("#step-1-pessoas").display is True
        error_text = screen.query_one("#error-label", Label).render().plain
        assert "cliente" in error_text.lower()


@pytest.mark.asyncio
async def test_step2_validation_error_empty_fields(mock_config):
    app = EmissorApp(env="homologacao")
    async with app.run_test() as pilot:
        await pilot.press("n")
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, NewInvoiceScreen)

        await _fill_step1(screen, pilot)

        # Clear required fields
        screen.query_one("#x-desc-serv", Input).value = ""
        screen.query_one("#c-trib-nac", Input).value = ""

        screen.query_one("#btn-step2-next", Button).press()
        await pilot.pause()

        assert screen._step == 2
        error_text = screen.query_one("#error-label-step2", Label).render().plain
        assert "obrigatório" in error_text.lower()


@pytest.mark.asyncio
async def test_prepare_invalid_monetary(mock_config):
    app = EmissorApp(env="homologacao")
    async with app.run_test() as pilot:
        await pilot.press("n")
        await pilot.pause()

        screen = app.screen
        assert isinstance(screen, NewInvoiceScreen)

        await _fill_step1(screen, pilot)
        await _fill_step2(screen, pilot)

        screen.query_one("#valor-brl", Input).value = "abc"
        screen.query_one("#valor-usd", Input).value = "not-a-number"

        screen.query_one("#btn-preparar", Button).press()
        await pilot.pause()

        assert screen.query_one("#step-3-valores").display is True
        error_text = screen.query_one("#error-label-step3", Label).render().plain
        assert "BRL" in error_text or "USD" in error_text


@pytest.mark.asyncio
async def test_prepare_exception_shows_error_on_step3(mock_config):
    """prepare() exception shows error on Step 3 and re-enables Preparar button."""
    with patch(
        "emissor.services.emission.prepare",
        side_effect=ValueError("Bad certificate"),
    ):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.press("n")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, NewInvoiceScreen)

            # Navigate to Step 3 manually (skip helpers to avoid step 4 assertion)
            screen.query_one("#client-select", Select).value = "acme"
            screen.query_one("#competencia", MaskedInput).value = "30/12/2025"
            screen.query_one("#btn-step1-next", Button).press()
            await pilot.pause()

            if not screen.query_one("#x-desc-serv", Input).value:
                screen.query_one("#x-desc-serv", Input).value = "Dev"
            if not screen.query_one("#c-trib-nac", Input).value:
                screen.query_one("#c-trib-nac", Input).value = "010101"
            screen.query_one("#btn-step2-next", Button).press()
            await pilot.pause()

            screen.query_one("#valor-brl", Input).value = "1000.00"
            screen.query_one("#valor-usd", Input).value = "200.00"
            screen.query_one("#btn-preparar", Button).press()
            await pilot.pause()
            await pilot.pause()  # Wait for thread worker

            # Should be back on Step 3 with error
            assert screen._step == 3
            error_text = screen.query_one("#error-label-step3", Label).render().plain
            assert "Bad certificate" in error_text
            assert screen.query_one("#btn-preparar", Button).disabled is False


# --- Prepare / Preview tests ---


@pytest.mark.asyncio
async def test_prepare_shows_preview(mock_config):
    mock_prepared = _make_mock_prepared(client_nome="Client X")

    with patch("emissor.services.emission.prepare", return_value=mock_prepared):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.press("n")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, NewInvoiceScreen)

            await _navigate_to_step4(screen, pilot)

            # Should show step 4 (revisão)
            assert screen.query_one("#step-4-revisao").display is True
            assert screen.query_one("#step-3-valores").display is False


@pytest.mark.asyncio
async def test_preview_voltar_returns_to_step3(mock_config):
    mock_prepared = _make_mock_prepared()

    with patch("emissor.services.emission.prepare", return_value=mock_prepared):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.press("n")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, NewInvoiceScreen)

            await _navigate_to_step4(screen, pilot)
            assert screen._step == 4

            screen.query_one("#btn-preview-voltar", Button).press()
            await pilot.pause()

            assert screen._step == 3
            assert screen.query_one("#btn-preparar", Button).disabled is False


@pytest.mark.asyncio
async def test_preparar_re_enabled_after_back_from_step4(mock_config):
    """Returning from revisão to step 3 re-enables the Preparar button."""
    mock_prepared = _make_mock_prepared()

    with patch("emissor.services.emission.prepare", return_value=mock_prepared):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.press("n")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, NewInvoiceScreen)

            await _navigate_to_step4(screen, pilot)
            assert screen._step == 4
            assert screen.query_one("#btn-preparar", Button).disabled is True

            screen.query_one("#btn-preview-voltar", Button).press()
            await pilot.pause()

            assert screen._step == 3
            assert screen.query_one("#btn-preparar", Button).disabled is False


# --- Submit / Result tests ---


@pytest.mark.asyncio
async def test_submit_disables_buttons(mock_config):
    mock_prepared = _make_mock_prepared()

    with patch("emissor.services.emission.prepare", return_value=mock_prepared):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.press("n")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, NewInvoiceScreen)

            await _navigate_to_step4(screen, pilot)

            btn_enviar = screen.query_one("#btn-enviar", Button)
            btn_salvar = screen.query_one("#btn-salvar", Button)
            assert btn_enviar.disabled is False
            assert btn_salvar.disabled is False

            with patch.object(screen, "_run_submit"):
                screen._do_submit()
                assert btn_enviar.disabled is True
                assert btn_salvar.disabled is True


@pytest.mark.asyncio
async def test_submit_success_shows_result(mock_config):
    mock_prepared = _make_mock_prepared()
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

            await _navigate_to_step4(screen, pilot)

            screen.query_one("#btn-enviar", Button).press()
            await pilot.pause()

            assert screen.query_one("#result-container").display is True
            result_text = screen.query_one("#result-info", Label).render().plain
            assert "NFSe_test_123" in result_text


@pytest.mark.asyncio
async def test_save_xml_success(mock_config):
    mock_prepared = _make_mock_prepared()

    with (
        patch("emissor.services.emission.prepare", return_value=mock_prepared),
        patch("emissor.services.emission.save_xml", return_value="/tmp/dry_run_dps_5.xml"),
    ):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.press("n")
            await pilot.pause()
            screen = app.screen

            await _navigate_to_step4(screen, pilot)

            screen.query_one("#btn-salvar", Button).press()
            await pilot.pause()

            status_text = screen.query_one("#status-label", Label).render().plain
            assert "dry_run_dps_5" in status_text


@pytest.mark.asyncio
async def test_submit_producao_shows_confirm_dialog(mock_config):
    from emissor.tui.screens.confirm import ConfirmScreen

    mock_prepared = _make_mock_prepared(env="producao")

    with patch("emissor.services.emission.prepare", return_value=mock_prepared):
        app = EmissorApp(env="producao")
        async with app.run_test() as pilot:
            await pilot.press("n")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, NewInvoiceScreen)

            await _navigate_to_step4(screen, pilot)

            screen.query_one("#btn-enviar", Button).press()
            await pilot.pause()

            assert isinstance(app.screen, ConfirmScreen)

            app.screen.query_one("#btn-cancel", Button).press()
            await pilot.pause()

            assert isinstance(app.screen, NewInvoiceScreen)
            assert app.screen.query_one("#step-4-revisao").display is True


@pytest.mark.asyncio
async def test_submit_error_re_enables_buttons(mock_config):
    mock_prepared = _make_mock_prepared()

    with (
        patch("emissor.services.emission.prepare", return_value=mock_prepared),
        patch(
            "emissor.services.emission.submit",
            side_effect=RuntimeError("SEFIN offline"),
        ),
    ):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.press("n")
            await pilot.pause()
            screen = app.screen

            await _navigate_to_step4(screen, pilot)

            screen.query_one("#btn-enviar", Button).press()
            await pilot.pause()
            await pilot.pause()

            btn_enviar = screen.query_one("#btn-enviar", Button)
            btn_salvar = screen.query_one("#btn-salvar", Button)
            assert btn_enviar.disabled is False
            assert btn_salvar.disabled is False

            status_text = screen.query_one("#status-label", Label).render().plain
            assert "Erro" in status_text


@pytest.mark.asyncio
async def test_save_xml_error(mock_config):
    mock_prepared = _make_mock_prepared()

    with (
        patch("emissor.services.emission.prepare", return_value=mock_prepared),
        patch(
            "emissor.services.emission.save_xml",
            side_effect=RuntimeError("Disk full"),
        ),
    ):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.press("n")
            await pilot.pause()
            screen = app.screen

            await _navigate_to_step4(screen, pilot)

            screen.query_one("#btn-salvar", Button).press()
            await pilot.pause()
            await pilot.pause()

            status_text = screen.query_one("#status-label", Label).render().plain
            assert "Erro" in status_text


# --- Result action tests ---


@pytest.mark.asyncio
async def test_result_open_pdf(mock_config):
    from emissor.tui.screens.download_pdf import DownloadPdfScreen

    mock_prepared = _make_mock_prepared()
    submit_result = {
        "n_dps": 5,
        "response": {"chNFSe": "NFSe_pdf_test", "nNFSe": "42"},
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

            await _navigate_to_step4(screen, pilot)

            screen.query_one("#btn-enviar", Button).press()
            await pilot.pause()

            screen.query_one("#btn-result-pdf", Button).press()
            await pilot.pause()

            assert isinstance(app.screen, DownloadPdfScreen)


@pytest.mark.asyncio
async def test_result_open_query(mock_config):
    from emissor.tui.screens.query import QueryScreen

    mock_prepared = _make_mock_prepared()
    submit_result = {
        "n_dps": 5,
        "response": {"chNFSe": "NFSe_query_test", "nNFSe": "42"},
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

            await _navigate_to_step4(screen, pilot)

            screen.query_one("#btn-enviar", Button).press()
            await pilot.pause()

            screen.query_one("#btn-result-consultar", Button).press()
            await pilot.pause()

            assert isinstance(app.screen, QueryScreen)


@pytest.mark.asyncio
async def test_result_pdf_no_chave(mock_config):
    app = EmissorApp(env="homologacao")
    async with app.run_test() as pilot:
        await pilot.press("n")
        await pilot.pause()

        screen = app.screen
        assert isinstance(screen, NewInvoiceScreen)

        screen._result_ch_nfse = "N/A"
        screen._show_result_phase()
        await pilot.pause()

        screen.query_one("#btn-result-pdf", Button).press()
        await pilot.pause()

        assert isinstance(app.screen, NewInvoiceScreen)


# --- Prefill tests ---


@pytest.mark.asyncio
async def test_new_invoice_prefill_sets_values(mock_config):
    prefill = {"client_slug": "acme", "valor_brl": "5000.00", "valor_usd": "1000.00"}
    app = EmissorApp(env="homologacao")
    async with app.run_test() as pilot:
        app.push_screen(NewInvoiceScreen(prefill=prefill))
        await pilot.pause()

        screen = app.screen
        assert isinstance(screen, NewInvoiceScreen)

        sel = screen.query_one("#client-select", Select)
        assert sel.value == "acme"
        # valor_brl/usd are in step 3 now
        assert screen.query_one("#valor-brl", Input).value == "5000.00"
        assert screen.query_one("#valor-usd", Input).value == "1000.00"
        assert screen.query_one("#competencia", MaskedInput).value == ""


@pytest.mark.asyncio
async def test_new_invoice_no_prefill_default(mock_config):
    app = EmissorApp(env="homologacao")
    async with app.run_test() as pilot:
        await pilot.press("n")
        await pilot.pause()

        screen = app.screen
        assert isinstance(screen, NewInvoiceScreen)

        sel = screen.query_one("#client-select", Select)
        assert sel.value is Select.BLANK
        assert screen.query_one("#valor-brl", Input).value == ""
        assert screen.query_one("#valor-usd", Input).value == ""


# --- Client loading tests ---


@pytest.mark.asyncio
async def test_client_load_error(mock_config):
    with patch("emissor.config.list_clients", side_effect=RuntimeError("no config")):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.press("n")
            await pilot.pause()

            screen = app.screen
            assert isinstance(screen, NewInvoiceScreen)

            sel = screen.query_one("#client-select", Select)
            real_options = [o for o in sel._options if o[1] is not Select.BLANK]
            assert len(real_options) == 0


# --- Emitter pre-fill tests ---


@pytest.mark.asyncio
async def test_client_change_updates_comex_fields(mock_config):
    """Selecting a client pre-fills COMEX fields in Step 2."""
    client_dict = {
        "nif": "555",
        "nome": "Globex",
        "logradouro": "X",
        "numero": "1",
        "cidade": "X",
        "estado": "X",
        "cep": "00000",
        "mec_af_comex_p": "07",
        "mec_af_comex_t": "09",
    }
    with patch("emissor.config.load_client", return_value=client_dict):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.press("n")
            await pilot.pause()

            screen = app.screen
            assert isinstance(screen, NewInvoiceScreen)

            screen.query_one("#client-select", Select).value = "globex"
            await pilot.pause()
            await pilot.pause()  # Extra pause for thread worker

            assert screen.query_one("#mec-af-comex-p", Select).value == "07"
            assert screen.query_one("#mec-af-comex-t", Select).value == "09"


@pytest.mark.asyncio
async def test_overrides_reach_prepare(mock_config):
    """Step 2/3 field values are passed as overrides to emission.prepare()."""
    mock_prepared = _make_mock_prepared()

    with patch("emissor.services.emission.prepare", return_value=mock_prepared) as mock_prep:
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.press("n")
            await pilot.pause()

            screen = app.screen
            assert isinstance(screen, NewInvoiceScreen)

            # Step 1
            screen.query_one("#client-select", Select).value = "acme"
            screen.query_one("#competencia", MaskedInput).value = "30/12/2025"
            screen.query_one("#btn-step1-next", Button).press()
            await pilot.pause()

            # Step 2 — set a custom override
            screen.query_one("#x-desc-serv", Input).value = "Custom Override Desc"
            screen.query_one("#c-trib-nac", Input).value = "999999"
            screen.query_one("#btn-step2-next", Button).press()
            await pilot.pause()

            # Step 3 — fill monetary and a tax override
            screen.query_one("#valor-brl", Input).value = "5000.00"
            screen.query_one("#valor-usd", Input).value = "1000.00"
            screen.query_one("#trib-issqn", Select).value = "2"
            screen.query_one("#btn-preparar", Button).press()
            await pilot.pause()

            mock_prep.assert_called_once()
            call_kwargs = mock_prep.call_args.kwargs
            overrides = call_kwargs["overrides"]
            assert overrides["x_desc_serv"] == "Custom Override Desc"
            assert overrides["c_trib_nac"] == "999999"
            assert overrides["trib_issqn"] == "2"


@pytest.mark.asyncio
async def test_emitter_prefills_step2_fields(mock_config):
    """Emitter config values should pre-fill Step 2 service fields."""
    emitter_dict = {
        "cnpj": "12345678000199",
        "razao_social": "ACME",
        "logradouro": "X",
        "numero": "1",
        "bairro": "X",
        "cod_municipio": "1234567",
        "uf": "SP",
        "cep": "00000000",
        "fone": "11999999999",
        "email": "x@x.com",
        "servico": {
            "cTribNac": "030303",
            "xDescServ": "Consultoria",
            "cNBS": "777777777",
            "tpMoeda": "978",
            "cPaisResult": "DE",
        },
    }
    with patch("emissor.config.load_emitter", return_value=emitter_dict):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.press("n")
            await pilot.pause()
            await pilot.pause()  # Extra pause for thread worker

            screen = app.screen
            assert isinstance(screen, NewInvoiceScreen)

            assert screen.query_one("#x-desc-serv", Input).value == "Consultoria"
            assert screen.query_one("#c-trib-nac", Input).value == "030303"
            assert screen.query_one("#c-nbs", Input).value == "777777777"
            assert screen.query_one("#tp-moeda", Input).value == "978"
            assert screen.query_one("#c-pais-result", Input).value == "DE"
