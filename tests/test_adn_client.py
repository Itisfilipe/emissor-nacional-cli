from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from emissor.services.adn_client import _check_response, download_danfse, query_nfse


def _mock_response(
    ok: bool = True, status_code: int = 200, json_data=None, text: str = "", content: bytes = b""
):
    resp = MagicMock()
    resp.ok = ok
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.text = text
    resp.content = content
    return resp


class TestQueryNfse:
    @patch("emissor.services.adn_client.get")
    def test_success(self, mock_get):
        mock_get.return_value = _mock_response(json_data={"chNFSe": "key123"})
        result = query_nfse("key123", "/cert.pfx", "pass")
        assert result == {"chNFSe": "key123"}

    @patch("emissor.services.adn_client.get")
    def test_url(self, mock_get):
        mock_get.return_value = _mock_response()
        query_nfse("CHAVE123", "/cert.pfx", "pass", env="homologacao")
        url = mock_get.call_args[0][0]
        assert url.endswith("/contribuintes/NFSe/CHAVE123")

    @patch("emissor.services.adn_client.get")
    def test_http_error(self, mock_get):
        mock_get.return_value = _mock_response(ok=False, status_code=404, text="Not Found")
        with pytest.raises(RuntimeError, match=r"ADN query error.*404"):
            query_nfse("key", "/cert.pfx", "pass")

    @patch("emissor.services.adn_client.get")
    def test_producao(self, mock_get):
        mock_get.return_value = _mock_response()
        query_nfse("key", "/cert.pfx", "pass", env="producao")
        url = mock_get.call_args[0][0]
        assert "adn.nfse.gov.br" in url


class TestDownloadDanfse:
    @patch("emissor.services.adn_client.get")
    def test_success(self, mock_get):
        mock_get.return_value = _mock_response(content=b"%PDF-1.4 fake pdf")
        result = download_danfse("key123", "/cert.pfx", "pass")
        assert result == b"%PDF-1.4 fake pdf"

    @patch("emissor.services.adn_client.get")
    def test_url(self, mock_get):
        mock_get.return_value = _mock_response()
        download_danfse("CHAVE123", "/cert.pfx", "pass")
        url = mock_get.call_args[0][0]
        assert url.endswith("/contribuintes/NFSe/CHAVE123/PDF")

    @patch("emissor.services.adn_client.get")
    def test_http_error(self, mock_get):
        mock_get.return_value = _mock_response(ok=False, status_code=500, text="Error")
        with pytest.raises(RuntimeError, match=r"ADN download error.*500"):
            download_danfse("key", "/cert.pfx", "pass")


class TestCheckResponse:
    def test_ok(self):
        resp = _mock_response(ok=True)
        _check_response(resp, "test")  # should not raise
