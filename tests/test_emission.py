from __future__ import annotations

import base64
import gzip
from pathlib import Path
from unittest.mock import patch

import pytest

from emissor.services import emission as emission_mod


@pytest.fixture
def _patch_emission(monkeypatch, tmp_path, emitter_dict, client_dict):
    """Patch all external dependencies for emission.emit tests."""
    monkeypatch.setattr(emission_mod, "DATA_DIR", tmp_path)

    with (
        patch.object(emission_mod, "load_emitter", return_value=emitter_dict),
        patch.object(emission_mod, "load_client", return_value=client_dict),
        patch.object(emission_mod, "get_cert_path", return_value="/fake.pfx"),
        patch.object(emission_mod, "get_cert_password", return_value="fakepass"),
        patch.object(emission_mod, "load_pfx", return_value=(b"key", b"cert", [])),
        patch.object(emission_mod, "sign_dps", side_effect=lambda dps, *a: dps),
        patch.object(emission_mod, "emit_nfse", return_value={"chNFSe": "NFSe123"}) as mock_emit,
        patch.object(emission_mod, "next_n_dps", return_value=42) as mock_next,
        patch.object(emission_mod, "peek_next_n_dps", return_value=42) as mock_peek,
        patch.object(emission_mod, "_now_brt", return_value="2025-12-30T15:00:00-03:00"),
    ):
        yield {
            "mock_emit_nfse": mock_emit,
            "mock_next": mock_next,
            "mock_peek": mock_peek,
            "tmp_path": tmp_path,
        }


class TestEmitDryRun:
    def test_saves_xml(self, _patch_emission):
        result = emission_mod.emit("acme", "1000.00", "200.00", "2025-12-30", dry_run=True)
        assert result.get("saved_to") is not None
        saved = Path(result["saved_to"])
        assert saved.exists()
        assert saved.suffix == ".xml"

    def test_uses_peek(self, _patch_emission):
        emission_mod.emit("acme", "1000.00", "200.00", "2025-12-30", dry_run=True)
        _patch_emission["mock_peek"].assert_called_once()
        _patch_emission["mock_next"].assert_not_called()

    def test_response_none(self, _patch_emission):
        result = emission_mod.emit("acme", "1000.00", "200.00", "2025-12-30", dry_run=True)
        assert result["response"] is None


class TestEmitNormal:
    def test_calls_sefin(self, _patch_emission):
        emission_mod.emit("acme", "1000.00", "200.00", "2025-12-30")
        _patch_emission["mock_emit_nfse"].assert_called_once()

    def test_increments_sequence(self, _patch_emission):
        emission_mod.emit("acme", "1000.00", "200.00", "2025-12-30")
        _patch_emission["mock_next"].assert_called_once()
        _patch_emission["mock_peek"].assert_not_called()

    def test_returns_n_dps(self, _patch_emission):
        result = emission_mod.emit("acme", "1000.00", "200.00", "2025-12-30")
        assert result["n_dps"] == 42

    def test_returns_sefin_response(self, _patch_emission):
        result = emission_mod.emit("acme", "1000.00", "200.00", "2025-12-30")
        assert result["response"] == {"chNFSe": "NFSe123"}

    def test_saves_nfse_xml_from_response(self, _patch_emission):
        nfse_xml = base64.b64encode(gzip.compress(b"<nfse>test</nfse>")).decode()
        _patch_emission["mock_emit_nfse"].return_value = {
            "chNFSe": "NFSe456",
            "nfseXmlGZipB64": nfse_xml,
        }
        result = emission_mod.emit("acme", "1000.00", "200.00", "2025-12-30")
        saved = Path(result["saved_to"])
        assert saved.exists()
        assert saved.read_bytes() == b"<nfse>test</nfse>"

    def test_handles_missing_nfse_xml(self, _patch_emission):
        _patch_emission["mock_emit_nfse"].return_value = {"chNFSe": "NFSe789"}
        result = emission_mod.emit("acme", "1000.00", "200.00", "2025-12-30")
        assert "saved_to" not in result

    def test_with_intermediary(
        self, monkeypatch, tmp_path, emitter_dict, client_dict, intermediary_dict
    ):
        monkeypatch.setattr(emission_mod, "DATA_DIR", tmp_path)

        def fake_load_client(name):
            if name == "inter":
                return intermediary_dict
            return client_dict

        with (
            patch.object(emission_mod, "load_emitter", return_value=emitter_dict),
            patch.object(emission_mod, "load_client", side_effect=fake_load_client),
            patch.object(emission_mod, "get_cert_path", return_value="/fake.pfx"),
            patch.object(emission_mod, "get_cert_password", return_value="fakepass"),
            patch.object(emission_mod, "load_pfx", return_value=(b"key", b"cert", [])),
            patch.object(emission_mod, "sign_dps", side_effect=lambda dps, *a: dps),
            patch.object(emission_mod, "emit_nfse", return_value={}),
            patch.object(emission_mod, "next_n_dps", return_value=1),
            patch.object(emission_mod, "_now_brt", return_value="2025-12-30T15:00:00-03:00"),
        ):
            result = emission_mod.emit(
                "acme",
                "1000.00",
                "200.00",
                "2025-12-30",
                intermediario="inter",
            )
            assert result["n_dps"] == 1

    def test_silent_failure_on_bad_xml(self, _patch_emission):
        _patch_emission["mock_emit_nfse"].return_value = {
            "chNFSe": "NFSe000",
            "nfseXmlGZipB64": "not_valid_base64!!!",
        }
        # Should not raise
        result = emission_mod.emit("acme", "1000.00", "200.00", "2025-12-30")
        assert result["response"]["chNFSe"] == "NFSe000"
        assert "saved_to" not in result
