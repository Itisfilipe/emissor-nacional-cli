from __future__ import annotations

from unittest.mock import patch

from emissor.utils.registry import (
    add_invoice,
    find_invoice,
    get_last_nsu,
    list_invoices,
    remove_invoice,
    set_last_nsu,
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
    """_load() returns empty list when JSON file is corrupt."""
    rp = tmp_path / "invoices.json"
    rp.write_text("not valid json {{{")
    with (
        patch("emissor.utils.registry._registry_path", return_value=rp),
        patch("emissor.utils.registry._locked"),
    ):
        result = list_invoices()
        assert result == []


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
    """get_last_nsu returns 0 when sync state file has bad JSON."""
    sp = tmp_path / "sync.json"
    sp.write_text("not json")
    with patch("emissor.utils.registry._sync_state_path", return_value=sp):
        assert get_last_nsu("homologacao") == 0


def test_set_last_nsu_overwrites_malformed(tmp_path):
    """set_last_nsu recovers from corrupt sync state file."""
    sp = tmp_path / "sync.json"
    sp.write_text("not json")
    with patch("emissor.utils.registry._sync_state_path", return_value=sp):
        set_last_nsu("homologacao", 99)
        assert get_last_nsu("homologacao") == 99
