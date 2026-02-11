from __future__ import annotations

import pytest

from emissor.utils.certificate import load_pfx, validate_certificate


class TestLoadPfx:
    def test_returns_key_and_cert(self, test_pfx):
        pfx_path, password = test_pfx
        key_pem, cert_pem, chain = load_pfx(pfx_path, password)
        assert key_pem is not None
        assert cert_pem is not None
        assert isinstance(chain, list)

    def test_key_is_pem(self, test_pfx):
        pfx_path, password = test_pfx
        key_pem, _, _ = load_pfx(pfx_path, password)
        assert key_pem.startswith(b"-----BEGIN")

    def test_cert_is_pem(self, test_pfx):
        pfx_path, password = test_pfx
        _, cert_pem, _ = load_pfx(pfx_path, password)
        assert cert_pem.startswith(b"-----BEGIN")

    def test_chain_empty_self_signed(self, test_pfx):
        pfx_path, password = test_pfx
        _, _, chain = load_pfx(pfx_path, password)
        assert chain == []

    def test_wrong_password(self, test_pfx):
        pfx_path, _ = test_pfx
        with pytest.raises(ValueError):
            load_pfx(pfx_path, "wrongpassword")

    def test_missing_file(self):
        with pytest.raises(FileNotFoundError):
            load_pfx("/nonexistent/path.pfx", "pass")


class TestValidateCertificate:
    def test_keys(self, test_pfx):
        pfx_path, password = test_pfx
        info = validate_certificate(pfx_path, password)
        assert "subject" in info
        assert "issuer" in info
        assert "not_before" in info
        assert "not_after" in info
        assert "valid" in info
        assert "serial" in info

    def test_valid_true(self, test_pfx):
        pfx_path, password = test_pfx
        info = validate_certificate(pfx_path, password)
        assert info["valid"] is True
