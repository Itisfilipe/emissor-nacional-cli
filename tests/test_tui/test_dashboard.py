from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from emissor.tui.app import EmissorApp


def _patch_data(tmp_path):
    """Patch both DATA_DIR and REGISTRY_PATH to use tmp_path."""
    registry_path = tmp_path / "invoices.json"
    return (
        patch("emissor.config.DATA_DIR", tmp_path),
        patch("emissor.utils.registry.REGISTRY_PATH", registry_path),
    )


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
async def test_dashboard_loads_clients(mock_config):
    app = EmissorApp(env="homologacao")
    async with app.run_test() as pilot:
        await pilot.pause()
        label = app.screen.query_one("#clients-info")
        text = label.render().plain
        assert "acme" in text
        assert "globex" in text


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

    p1, p2 = _patch_data(tmp_path)
    with p1, p2:
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

    p1, p2 = _patch_data(tmp_path)
    with p1, p2:
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

    p1, p2 = _patch_data(tmp_path)
    with p1, p2:
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
    """Pressing 'e' toggles env and reloads the table."""
    from textual.widgets import DataTable

    homol = tmp_path / "homologacao" / "issued"
    homol.mkdir(parents=True)
    (homol / "NFSe_homol_1.xml").write_text("<xml/>")

    prod = tmp_path / "producao" / "issued"
    prod.mkdir(parents=True)
    (prod / "NFSe_prod_1.xml").write_text("<xml/>")
    (prod / "NFSe_prod_2.xml").write_text("<xml/>")

    p1, p2 = _patch_data(tmp_path)
    with p1, p2:
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.pause()
            table = app.screen.query_one("#recent-table", DataTable)
            assert table.row_count == 1

            # Toggle to producao
            await pilot.press("e")
            await pilot.pause()

            assert app.env == "producao"
            assert table.row_count == 2


@pytest.mark.asyncio
async def test_filter_preset_hoje(mock_config, tmp_path):
    """The 'Hoje' filter only shows files modified today."""
    from textual.widgets import DataTable, RadioButton

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

    p1, p2 = _patch_data(tmp_path)
    with p1, p2:
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.pause()
            table = app.screen.query_one("#recent-table", DataTable)
            assert table.row_count == 2  # Todos shows all

            # Click "Hoje"
            hoje_radio = app.screen.query_one("#filter-hoje", RadioButton)
            hoje_radio.value = True
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

    p1, p2 = _patch_data(tmp_path)
    with p1, p2:
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

    p1, p2 = _patch_data(tmp_path)
    with p1, p2:
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
async def test_action_bar_visible_on_row_select(mock_config, tmp_path):
    """Action bar appears when table has rows."""
    from textual.containers import Horizontal

    issued = tmp_path / "homologacao" / "issued"
    issued.mkdir(parents=True)
    (issued / "NFSe_x.xml").write_text("<xml/>")

    p1, p2 = _patch_data(tmp_path)
    with p1, p2:
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.pause()
            action_bar = app.screen.query_one("#action-bar", Horizontal)
            assert action_bar.display is True


@pytest.mark.asyncio
async def test_action_bar_hidden_when_empty(mock_config, tmp_path):
    """Action bar is hidden when table has no rows."""
    from textual.containers import Horizontal

    # No issued dir = no files, and empty registry
    p1, p2 = _patch_data(tmp_path)
    with p1, p2:
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.pause()
            action_bar = app.screen.query_one("#action-bar", Horizontal)
            assert action_bar.display is False


@pytest.mark.asyncio
async def test_action_consultar_opens_query(mock_config, tmp_path):
    """Clicking Consultar button opens QueryScreen for emitted invoice."""
    from textual.widgets import Button

    from emissor.tui.screens.query import QueryScreen

    issued = tmp_path / "homologacao" / "issued"
    issued.mkdir(parents=True)
    (issued / "NFSe_abc.xml").write_text("<xml/>")

    p1, p2 = _patch_data(tmp_path)
    with p1, p2:
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.pause()
            btn = app.screen.query_one("#btn-consultar", Button)
            btn.press()
            await pilot.pause()
            assert isinstance(app.screen, QueryScreen)


@pytest.mark.asyncio
async def test_action_pdf_opens_download(mock_config, tmp_path):
    """Clicking Baixar PDF button opens DownloadPdfScreen."""
    from textual.widgets import Button

    from emissor.tui.screens.download_pdf import DownloadPdfScreen

    issued = tmp_path / "homologacao" / "issued"
    issued.mkdir(parents=True)
    (issued / "NFSe_def.xml").write_text("<xml/>")

    p1, p2 = _patch_data(tmp_path)
    with p1, p2:
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.pause()
            btn = app.screen.query_one("#btn-pdf", Button)
            btn.press()
            await pilot.pause()
            assert isinstance(app.screen, DownloadPdfScreen)


@pytest.mark.asyncio
async def test_dry_run_disables_consultar_pdf(mock_config, tmp_path):
    """Consultar and PDF buttons are disabled for dry_run rows."""
    from textual.widgets import Button

    issued = tmp_path / "homologacao" / "issued"
    issued.mkdir(parents=True)
    (issued / "dry_run_dps_99.xml").write_text("<xml/>")

    p1, p2 = _patch_data(tmp_path)
    with p1, p2:
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.pause()
            btn_consultar = app.screen.query_one("#btn-consultar", Button)
            btn_pdf = app.screen.query_one("#btn-pdf", Button)
            assert btn_consultar.disabled is True
            assert btn_pdf.disabled is True


@pytest.mark.asyncio
async def test_data_migration(tmp_path):
    """migrate_data_layout moves old issued/*.xml to homologacao/issued/."""
    from emissor.config import migrate_data_layout

    old_dir = tmp_path / "issued"
    old_dir.mkdir()
    (old_dir / "NFSe_1.xml").write_text("<xml/>")
    (old_dir / "NFSe_2.xml").write_text("<xml/>")

    with patch("emissor.config.DATA_DIR", tmp_path):
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

    with patch("emissor.config.DATA_DIR", tmp_path):
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
    registry_path.write_text(json.dumps([
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
    ]))

    p1, p2 = _patch_data(tmp_path)
    with p1, p2:
        app = EmissorApp(env="homologacao")
        async with app.run_test() as pilot:
            await pilot.pause()
            table = app.screen.query_one("#recent-table", DataTable)
            # Only the 2 homologacao invoices, not the producao one
            assert table.row_count == 2
