from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests.exceptions

from emissor.services.exceptions import SefinRejectError
from emissor.services.sefin_client import check_sefin_connectivity, emit_nfse

_VALID_RESPONSE = {"chNFSe": "test", "nNFSe": "1", "cStat": "100"}


def _mock_response(ok: bool = True, status_code: int = 200, json_data=None, text: str = ""):
    resp = MagicMock()
    resp.ok = ok
    resp.status_code = status_code
    resp.json.return_value = json_data if json_data is not None else _VALID_RESPONSE
    resp.text = text
    return resp


class TestEmitNfse:
    @patch("emissor.services.sefin_client.post")
    def test_success(self, mock_post):
        mock_post.return_value = _mock_response(
            json_data={"chNFSe": "abc123", "nNFSe": "1", "cStat": "100"}
        )
        result = emit_nfse("b64data", "/cert.pfx", "pass")
        assert result["chNFSe"] == "abc123"

    @patch("emissor.services.sefin_client.post")
    def test_correct_payload(self, mock_post):
        mock_post.return_value = _mock_response()
        emit_nfse("my_encoded_dps", "/cert.pfx", "pass")
        _, kwargs = mock_post.call_args
        assert kwargs["json"] == {"dpsXmlGZipB64": "my_encoded_dps"}

    @patch("emissor.services.sefin_client.post")
    def test_homologacao_url(self, mock_post):
        mock_post.return_value = _mock_response()
        emit_nfse("b64", "/cert.pfx", "pass", env="homologacao")
        url = mock_post.call_args[0][0]
        assert "producaorestrita" in url

    @patch("emissor.services.sefin_client.post")
    def test_producao_url(self, mock_post):
        mock_post.return_value = _mock_response()
        emit_nfse("b64", "/cert.pfx", "pass", env="producao")
        url = mock_post.call_args[0][0]
        assert url == "https://sefin.nfse.gov.br/SefinNacional/nfse"

    @patch("emissor.services.sefin_client.post")
    def test_http_error(self, mock_post):
        mock_post.return_value = _mock_response(ok=False, status_code=400, text="Bad Request")
        with pytest.raises(RuntimeError, match=r"Erro na API SEFIN.*400"):
            emit_nfse("b64", "/cert.pfx", "pass")

    @patch("emissor.services.sefin_client.post")
    def test_truncates_body(self, mock_post):
        long_body = "x" * 1000
        mock_post.return_value = _mock_response(ok=False, status_code=500, text=long_body)
        with pytest.raises(RuntimeError) as exc_info:
            emit_nfse("b64", "/cert.pfx", "pass")
        error_msg = str(exc_info.value)
        assert "x" * 500 in error_msg
        assert "x" * 501 not in error_msg

    @patch("emissor.services.sefin_client.post")
    def test_passes_pkcs12_args(self, mock_post):
        mock_post.return_value = _mock_response()
        emit_nfse("b64", "/my/cert.pfx", "mypass")
        _, kwargs = mock_post.call_args
        assert kwargs["pkcs12_filename"] == "/my/cert.pfx"
        assert kwargs["pkcs12_password"] == "mypass"

    # --- Response validation tests ---

    @patch("emissor.services.sefin_client.post")
    def test_missing_ch_nfse_raises_reject(self, mock_post):
        mock_post.return_value = _mock_response(json_data={"nNFSe": "42", "cStat": "100"})
        with pytest.raises(SefinRejectError, match="chNFSe"):
            emit_nfse("b64", "/cert.pfx", "pass")

    @patch("emissor.services.sefin_client.post")
    def test_blank_ch_nfse_raises_reject(self, mock_post):
        mock_post.return_value = _mock_response(json_data={"chNFSe": "", "cStat": "100"})
        with pytest.raises(SefinRejectError, match="chNFSe"):
            emit_nfse("b64", "/cert.pfx", "pass")

    @patch("emissor.services.sefin_client.post")
    def test_error_payload_erros_field(self, mock_post):
        mock_post.return_value = _mock_response(
            json_data={"erros": ["DPS inválida", "CNPJ divergente"]}
        )
        with pytest.raises(SefinRejectError, match="DPS inválida"):
            emit_nfse("b64", "/cert.pfx", "pass")

    @patch("emissor.services.sefin_client.post")
    def test_error_payload_mensagem_field(self, mock_post):
        mock_post.return_value = _mock_response(json_data={"mensagem": "Certificado expirado"})
        with pytest.raises(SefinRejectError, match="Certificado expirado"):
            emit_nfse("b64", "/cert.pfx", "pass")

    @patch("emissor.services.sefin_client.post")
    def test_error_payload_cstat_rejection(self, mock_post):
        mock_post.return_value = _mock_response(
            json_data={"cStat": "204", "xMotivo": "Rejeicao: CNPJ invalido", "chNFSe": "x"}
        )
        with pytest.raises(SefinRejectError, match="cStat 204"):
            emit_nfse("b64", "/cert.pfx", "pass")

    @patch("emissor.services.sefin_client.post")
    def test_cstat_100_succeeds(self, mock_post):
        mock_post.return_value = _mock_response(
            json_data={"cStat": "100", "chNFSe": "abc123", "nNFSe": "1"}
        )
        result = emit_nfse("b64", "/cert.pfx", "pass")
        assert result["chNFSe"] == "abc123"

    @patch("emissor.services.sefin_client.post")
    def test_reject_error_carries_response(self, mock_post):
        payload = {"erros": ["bad data"]}
        mock_post.return_value = _mock_response(json_data=payload)
        with pytest.raises(SefinRejectError) as exc_info:
            emit_nfse("b64", "/cert.pfx", "pass")
        assert exc_info.value.response == payload

    @patch("emissor.services.sefin_client.post")
    def test_missing_n_nfse_raises_reject(self, mock_post):
        mock_post.return_value = _mock_response(json_data={"chNFSe": "abc123", "cStat": "100"})
        with pytest.raises(SefinRejectError, match="nNFSe"):
            emit_nfse("b64", "/cert.pfx", "pass")

    @patch("emissor.services.sefin_client.post")
    def test_missing_cstat_raises_reject(self, mock_post):
        mock_post.return_value = _mock_response(json_data={"chNFSe": "abc123", "nNFSe": "1"})
        with pytest.raises(SefinRejectError, match="cStat"):
            emit_nfse("b64", "/cert.pfx", "pass")

    @patch("emissor.services.sefin_client.post")
    def test_empty_response_raises_reject(self, mock_post):
        mock_post.return_value = _mock_response(json_data={})
        with pytest.raises(SefinRejectError, match="cStat"):
            emit_nfse("b64", "/cert.pfx", "pass")


class TestEmitNfseRetry:
    @patch("emissor.services.sefin_client.post")
    def test_retries_connection_error_then_succeeds(self, mock_post):
        mock_post.side_effect = [
            requests.exceptions.ConnectionError("reset"),
            _mock_response(json_data={"chNFSe": "abc123", "nNFSe": "1", "cStat": "100"}),
        ]
        result = emit_nfse("b64", "/cert.pfx", "pass")
        assert result["chNFSe"] == "abc123"
        assert mock_post.call_count == 2

    @patch("emissor.services.sefin_client.post")
    def test_does_not_retry_http_500(self, mock_post):
        """An HTTP response (even 500) means server received request — no retry."""
        mock_post.return_value = _mock_response(ok=False, status_code=500, text="Error")
        with pytest.raises(RuntimeError, match="Erro na API SEFIN"):
            emit_nfse("b64", "/cert.pfx", "pass")
        assert mock_post.call_count == 1

    @patch("emissor.services.sefin_client.post")
    def test_does_not_retry_read_timeout(self, mock_post):
        """ReadTimeout is ambiguous — server may have received request."""
        mock_post.side_effect = requests.exceptions.ReadTimeout("read timed out")
        with pytest.raises(requests.exceptions.ReadTimeout):
            emit_nfse("b64", "/cert.pfx", "pass")
        assert mock_post.call_count == 1

    @patch("emissor.services.sefin_client.post")
    def test_retries_connect_timeout(self, mock_post):
        """ConnectTimeout inherits from ConnectionError — safe to retry."""
        mock_post.side_effect = [
            requests.exceptions.ConnectTimeout("connect timed out"),
            _mock_response(json_data={"chNFSe": "abc123", "nNFSe": "1", "cStat": "100"}),
        ]
        result = emit_nfse("b64", "/cert.pfx", "pass")
        assert result["chNFSe"] == "abc123"
        assert mock_post.call_count == 2


class TestCheckSefinConnectivity:
    @patch("emissor.services.sefin_client.get")
    def test_success_on_405(self, mock_get):
        """A 405 Method Not Allowed still proves connectivity — no exception."""
        mock_get.return_value = _mock_response(ok=False, status_code=405)
        check_sefin_connectivity("/cert.pfx", "pass")

    @patch("emissor.services.sefin_client.get")
    def test_connection_error_propagates(self, mock_get):
        """ConnectionError should propagate after retries exhausted."""
        mock_get.side_effect = requests.exceptions.ConnectionError("refused")
        with pytest.raises(requests.exceptions.ConnectionError):
            check_sefin_connectivity("/cert.pfx", "pass")

    @patch("emissor.services.sefin_client.get")
    def test_accepts_any_http_status(self, mock_get):
        """Any HTTP response (even 500) means the endpoint is reachable."""
        mock_get.return_value = _mock_response(ok=False, status_code=500)
        check_sefin_connectivity("/cert.pfx", "pass")
