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
