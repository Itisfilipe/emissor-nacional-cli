from __future__ import annotations

import base64
import gzip
from collections.abc import Iterator
from typing import Any

from lxml import etree
from requests_pkcs12 import get

from emissor.config import ADN_TIMEOUT, ENDPOINTS, NFSE_NS
from emissor.services.http_retry import ADN_READ, RetryableHTTPError, retry_call

_NFSE_XPATH_NS = {"n": NFSE_NS}


def _check_response(resp: Any, action: str) -> None:
    if not resp.ok:
        body = resp.text[:500] if resp.text else ""
        if resp.status_code in ADN_READ.retryable_status_codes:
            raise RetryableHTTPError(f"Erro ADN {action} ({resp.status_code}): {body}")
        raise RuntimeError(f"Erro ADN {action} ({resp.status_code}): {body}")


def query_nfse(
    chave_acesso: str,
    pfx_path: str,
    pfx_password: str,
    env: str = "homologacao",
    start_nsu: int = 0,
) -> dict:
    """Query an NFS-e by its access key via DFe distribution.

    The ADN API has no direct query-by-chave endpoint. We fetch DFe
    documents (paginated) starting from *start_nsu* and find the one
    matching the requested chave.  Callers should pass the invoice's
    known NSU (from the local registry) to avoid scanning from zero.
    """
    for doc in iter_dfe(pfx_path, pfx_password, nsu=start_nsu, env=env):
        if doc.get("ChaveAcesso") == chave_acesso:
            meta = parse_dfe_xml(doc["ArquivoXml"])
            meta["chave"] = chave_acesso
            meta["nsu"] = doc.get("NSU")
            meta["data_hora"] = doc.get("DataHoraGeracao")
            meta["tipo_documento"] = doc.get("TipoDocumento")
            return meta
    raise RuntimeError(f"NFS-e não encontrada para chave {chave_acesso[:20]}…")


def _fetch_dfe_page(
    pfx_path: str,
    pfx_password: str,
    nsu: int,
    env: str,
) -> dict:
    """Fetch a single page of DFe documents starting from NSU."""
    base = ENDPOINTS[env]["adn"]
    url = f"{base}/contribuintes/DFe/{nsu}"

    def _do_get():
        resp = get(
            url,
            pkcs12_filename=pfx_path,
            pkcs12_password=pfx_password,
            timeout=ADN_TIMEOUT,
        )
        if resp.status_code != 404:
            _check_response(resp, "list_dfe")
        return resp.json()

    return retry_call(_do_get, ADN_READ)


def iter_dfe(
    pfx_path: str,
    pfx_password: str,
    nsu: int = 0,
    env: str = "homologacao",
) -> Iterator[dict[str, Any]]:
    """Yield all DFe documents, paginating automatically.

    Each yielded item is a dict with NSU, ChaveAcesso, TipoDocumento,
    ArquivoXml (gzip+base64), DataHoraGeracao.
    """
    while True:
        data = _fetch_dfe_page(pfx_path, pfx_password, nsu, env)
        docs = data.get("LoteDFe", [])
        if not docs:
            return
        yield from docs
        max_nsu = max(d.get("NSU", 0) for d in docs)
        if max_nsu <= nsu:
            return
        nsu = max_nsu


def list_dfe(
    pfx_path: str,
    pfx_password: str,
    nsu: int = 0,
    env: str = "homologacao",
) -> dict:
    """Fetch all distributed DF-e documents starting from a given NSU.

    Paginates automatically. Returns a dict with LoteDFe containing all docs.
    """
    all_docs = list(iter_dfe(pfx_path, pfx_password, nsu, env))
    status = "DOCUMENTOS_LOCALIZADOS" if all_docs else "NENHUM_DOCUMENTO_LOCALIZADO"
    return {"LoteDFe": all_docs, "StatusProcessamento": status}


def parse_dfe_xml(arquivo_xml_b64: str) -> dict[str, Any]:
    """Decode a gzip+base64 ArquivoXml from DFe and extract metadata."""
    xml_bytes = gzip.decompress(base64.b64decode(arquivo_xml_b64))
    root = etree.fromstring(xml_bytes)

    def txt(xpath: str) -> str:
        return root.findtext(xpath, default="", namespaces=_NFSE_XPATH_NS).strip()

    return {
        "emit_cnpj": txt(".//n:emit/n:CNPJ"),
        "emit_nome": txt(".//n:emit/n:xNome"),
        "toma_cnpj": txt(".//n:toma/n:CNPJ"),
        "toma_nome": txt(".//n:toma/n:xNome"),
        "n_nfse": txt(".//n:infNFSe/n:nNFSe"),
        "competencia": txt(".//n:infDPS/n:dCompet"),
        "valor": txt(".//n:valores/n:vLiq"),
    }


def check_connectivity(
    pfx_path: str,
    pfx_password: str,
    env: str = "homologacao",
) -> None:
    """Test ADN API connectivity by fetching DFe page at NSU 0.

    Raises RuntimeError on failure.
    """
    _fetch_dfe_page(pfx_path, pfx_password, 0, env)


def download_danfse(
    chave_acesso: str,
    pfx_path: str,
    pfx_password: str,
    env: str = "homologacao",
) -> bytes:
    """Download the DANFSE PDF for a given NFS-e access key."""
    base = ENDPOINTS[env]["adn"]
    url = f"{base}/danfse/{chave_acesso}"

    def _do_get():
        resp = get(
            url,
            pkcs12_filename=pfx_path,
            pkcs12_password=pfx_password,
            timeout=ADN_TIMEOUT,
        )
        _check_response(resp, "download")
        return resp.content

    return retry_call(_do_get, ADN_READ)
