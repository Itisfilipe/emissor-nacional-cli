from __future__ import annotations

from unittest.mock import patch

import pytest


@pytest.fixture
def mock_config():
    """Patch config-dependent calls so the TUI can launch without real files."""
    emitter_dict = {
        "cnpj": "12345678000199",
        "razao_social": "ACME SOFTWARE LTDA",
        "logradouro": "RUA DAS FLORES",
        "numero": "100",
        "bairro": "CENTRO",
        "cod_municipio": "4205407",
        "uf": "SC",
        "cep": "88000000",
        "fone": "48999999999",
        "email": "contato@acme.com.br",
    }
    with (
        patch("emissor.config.load_emitter", return_value=emitter_dict),
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
