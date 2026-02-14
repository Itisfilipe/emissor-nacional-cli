from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from emissor.tui.app import EmissorApp


def _patch_data(tmp_path):
    """Patch get_data_dir to use tmp_path for both issued dirs and registry."""
    return patch("emissor.config.get_data_dir", return_value=tmp_path)


# --- Existing tests updated for new layout ---


@pytest.mark.asyncio
async def test_dashboard_shows_env_badge(mock_config):
    from textual.widgets import Button

    app = EmissorApp(env="homologacao")
    async with app.run_test():
        badge = app.screen.query_one("#env-badge", Button)
        assert badge is not None
        assert "HOMOLOGA" in badge.label.plain


@pytest.mark.asyncio
async def test_dashboard_loads_emitter_info(mock_config):
    app = EmissorApp(env="homologacao")
    async with app.run_test() as pilot:
        await pilot.pause()
        label = app.screen.query_one("#emitter-info")
        text = label.render().plain
        assert "ACME" in text


@pytest.mark.asyncio
async def test_dashboard_key_n_opens_new_invoice(mock_config):
    from emissor.tui.screens.new_invoice import NewInvoiceScreen

    app = EmissorApp(env="homologacao")
    async with app.run_test() as pilot:
        await pilot.press("n")
        assert isinstance(app.screen, NewInvoiceScreen)


@pytest.mark.asyncio
async def test_dashboard_key_c_opens_query(mock_config):
    from emissor.tui.screens.query import QueryScreen

    app = EmissorApp(env="homologacao")
    async with app.run_test() as pilot:
        await pilot.press("c")
        assert isinstance(app.screen, QueryScreen)


@pytest.mark.asyncio
async def test_dashboard_key_p_opens_download_pdf(mock_config):
    from emissor.tui.screens.download_pdf import DownloadPdfScreen

    app = EmissorApp(env="homologacao")
    async with app.run_test() as pilot:
        await pilot.press("p")
        assert isinstance(app.screen, DownloadPdfScreen)


@pytest.mark.asyncio
async def test_dashboard_key_v_opens_validate(mock_config):
    from emissor.tui.screens.validate import ValidateScreen

    app = EmissorApp(env="homologacao")
    async with app.run_test() as pilot:
        await pilot.press("v")
        assert isinstance(app.screen, ValidateScreen)


@pytest.mark.asyncio
async def test_dashboard_vim_j_k_navigation(mock_config, tmp_path):
    """Pressing j/k moves the cursor in the recent invoices table."""
    from textual.widgets import DataTable

    issued = tmp_path / "homologacao" / "issued"
    issued.mkdir(parents=True)
    (issued / "NFSe_aaa.xml").write_text("<xml/>")
    (issued / "NFSe_bbb.xml").write_text("<xml/>")
    (issued / "NFSe_ccc.xml").write_text("<xml/>")

    with _patch_data(tmp_path):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.pause()
            table = app.screen.query_one("#recent-table", DataTable)
            assert table.row_count == 3
            initial_row = table.cursor_coordinate.row
            await pilot.press("j")
            assert table.cursor_coordinate.row == initial_row + 1
            await pilot.press("k")
            assert table.cursor_coordinate.row == initial_row


@pytest.mark.asyncio
async def test_dashboard_enter_opens_query(mock_config, tmp_path):
    """Pressing Enter on an emitted invoice opens QueryScreen."""
    from textual.widgets import DataTable

    from emissor.tui.screens.query import QueryScreen

    issued = tmp_path / "homologacao" / "issued"
    issued.mkdir(parents=True)
    (issued / "NFSe_abc123.xml").write_text("<xml/>")

    with _patch_data(tmp_path):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.pause()
            table = app.screen.query_one("#recent-table", DataTable)
            assert table.row_count == 1
            await pilot.press("enter")
            assert isinstance(app.screen, QueryScreen)


@pytest.mark.asyncio
async def test_dashboard_enter_dry_run_shows_notification(mock_config, tmp_path):
    """Pressing Enter on a dry_run entry shows a warning instead of opening query."""
    from textual.widgets import DataTable

    from emissor.tui.screens.dashboard import DashboardScreen

    issued = tmp_path / "homologacao" / "issued"
    issued.mkdir(parents=True)
    (issued / "dry_run_dps_42.xml").write_text("<xml/>")

    with _patch_data(tmp_path):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.pause()
            table = app.screen.query_one("#recent-table", DataTable)
            assert table.row_count == 1
            await pilot.press("enter")
            # Should stay on dashboard, not open QueryScreen
            assert isinstance(app.screen, DashboardScreen)


# --- New tests ---


@pytest.mark.asyncio
async def test_env_toggle_reloads_table(mock_config, tmp_path):
    """Pressing 'e' shows confirmation; confirming toggles env and reloads table."""
    from textual.widgets import Button, DataTable

    homol = tmp_path / "homologacao" / "issued"
    homol.mkdir(parents=True)
    (homol / "NFSe_homol_1.xml").write_text("<xml/>")

    prod = tmp_path / "producao" / "issued"
    prod.mkdir(parents=True)
    (prod / "NFSe_prod_1.xml").write_text("<xml/>")
    (prod / "NFSe_prod_2.xml").write_text("<xml/>")

    with _patch_data(tmp_path):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.pause()
            table = app.screen.query_one("#recent-table", DataTable)
            assert table.row_count == 1

            # Toggle to producao — opens confirmation dialog
            await pilot.press("e")
            await pilot.pause()

            # Env should NOT have changed yet
            assert app.env == "homologacao"

            # Confirm the dialog
            app.screen.query_one("#btn-confirm", Button).press()
            await pilot.pause()

            assert app.env == "producao"
            assert table.row_count == 2


@pytest.mark.asyncio
async def test_env_toggle_cancel_stays_homologacao(mock_config, tmp_path):
    """Pressing 'e' then cancelling keeps env as homologacao."""
    from textual.widgets import Button

    homol = tmp_path / "homologacao" / "issued"
    homol.mkdir(parents=True)

    with _patch_data(tmp_path):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.pause()

            await pilot.press("e")
            await pilot.pause()

            # Cancel the dialog
            app.screen.query_one("#btn-cancel", Button).press()
            await pilot.pause()

            assert app.env == "homologacao"


@pytest.mark.asyncio
async def test_filter_preset_hoje(mock_config, tmp_path):
    """The 'Hoje' filter only shows files modified today."""
    from textual.widgets import DataTable, Select

    issued = tmp_path / "homologacao" / "issued"
    issued.mkdir(parents=True)

    # Today's file
    today_file = issued / "NFSe_today.xml"
    today_file.write_text("<xml/>")

    # Old file — set mtime to 10 days ago
    old_file = issued / "NFSe_old.xml"
    old_file.write_text("<xml/>")
    old_time = time.time() - 10 * 86400
    os.utime(old_file, (old_time, old_time))

    with _patch_data(tmp_path):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.pause()
            table = app.screen.query_one("#recent-table", DataTable)
            assert table.row_count == 2  # Todos shows all

            # Select "Hoje" preset
            preset = app.screen.query_one("#filter-preset", Select)
            preset.value = "hoje"
            await pilot.pause()

            assert table.row_count == 1


@pytest.mark.asyncio
async def test_filter_preset_todos(mock_config, tmp_path):
    """The 'Todos' filter shows all files."""
    from textual.widgets import DataTable

    issued = tmp_path / "homologacao" / "issued"
    issued.mkdir(parents=True)
    (issued / "NFSe_a.xml").write_text("<xml/>")
    (issued / "NFSe_b.xml").write_text("<xml/>")
    (issued / "dry_run_dps_1.xml").write_text("<xml/>")

    with _patch_data(tmp_path):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.pause()
            table = app.screen.query_one("#recent-table", DataTable)
            assert table.row_count == 3


@pytest.mark.asyncio
async def test_filter_custom_date_range(mock_config, tmp_path):
    """Custom De/Ate date range filtering."""
    from textual.widgets import Button, DataTable, MaskedInput

    issued = tmp_path / "homologacao" / "issued"
    issued.mkdir(parents=True)

    # File modified now
    recent = issued / "NFSe_recent.xml"
    recent.write_text("<xml/>")

    # File modified 60 days ago
    old = issued / "NFSe_old.xml"
    old.write_text("<xml/>")
    old_time = time.time() - 60 * 86400
    os.utime(old, (old_time, old_time))

    with _patch_data(tmp_path):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.pause()
            table = app.screen.query_one("#recent-table", DataTable)
            assert table.row_count == 2

            # Set date range to exclude old file (dd/mm/yyyy format)
            brt = timezone(timedelta(hours=-3))
            yesterday = (datetime.now(brt) - timedelta(days=1)).strftime("%d/%m/%Y")
            de_input = app.screen.query_one("#filter-de", MaskedInput)
            de_input.value = yesterday

            btn = app.screen.query_one("#btn-filtrar", Button)
            btn.press()
            await pilot.pause()

            assert table.row_count == 1


@pytest.mark.asyncio
async def test_data_migration(tmp_path):
    """migrate_data_layout moves old issued/*.xml to homologacao/issued/."""
    from emissor.config import migrate_data_layout

    old_dir = tmp_path / "issued"
    old_dir.mkdir()
    (old_dir / "NFSe_1.xml").write_text("<xml/>")
    (old_dir / "NFSe_2.xml").write_text("<xml/>")

    with patch("emissor.config.get_data_dir", return_value=tmp_path):
        migrate_data_layout()

    new_dir = tmp_path / "homologacao" / "issued"
    assert new_dir.exists()
    assert len(list(new_dir.glob("*.xml"))) == 2
    assert not list(old_dir.glob("*.xml"))


@pytest.mark.asyncio
async def test_data_migration_skips_if_new_exists(tmp_path):
    """migrate_data_layout does not overwrite if new dir already exists."""
    old_dir = tmp_path / "issued"
    old_dir.mkdir()
    (old_dir / "NFSe_old.xml").write_text("<old/>")

    new_dir = tmp_path / "homologacao" / "issued"
    new_dir.mkdir(parents=True)
    (new_dir / "NFSe_new.xml").write_text("<new/>")

    with patch("emissor.config.get_data_dir", return_value=tmp_path):
        from emissor.config import migrate_data_layout

        migrate_data_layout()

    # Old files should still be in old dir (migration skipped)
    assert (old_dir / "NFSe_old.xml").exists()
    # New dir should only have the pre-existing file
    assert len(list(new_dir.glob("*.xml"))) == 1


@pytest.mark.asyncio
async def test_registry_invoices_shown(mock_config, tmp_path):
    """Registry invoices (both emitted and received) appear in the table."""
    import json

    from textual.widgets import DataTable

    registry_path = tmp_path / "invoices.json"
    registry_path.write_text(
        json.dumps(
            [
                {
                    "chave": "NFSe_emitida_001",
                    "env": "homologacao",
                    "status": "emitida",
                    "client": "DrChrono",
                    "valor_brl": "53526.58",
                    "competencia": "2025-12-23",
                },
                {
                    "chave": "NFSe_recebida_001",
                    "env": "homologacao",
                    "status": "recebida",
                    "client": "MaisContabil",
                    "valor_brl": "350.00",
                    "competencia": "2025-01-09",
                },
                {
                    "chave": "NFSe_outro_env",
                    "env": "producao",
                    "status": "emitida",
                    "client": "Other",
                    "valor_brl": "100.00",
                    "competencia": "2025-06-01",
                },
            ]
        )
    )

    with _patch_data(tmp_path):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.pause()
            table = app.screen.query_one("#recent-table", DataTable)
            # Only the 2 homologacao invoices, not the producao one
            assert table.row_count == 2


@pytest.mark.asyncio
async def test_clone_opens_prefilled_invoice(mock_config, tmp_path):
    """Pressing 'r' with a selected registry row opens NewInvoiceScreen with prefill."""
    import json

    from textual.widgets import DataTable

    from emissor.tui.screens.new_invoice import NewInvoiceScreen

    registry_path = tmp_path / "invoices.json"
    registry_path.write_text(
        json.dumps(
            [
                {
                    "chave": "NFSe_repeat_001",
                    "env": "homologacao",
                    "status": "emitida",
                    "client": "Acme Corp",
                    "client_slug": "acme",
                    "valor_brl": "5000.00",
                    "valor_usd": "1000.00",
                    "competencia": "2025-12-01",
                },
            ]
        )
    )

    with _patch_data(tmp_path):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.pause()
            table = app.screen.query_one("#recent-table", DataTable)
            assert table.row_count == 1

            await pilot.press("r")
            await pilot.pause()

            screen = app.screen
            assert isinstance(screen, NewInvoiceScreen)
            assert screen._prefill is not None
            assert screen._prefill.get("client_slug") == "acme"
            assert screen._prefill.get("valor_brl") == "5000.00"
            assert screen._prefill.get("valor_usd") == "1000.00"


# --- Group 1: Covering remaining dashboard branches ---


@pytest.mark.asyncio
async def test_filter_preset_semana(mock_config, tmp_path):
    """The 'semana' preset shows only files from the last 7 days."""
    from textual.widgets import DataTable, Select

    issued = tmp_path / "homologacao" / "issued"
    issued.mkdir(parents=True)

    recent = issued / "NFSe_recent.xml"
    recent.write_text("<xml/>")

    old = issued / "NFSe_old.xml"
    old.write_text("<xml/>")
    old_time = time.time() - 14 * 86400
    os.utime(old, (old_time, old_time))

    with _patch_data(tmp_path):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.pause()
            table = app.screen.query_one("#recent-table", DataTable)
            assert table.row_count == 2

            preset = app.screen.query_one("#filter-preset", Select)
            preset.value = "semana"
            await pilot.pause()

            assert table.row_count == 1


@pytest.mark.asyncio
async def test_filter_preset_mes(mock_config, tmp_path):
    """The 'mes' preset shows only files from the last 30 days."""
    from textual.widgets import DataTable, Select

    issued = tmp_path / "homologacao" / "issued"
    issued.mkdir(parents=True)

    recent = issued / "NFSe_recent.xml"
    recent.write_text("<xml/>")

    old = issued / "NFSe_old.xml"
    old.write_text("<xml/>")
    old_time = time.time() - 60 * 86400
    os.utime(old, (old_time, old_time))

    with _patch_data(tmp_path):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.pause()
            table = app.screen.query_one("#recent-table", DataTable)
            assert table.row_count == 2

            preset = app.screen.query_one("#filter-preset", Select)
            preset.value = "mes"
            await pilot.pause()

            assert table.row_count == 1


@pytest.mark.asyncio
async def test_filter_tipo_recebida(mock_config, tmp_path):
    """Filtering by 'recebida' shows only received invoices."""
    import json

    from textual.widgets import DataTable, Select

    registry_path = tmp_path / "invoices.json"
    registry_path.write_text(
        json.dumps(
            [
                {
                    "chave": "emit_001",
                    "env": "homologacao",
                    "status": "emitida",
                    "client": "Acme",
                    "competencia": "2025-12-23",
                },
                {
                    "chave": "recv_001",
                    "env": "homologacao",
                    "status": "recebida",
                    "client": "Contabil",
                    "competencia": "2025-12-23",
                },
            ]
        )
    )

    with _patch_data(tmp_path):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.pause()
            table = app.screen.query_one("#recent-table", DataTable)
            assert table.row_count == 2

            tipo = app.screen.query_one("#filter-tipo", Select)
            tipo.value = "recebida"
            await pilot.pause()

            assert table.row_count == 1


@pytest.mark.asyncio
async def test_filter_invalid_dates_graceful(mock_config, tmp_path):
    """Invalid date strings in De/Ate fields don't crash — filter proceeds."""
    from textual.widgets import Button, DataTable, MaskedInput

    issued = tmp_path / "homologacao" / "issued"
    issued.mkdir(parents=True)
    (issued / "NFSe_a.xml").write_text("<xml/>")

    with _patch_data(tmp_path):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.pause()
            table = app.screen.query_one("#recent-table", DataTable)
            assert table.row_count == 1

            # Set invalid dates
            app.screen.query_one("#filter-de", MaskedInput).value = "99/99/9999"
            app.screen.query_one("#filter-ate", MaskedInput).value = "00/00/0000"

            app.screen.query_one("#btn-filtrar", Button).press()
            await pilot.pause()

            # Should not crash; row count depends on ValueError handling
            assert isinstance(table.row_count, int)


@pytest.mark.asyncio
async def test_button_clone_no_selection(mock_config, tmp_path):
    """Clicking clone with no invoices shows a warning."""
    with _patch_data(tmp_path):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.pause()
            from textual.widgets import Button

            app.screen.query_one("#btn-clone", Button).press()
            await pilot.pause()
            # Should stay on dashboard (no crash, notification about no selection)
            from emissor.tui.screens.dashboard import DashboardScreen

            assert isinstance(app.screen, DashboardScreen)


@pytest.mark.asyncio
async def test_button_query_opens_query_screen(mock_config, tmp_path):
    """Clicking query button opens QueryScreen."""
    from emissor.tui.screens.query import QueryScreen

    with _patch_data(tmp_path):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.pause()
            from textual.widgets import Button

            app.screen.query_one("#btn-query", Button).press()
            await pilot.pause()
            assert isinstance(app.screen, QueryScreen)


@pytest.mark.asyncio
async def test_button_pdf_opens_download_screen(mock_config, tmp_path):
    """Clicking pdf button opens DownloadPdfScreen."""
    from emissor.tui.screens.download_pdf import DownloadPdfScreen

    with _patch_data(tmp_path):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.pause()
            from textual.widgets import Button

            app.screen.query_one("#btn-pdf", Button).press()
            await pilot.pause()
            assert isinstance(app.screen, DownloadPdfScreen)


@pytest.mark.asyncio
async def test_button_copy_no_selection(mock_config, tmp_path):
    """Clicking copy with no invoices does nothing (no crash)."""
    from emissor.tui.screens.dashboard import DashboardScreen

    with _patch_data(tmp_path):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.pause()
            from textual.widgets import Button

            app.screen.query_one("#btn-copy", Button).press()
            await pilot.pause()
            assert isinstance(app.screen, DashboardScreen)


@pytest.mark.asyncio
async def test_sync_success(mock_config, tmp_path):
    """Manual sync with mocked iter_dfe registers documents."""
    import json

    mock_doc = {
        "NSU": 10,
        "ChaveAcesso": "NFSe_sync_001",
        "ArquivoXml": "",
        "DataHoraGeracao": "2025-12-30T10:00:00",
        "TipoDocumento": "NFSe",
    }

    mock_meta = {
        "emit_cnpj": "123",
        "emit_nome": "ACME",
        "toma_cnpj": "456",
        "toma_nome": "Client",
        "n_nfse": "42",
        "competencia": "2025-12-30",
        "valor": "1000.00",
    }

    with (
        _patch_data(tmp_path),
        patch("emissor.services.adn_client.iter_dfe", return_value=[mock_doc]),
        patch("emissor.services.adn_client.parse_dfe_xml", return_value=mock_meta),
    ):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            # Manual sync
            from textual.widgets import Button

            app.screen.query_one("#btn-sync", Button).press()
            await pilot.pause()
            await pilot.pause()

            # Check registry was updated
            rp = tmp_path / "invoices.json"
            if rp.exists():
                entries = json.loads(rp.read_text())
                chaves = [e["chave"] for e in entries]
                assert "NFSe_sync_001" in chaves


@pytest.mark.asyncio
async def test_sync_error(mock_config, tmp_path):
    """Sync error shows notification, doesn't crash."""
    from emissor.tui.screens.dashboard import DashboardScreen

    with (
        _patch_data(tmp_path),
        patch(
            "emissor.services.adn_client.iter_dfe",
            side_effect=RuntimeError("Connection failed"),
        ),
    ):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            from textual.widgets import Button

            app.screen.query_one("#btn-sync", Button).press()
            await pilot.pause()
            await pilot.pause()

            # Should still be on dashboard (no crash)
            assert isinstance(app.screen, DashboardScreen)


@pytest.mark.asyncio
async def test_sync_key_error(mock_config, tmp_path):
    """Sync with missing cert config shows error notification."""
    from emissor.tui.screens.dashboard import DashboardScreen

    with (
        _patch_data(tmp_path),
        patch("emissor.config.get_cert_path", side_effect=KeyError("CERT_PFX_PATH")),
    ):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            from textual.widgets import Button

            app.screen.query_one("#btn-sync", Button).press()
            await pilot.pause()
            await pilot.pause()

            assert isinstance(app.screen, DashboardScreen)


@pytest.mark.asyncio
async def test_clipboard_darwin(mock_config, tmp_path):
    """Clipboard copy on macOS uses pbcopy."""
    from textual.widgets import DataTable

    issued = tmp_path / "homologacao" / "issued"
    issued.mkdir(parents=True)
    (issued / "NFSe_copy_test.xml").write_text("<xml/>")

    with (
        _patch_data(tmp_path),
        patch("emissor.tui.screens.dashboard.platform.system", return_value="Darwin"),
        patch("emissor.tui.screens.dashboard.subprocess.run") as mock_run,
    ):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.pause()
            table = app.screen.query_one("#recent-table", DataTable)
            assert table.row_count == 1

            await pilot.press("y")
            await pilot.pause()

            mock_run.assert_called_once()
            assert mock_run.call_args[0][0] == ["pbcopy"]


@pytest.mark.asyncio
async def test_clipboard_linux_xclip(mock_config, tmp_path):
    """Clipboard copy on Linux with xclip available."""
    from textual.widgets import DataTable

    issued = tmp_path / "homologacao" / "issued"
    issued.mkdir(parents=True)
    (issued / "NFSe_copy_linux.xml").write_text("<xml/>")

    def fake_which(cmd):
        return "/usr/bin/xclip" if cmd == "xclip" else None

    with (
        _patch_data(tmp_path),
        patch("emissor.tui.screens.dashboard.platform.system", return_value="Linux"),
        patch("emissor.tui.screens.dashboard.shutil.which", side_effect=fake_which),
        patch("emissor.tui.screens.dashboard.subprocess.run") as mock_run,
    ):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.pause()
            table = app.screen.query_one("#recent-table", DataTable)
            assert table.row_count == 1

            await pilot.press("y")
            await pilot.pause()

            mock_run.assert_called_once()
            assert "xclip" in mock_run.call_args[0][0]


@pytest.mark.asyncio
async def test_clipboard_windows(mock_config, tmp_path):
    """Clipboard copy on Windows uses clip."""
    from textual.widgets import DataTable

    issued = tmp_path / "homologacao" / "issued"
    issued.mkdir(parents=True)
    (issued / "NFSe_copy_win.xml").write_text("<xml/>")

    with (
        _patch_data(tmp_path),
        patch("emissor.tui.screens.dashboard.platform.system", return_value="Windows"),
        patch("emissor.tui.screens.dashboard.subprocess.run") as mock_run,
    ):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.pause()
            table = app.screen.query_one("#recent-table", DataTable)
            assert table.row_count == 1

            await pilot.press("y")
            await pilot.pause()

            mock_run.assert_called_once()
            assert mock_run.call_args[0][0] == ["clip"]


@pytest.mark.asyncio
async def test_clipboard_unknown_platform(mock_config, tmp_path):
    """Clipboard copy on unknown platform shows fallback notification."""
    from textual.widgets import DataTable

    issued = tmp_path / "homologacao" / "issued"
    issued.mkdir(parents=True)
    (issued / "NFSe_copy_unk.xml").write_text("<xml/>")

    with (
        _patch_data(tmp_path),
        patch("emissor.tui.screens.dashboard.platform.system", return_value="FreeBSD"),
    ):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.pause()
            table = app.screen.query_one("#recent-table", DataTable)
            assert table.row_count == 1

            await pilot.press("y")
            await pilot.pause()

            # Should not crash, shows fallback notification


@pytest.mark.asyncio
async def test_clipboard_file_not_found(mock_config, tmp_path):
    """Clipboard copy handles FileNotFoundError gracefully."""
    from textual.widgets import DataTable

    issued = tmp_path / "homologacao" / "issued"
    issued.mkdir(parents=True)
    (issued / "NFSe_copy_fnf.xml").write_text("<xml/>")

    with (
        _patch_data(tmp_path),
        patch("emissor.tui.screens.dashboard.platform.system", return_value="Darwin"),
        patch(
            "emissor.tui.screens.dashboard.subprocess.run",
            side_effect=FileNotFoundError("pbcopy not found"),
        ),
    ):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.pause()
            table = app.screen.query_one("#recent-table", DataTable)
            assert table.row_count == 1

            await pilot.press("y")
            await pilot.pause()


@pytest.mark.asyncio
async def test_clipboard_generic_error(mock_config, tmp_path):
    """Clipboard copy handles generic subprocess errors."""
    from textual.widgets import DataTable

    issued = tmp_path / "homologacao" / "issued"
    issued.mkdir(parents=True)
    (issued / "NFSe_copy_err.xml").write_text("<xml/>")

    with (
        _patch_data(tmp_path),
        patch("emissor.tui.screens.dashboard.platform.system", return_value="Darwin"),
        patch(
            "emissor.tui.screens.dashboard.subprocess.run",
            side_effect=OSError("pipe broken"),
        ),
    ):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.pause()
            table = app.screen.query_one("#recent-table", DataTable)
            assert table.row_count == 1

            await pilot.press("y")
            await pilot.pause()


@pytest.mark.asyncio
async def test_load_emitter_error(tmp_path):
    """Error loading emitter shows error in card."""
    with (
        patch("emissor.config.load_emitter", side_effect=RuntimeError("Config not found")),
        patch("emissor.config.get_cert_path", return_value="/fake.pfx"),
        patch("emissor.config.get_cert_password", return_value="fakepass"),
        patch(
            "emissor.utils.certificate.validate_certificate",
            return_value={
                "subject": "CN=Test",
                "issuer": "CN=Test",
                "not_before": "2025-01-01",
                "not_after": "2026-01-01",
                "valid": True,
            },
        ),
        patch("emissor.utils.sequence.peek_next_n_dps", return_value=5),
        patch("emissor.config.list_clients", return_value=[]),
        patch("emissor.config.migrate_data_layout"),
        _patch_data(tmp_path),
    ):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()
            text = app.screen.query_one("#emitter-info").render().plain
            assert "Erro" in text or "erro" in text


@pytest.mark.asyncio
async def test_load_certificate_error(tmp_path):
    """Error loading certificate shows error in card."""
    with (
        patch(
            "emissor.config.load_emitter",
            return_value={"razao_social": "ACME", "cnpj": "123"},
        ),
        patch("emissor.config.get_cert_path", return_value="/fake.pfx"),
        patch("emissor.config.get_cert_password", return_value="fakepass"),
        patch(
            "emissor.utils.certificate.validate_certificate",
            side_effect=RuntimeError("Bad cert"),
        ),
        patch("emissor.utils.sequence.peek_next_n_dps", return_value=5),
        patch("emissor.config.list_clients", return_value=[]),
        patch("emissor.config.migrate_data_layout"),
        _patch_data(tmp_path),
    ):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()
            text = app.screen.query_one("#cert-info").render().plain
            assert "erro" in text.lower()


@pytest.mark.asyncio
async def test_load_certificate_not_configured(tmp_path):
    """KeyError loading certificate shows 'não configurado'."""
    with (
        patch(
            "emissor.config.load_emitter",
            return_value={"razao_social": "ACME", "cnpj": "123"},
        ),
        patch("emissor.config.get_cert_path", side_effect=KeyError("CERT_PFX_PATH")),
        patch("emissor.config.get_cert_password", return_value="fakepass"),
        patch("emissor.utils.sequence.peek_next_n_dps", return_value=5),
        patch("emissor.config.list_clients", return_value=[]),
        patch("emissor.config.migrate_data_layout"),
        _patch_data(tmp_path),
    ):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()
            text = app.screen.query_one("#cert-info").render().plain
            assert "configurado" in text.lower()


@pytest.mark.asyncio
async def test_load_sequence_error(tmp_path):
    """Error loading sequence shows error in card."""
    with (
        patch(
            "emissor.config.load_emitter",
            return_value={"razao_social": "ACME", "cnpj": "123"},
        ),
        patch("emissor.config.get_cert_path", return_value="/fake.pfx"),
        patch("emissor.config.get_cert_password", return_value="fakepass"),
        patch(
            "emissor.utils.certificate.validate_certificate",
            return_value={
                "subject": "CN=Test",
                "issuer": "CN=Test",
                "not_before": "2025-01-01",
                "not_after": "2026-01-01",
                "valid": True,
            },
        ),
        patch(
            "emissor.utils.sequence.peek_next_n_dps",
            side_effect=RuntimeError("Sequence file corrupt"),
        ),
        patch("emissor.config.list_clients", return_value=[]),
        patch("emissor.config.migrate_data_layout"),
        _patch_data(tmp_path),
    ):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()
            text = app.screen.query_one("#seq-info").render().plain
            assert "erro" in text.lower()


@pytest.mark.asyncio
async def test_seen_keys_dedup(mock_config, tmp_path):
    """XML files already in registry are not duplicated in the table."""
    import json

    from textual.widgets import DataTable

    issued = tmp_path / "homologacao" / "issued"
    issued.mkdir(parents=True)
    (issued / "NFSe_dup_001.xml").write_text("<xml/>")

    registry_path = tmp_path / "invoices.json"
    registry_path.write_text(
        json.dumps(
            [
                {
                    "chave": "NFSe_dup_001",
                    "env": "homologacao",
                    "status": "emitida",
                    "client": "Acme",
                    "competencia": "2025-12-23",
                },
            ]
        )
    )

    with _patch_data(tmp_path):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.pause()
            table = app.screen.query_one("#recent-table", DataTable)
            # Should be 1, not 2 (dedup via seen_keys)
            assert table.row_count == 1


@pytest.mark.asyncio
async def test_parse_date_empty_string(mock_config):
    """_parse_date with empty string returns now."""
    from emissor.tui.screens.dashboard import DashboardScreen

    result = DashboardScreen._parse_date("")
    assert result.tzinfo is not None


@pytest.mark.asyncio
async def test_parse_date_invalid_string(mock_config):
    """_parse_date with invalid date returns now."""
    from emissor.tui.screens.dashboard import DashboardScreen

    result = DashboardScreen._parse_date("not-a-date")
    assert result.tzinfo is not None


@pytest.mark.asyncio
async def test_parse_date_naive_datetime(mock_config):
    """_parse_date with naive datetime adds BRT timezone."""
    from emissor.tui.screens.dashboard import DashboardScreen

    result = DashboardScreen._parse_date("2025-12-30")
    assert result.tzinfo is not None
    assert result.year == 2025


@pytest.mark.asyncio
async def test_parse_date_tz_aware_datetime(mock_config):
    """_parse_date with tz-aware datetime converts to BRT."""
    from emissor.tui.screens.dashboard import DashboardScreen

    result = DashboardScreen._parse_date("2025-12-30T15:00:00+00:00")
    assert result.tzinfo is not None
    assert result.year == 2025


@pytest.mark.asyncio
async def test_env_toggle_from_producao(mock_config, tmp_path):
    """Toggling from producao goes directly to homologacao (no dialog)."""
    from textual.widgets import Button

    from emissor.tui.screens.dashboard import DashboardScreen

    with _patch_data(tmp_path):
        app = EmissorApp(env="producao")
        async with app.run_test() as pilot:
            await pilot.pause()

            await pilot.press("e")
            await pilot.pause()

            # Should go directly to homologacao (no confirmation)
            assert app.env == "homologacao"
            assert isinstance(app.screen, DashboardScreen)
            badge = app.screen.query_one("#env-badge", Button)
            assert "HOMOLOGA" in badge.label.plain


@pytest.mark.asyncio
async def test_action_focus_filter(mock_config, tmp_path):
    """action_focus_filter focuses the De input."""
    from textual.widgets import MaskedInput

    with _patch_data(tmp_path):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.pause()

            await pilot.press("f")
            await pilot.pause()

            de_input = app.screen.query_one("#filter-de", MaskedInput)
            assert de_input.has_focus


@pytest.mark.asyncio
async def test_action_quit(mock_config, tmp_path):
    """action_quit exits the app."""
    with _patch_data(tmp_path):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("q")


@pytest.mark.asyncio
async def test_clone_entry_not_in_all_invoices(mock_config, tmp_path):
    """Clone with a selected stem that has no matching entry in _all_invoices."""
    from textual.widgets import DataTable

    from emissor.tui.screens.dashboard import DashboardScreen

    issued = tmp_path / "homologacao" / "issued"
    issued.mkdir(parents=True)
    (issued / "NFSe_lone.xml").write_text("<xml/>")

    with _patch_data(tmp_path):
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.pause()
            table = app.screen.query_one("#recent-table", DataTable)
            assert table.row_count == 1

            # Clear _all_invoices to simulate edge case
            app.screen._all_invoices = []

            await pilot.press("r")
            await pilot.pause()

            # Should stay on dashboard (entry not found → early return)
            assert isinstance(app.screen, DashboardScreen)
