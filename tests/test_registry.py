from __future__ import annotations

from unittest.mock import patch

from emissor.utils.registry import (
    _backup_corrupt,
    add_invoice,
    check_registry_health,
    find_invoice,
    get_last_nsu,
    get_last_overrides,
    list_invoices,
    remove_invoice,
    set_last_nsu,
    update_invoice,
)


def test_get_last_nsu_default(tmp_path):
    with patch("emissor.utils.registry._sync_state_path", return_value=tmp_path / "sync.json"):
        assert get_last_nsu("homologacao") == 0


def test_set_and_get_last_nsu(tmp_path):
    sp = tmp_path / "sync.json"
    with patch("emissor.utils.registry._sync_state_path", return_value=sp):
        set_last_nsu("homologacao", 42)
        assert get_last_nsu("homologacao") == 42
        assert get_last_nsu("producao") == 0

        set_last_nsu("producao", 100)
        assert get_last_nsu("homologacao") == 42
        assert get_last_nsu("producao") == 100


def test_find_invoice_found(tmp_path):
    rp = tmp_path / "invoices.json"
    with (
        patch("emissor.utils.registry._registry_path", return_value=rp),
        patch("emissor.utils.registry._locked"),
    ):
        add_invoice("chave123", env="homologacao", nsu=10)
        result = find_invoice("chave123")
        assert result is not None
        assert result["chave"] == "chave123"
        assert result["nsu"] == 10


def test_find_invoice_not_found(tmp_path):
    rp = tmp_path / "invoices.json"
    with (
        patch("emissor.utils.registry._registry_path", return_value=rp),
        patch("emissor.utils.registry._locked"),
    ):
        assert find_invoice("nonexistent") is None


def test_find_invoice_with_env_filter(tmp_path):
    """find_invoice filters by env when specified."""
    rp = tmp_path / "invoices.json"
    with (
        patch("emissor.utils.registry._registry_path", return_value=rp),
        patch("emissor.utils.registry._locked"),
    ):
        add_invoice("chave_both", env="homologacao", nsu=1)
        add_invoice("chave_prod", env="producao", nsu=2)

        # Without env — finds first match
        assert find_invoice("chave_both") is not None

        # With env — scoped
        assert find_invoice("chave_both", env="homologacao") is not None
        assert find_invoice("chave_both", env="producao") is None
        assert find_invoice("chave_prod", env="producao") is not None
        assert find_invoice("chave_prod", env="homologacao") is None


def test_merge_fills_missing_fields(tmp_path):
    """add_invoice merges new non-None fields into an existing entry."""
    rp = tmp_path / "invoices.json"
    with (
        patch("emissor.utils.registry._registry_path", return_value=rp),
        patch("emissor.utils.registry._locked"),
    ):
        # Initial entry from emission — has client_slug/valor_usd but no nsu
        add_invoice(
            "chave1", client="Acme", client_slug="acme", valor_usd="100.00", env="producao"
        )
        # Sync pass — provides nsu and valor_brl
        result = add_invoice("chave1", nsu=42, valor_brl="500.00", env="producao")
        assert result["nsu"] == 42
        assert result["valor_brl"] == "500.00"
        # Original fields still present
        assert result["client"] == "Acme"
        assert result["client_slug"] == "acme"
        assert result["valor_usd"] == "100.00"


def test_merge_does_not_overwrite_existing(tmp_path):
    """add_invoice never overwrites fields that are already set."""
    rp = tmp_path / "invoices.json"
    with (
        patch("emissor.utils.registry._registry_path", return_value=rp),
        patch("emissor.utils.registry._locked"),
    ):
        add_invoice("chave2", client="Original", valor_brl="1000.00", env="producao")
        result = add_invoice("chave2", client="Different", valor_brl="9999.99", env="producao")
        assert result["client"] == "Original"
        assert result["valor_brl"] == "1000.00"


def test_merge_no_write_when_nothing_new(tmp_path):
    """add_invoice doesn't write to disk when merging adds nothing new."""
    rp = tmp_path / "invoices.json"
    with (
        patch("emissor.utils.registry._registry_path", return_value=rp),
        patch("emissor.utils.registry._locked"),
    ):
        add_invoice("chave3", client="Acme", nsu=10, env="producao")
        # Same values — should not trigger a save
        with patch("emissor.utils.registry._save") as mock_save:
            add_invoice("chave3", client="Acme", nsu=10, env="producao")
            mock_save.assert_not_called()


def test_load_malformed_json(tmp_path):
    """_load() returns empty list and creates backup when JSON file is corrupt."""
    rp = tmp_path / "invoices.json"
    rp.write_text("not valid json {{{")
    with (
        patch("emissor.utils.registry._registry_path", return_value=rp),
        patch("emissor.utils.registry._locked"),
    ):
        result = list_invoices()
        assert result == []
    # Original file should be gone, backup should exist
    assert not rp.exists()
    backups = list(tmp_path.glob("invoices.json.corrupt.*"))
    assert len(backups) == 1
    assert backups[0].read_text() == "not valid json {{{"


def test_remove_invoice_existing(tmp_path):
    """remove_invoice returns True and removes the entry."""
    rp = tmp_path / "invoices.json"
    with (
        patch("emissor.utils.registry._registry_path", return_value=rp),
        patch("emissor.utils.registry._locked"),
    ):
        add_invoice("chave_rm", env="homologacao")
        assert find_invoice("chave_rm") is not None
        assert remove_invoice("chave_rm") is True
        assert find_invoice("chave_rm") is None


def test_remove_invoice_nonexistent(tmp_path):
    """remove_invoice returns False for unknown chave."""
    rp = tmp_path / "invoices.json"
    with (
        patch("emissor.utils.registry._registry_path", return_value=rp),
        patch("emissor.utils.registry._locked"),
    ):
        assert remove_invoice("does_not_exist") is False


def test_get_last_nsu_malformed_sync_state(tmp_path):
    """get_last_nsu returns 0 and creates backup when sync state file has bad JSON."""
    sp = tmp_path / "sync.json"
    sp.write_text("not json")
    with patch("emissor.utils.registry._sync_state_path", return_value=sp):
        assert get_last_nsu("homologacao") == 0
    assert not sp.exists()
    backups = list(tmp_path.glob("sync.json.corrupt.*"))
    assert len(backups) == 1


def test_set_last_nsu_overwrites_malformed(tmp_path):
    """set_last_nsu recovers from corrupt sync state file and creates backup."""
    sp = tmp_path / "sync.json"
    sp.write_text("not json")
    with patch("emissor.utils.registry._sync_state_path", return_value=sp):
        set_last_nsu("homologacao", 99)
        assert get_last_nsu("homologacao") == 99
    backups = list(tmp_path.glob("sync.json.corrupt.*"))
    assert len(backups) == 1


# --- Overrides storage and get_last_overrides ---

SAMPLE_OVERRIDES = {
    "x_desc_serv": "Software development",
    "c_trib_nac": "01.01.01",
    "trib_issqn": "3",
    "cst_pis_cofins": "08",
}


def test_add_invoice_stores_overrides(tmp_path):
    """add_invoice persists overrides dict in registry entry."""
    rp = tmp_path / "invoices.json"
    with (
        patch("emissor.utils.registry._registry_path", return_value=rp),
        patch("emissor.utils.registry._locked"),
    ):
        entry = add_invoice(
            "chave_ov1",
            client_slug="acme",
            env="producao",
            overrides=SAMPLE_OVERRIDES,
        )
        assert entry["overrides"] == SAMPLE_OVERRIDES


def test_add_invoice_no_overrides_omits_key(tmp_path):
    """add_invoice without overrides produces entry without 'overrides' key."""
    rp = tmp_path / "invoices.json"
    with (
        patch("emissor.utils.registry._registry_path", return_value=rp),
        patch("emissor.utils.registry._locked"),
    ):
        entry = add_invoice("chave_no_ov", client_slug="acme", env="producao")
        assert "overrides" not in entry


def test_get_last_overrides_returns_most_recent(tmp_path):
    """get_last_overrides returns overrides from the most recent matching entry."""
    rp = tmp_path / "invoices.json"
    with (
        patch("emissor.utils.registry._registry_path", return_value=rp),
        patch("emissor.utils.registry._locked"),
    ):
        old_overrides = {"x_desc_serv": "Old description", "trib_issqn": "1"}
        new_overrides = {"x_desc_serv": "New description", "trib_issqn": "5"}
        add_invoice("chave_old", client_slug="acme", env="producao", overrides=old_overrides)
        add_invoice("chave_new", client_slug="acme", env="producao", overrides=new_overrides)
        result = get_last_overrides("acme", "producao")
        assert result == new_overrides


def test_get_last_overrides_no_history(tmp_path):
    """get_last_overrides returns None when no entries exist for the client."""
    rp = tmp_path / "invoices.json"
    with (
        patch("emissor.utils.registry._registry_path", return_value=rp),
        patch("emissor.utils.registry._locked"),
    ):
        assert get_last_overrides("unknown", "producao") is None


def test_get_last_overrides_skips_entries_without_overrides(tmp_path):
    """Entries without overrides (sync-originated, pre-feature) are skipped."""
    rp = tmp_path / "invoices.json"
    with (
        patch("emissor.utils.registry._registry_path", return_value=rp),
        patch("emissor.utils.registry._locked"),
    ):
        add_invoice("chave_sync", client_slug="acme", env="producao")  # no overrides
        assert get_last_overrides("acme", "producao") is None


def test_get_last_overrides_prefers_same_env(tmp_path):
    """get_last_overrides prefers same-env match over cross-env."""
    rp = tmp_path / "invoices.json"
    with (
        patch("emissor.utils.registry._registry_path", return_value=rp),
        patch("emissor.utils.registry._locked"),
    ):
        homolog_overrides = {"trib_issqn": "3"}
        prod_overrides = {"trib_issqn": "5"}
        add_invoice("ch_h", client_slug="acme", env="homologacao", overrides=homolog_overrides)
        add_invoice("ch_p", client_slug="acme", env="producao", overrides=prod_overrides)
        result = get_last_overrides("acme", "homologacao")
        assert result == homolog_overrides


def test_get_last_overrides_cross_env_fallback(tmp_path):
    """get_last_overrides falls back to cross-env when no same-env match."""
    rp = tmp_path / "invoices.json"
    with (
        patch("emissor.utils.registry._registry_path", return_value=rp),
        patch("emissor.utils.registry._locked"),
    ):
        prod_overrides = {"trib_issqn": "5", "cst_pis_cofins": "08"}
        add_invoice("ch_prod", client_slug="acme", env="producao", overrides=prod_overrides)
        # Query for homologacao — no same-env match, falls back to producao
        result = get_last_overrides("acme", "homologacao")
        assert result == prod_overrides


# --- _backup_corrupt and check_registry_health ---


def test_backup_corrupt_creates_timestamped_file(tmp_path):
    """_backup_corrupt renames file to .corrupt.{timestamp} and returns backup path."""
    f = tmp_path / "test.json"
    f.write_text("bad data")
    backup = _backup_corrupt(f)
    assert not f.exists()
    assert backup.exists()
    assert backup.read_text() == "bad data"
    assert "test.json.corrupt." in backup.name


def test_check_registry_health_ok(tmp_path):
    """check_registry_health reports healthy when files are valid."""
    rp = tmp_path / "invoices.json"
    sp = tmp_path / "sync_state.json"
    rp.write_text('[{"chave": "a"}, {"chave": "b"}]')
    sp.write_text('{"homologacao": 42}')
    with (
        patch("emissor.utils.registry._registry_path", return_value=rp),
        patch("emissor.utils.registry._sync_state_path", return_value=sp),
    ):
        health = check_registry_health()
    assert health.registry_ok is True
    assert health.registry_count == 2
    assert health.registry_corrupt_backups == []
    assert health.sync_state_ok is True
    assert health.sync_state_corrupt_backups == []


def test_check_registry_health_corrupt_registry(tmp_path):
    """check_registry_health detects corrupt registry file."""
    rp = tmp_path / "invoices.json"
    rp.write_text("not json")
    sp = tmp_path / "sync_state.json"
    sp.write_text('{"homologacao": 0}')
    with (
        patch("emissor.utils.registry._registry_path", return_value=rp),
        patch("emissor.utils.registry._sync_state_path", return_value=sp),
    ):
        health = check_registry_health()
    assert health.registry_ok is False
    assert health.registry_count == 0


def test_check_registry_health_finds_backups(tmp_path):
    """check_registry_health picks up existing .corrupt.* backup files."""
    rp = tmp_path / "invoices.json"
    rp.write_text("[]")
    # Create fake backup files
    (tmp_path / "invoices.json.corrupt.20260101T000000").write_text("old corrupt")
    (tmp_path / "invoices.json.corrupt.20260201T000000").write_text("newer corrupt")
    sp = tmp_path / "sync_state.json"
    with (
        patch("emissor.utils.registry._registry_path", return_value=rp),
        patch("emissor.utils.registry._sync_state_path", return_value=sp),
    ):
        health = check_registry_health()
    assert health.registry_ok is True
    assert len(health.registry_corrupt_backups) == 2
    assert health.registry_corrupt_backups[0].endswith("invoices.json.corrupt.20260101T000000")
    assert health.registry_corrupt_backups[1].endswith("invoices.json.corrupt.20260201T000000")


def test_check_registry_health_corrupt_sync_state(tmp_path):
    """check_registry_health detects corrupt sync state file."""
    rp = tmp_path / "invoices.json"
    sp = tmp_path / "sync_state.json"
    sp.write_text("{broken")
    with (
        patch("emissor.utils.registry._registry_path", return_value=rp),
        patch("emissor.utils.registry._sync_state_path", return_value=sp),
    ):
        health = check_registry_health()
    assert health.sync_state_ok is False


# --- update_invoice ---


def test_update_invoice_promotes_draft(tmp_path):
    """update_invoice promotes a draft entry to emitida with a real chave."""
    rp = tmp_path / "invoices.json"
    with (
        patch("emissor.utils.registry._registry_path", return_value=rp),
        patch("emissor.utils.registry._locked"),
    ):
        add_invoice("draft_homologacao_10", n_dps=10, env="homologacao", status="preparada")
        result = update_invoice(
            n_dps=10, env="homologacao", status="emitida", chave="NFSe_REAL_123"
        )
        assert result is not None
        assert result["status"] == "emitida"
        assert result["chave"] == "NFSe_REAL_123"


def test_update_invoice_marks_failure(tmp_path):
    """update_invoice marks a draft as falha with an error message."""
    rp = tmp_path / "invoices.json"
    with (
        patch("emissor.utils.registry._registry_path", return_value=rp),
        patch("emissor.utils.registry._locked"),
    ):
        add_invoice("draft_homologacao_11", n_dps=11, env="homologacao", status="preparada")
        result = update_invoice(n_dps=11, env="homologacao", status="falha", error="SEFIN 204")
        assert result is not None
        assert result["status"] == "falha"
        assert result["error"] == "SEFIN 204"


def test_update_invoice_clears_error_on_promotion(tmp_path):
    """Promoting a failed entry to emitida clears the error field."""
    rp = tmp_path / "invoices.json"
    with (
        patch("emissor.utils.registry._registry_path", return_value=rp),
        patch("emissor.utils.registry._locked"),
    ):
        add_invoice("draft_homologacao_12", n_dps=12, env="homologacao", status="falha")
        # Manually add error
        update_invoice(n_dps=12, env="homologacao", error="some error")
        # Promote to emitida — error should be cleared
        result = update_invoice(n_dps=12, env="homologacao", status="emitida", chave="NFSe_OK")
        assert result is not None
        assert result["status"] == "emitida"
        assert "error" not in result


def test_update_invoice_not_found(tmp_path):
    """update_invoice returns None when no matching entry exists."""
    rp = tmp_path / "invoices.json"
    with (
        patch("emissor.utils.registry._registry_path", return_value=rp),
        patch("emissor.utils.registry._locked"),
    ):
        result = update_invoice(n_dps=999, env="homologacao", status="emitida")
        assert result is None


def test_update_invoice_no_write_when_unchanged(tmp_path):
    """update_invoice skips disk write when nothing actually changes."""
    rp = tmp_path / "invoices.json"
    with (
        patch("emissor.utils.registry._registry_path", return_value=rp),
        patch("emissor.utils.registry._locked"),
    ):
        add_invoice("draft_homologacao_13", n_dps=13, env="homologacao", status="preparada")
        with patch("emissor.utils.registry._save") as mock_save:
            # Same status, no chave/error change — should not write
            update_invoice(n_dps=13, env="homologacao", status="preparada")
            mock_save.assert_not_called()
