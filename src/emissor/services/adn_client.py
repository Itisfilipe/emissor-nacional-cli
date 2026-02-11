from __future__ import annotations

from requests_pkcs12 import get

from emissor.config import ENDPOINTS


def _check_response(resp, action: str) -> None:
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
