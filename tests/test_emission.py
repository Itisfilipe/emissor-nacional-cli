from __future__ import annotations

import base64
import gzip
from pathlib import Path
from unittest.mock import patch

import pytest

from emissor.services import emission as emission_mod
from emissor.services.exceptions import SefinRejectError


@pytest.fixture
def _patch_emission(monkeypatch, tmp_path, emitter_dict, client_dict):
    """Patch all external dependencies for emission tests."""
    issued_dir = tmp_path / "homologacao" / "issued"
    issued_dir.mkdir(parents=True)

    with (
        patch.object(
            emission_mod, "get_issued_dir", side_effect=lambda env: tmp_path / env / "issued"
        ),
        patch.object(emission_mod, "load_emitter", return_value=emitter_dict),
        patch.object(emission_mod, "load_client", return_value=client_dict),
        patch.object(emission_mod, "get_cert_path", return_value="/fake.pfx"),
        patch.object(emission_mod, "get_cert_password", return_value="fakepass"),
        patch.object(emission_mod, "load_pfx", return_value=(b"key", b"cert", [])),
        patch.object(emission_mod, "sign_dps", side_effect=lambda dps, *a: dps),
        patch.object(emission_mod, "emit_nfse", return_value={"chNFSe": "NFSe123"}) as mock_emit,
        patch.object(emission_mod, "next_n_dps", return_value=42) as mock_next,
        patch.object(emission_mod, "_now_brt", return_value="2025-12-30T15:00:00-03:00"),
        patch.object(emission_mod, "add_invoice", return_value={}) as mock_add,
        patch.object(
            emission_mod, "update_invoice", return_value={"status": "emitida"}
        ) as mock_update,
    ):
        yield {
            "mock_emit_nfse": mock_emit,
            "mock_next": mock_next,
            "mock_add": mock_add,
            "mock_update": mock_update,
            "tmp_path": tmp_path,
        }


class TestPrepare:
    def test_returns_prepared_dps(self, _patch_emission):
        prepared = emission_mod.prepare("acme", "1000.00", "200.00", "2025-12-30")
        assert prepared.n_dps == 42
        assert prepared.emitter.cnpj == "12345678000199"
        assert prepared.client.nif == "123456789"
        assert prepared.env == "homologacao"
        assert prepared.signed_xml is not None

    def test_reserves_sequence_on_prepare(self, _patch_emission):
        """prepare() atomically reserves the sequence number via next_n_dps()."""
        emission_mod.prepare("acme", "1000.00", "200.00", "2025-12-30")
        _patch_emission["mock_next"].assert_called_once()

    def test_with_intermediary(
        self, monkeypatch, tmp_path, emitter_dict, client_dict, intermediary_dict
    ):
        def fake_load_client(name):
            if name == "inter":
                return intermediary_dict
            return client_dict

        with (
            patch.object(
                emission_mod,
                "get_issued_dir",
                side_effect=lambda env: tmp_path / env / "issued",
            ),
            patch.object(emission_mod, "load_emitter", return_value=emitter_dict),
            patch.object(emission_mod, "load_client", side_effect=fake_load_client),
            patch.object(emission_mod, "get_cert_path", return_value="/fake.pfx"),
            patch.object(emission_mod, "get_cert_password", return_value="fakepass"),
            patch.object(emission_mod, "load_pfx", return_value=(b"key", b"cert", [])),
            patch.object(emission_mod, "sign_dps", side_effect=lambda dps, *a: dps),
            patch.object(emission_mod, "next_n_dps", return_value=1),
            patch.object(emission_mod, "_now_brt", return_value="2025-12-30T15:00:00-03:00"),
        ):
            prepared = emission_mod.prepare(
                "acme", "1000.00", "200.00", "2025-12-30", intermediario="inter"
            )
            assert prepared.intermediary is not None
            assert prepared.intermediary.nome == "GLOBAL PAYMENTS INC"

    def test_overrides_passed_to_invoice(self, _patch_emission):
        prepared = emission_mod.prepare(
            "acme",
            "1000.00",
            "200.00",
            "2025-12-30",
            overrides={"trib_issqn": "5", "x_desc_serv": "Custom"},
        )
        assert prepared.invoice.trib_issqn == "5"
        assert prepared.invoice.x_desc_serv == "Custom"
        # Non-overridden fields stay None
        assert prepared.invoice.c_trib_nac is None

    def test_prepare_fails_when_draft_persistence_fails(self, _patch_emission):
        """prepare() must propagate add_invoice errors — burned sequences need audit trail."""
        _patch_emission["mock_add"].side_effect = RuntimeError("disk full")
        with pytest.raises(RuntimeError, match="disk full"):
            emission_mod.prepare("acme", "1000.00", "200.00", "2025-12-30")


class TestSubmit:
    def test_calls_sefin_and_returns_response(self, _patch_emission):
        prepared = emission_mod.prepare("acme", "1000.00", "200.00", "2025-12-30")
        result = emission_mod.submit(prepared)
        _patch_emission["mock_emit_nfse"].assert_called_once()
        assert result["response"] == {"chNFSe": "NFSe123"}
        assert result["n_dps"] == 42

    def test_submit_does_not_increment_sequence(self, _patch_emission):
        """submit() must not call next_n_dps() — sequence was reserved in prepare()."""
        prepared = emission_mod.prepare("acme", "1000.00", "200.00", "2025-12-30")
        _patch_emission["mock_next"].reset_mock()
        emission_mod.submit(prepared)
        _patch_emission["mock_next"].assert_not_called()

    def test_saves_nfse_xml(self, _patch_emission):
        nfse_xml = base64.b64encode(gzip.compress(b"<nfse>test</nfse>")).decode()
        _patch_emission["mock_emit_nfse"].return_value = {
            "chNFSe": "NFSe456",
            "nfseXmlGZipB64": nfse_xml,
        }
        prepared = emission_mod.prepare("acme", "1000.00", "200.00", "2025-12-30")
        result = emission_mod.submit(prepared)
        saved = Path(result["saved_to"])
        assert saved.exists()
        assert saved.read_bytes() == b"<nfse>test</nfse>"

    def test_submit_passes_overrides_to_registry_on_fallback(self, _patch_emission):
        """submit() falls back to add_invoice with overrides when no draft found."""
        prepared = emission_mod.prepare(
            "acme",
            "1000.00",
            "200.00",
            "2025-12-30",
            overrides={"trib_issqn": "5", "x_desc_serv": "Custom"},
        )
        # update_invoice returns None → triggers add_invoice fallback
        with (
            patch.object(emission_mod, "update_invoice", return_value=None),
            patch.object(emission_mod, "add_invoice", return_value={}) as mock_add,
        ):
            emission_mod.submit(prepared)
            mock_add.assert_called_once()
            call_kwargs = mock_add.call_args[1]
            assert call_kwargs["overrides"] is not None
            assert call_kwargs["overrides"]["trib_issqn"] == "5"
            assert call_kwargs["overrides"]["x_desc_serv"] == "Custom"


class TestSubmitRejection:
    def test_submit_propagates_reject(self, _patch_emission):
        _patch_emission["mock_emit_nfse"].side_effect = SefinRejectError(
            "cStat 204: Rejeicao", response={"cStat": "204"}
        )
        prepared = emission_mod.prepare("acme", "1000.00", "200.00", "2025-12-30")
        with pytest.raises(SefinRejectError, match="cStat 204"):
            emission_mod.submit(prepared)

    def test_no_registry_on_rejection(self, _patch_emission):
        _patch_emission["mock_emit_nfse"].side_effect = SefinRejectError("rejected")
        prepared = emission_mod.prepare("acme", "1000.00", "200.00", "2025-12-30")
        with (
            patch.object(emission_mod, "add_invoice") as mock_add,
            pytest.raises(SefinRejectError),
        ):
            emission_mod.submit(prepared)
        mock_add.assert_not_called()


class TestSaveXml:
    def test_saves_to_disk(self, _patch_emission):
        prepared = emission_mod.prepare("acme", "1000.00", "200.00", "2025-12-30")
        path = emission_mod.save_xml(prepared)
        assert Path(path).exists()
        assert "dry_run_dps_42" in path

    def test_save_xml_does_not_increment_sequence(self, _patch_emission):
        """save_xml() must not call next_n_dps() — sequence was reserved in prepare()."""
        prepared = emission_mod.prepare("acme", "1000.00", "200.00", "2025-12-30")
        _patch_emission["mock_next"].reset_mock()
        emission_mod.save_xml(prepared)
        _patch_emission["mock_next"].assert_not_called()


class TestDraftAndPromote:
    def test_prepare_creates_draft_entry(self, _patch_emission):
        """prepare() calls add_invoice with status='preparada' after reserving sequence."""
        emission_mod.prepare("acme", "1000.00", "200.00", "2025-12-30")
        mock_add = _patch_emission["mock_add"]
        # Find the call with status="preparada" (draft creation)
        draft_calls = [c for c in mock_add.call_args_list if c[1].get("status") == "preparada"]
        assert len(draft_calls) == 1
        call_kwargs = draft_calls[0][1]
        assert call_kwargs["n_dps"] == 42
        assert call_kwargs["env"] == "homologacao"
        # Positional arg is the synthetic chave
        assert draft_calls[0][0][0] == "draft_homologacao_42"

    def test_submit_promotes_draft(self, _patch_emission):
        """submit() calls update_invoice with status='emitida' and real chave."""
        prepared = emission_mod.prepare("acme", "1000.00", "200.00", "2025-12-30")
        emission_mod.submit(prepared)
        mock_update = _patch_emission["mock_update"]
        mock_update.assert_called_once_with(
            n_dps=42, env="homologacao", status="emitida", chave="NFSe123"
        )

    def test_submit_fallback_when_no_draft(self, _patch_emission):
        """submit() falls back to add_invoice when update_invoice returns None."""
        prepared = emission_mod.prepare("acme", "1000.00", "200.00", "2025-12-30")
        _patch_emission["mock_update"].return_value = None
        _patch_emission["mock_add"].reset_mock()
        emission_mod.submit(prepared)
        # add_invoice should be called with the real chave
        fallback_calls = [
            c for c in _patch_emission["mock_add"].call_args_list if c[0][0] == "NFSe123"
        ]
        assert len(fallback_calls) == 1

    def test_save_xml_updates_to_rascunho(self, _patch_emission):
        """save_xml() calls update_invoice with status='rascunho'."""
        prepared = emission_mod.prepare("acme", "1000.00", "200.00", "2025-12-30")
        _patch_emission["mock_update"].reset_mock()
        emission_mod.save_xml(prepared)
        _patch_emission["mock_update"].assert_called_once_with(
            n_dps=42, env="homologacao", status="rascunho"
        )

    def test_mark_failed_updates_registry(self, _patch_emission):
        """mark_failed() calls update_invoice with status='falha' and truncated error."""
        prepared = emission_mod.prepare("acme", "1000.00", "200.00", "2025-12-30")
        _patch_emission["mock_update"].reset_mock()
        long_error = "x" * 600
        emission_mod.mark_failed(prepared, long_error)
        _patch_emission["mock_update"].assert_called_once_with(
            n_dps=42, env="homologacao", status="falha", error="x" * 500
        )
