from __future__ import annotations

import pytest

from emissor.tui.app import EmissorApp
from emissor.tui.screens.dashboard import DashboardScreen
from emissor.tui.screens.help import HelpScreen


@pytest.mark.asyncio
async def test_help_screen_opens(mock_config):
    app = EmissorApp(env="homologacao")
    async with app.run_test() as pilot:
        await pilot.press("h")
        assert isinstance(app.screen, HelpScreen)


@pytest.mark.asyncio
async def test_help_screen_closes_on_escape(mock_config):
    app = EmissorApp(env="homologacao")
    async with app.run_test() as pilot:
        await pilot.press("h")
        assert isinstance(app.screen, HelpScreen)
        await pilot.press("escape")
        assert isinstance(app.screen, DashboardScreen)


@pytest.mark.asyncio
async def test_help_screen_closes_on_button(mock_config):
    from textual.widgets import Button

    app = EmissorApp(env="homologacao")
    async with app.run_test() as pilot:
        await pilot.press("h")
        assert isinstance(app.screen, HelpScreen)
        app.screen.query_one("#btn-voltar", Button).press()
        await pilot.pause()
        assert isinstance(app.screen, DashboardScreen)
