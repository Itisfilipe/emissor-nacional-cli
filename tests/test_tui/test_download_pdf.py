from __future__ import annotations

import pytest

from emissor.tui.app import EmissorApp
from emissor.tui.screens.download_pdf import DownloadPdfScreen


@pytest.mark.asyncio
async def test_download_pdf_screen_opens(mock_config):
    app = EmissorApp(env="homologacao")
    async with app.run_test() as pilot:
        await pilot.press("p")
        assert isinstance(app.screen, DownloadPdfScreen)


@pytest.mark.asyncio
async def test_download_pdf_pre_fills_chave(mock_config):
    app = EmissorApp(env="homologacao")
    async with app.run_test() as pilot:
        app.push_screen(DownloadPdfScreen(chave="nfse_key_456"))
        await pilot.pause()
        from textual.widgets import Input

        chave_input = app.screen.query_one("#chave-input", Input)
        assert chave_input.value == "nfse_key_456"

        output_input = app.screen.query_one("#output-input", Input)
        assert output_input.value == "nfse_key_456.pdf"


@pytest.mark.asyncio
async def test_download_pdf_escape_goes_back(mock_config):
    from emissor.tui.screens.dashboard import DashboardScreen

    app = EmissorApp(env="homologacao")
    async with app.run_test() as pilot:
        await pilot.press("p")
        assert isinstance(app.screen, DownloadPdfScreen)
        await pilot.press("escape")
        assert isinstance(app.screen, DashboardScreen)
