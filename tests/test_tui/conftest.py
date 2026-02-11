from __future__ import annotations

from unittest.mock import patch

import pytest


@pytest.fixture
def mock_config():
    """Patch config-dependent calls so the TUI can launch without real files."""
    with (
        patch("emissor.config.load_emitter", return_value={"razao_social": "ACME", "cnpj": "123"}),
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
        patch("emissor.config.list_clients", return_value=["acme", "globex"]),
        patch("emissor.config.migrate_data_layout"),
    ):
        yield


@pytest.fixture
def issued_dir_homol(tmp_path):
    """Create env-scoped issued dir for homologacao."""
    d = tmp_path / "homologacao" / "issued"
    d.mkdir(parents=True)
    return d


@pytest.fixture
def issued_dir_prod(tmp_path):
    """Create env-scoped issued dir for producao."""
    d = tmp_path / "producao" / "issued"
    d.mkdir(parents=True)
    return d
