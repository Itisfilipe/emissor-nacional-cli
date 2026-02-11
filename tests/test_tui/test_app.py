from __future__ import annotations

import pytest

from emissor.tui.app import EmissorApp


@pytest.mark.asyncio
async def test_app_launches(mock_config):
    app = EmissorApp(env="homologacao")
    async with app.run_test():
        assert app.title == "Emissor Nacional"


@pytest.mark.asyncio
async def test_app_default_screen_is_dashboard(mock_config):
    from emissor.tui.screens.dashboard import DashboardScreen

    app = EmissorApp(env="homologacao")
    async with app.run_test():
        assert isinstance(app.screen, DashboardScreen)


@pytest.mark.asyncio
async def test_app_stores_env(mock_config):
    app = EmissorApp(env="producao")
    async with app.run_test():
        assert app.env == "producao"
