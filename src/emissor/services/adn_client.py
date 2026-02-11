from __future__ import annotations

import base64
import gzip
from typing import Any

from lxml import etree
from requests_pkcs12 import get

from emissor.config import ENDPOINTS

NFSE_NS = {"n": "http://www.sped.fazenda.gov.br/nfse"}


def _check_response(resp: Any, action: str) -> None:
    if not resp.ok:
        body = resp.text[:500] if resp.text else ""
        raise RuntimeError(f"ADN {action} error ({resp.status_code}): {body}")


def query_nfse(
    chave_acesso: str,
    pfx_path: str,
    pfx_password: str,
    env: str = "homologacao",
) -> dict:
    """Query an issued NFS-e by its access key."""
    base = ENDPOINTS[env]["adn"]
    url = f"{base}/contribuintes/NFSe/{chave_acesso}"

    resp = get(
        url,
        pkcs12_filename=pfx_path,
        pkcs12_password=pfx_password,
        timeout=30,
    )
    _check_response(resp, "query")
    return resp.json()


def list_dfe(
    pfx_path: str,
    pfx_password: str,
    nsu: int = 0,
    env: str = "producao",
) -> dict:
    """Fetch distributed DF-e documents starting from a given NSU.

    Uses GET /contribuintes/DFe/{NSU} to retrieve invoices (emitted/received)
    for the CNPJ identified by the certificate. NSU=0 starts from the beginning.

    Returns dict with:
      - LoteDFe: list of docs, each with NSU, ChaveAcesso, TipoDocumento,
                 ArquivoXml (gzip+base64), DataHoraGeracao
      - StatusProcessamento: "DOCUMENTOS_LOCALIZADOS" or "NENHUM_DOCUMENTO_LOCALIZADO"
    Returns empty LoteDFe on 404 (no documents found) instead of raising.
    """
    base = ENDPOINTS[env]["adn"]
    url = f"{base}/contribuintes/DFe/{nsu}"

    resp = get(
        url,
        pkcs12_filename=pfx_path,
        pkcs12_password=pfx_password,
        timeout=30,
    )
    # 404 means no documents found — return the body (has empty LoteDFe)
    if resp.status_code == 404:
        return resp.json()
    _check_response(resp, "list_dfe")
    return resp.json()


def parse_dfe_xml(arquivo_xml_b64: str) -> dict[str, Any]:
    """Decode a gzip+base64 ArquivoXml from DFe and extract metadata."""
    xml_bytes = gzip.decompress(base64.b64decode(arquivo_xml_b64))
    root = etree.fromstring(xml_bytes)

    def txt(xpath: str) -> str:
        return root.findtext(xpath, default="", namespaces=NFSE_NS).strip()

    return {
        "emit_cnpj": txt(".//n:emit/n:CNPJ"),
        "emit_nome": txt(".//n:emit/n:xNome"),
        "toma_cnpj": txt(".//n:toma/n:CNPJ"),
        "toma_nome": txt(".//n:toma/n:xNome"),
        "n_nfse": txt(".//n:infNFSe/n:nNFSe"),
        "competencia": txt(".//n:infDPS/n:dCompet"),
        "valor": txt(".//n:valores/n:vLiq"),
    }


def download_danfse(
    chave_acesso: str,
    pfx_path: str,
    pfx_password: str,
    env: str = "homologacao",
) -> bytes:
    """Download the DANFSE PDF for a given NFS-e access key."""
    base = ENDPOINTS[env]["adn"]
    url = f"{base}/contribuintes/NFSe/{chave_acesso}/PDF"

    resp = get(
        url,
        pkcs12_filename=pfx_path,
        pkcs12_password=pfx_password,
        timeout=30,
    )
    _check_response(resp, "download")
    return resp.content
