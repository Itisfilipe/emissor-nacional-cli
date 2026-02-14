from __future__ import annotations

import pytest

from emissor.tui.app import EmissorApp
from emissor.tui.screens.download_pdf import DownloadPdfScreen, _unique_path


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


# --- _unique_path tests ---


def test_unique_path_no_conflict(tmp_path):
    target = tmp_path / "file.pdf"
    assert _unique_path(target) == target


def test_unique_path_single_conflict(tmp_path):
    target = tmp_path / "file.pdf"
    target.write_bytes(b"existing")
    result = _unique_path(target)
    assert result == tmp_path / "file_1.pdf"


def test_unique_path_multiple_conflicts(tmp_path):
    target = tmp_path / "file.pdf"
    target.write_bytes(b"existing")
    (tmp_path / "file_1.pdf").write_bytes(b"existing")
    (tmp_path / "file_2.pdf").write_bytes(b"existing")
    result = _unique_path(target)
    assert result == tmp_path / "file_3.pdf"


@pytest.mark.asyncio
async def test_download_success(mock_config, tmp_path):
    """Successful download writes PDF file and shows success."""
    from unittest.mock import patch

    from textual.widgets import Button, Input, Label

    output_path = str(tmp_path / "test_download.pdf")

    with patch(
        "emissor.services.adn_client.download_danfse",
        return_value=b"%PDF-fake-content",
    ):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            app.push_screen(DownloadPdfScreen(chave="NFSe_dl_test"))
            await pilot.pause()

            app.screen.query_one("#output-input", Input).value = output_path
            app.screen.query_one("#btn-baixar", Button).press()
            await pilot.pause()
            await pilot.pause()

            status = app.screen.query_one("#status-label", Label)
            text = status.render().plain
            assert "salvo" in text.lower() or "PDF" in text

            from pathlib import Path

            assert Path(output_path).exists()
            assert Path(output_path).read_bytes() == b"%PDF-fake-content"


@pytest.mark.asyncio
async def test_download_error(mock_config):
    """Download error shows error in label."""
    from unittest.mock import patch

    from textual.widgets import Button, Label

    with patch(
        "emissor.services.adn_client.download_danfse",
        side_effect=RuntimeError("Download failed"),
    ):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            app.push_screen(DownloadPdfScreen(chave="NFSe_err_test"))
            await pilot.pause()

            app.screen.query_one("#btn-baixar", Button).press()
            await pilot.pause()
            await pilot.pause()

            error = app.screen.query_one("#error-label", Label)
            assert "Erro" in error.render().plain


@pytest.mark.asyncio
async def test_download_empty_chave_shows_error(mock_config):
    """Clicking Baixar with empty chave shows error."""
    from textual.widgets import Button, Label

    app = EmissorApp(env="homologacao")
    async with app.run_test() as pilot:
        app.push_screen(DownloadPdfScreen(chave=""))
        await pilot.pause()

        app.screen.query_one("#btn-baixar", Button).press()
        await pilot.pause()

        error = app.screen.query_one("#error-label", Label)
        assert "chave" in error.render().plain.lower()


@pytest.mark.asyncio
async def test_download_empty_output_uses_chave(mock_config, tmp_path):
    """When output is empty, defaults to {chave}.pdf."""
    from unittest.mock import patch

    from textual.widgets import Button, Input

    with (
        patch(
            "emissor.services.adn_client.download_danfse",
            return_value=b"%PDF-content",
        ),
        patch("emissor.tui.screens.download_pdf.Path") as MockPath,
    ):
        mock_path_instance = MockPath.return_value
        mock_path_instance.exists.return_value = False
        mock_path_instance.write_bytes = lambda x: None

        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            app.push_screen(DownloadPdfScreen(chave="NFSe_auto_name"))
            await pilot.pause()

            # Clear the output field so it uses default
            app.screen.query_one("#output-input", Input).value = ""
            app.screen.query_one("#btn-baixar", Button).press()
            await pilot.pause()
            await pilot.pause()


@pytest.mark.asyncio
async def test_download_input_submitted(mock_config):
    """Pressing Enter in input triggers download."""
    from unittest.mock import patch

    from textual.widgets import Input, Label

    with patch(
        "emissor.services.adn_client.download_danfse",
        side_effect=RuntimeError("fail"),
    ):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            app.push_screen(DownloadPdfScreen(chave="NFSe_enter"))
            await pilot.pause()

            inp = app.screen.query_one("#chave-input", Input)
            inp.focus()
            await pilot.press("enter")
            await pilot.pause()
            await pilot.pause()

            error = app.screen.query_one("#error-label", Label)
            assert "Erro" in error.render().plain


@pytest.mark.asyncio
async def test_download_close_button(mock_config):
    """Clicking close button pops screen."""
    from textual.widgets import Button

    from emissor.tui.screens.dashboard import DashboardScreen

    app = EmissorApp(env="homologacao")
    async with app.run_test() as pilot:
        app.push_screen(DownloadPdfScreen(chave="test"))
        await pilot.pause()

        app.screen.query_one("#btn-voltar", Button).press()
        await pilot.pause()

        assert isinstance(app.screen, DashboardScreen)


@pytest.mark.asyncio
async def test_download_modal_close(mock_config):
    """Clicking X button pops screen."""
    from textual.widgets import Button

    from emissor.tui.screens.dashboard import DashboardScreen

    app = EmissorApp(env="homologacao")
    async with app.run_test() as pilot:
        app.push_screen(DownloadPdfScreen(chave="test"))
        await pilot.pause()

        app.screen.query_one("#btn-modal-close", Button).press()
        await pilot.pause()

        assert isinstance(app.screen, DashboardScreen)
