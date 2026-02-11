from __future__ import annotations

from requests_pkcs12 import post

from emissor.config import ENDPOINTS


def emit_nfse(
    dps_b64: str,
    pfx_path: str,
    pfx_password: str,
    env: str = "homologacao",
) -> dict:
    """Send the signed+encoded DPS to SEFIN and return the response.

    Uses mTLS with the .pfx certificate.
    """
    url = ENDPOINTS[env]["sefin"]
    payload = {"dpsXmlGZipB64": dps_b64}

    resp = post(
        url,
        json=payload,
        pkcs12_filename=pfx_path,
        pkcs12_password=pfx_password,
        timeout=60,
    )

    if not resp.ok:
        body = resp.text[:500] if resp.text else ""
        raise RuntimeError(f"SEFIN API error ({resp.status_code}): {body}")
    return resp.json()
