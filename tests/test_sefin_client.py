from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from emissor.services.sefin_client import emit_nfse


def _mock_response(ok: bool = True, status_code: int = 200, json_data=None, text: str = ""):
    resp = MagicMock()
    resp.ok = ok
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.text = text
    return resp


class TestEmitNfse:
    @patch("emissor.services.sefin_client.post")
    def test_success(self, mock_post):
        mock_post.return_value = _mock_response(json_data={"chNFSe": "abc123"})
        result = emit_nfse("b64data", "/cert.pfx", "pass")
        assert result == {"chNFSe": "abc123"}

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
        with pytest.raises(RuntimeError, match=r"SEFIN API error.*400"):
            emit_nfse("b64", "/cert.pfx", "pass")

    @patch("emissor.services.sefin_client.post")
    def test_truncates_body(self, mock_post):
        long_body = "x" * 1000
        mock_post.return_value = _mock_response(ok=False, status_code=500, text=long_body)
        with pytest.raises(RuntimeError) as exc_info:
            emit_nfse("b64", "/cert.pfx", "pass")
        # Body in error message should be truncated to 500 chars
        error_msg = str(exc_info.value)
        # The body part after the status code prefix
        assert len(long_body[:500]) == 500
        assert "x" * 500 in error_msg
        assert "x" * 501 not in error_msg

    @patch("emissor.services.sefin_client.post")
    def test_passes_pkcs12_args(self, mock_post):
        mock_post.return_value = _mock_response()
        emit_nfse("b64", "/my/cert.pfx", "mypass")
        _, kwargs = mock_post.call_args
        assert kwargs["pkcs12_filename"] == "/my/cert.pfx"
        assert kwargs["pkcs12_password"] == "mypass"
