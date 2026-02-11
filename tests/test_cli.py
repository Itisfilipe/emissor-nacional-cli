from __future__ import annotations

from unittest.mock import patch

import pytest
from click.testing import CliRunner

from emissor.cli import _validate_date, _validate_monetary, cli


class _FakeCtx:
    """Minimal Click context for testing callbacks."""


class _FakeParam:
    name = "test"


@pytest.fixture
def runner():
    return CliRunner()


# --- _validate_monetary ---


class TestValidateMonetary:
    def test_valid(self):
        result = _validate_monetary(_FakeCtx(), _FakeParam(), "19684.93")
        assert result == "19684.93"

    def test_nan(self):
        with pytest.raises(Exception, match="inválido"):
            _validate_monetary(_FakeCtx(), _FakeParam(), "NaN")

    def test_infinity(self):
        with pytest.raises(Exception, match="inválido"):
            _validate_monetary(_FakeCtx(), _FakeParam(), "Infinity")

    def test_non_numeric(self):
        with pytest.raises(Exception, match="inválido"):
            _validate_monetary(_FakeCtx(), _FakeParam(), "abc")

    def test_zero(self):
        with pytest.raises(Exception, match="positivo"):
            _validate_monetary(_FakeCtx(), _FakeParam(), "0")

    def test_negative(self):
        with pytest.raises(Exception, match="positivo"):
            _validate_monetary(_FakeCtx(), _FakeParam(), "-5")

    def test_normalizes(self):
        result = _validate_monetary(_FakeCtx(), _FakeParam(), "100.00")
        assert result == "100"

    def test_preserves_decimals(self):
        result = _validate_monetary(_FakeCtx(), _FakeParam(), "19684.93")
        assert result == "19684.93"

    def test_strips_trailing_zeros(self):
        result = _validate_monetary(_FakeCtx(), _FakeParam(), "1000.10")
        assert result == "1000.1"


# --- _validate_date ---


class TestValidateDate:
    def test_valid(self):
        result = _validate_date(_FakeCtx(), _FakeParam(), "2025-12-30")
        assert result == "2025-12-30"

    def test_invalid(self):
        with pytest.raises(Exception, match="inválida"):
            _validate_date(_FakeCtx(), _FakeParam(), "not-a-date")


# --- CLI commands ---


class TestCliGroup:
    def test_defaults_homologacao(self, runner):
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "homologacao" in result.output


class TestEmitCommand:
    @patch("emissor.services.emission.emit")
    def test_success(self, mock_emit, runner):
        mock_emit.return_value = {
            "n_dps": 1,
            "response": {"chNFSe": "abc", "nNFSe": "123"},
            "dps_xml": "<xml/>",
        }
        result = runner.invoke(
            cli,
            [
                "emit",
                "acme",
                "--valor-brl",
                "1000.00",
                "--valor-usd",
                "200.00",
                "--competencia",
                "2025-12-30",
            ],
        )
        assert result.exit_code == 0
        assert "nDPS: 1" in result.output

    @patch("emissor.services.emission.emit")
    def test_dry_run(self, mock_emit, runner):
        mock_emit.return_value = {
            "n_dps": 1,
            "response": None,
            "saved_to": "/tmp/dry_run_dps_1.xml",
        }
        result = runner.invoke(
            cli,
            [
                "emit",
                "acme",
                "--valor-brl",
                "1000.00",
                "--valor-usd",
                "200.00",
                "--competencia",
                "2025-12-30",
                "--dry-run",
            ],
        )
        assert result.exit_code == 0
        assert "dry_run_dps_1.xml" in result.output

    @patch("emissor.services.emission.emit", side_effect=RuntimeError("API failed"))
    def test_error_exits_1(self, mock_emit, runner):
        result = runner.invoke(
            cli,
            [
                "emit",
                "acme",
                "--valor-brl",
                "1000.00",
                "--valor-usd",
                "200.00",
                "--competencia",
                "2025-12-30",
            ],
        )
        assert result.exit_code == 1
        assert "Erro" in result.output

    @patch("emissor.services.emission.emit")
    def test_with_intermediario(self, mock_emit, runner):
        mock_emit.return_value = {
            "n_dps": 1,
            "response": {"chNFSe": "abc"},
            "dps_xml": "<xml/>",
        }
        result = runner.invoke(
            cli,
            [
                "emit",
                "acme",
                "--valor-brl",
                "1000.00",
                "--valor-usd",
                "200.00",
                "--competencia",
                "2025-12-30",
                "--intermediario",
                "oyster",
            ],
        )
        assert result.exit_code == 0
        mock_emit.assert_called_once()
        _, kwargs = mock_emit.call_args
        assert kwargs["intermediario"] == "oyster"


class TestValidateCommand:
    @patch("emissor.utils.certificate.validate_certificate")
    @patch("emissor.config.get_cert_password", return_value="fakepass")
    @patch("emissor.config.get_cert_path", return_value="/fake.pfx")
    @patch("emissor.config.load_emitter")
    def test_success(self, mock_emitter, mock_path, mock_pw, mock_cert, runner):
        mock_emitter.return_value = {"razao_social": "ACME", "cnpj": "123"}
        mock_cert.return_value = {
            "subject": "CN=Test",
            "issuer": "CN=Test",
            "not_before": "2025-01-01",
            "not_after": "2026-01-01",
            "valid": True,
            "serial": 12345,
        }
        result = runner.invoke(cli, ["validate"])
        assert result.exit_code == 0
        assert "OK" in result.output

    @patch("emissor.config.get_cert_path", side_effect=KeyError("CERT_PFX_PATH"))
    @patch("emissor.config.load_emitter")
    def test_missing_cert_exits_1(self, mock_emitter, mock_path, runner):
        mock_emitter.return_value = {"razao_social": "ACME", "cnpj": "123"}
        result = runner.invoke(cli, ["validate"])
        assert result.exit_code == 1
        assert "CERT_PFX_PATH" in result.output


class TestQueryCommand:
    @patch("emissor.services.adn_client.query_nfse")
    @patch("emissor.config.get_cert_password", return_value="fakepass")
    @patch("emissor.config.get_cert_path", return_value="/fake.pfx")
    def test_success(self, mock_path, mock_pw, mock_query, runner):
        mock_query.return_value = {"chNFSe": "key123", "status": "ok"}
        result = runner.invoke(cli, ["query", "key123"])
        assert result.exit_code == 0
        assert "key123" in result.output


class TestPdfCommand:
    @patch("emissor.services.adn_client.download_danfse")
    @patch("emissor.config.get_cert_password", return_value="fakepass")
    @patch("emissor.config.get_cert_path", return_value="/fake.pfx")
    def test_success(self, mock_path, mock_pw, mock_download, runner, tmp_path):
        mock_download.return_value = b"%PDF-1.4 fake"
        output = tmp_path / "out.pdf"
        result = runner.invoke(cli, ["pdf", "key123", "-o", str(output)])
        assert result.exit_code == 0
        assert output.exists()
        assert output.read_bytes() == b"%PDF-1.4 fake"
