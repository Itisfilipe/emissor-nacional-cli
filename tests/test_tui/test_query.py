from __future__ import annotations

import pytest

from emissor.tui.app import EmissorApp
from emissor.tui.screens.query import QueryScreen


@pytest.mark.asyncio
async def test_query_screen_opens(mock_config):
    app = EmissorApp(env="homologacao")
    async with app.run_test() as pilot:
        await pilot.press("c")
        assert isinstance(app.screen, QueryScreen)


@pytest.mark.asyncio
async def test_query_pre_fills_chave(mock_config):
    app = EmissorApp(env="homologacao")
    async with app.run_test() as pilot:
        app.push_screen(QueryScreen(chave="test_key_123"))
        await pilot.pause()
        from textual.widgets import Input

        input_widget = app.screen.query_one("#chave-input", Input)
        assert input_widget.value == "test_key_123"


@pytest.mark.asyncio
async def test_query_escape_goes_back(mock_config):
    from emissor.tui.screens.dashboard import DashboardScreen

    app = EmissorApp(env="homologacao")
    async with app.run_test() as pilot:
        await pilot.press("c")
        assert isinstance(app.screen, QueryScreen)
        await pilot.press("escape")
        assert isinstance(app.screen, DashboardScreen)


@pytest.mark.asyncio
async def test_query_empty_input_shows_error(mock_config):
    """Clicking Consultar with empty chave shows an error label."""
    from textual.widgets import Button, Label

    app = EmissorApp(env="homologacao")
    async with app.run_test() as pilot:
        app.push_screen(QueryScreen(chave=""))
        await pilot.pause()
        app.screen.query_one("#btn-consultar", Button).press()
        await pilot.pause()
        error = app.screen.query_one("#error-label", Label)
        assert "chave" in error.render().plain.lower()  # type: ignore[union-attr]


@pytest.mark.asyncio
async def test_query_success(mock_config):
    """Successful query displays result in RichLog."""
    from unittest.mock import patch

    from textual.widgets import Button, RichLog

    mock_result = {"chave": "NFSe_test_abc", "n_nfse": "99", "valor": "5000.00"}

    with (
        patch("emissor.services.adn_client.query_nfse", return_value=mock_result),
        patch(
            "emissor.utils.registry.find_invoice",
            return_value={"nsu": 10, "chave": "NFSe_test_abc"},
        ),
    ):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            app.push_screen(QueryScreen(chave="NFSe_test_abc"))
            await pilot.pause()

            app.screen.query_one("#btn-consultar", Button).press()
            await pilot.pause()
            await pilot.pause()

            log = app.screen.query_one("#query-result", RichLog)
            lines = [str(line) for line in log.lines]
            text = "\n".join(lines)
            assert "NFSe_test_abc" in text


@pytest.mark.asyncio
async def test_query_error(mock_config):
    """Query error shows error in label."""
    from unittest.mock import patch

    from textual.widgets import Button, Label

    with patch(
        "emissor.services.adn_client.query_nfse",
        side_effect=RuntimeError("NFS-e não encontrada"),
    ):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            app.push_screen(QueryScreen(chave="NFSe_unknown"))
            await pilot.pause()

            app.screen.query_one("#btn-consultar", Button).press()
            await pilot.pause()
            await pilot.pause()

            error = app.screen.query_one("#error-label", Label)
            assert "Erro" in error.render().plain


@pytest.mark.asyncio
async def test_query_input_submitted(mock_config):
    """Pressing Enter in input triggers query."""
    from unittest.mock import patch

    from textual.widgets import Input, Label

    with patch(
        "emissor.services.adn_client.query_nfse",
        side_effect=RuntimeError("not found"),
    ):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            app.push_screen(QueryScreen(chave="NFSe_enter_test"))
            await pilot.pause()

            inp = app.screen.query_one("#chave-input", Input)
            inp.focus()
            await pilot.press("enter")
            await pilot.pause()
            await pilot.pause()

            error = app.screen.query_one("#error-label", Label)
            assert "Erro" in error.render().plain


@pytest.mark.asyncio
async def test_query_close_button(mock_config):
    """Clicking close button pops screen."""
    from textual.widgets import Button

    from emissor.tui.screens.dashboard import DashboardScreen

    app = EmissorApp(env="homologacao")
    async with app.run_test() as pilot:
        app.push_screen(QueryScreen(chave="test"))
        await pilot.pause()

        app.screen.query_one("#btn-voltar", Button).press()
        await pilot.pause()

        assert isinstance(app.screen, DashboardScreen)


@pytest.mark.asyncio
async def test_query_modal_close_button(mock_config):
    """Clicking X button pops screen."""
    from textual.widgets import Button

    from emissor.tui.screens.dashboard import DashboardScreen

    app = EmissorApp(env="homologacao")
    async with app.run_test() as pilot:
        app.push_screen(QueryScreen(chave="test"))
        await pilot.pause()

        app.screen.query_one("#btn-modal-close", Button).press()
        await pilot.pause()

        assert isinstance(app.screen, DashboardScreen)
