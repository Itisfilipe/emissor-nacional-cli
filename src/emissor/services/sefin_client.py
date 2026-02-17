from __future__ import annotations

import json
import logging

from requests_pkcs12 import get, post

from emissor.config import ENDPOINTS, SEFIN_TIMEOUT
from emissor.services.exceptions import SefinRejectError
from emissor.services.http_retry import SEFIN_SUBMIT, retry_call

logger = logging.getLogger(__name__)


def _format_erros(erros: object) -> str:
    """Format an ``erros`` field value as a human-readable string."""
    if isinstance(erros, list):
        return "; ".join(str(e) for e in erros)
    return str(erros)


def _extract_reason(data: dict) -> str:
    """Best-effort extraction of a human-readable rejection reason."""
    for key in ("xMotivo", "mensagem", "message"):
        val = data.get(key)
        if val:
            return str(val)
    erros = data.get("erros")
    if erros:
        return _format_erros(erros)
    return json.dumps(data, ensure_ascii=False)[:200]


def _check_error_payload(data: dict) -> None:
    """Raise SefinRejectError if the response contains known error indicators."""
    erros = data.get("erros")
    if erros:
        raise SefinRejectError(_format_erros(erros), response=data)

    mensagem = data.get("mensagem")
    if mensagem:
        raise SefinRejectError(str(mensagem), response=data)

    c_stat = data.get("cStat")
    if c_stat is not None and str(c_stat) not in ("100", "150"):
        motivo = data.get("xMotivo", "Código de status rejeitado")
        raise SefinRejectError(f"cStat {c_stat}: {motivo}", response=data)


def _validate_response(data: dict) -> None:
    """Validate the SEFIN response body after a successful HTTP call."""
    _check_error_payload(data)

    ch_nfse = data.get("chNFSe")
    if not ch_nfse or not str(ch_nfse).strip():
        reason = _extract_reason(data)
        raise SefinRejectError(
            f"Resposta sem chave de acesso (chNFSe): {reason}",
            response=data,
        )

    if not data.get("nNFSe"):
        logger.warning("Resposta sem nNFSe — usando chNFSe como identificador")


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

    def _do_post():
        return post(
            url,
            json=payload,
            pkcs12_filename=pfx_path,
            pkcs12_password=pfx_password,
            timeout=SEFIN_TIMEOUT,
        )

    resp = retry_call(_do_post, SEFIN_SUBMIT)

    if not resp.ok:
        body = resp.text[:500] if resp.text else ""
        raise RuntimeError(f"SEFIN API error ({resp.status_code}): {body}")

    data = resp.json()
    _validate_response(data)
    return data


def check_sefin_connectivity(
    pfx_path: str,
    pfx_password: str,
    env: str = "homologacao",
) -> None:
    """Test SEFIN API connectivity via mTLS GET to the submit endpoint.

    A non-200 response (e.g. 405) is expected and acceptable — it proves
    the endpoint is reachable and the TLS handshake succeeded.
    Raises on connection or timeout errors.
    """
    url = ENDPOINTS[env]["sefin"]

    def _do_get():
        return get(
            url,
            pkcs12_filename=pfx_path,
            pkcs12_password=pfx_password,
            timeout=SEFIN_TIMEOUT,
        )

    retry_call(_do_get, SEFIN_SUBMIT)
