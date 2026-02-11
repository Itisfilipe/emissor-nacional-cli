from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID
from lxml import etree

from emissor.models.client import Client, Intermediary
from emissor.models.emitter import Emitter
from emissor.models.invoice import Invoice


def xml_text(el: etree._Element, xpath: str) -> str | None:
    """Extract text from an XML element by xpath."""
    found = el.find(xpath)
    return found.text if found is not None else None


# --- Emitter fixtures ---


@pytest.fixture
def emitter_dict() -> dict:
    return {
        "cnpj": "12345678000199",
        "razao_social": "ACME SOFTWARE LTDA",
        "logradouro": "RUA DAS FLORES",
        "numero": "100",
        "bairro": "CENTRO",
        "cod_municipio": "4205407",
        "uf": "SC",
        "cep": "88000000",
        "fone": "48999999999",
        "email": "contato@acme-software.com.br",
        "op_simp_nac": "1",
        "reg_esp_trib": "0",
        "serie": "900",
        "ver_aplic": "emissor-nacional_0.1.0",
    }


@pytest.fixture
def emitter(emitter_dict: dict) -> Emitter:
    return Emitter.from_dict(emitter_dict)


# --- Client fixtures ---


@pytest.fixture
def client_dict() -> dict:
    return {
        "nif": "123456789",
        "nome": "Acme Corp",
        "pais": "US",
        "logradouro": "100 Main St, Ste",
        "numero": "100",
        "bairro": "n/a",
        "cidade": "New York",
        "estado": "NY",
        "cep": "10001",
        "mec_af_comex_p": "02",
        "mec_af_comex_t": "02",
    }


@pytest.fixture
def client(client_dict: dict) -> Client:
    return Client.from_dict(client_dict)


@pytest.fixture
def client_with_complement_dict() -> dict:
    return {
        "nif": "987654321",
        "nome": "Example Corp",
        "pais": "US",
        "logradouro": "Walnut St.",
        "numero": "3601",
        "bairro": "n/a",
        "cidade": "Denver",
        "estado": "Colorado",
        "cep": "80205",
        "complemento": "ste 400",
        "mec_af_comex_p": "01",
        "mec_af_comex_t": "01",
    }


@pytest.fixture
def client_with_complement(client_with_complement_dict: dict) -> Client:
    return Client.from_dict(client_with_complement_dict)


# --- Intermediary fixtures ---


@pytest.fixture
def intermediary_dict() -> dict:
    return {
        "nif": "9876543",
        "nome": "GLOBAL PAYMENTS INC",
        "pais": "US",
        "logradouro": "500 Broadway",
        "numero": "500",
        "bairro": "NA",
        "cidade": "San Francisco",
        "estado": "California",
        "cep": "94102",
    }


@pytest.fixture
def intermediary(intermediary_dict: dict) -> Intermediary:
    return Intermediary.from_dict(intermediary_dict)


# --- Invoice fixtures ---


@pytest.fixture
def sample_invoice() -> Invoice:
    return Invoice(
        valor_brl="19684.93",
        valor_usd="3640.00",
        competencia="2025-12-30",
        n_dps=3,
        dh_emi="2025-12-30T15:57:03-03:00",
    )


# --- Certificate / PFX fixtures ---


@pytest.fixture(scope="session")
def test_key_and_cert():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COMMON_NAME, "Test Certificate"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Test Org"),
        ]
    )
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(UTC) - timedelta(days=1))
        .not_valid_after(datetime.now(UTC) + timedelta(days=365))
        .sign(key, hashes.SHA256())
    )
    return key, cert


@pytest.fixture(scope="session")
def self_signed_pem(test_key_and_cert):
    key, cert = test_key_and_cert
    key_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )
    cert_pem = cert.public_bytes(serialization.Encoding.PEM)
    return key_pem, cert_pem


@pytest.fixture
def test_pfx(tmp_path, test_key_and_cert):
    key, cert = test_key_and_cert
    password = b"testpass"
    pfx_data = pkcs12.serialize_key_and_certificates(
        name=b"test",
        key=key,
        cert=cert,
        cas=None,
        encryption_algorithm=serialization.BestAvailableEncryption(password),
    )
    pfx_path = tmp_path / "test.pfx"
    pfx_path.write_bytes(pfx_data)
    return str(pfx_path), "testpass"


# --- Config dir fixture ---


@pytest.fixture
def config_dir(tmp_path, emitter_dict, client_dict):
    import yaml

    cfg = tmp_path / "config"
    cfg.mkdir()
    (cfg / "emitter.yaml").write_text(yaml.dump(emitter_dict))
    clients = cfg / "clients"
    clients.mkdir()
    (clients / "acme.yaml").write_text(yaml.dump(client_dict))
    return cfg
