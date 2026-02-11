from __future__ import annotations

from pathlib import Path

from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    pkcs12,
)
from cryptography.x509 import Certificate


def load_pfx(pfx_path: str, password: str) -> tuple[bytes, bytes, list[Certificate]]:
    """Load a .pfx/.p12 certificate and return (private_key_pem, cert_pem, chain).

    Returns:
        Tuple of (private_key_pem_bytes, certificate_pem_bytes, ca_chain_certs)
    """
    pfx_data = Path(pfx_path).read_bytes()
    private_key, certificate, chain = pkcs12.load_key_and_certificates(pfx_data, password.encode())

    if private_key is None or certificate is None:
        raise ValueError("Certificate or private key not found in .pfx file")

    key_pem = private_key.private_bytes(
        encoding=Encoding.PEM,
        format=PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=NoEncryption(),
    )
    cert_pem = certificate.public_bytes(Encoding.PEM)
    ca_certs = list(chain) if chain else []

    return key_pem, cert_pem, ca_certs


def validate_certificate(pfx_path: str, password: str) -> dict:
    """Validate certificate and return info."""
    from datetime import UTC, datetime

    pfx_data = Path(pfx_path).read_bytes()
    _, certificate, _ = pkcs12.load_key_and_certificates(pfx_data, password.encode())

    if certificate is None:
        raise ValueError("No certificate found in .pfx file")

    now = datetime.now(UTC)
    return {
        "subject": certificate.subject.rfc4514_string(),
        "issuer": certificate.issuer.rfc4514_string(),
        "not_before": certificate.not_valid_before_utc,
        "not_after": certificate.not_valid_after_utc,
        "valid": certificate.not_valid_before_utc <= now <= certificate.not_valid_after_utc,
        "serial": certificate.serial_number,
    }
