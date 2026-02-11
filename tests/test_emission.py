from __future__ import annotations

import base64
import gzip
from pathlib import Path
from unittest.mock import patch

import pytest

from emissor.services import emission as emission_mod


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
        patch.object(emission_mod, "add_invoice", return_value={}),
    ):
        yield {
            "mock_emit_nfse": mock_emit,
            "mock_next": mock_next,
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
