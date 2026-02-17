from __future__ import annotations

from unittest.mock import patch

import pytest

from emissor.tui.app import EmissorApp
from emissor.tui.screens.dashboard import DashboardScreen
from emissor.tui.screens.validate import ValidateScreen


@pytest.mark.asyncio
async def test_validate_screen_opens(mock_config):
    app = EmissorApp(env="homologacao")
    async with app.run_test() as pilot:
        await pilot.press("v")
        assert isinstance(app.screen, ValidateScreen)


@pytest.mark.asyncio
async def test_validate_screen_closes_on_escape(mock_config):
    app = EmissorApp(env="homologacao")
    async with app.run_test() as pilot:
        await pilot.press("v")
        assert isinstance(app.screen, ValidateScreen)
        await pilot.press("escape")
        assert isinstance(app.screen, DashboardScreen)


@pytest.mark.asyncio
async def test_validate_screen_closes_on_button(mock_config):
    from textual.widgets import Button

    app = EmissorApp(env="homologacao")
    async with app.run_test() as pilot:
        await pilot.press("v")
        assert isinstance(app.screen, ValidateScreen)
        app.screen.query_one("#btn-voltar", Button).press()
        await pilot.pause()
        assert isinstance(app.screen, DashboardScreen)


@pytest.mark.asyncio
async def test_validate_connectivity_success(mock_config):
    """Mocked connectivity success shows OK in output."""
    from textual.widgets import RichLog

    with (
        patch("emissor.services.adn_client.check_connectivity"),
        patch("emissor.services.sefin_client.check_sefin_connectivity"),
    ):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.press("v")
            await pilot.pause()
            log = app.screen.query_one("#validation-output", RichLog)
            # Wait for the threaded worker to complete
            await pilot.pause()
            await pilot.pause()
            lines = [str(line) for line in log.lines]
            text = "\n".join(lines)
            assert "Conectividade ADN" in text


@pytest.mark.asyncio
async def test_validate_connectivity_error(mock_config):
    """Mocked connectivity failure shows ERRO in output."""
    from textual.widgets import RichLog

    with (
        patch(
            "emissor.services.adn_client.check_connectivity",
            side_effect=RuntimeError("Connection refused"),
        ),
        patch("emissor.services.sefin_client.check_sefin_connectivity"),
    ):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.press("v")
            await pilot.pause()
            await pilot.pause()
            await pilot.pause()
            log = app.screen.query_one("#validation-output", RichLog)
            lines = [str(line) for line in log.lines]
            text = "\n".join(lines)
            assert "ERRO" in text
            assert "Conectividade ADN" in text


@pytest.mark.asyncio
async def test_validate_cert_not_configured(mock_config):
    """Missing cert env vars shows ERRO for certificate."""
    from textual.widgets import RichLog

    with (
        patch("emissor.config.get_cert_path", side_effect=KeyError("CERT_PFX_PATH")),
        patch("emissor.services.adn_client.check_connectivity"),
        patch("emissor.services.sefin_client.check_sefin_connectivity"),
    ):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.press("v")
            await pilot.pause()
            await pilot.pause()
            await pilot.pause()
            log = app.screen.query_one("#validation-output", RichLog)
            lines = [str(line) for line in log.lines]
            text = "\n".join(lines)
            assert "ERRO" in text
            assert "CERT_PFX_PATH" in text or "não definidos" in text


@pytest.mark.asyncio
async def test_validate_client_with_error(mock_config):
    """Invalid client data shows ERRO in validation output."""
    from textual.widgets import RichLog

    def mock_load(name):
        if name == "bad-client":
            raise RuntimeError("Invalid YAML")
        return {
            "nif": "123",
            "nome": "Good",
            "pais": "US",
            "logradouro": "St",
            "numero": "1",
            "bairro": "n/a",
            "cidade": "NYC",
            "estado": "NY",
            "cep": "10001",
        }

    with (
        patch("emissor.config.list_clients", return_value=["good-client", "bad-client"]),
        patch("emissor.config.load_client", side_effect=mock_load),
        patch("emissor.services.adn_client.check_connectivity"),
        patch("emissor.services.sefin_client.check_sefin_connectivity"),
    ):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.press("v")
            await pilot.pause()
            await pilot.pause()
            await pilot.pause()
            log = app.screen.query_one("#validation-output", RichLog)
            lines = [str(line) for line in log.lines]
            text = "\n".join(lines)
            assert "ERRO" in text
            assert "bad-client" in text


@pytest.mark.asyncio
async def test_validate_no_clients_warning(mock_config):
    """No clients configured shows AVISO."""
    from textual.widgets import RichLog

    with (
        patch("emissor.config.list_clients", return_value=[]),
        patch("emissor.services.adn_client.check_connectivity"),
        patch("emissor.services.sefin_client.check_sefin_connectivity"),
    ):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.press("v")
            await pilot.pause()
            await pilot.pause()
            await pilot.pause()
            log = app.screen.query_one("#validation-output", RichLog)
            lines = [str(line) for line in log.lines]
            text = "\n".join(lines)
            assert "AVISO" in text or "Nenhum" in text


@pytest.mark.asyncio
async def test_validate_all_ok_notification(mock_config):
    """When everything is OK, notification says 'tudo OK'."""
    from textual.widgets import RichLog

    def mock_load(name):
        return {
            "nif": "123",
            "nome": "Good",
            "pais": "US",
            "logradouro": "St",
            "numero": "1",
            "bairro": "n/a",
            "cidade": "NYC",
            "estado": "NY",
            "cep": "10001",
        }

    with (
        patch("emissor.config.load_client", side_effect=mock_load),
        patch("emissor.services.adn_client.check_connectivity"),
        patch("emissor.services.sefin_client.check_sefin_connectivity"),
    ):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.press("v")
            await pilot.pause()
            await pilot.pause()
            await pilot.pause()
            log = app.screen.query_one("#validation-output", RichLog)
            lines = [str(line) for line in log.lines]
            text = "\n".join(lines)
            # All checks should be OK, no ERRO
            assert "OK" in text
            assert "ERRO" not in text


@pytest.mark.asyncio
async def test_validate_modal_close_button(mock_config):
    """Clicking X button pops screen."""
    from textual.widgets import Button

    app = EmissorApp(env="homologacao")
    async with app.run_test() as pilot:
        await pilot.press("v")
        assert isinstance(app.screen, ValidateScreen)
        app.screen.query_one("#btn-modal-close", Button).press()
        await pilot.pause()
        assert isinstance(app.screen, DashboardScreen)


@pytest.mark.asyncio
async def test_validate_emitter_error(mock_config):
    """Emitter config error shows ERRO in output."""
    from textual.widgets import RichLog

    with (
        patch(
            "emissor.config.load_emitter",
            side_effect=RuntimeError("emitter.yaml not found"),
        ),
        patch("emissor.services.adn_client.check_connectivity"),
        patch("emissor.services.sefin_client.check_sefin_connectivity"),
    ):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.press("v")
            await pilot.pause()
            await pilot.pause()
            await pilot.pause()
            log = app.screen.query_one("#validation-output", RichLog)
            lines = [str(line) for line in log.lines]
            text = "\n".join(lines)
            assert "ERRO" in text
            assert "Emitente" in text


@pytest.mark.asyncio
async def test_validate_sefin_success(mock_config):
    """Mocked SEFIN connectivity success shows OK in output."""
    from textual.widgets import RichLog

    with (
        patch("emissor.services.adn_client.check_connectivity"),
        patch("emissor.services.sefin_client.check_sefin_connectivity"),
    ):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.press("v")
            await pilot.pause()
            await pilot.pause()
            await pilot.pause()
            log = app.screen.query_one("#validation-output", RichLog)
            lines = [str(line) for line in log.lines]
            text = "\n".join(lines)
            assert "Conectividade SEFIN" in text
            assert "OK" in text


@pytest.mark.asyncio
async def test_validate_sefin_error(mock_config):
    """Mocked SEFIN connectivity failure shows ERRO in output."""
    from textual.widgets import RichLog

    with (
        patch("emissor.services.adn_client.check_connectivity"),
        patch(
            "emissor.services.sefin_client.check_sefin_connectivity",
            side_effect=RuntimeError("Connection refused"),
        ),
    ):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.press("v")
            await pilot.pause()
            await pilot.pause()
            await pilot.pause()
            log = app.screen.query_one("#validation-output", RichLog)
            lines = [str(line) for line in log.lines]
            text = "\n".join(lines)
            assert "ERRO" in text
            assert "Conectividade SEFIN" in text
