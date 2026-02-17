from __future__ import annotations

import base64
import gzip
from unittest.mock import MagicMock, call, patch

import pytest
import requests.exceptions

from emissor.services.adn_client import (
    _check_response,
    _fetch_dfe_page,
    check_connectivity,
    download_danfse,
    iter_dfe,
    list_dfe,
    query_nfse,
)

NFSE_XML = b"""\
<NFSe xmlns="http://www.sped.fazenda.gov.br/nfse">
  <infNFSe><nNFSe>1</nNFSe></infNFSe>
  <emit><CNPJ>11111111000100</CNPJ><xNome>Emitter</xNome></emit>
  <toma><CNPJ>22222222000200</CNPJ><xNome>Taker</xNome></toma>
  <infDPS><dCompet>2025-12-30</dCompet></infDPS>
  <valores><vLiq>1000.00</vLiq></valores>
</NFSe>
"""
NFSE_GZ_B64 = base64.b64encode(gzip.compress(NFSE_XML)).decode()


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


def _make_doc(chave: str, nsu: int) -> dict:
    return {
        "ChaveAcesso": chave,
        "ArquivoXml": NFSE_GZ_B64,
        "NSU": nsu,
        "DataHoraGeracao": "2025-12-30T10:00:00",
        "TipoDocumento": "NFSE",
    }


class TestQueryNfse:
    @patch("emissor.services.adn_client.iter_dfe")
    def test_success(self, mock_iter):
        mock_iter.return_value = iter([_make_doc("key123", 1)])
        result = query_nfse("key123", "/cert.pfx", "pass")
        assert result["chave"] == "key123"
        assert result["emit_cnpj"] == "11111111000100"
        assert result["valor"] == "1000.00"

    @patch("emissor.services.adn_client.iter_dfe")
    def test_not_found(self, mock_iter):
        mock_iter.return_value = iter([])
        with pytest.raises(RuntimeError, match="não encontrada"):
            query_nfse("missing_key", "/cert.pfx", "pass")

    @patch("emissor.services.adn_client.iter_dfe")
    def test_passes_env(self, mock_iter):
        mock_iter.return_value = iter([])
        with pytest.raises(RuntimeError):
            query_nfse("key", "/cert.pfx", "pass", env="producao")
        mock_iter.assert_called_once_with("/cert.pfx", "pass", nsu=0, env="producao")

    @patch("emissor.services.adn_client.iter_dfe")
    def test_start_nsu(self, mock_iter):
        mock_iter.return_value = iter([_make_doc("key456", 50)])
        result = query_nfse("key456", "/cert.pfx", "pass", start_nsu=42)
        assert result["chave"] == "key456"
        mock_iter.assert_called_once_with("/cert.pfx", "pass", nsu=42, env="homologacao")


class TestListDfe:
    @patch("emissor.services.adn_client._fetch_dfe_page")
    def test_single_page(self, mock_fetch):
        mock_fetch.side_effect = [
            {"LoteDFe": [_make_doc("a", 1), _make_doc("b", 2)]},
            {"LoteDFe": []},
        ]
        result = list_dfe("/cert.pfx", "pass", nsu=0, env="producao")
        assert len(result["LoteDFe"]) == 2
        assert result["StatusProcessamento"] == "DOCUMENTOS_LOCALIZADOS"

    @patch("emissor.services.adn_client._fetch_dfe_page")
    def test_pagination(self, mock_fetch):
        mock_fetch.side_effect = [
            {"LoteDFe": [_make_doc("a", 1), _make_doc("b", 2)]},
            {"LoteDFe": [_make_doc("c", 3)]},
            {"LoteDFe": []},
        ]
        result = list_dfe("/cert.pfx", "pass", nsu=0, env="producao")
        assert len(result["LoteDFe"]) == 3
        assert mock_fetch.call_count == 3
        # NSU progression: 0, 2 (max of first batch), 3 (max of second)
        assert mock_fetch.call_args_list == [
            call("/cert.pfx", "pass", 0, "producao"),
            call("/cert.pfx", "pass", 2, "producao"),
            call("/cert.pfx", "pass", 3, "producao"),
        ]

    @patch("emissor.services.adn_client._fetch_dfe_page")
    def test_empty(self, mock_fetch):
        mock_fetch.return_value = {"LoteDFe": []}
        result = list_dfe("/cert.pfx", "pass")
        assert result["StatusProcessamento"] == "NENHUM_DOCUMENTO_LOCALIZADO"
        assert result["LoteDFe"] == []

    @patch("emissor.services.adn_client.get")
    def test_fetch_page_url(self, mock_get):
        mock_get.return_value = _mock_response(json_data={"LoteDFe": []})
        _fetch_dfe_page("/cert.pfx", "pass", 5, "homologacao")
        url = mock_get.call_args[0][0]
        assert "producaorestrita" in url
        assert url.endswith("/contribuintes/DFe/5")

    @patch("emissor.services.adn_client.get")
    def test_fetch_page_404_returns_body(self, mock_get):
        mock_get.return_value = _mock_response(
            ok=False, status_code=404, json_data={"LoteDFe": []}
        )
        result = _fetch_dfe_page("/cert.pfx", "pass", 0, "producao")
        assert result == {"LoteDFe": []}


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
        assert url.endswith("/danfse/CHAVE123")

    @patch("emissor.services.adn_client.get")
    def test_http_error(self, mock_get):
        mock_get.return_value = _mock_response(ok=False, status_code=500, text="Error")
        with pytest.raises(RuntimeError, match=r"ADN download error.*500"):
            download_danfse("key", "/cert.pfx", "pass")


class TestCheckConnectivity:
    @patch("emissor.services.adn_client._fetch_dfe_page")
    def test_success(self, mock_fetch):
        mock_fetch.return_value = {"LoteDFe": []}
        check_connectivity("/cert.pfx", "pass", "homologacao")
        mock_fetch.assert_called_once_with("/cert.pfx", "pass", 0, "homologacao")

    @patch("emissor.services.adn_client._fetch_dfe_page")
    def test_error(self, mock_fetch):
        mock_fetch.side_effect = RuntimeError("Connection refused")
        with pytest.raises(RuntimeError, match="Connection refused"):
            check_connectivity("/cert.pfx", "pass", "producao")


class TestEnvDefaults:
    """Verify all public functions default to homologacao."""

    @pytest.mark.parametrize(
        "func",
        [iter_dfe, list_dfe, query_nfse, download_danfse, check_connectivity],
        ids=lambda f: f.__name__,
    )
    def test_env_defaults_to_homologacao(self, func):
        import inspect

        sig = inspect.signature(func)
        assert sig.parameters["env"].default == "homologacao"


class TestCheckResponse:
    def test_ok(self):
        resp = _mock_response(ok=True)
        _check_response(resp, "test")  # should not raise

    def test_retryable_status_raises_retryable_error(self):
        from emissor.services.http_retry import RetryableHTTPError

        resp = _mock_response(ok=False, status_code=503, text="Service Unavailable")
        with pytest.raises(RetryableHTTPError, match="503"):
            _check_response(resp, "test")

    def test_non_retryable_status_raises_runtime_error(self):
        resp = _mock_response(ok=False, status_code=400, text="Bad Request")
        with pytest.raises(RuntimeError, match="400"):
            _check_response(resp, "test")


class TestAdnRetry:
    @patch("emissor.services.adn_client.get")
    def test_fetch_page_retries_connection_error(self, mock_get):
        mock_get.side_effect = [
            requests.exceptions.ConnectionError("reset"),
            _mock_response(json_data={"LoteDFe": []}),
        ]
        result = _fetch_dfe_page("/cert.pfx", "pass", 0, "homologacao")
        assert result == {"LoteDFe": []}
        assert mock_get.call_count == 2

    @patch("emissor.services.adn_client.get")
    def test_fetch_page_retries_503(self, mock_get):
        mock_get.side_effect = [
            _mock_response(ok=False, status_code=503, text="Unavailable"),
            _mock_response(json_data={"LoteDFe": [_make_doc("a", 1)]}),
        ]
        result = _fetch_dfe_page("/cert.pfx", "pass", 0, "homologacao")
        assert len(result["LoteDFe"]) == 1
        assert mock_get.call_count == 2

    @patch("emissor.services.adn_client.get")
    def test_fetch_page_retries_429(self, mock_get):
        mock_get.side_effect = [
            _mock_response(ok=False, status_code=429, text="Rate limited"),
            _mock_response(json_data={"LoteDFe": []}),
        ]
        result = _fetch_dfe_page("/cert.pfx", "pass", 0, "homologacao")
        assert result == {"LoteDFe": []}
        assert mock_get.call_count == 2

    @patch("emissor.services.adn_client.get")
    def test_fetch_page_does_not_retry_400(self, mock_get):
        mock_get.return_value = _mock_response(ok=False, status_code=400, text="Bad Request")
        with pytest.raises(RuntimeError, match="400"):
            _fetch_dfe_page("/cert.pfx", "pass", 0, "homologacao")
        assert mock_get.call_count == 1

    @patch("emissor.services.adn_client.get")
    def test_fetch_page_404_not_retried(self, mock_get):
        mock_get.return_value = _mock_response(
            ok=False, status_code=404, json_data={"LoteDFe": []}
        )
        result = _fetch_dfe_page("/cert.pfx", "pass", 0, "homologacao")
        assert result == {"LoteDFe": []}
        assert mock_get.call_count == 1

    @patch("emissor.services.adn_client.get")
    def test_download_retries_connection_error(self, mock_get):
        mock_get.side_effect = [
            requests.exceptions.ConnectionError("reset"),
            _mock_response(content=b"%PDF"),
        ]
        result = download_danfse("key123", "/cert.pfx", "pass")
        assert result == b"%PDF"
        assert mock_get.call_count == 2
