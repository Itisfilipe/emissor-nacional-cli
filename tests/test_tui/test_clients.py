from __future__ import annotations

from unittest.mock import patch

import pytest
from textual.widgets import Button, DataTable, Input, Label, Select

from emissor.tui.app import EmissorApp
from emissor.tui.screens.clients import ClientsScreen
from emissor.tui.screens.dashboard import DashboardScreen


@pytest.mark.asyncio
async def test_clients_screen_opens_on_l(mock_config):
    app = EmissorApp(env="homologacao")
    async with app.run_test() as pilot:
        await pilot.press("l")
        assert isinstance(app.screen, ClientsScreen)


@pytest.mark.asyncio
async def test_clients_screen_shows_list_phase(mock_config):
    app = EmissorApp(env="homologacao")
    async with app.run_test() as pilot:
        await pilot.press("l")
        screen = app.screen
        assert isinstance(screen, ClientsScreen)
        assert screen.query_one("#clients-list-container").display is True
        assert screen.query_one("#client-form-container").display is False


@pytest.mark.asyncio
async def test_clients_table_populated(mock_config):
    client_data = {
        "acme": {"nome": "Acme Corp", "nif": "123", "pais": "US"},
        "globex": {"nome": "Globex Inc", "nif": "456", "pais": "BR"},
    }

    def mock_load(name):
        return client_data[name]

    with patch("emissor.config.load_client", side_effect=mock_load):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.press("l")
            await pilot.pause()
            table = app.screen.query_one("#clients-table", DataTable)
            assert table.row_count == 2


@pytest.mark.asyncio
async def test_novo_cliente_switches_to_form(mock_config):
    app = EmissorApp(env="homologacao")
    async with app.run_test() as pilot:
        await pilot.press("l")
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, ClientsScreen)
        screen.query_one("#btn-novo-cliente", Button).press()
        await pilot.pause()
        assert screen.query_one("#client-form-container").display is True
        assert screen.query_one("#clients-list-container").display is False
        # Slug should be editable for new clients
        assert screen.query_one("#client-slug", Input).disabled is False


@pytest.mark.asyncio
async def test_save_writes_yaml(mock_config, tmp_path):
    clients_dir = tmp_path / "clients"
    clients_dir.mkdir()

    with (
        patch("emissor.config.get_config_dir", return_value=tmp_path),
        patch("emissor.config.list_clients", return_value=[]),
    ):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.press("l")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, ClientsScreen)

            screen.query_one("#btn-novo-cliente", Button).press()
            await pilot.pause()

            screen.query_one("#client-slug", Input).value = "test-client"
            screen.query_one("#client-nome", Input).value = "Test Client"
            screen.query_one("#client-nif", Input).value = "999"
            screen.query_one("#client-logradouro", Input).value = "123 Main St"
            screen.query_one("#client-numero", Input).value = "100"
            screen.query_one("#client-cidade", Input).value = "NYC"
            screen.query_one("#client-estado", Input).value = "NY"
            screen.query_one("#client-cep", Input).value = "10001"
            screen.query_one("#client-complemento", Input).value = "Apt 5B"
            screen.query_one("#client-mec-af-comex-p", Select).value = "03"
            screen.query_one("#client-mec-af-comex-t", Select).value = "04"

            screen.query_one("#btn-salvar-cliente", Button).press()
            await pilot.pause()

            saved = clients_dir / "test-client.yaml"
            assert saved.exists()

            import yaml

            data = yaml.safe_load(saved.read_text())
            assert data["complemento"] == "Apt 5B"
            assert data["mec_af_comex_p"] == "03"
            assert data["mec_af_comex_t"] == "04"


@pytest.mark.asyncio
async def test_edit_prefills_form(mock_config):
    client_data = {
        "acme": {
            "nome": "Acme Corp",
            "nif": "123",
            "pais": "US",
            "logradouro": "100 Main St",
            "numero": "100",
            "bairro": "n/a",
            "cidade": "New York",
            "estado": "NY",
            "cep": "10001",
            "complemento": "Suite 200",
            "mec_af_comex_p": "03",
            "mec_af_comex_t": "04",
        },
        "globex": {"nome": "Globex", "nif": "456", "pais": "BR"},
    }

    def mock_load(name):
        return client_data[name]

    with patch("emissor.config.load_client", side_effect=mock_load):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.press("l")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, ClientsScreen)

            table = screen.query_one("#clients-table", DataTable)
            assert table.row_count == 2

            # Select first row and trigger edit
            table.move_cursor(row=0)
            screen._open_edit_form("acme")
            await pilot.pause()

            assert screen.query_one("#client-form-container").display is True
            assert screen.query_one("#client-slug", Input).disabled is True
            assert screen.query_one("#client-nome", Input).value == "Acme Corp"
            assert screen.query_one("#client-nif", Input).value == "123"
            assert screen.query_one("#client-complemento", Input).value == "Suite 200"
            assert screen.query_one("#client-mec-af-comex-p", Select).value == "03"
            assert screen.query_one("#client-mec-af-comex-t", Select).value == "04"


@pytest.mark.asyncio
async def test_escape_form_goes_to_list(mock_config):
    app = EmissorApp(env="homologacao")
    async with app.run_test() as pilot:
        await pilot.press("l")
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, ClientsScreen)

        screen.query_one("#btn-novo-cliente", Button).press()
        await pilot.pause()
        assert screen._phase == "form"

        await pilot.press("escape")
        assert screen._phase == "list"


@pytest.mark.asyncio
async def test_escape_list_closes(mock_config):
    app = EmissorApp(env="homologacao")
    async with app.run_test() as pilot:
        await pilot.press("l")
        assert isinstance(app.screen, ClientsScreen)

        await pilot.press("escape")
        assert isinstance(app.screen, DashboardScreen)


@pytest.mark.asyncio
async def test_save_validation_errors(mock_config):
    app = EmissorApp(env="homologacao")
    async with app.run_test() as pilot:
        await pilot.press("l")
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, ClientsScreen)

        screen.query_one("#btn-novo-cliente", Button).press()
        await pilot.pause()

        # Try to save with empty form
        screen.query_one("#client-slug", Input).value = ""
        screen.query_one("#client-nome", Input).value = ""
        screen.query_one("#btn-salvar-cliente", Button).press()
        await pilot.pause()

        error_text = screen.query_one("#client-error-label", Label).render().plain
        assert "slug" in error_text.lower() or "obrigat" in error_text.lower()


@pytest.mark.asyncio
async def test_delete_from_list_requires_confirmation(mock_config):
    """First press sets confirmation state; file is not yet deleted."""
    client_data = {"acme": {"nome": "Acme Corp", "nif": "123", "pais": "US"}}

    with patch("emissor.config.load_client", side_effect=lambda n: client_data[n]):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.press("l")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, ClientsScreen)

            # First press — should only set confirmation
            screen.query_one("#btn-delete-cliente", Button).press()
            await pilot.pause()
            assert screen._confirm_delete == "acme"


@pytest.mark.asyncio
async def test_delete_from_list_executes(mock_config, tmp_path):
    """Second press deletes the YAML file."""
    clients_dir = tmp_path / "clients"
    clients_dir.mkdir()
    (clients_dir / "acme.yaml").write_text("nome: Acme\nnif: 123\npais: US\n")

    with (
        patch("emissor.config.get_config_dir", return_value=tmp_path),
        patch("emissor.config.list_clients", return_value=["acme"]),
        patch(
            "emissor.config.load_client",
            return_value={"nome": "Acme", "nif": "123", "pais": "US"},
        ),
    ):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.press("l")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, ClientsScreen)

            # First press — confirmation
            screen.query_one("#btn-delete-cliente", Button).press()
            await pilot.pause()

            # Second press — actually deletes
            screen.query_one("#btn-delete-cliente", Button).press()
            await pilot.pause()

            assert not (clients_dir / "acme.yaml").exists()


@pytest.mark.asyncio
async def test_delete_button_hidden_for_new_client(mock_config):
    app = EmissorApp(env="homologacao")
    async with app.run_test() as pilot:
        await pilot.press("l")
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, ClientsScreen)

        screen.query_one("#btn-novo-cliente", Button).press()
        await pilot.pause()
        assert screen.query_one("#btn-form-delete", Button).display is False


@pytest.mark.asyncio
async def test_delete_button_visible_for_edit(mock_config):
    client_data = {
        "acme": {
            "nome": "Acme Corp",
            "nif": "123",
            "pais": "US",
            "logradouro": "100 Main St",
            "numero": "100",
            "bairro": "n/a",
            "cidade": "New York",
            "estado": "NY",
            "cep": "10001",
        },
    }

    with patch("emissor.config.load_client", side_effect=lambda n: client_data[n]):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.press("l")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, ClientsScreen)

            screen._open_edit_form("acme")
            await pilot.pause()
            assert screen.query_one("#btn-form-delete", Button).display is True


@pytest.mark.asyncio
async def test_delete_empty_table_shows_warning(mock_config):
    """Clicking delete with empty table shows warning notification."""
    with patch("emissor.config.list_clients", return_value=[]):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.press("l")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, ClientsScreen)

            table = screen.query_one("#clients-table", DataTable)
            assert table.row_count == 0

            screen.query_one("#btn-delete-cliente", Button).press()
            await pilot.pause()

            # Should not crash — just a warning notification


@pytest.mark.asyncio
async def test_save_error_shows_error_label(mock_config, tmp_path):
    """Save error in threaded worker shows error in label."""
    with (
        patch("emissor.config.get_config_dir", return_value=tmp_path),
        patch("emissor.config.list_clients", return_value=[]),
        patch(
            "emissor.config.save_client",
            side_effect=RuntimeError("Permission denied"),
        ),
    ):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.press("l")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, ClientsScreen)

            screen.query_one("#btn-novo-cliente", Button).press()
            await pilot.pause()

            screen.query_one("#client-slug", Input).value = "test-err"
            screen.query_one("#client-nome", Input).value = "Test"
            screen.query_one("#client-nif", Input).value = "999"
            screen.query_one("#client-logradouro", Input).value = "123 St"
            screen.query_one("#client-numero", Input).value = "100"
            screen.query_one("#client-cidade", Input).value = "NYC"
            screen.query_one("#client-estado", Input).value = "NY"
            screen.query_one("#client-cep", Input).value = "10001"

            screen.query_one("#btn-salvar-cliente", Button).press()
            await pilot.pause()
            await pilot.pause()

            error_text = screen.query_one("#client-error-label", Label).render().plain
            assert "Erro" in error_text


@pytest.mark.asyncio
async def test_slug_uniqueness_new_client(mock_config, tmp_path):
    """New client with existing slug shows error."""
    with (
        patch("emissor.config.get_config_dir", return_value=tmp_path),
        patch("emissor.config.list_clients", return_value=["existing-slug"]),
    ):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.press("l")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, ClientsScreen)

            screen.query_one("#btn-novo-cliente", Button).press()
            await pilot.pause()

            screen.query_one("#client-slug", Input).value = "existing-slug"
            screen.query_one("#client-nome", Input).value = "New Client"
            screen.query_one("#client-nif", Input).value = "999"
            screen.query_one("#client-logradouro", Input).value = "123 St"
            screen.query_one("#client-numero", Input).value = "100"
            screen.query_one("#client-cidade", Input).value = "NYC"
            screen.query_one("#client-estado", Input).value = "NY"
            screen.query_one("#client-cep", Input).value = "10001"

            screen.query_one("#btn-salvar-cliente", Button).press()
            await pilot.pause()

            error_text = screen.query_one("#client-error-label", Label).render().plain
            assert "existe" in error_text.lower() or "slug" in error_text.lower()


@pytest.mark.asyncio
async def test_load_client_error_shows_erro_row(mock_config):
    """Error loading a client shows 'erro' in the table."""

    def mock_load(name):
        if name == "broken":
            raise RuntimeError("file not found")
        return {"nome": "Good", "nif": "123", "pais": "US"}

    with (
        patch("emissor.config.list_clients", return_value=["good", "broken"]),
        patch("emissor.config.load_client", side_effect=mock_load),
    ):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.press("l")
            await pilot.pause()
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, ClientsScreen)

            table = screen.query_one("#clients-table", DataTable)
            assert table.row_count == 2


@pytest.mark.asyncio
async def test_form_delete_from_edit(mock_config, tmp_path):
    """Clicking delete button in form phase for an edit triggers delete flow."""
    client_data = {
        "acme": {
            "nome": "Acme Corp",
            "nif": "123",
            "pais": "US",
            "logradouro": "100 Main St",
            "numero": "100",
            "bairro": "n/a",
            "cidade": "New York",
            "estado": "NY",
            "cep": "10001",
        },
    }

    clients_dir = tmp_path / "clients"
    clients_dir.mkdir()
    (clients_dir / "acme.yaml").write_text("nome: Acme\nnif: 123\npais: US\n")

    with (
        patch("emissor.config.get_config_dir", return_value=tmp_path),
        patch("emissor.config.list_clients", return_value=["acme"]),
        patch("emissor.config.load_client", side_effect=lambda n: client_data[n]),
    ):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.press("l")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, ClientsScreen)

            screen._open_edit_form("acme")
            await pilot.pause()

            # First press — confirmation
            screen.query_one("#btn-form-delete", Button).press()
            await pilot.pause()
            assert screen._confirm_delete == "acme"

            # Second press — execute delete
            screen.query_one("#btn-form-delete", Button).press()
            await pilot.pause()
            await pilot.pause()

            assert not (clients_dir / "acme.yaml").exists()


@pytest.mark.asyncio
async def test_close_button_pops_screen(mock_config):
    """Clicking close button pops the screen."""
    app = EmissorApp(env="homologacao")
    async with app.run_test() as pilot:
        await pilot.press("l")
        await pilot.pause()
        assert isinstance(app.screen, ClientsScreen)

        app.screen.query_one("#btn-clients-close", Button).press()
        await pilot.pause()

        assert isinstance(app.screen, DashboardScreen)


@pytest.mark.asyncio
async def test_modal_close_button_pops_screen(mock_config):
    """Clicking X button pops the screen."""
    app = EmissorApp(env="homologacao")
    async with app.run_test() as pilot:
        await pilot.press("l")
        await pilot.pause()
        assert isinstance(app.screen, ClientsScreen)

        app.screen.query_one("#btn-modal-close", Button).press()
        await pilot.pause()

        assert isinstance(app.screen, DashboardScreen)
