from __future__ import annotations

import base64
import gzip
import logging
from datetime import datetime, timedelta, timezone

from lxml import etree

from emissor.config import (
    DATA_DIR,
    TP_AMB,
    get_cert_password,
    get_cert_path,
    load_client,
    load_emitter,
)
from emissor.models.client import Client, Intermediary
from emissor.models.emitter import Emitter
from emissor.models.invoice import Invoice
from emissor.services.dps_builder import build_dps
from emissor.services.sefin_client import emit_nfse
from emissor.services.xml_encoder import encode_dps
from emissor.services.xml_signer import sign_dps
from emissor.utils.certificate import load_pfx
from emissor.utils.sequence import next_n_dps, peek_next_n_dps

logger = logging.getLogger(__name__)

BRT = timezone(timedelta(hours=-3))


def _now_brt() -> str:
    return datetime.now(BRT).strftime("%Y-%m-%dT%H:%M:%S-03:00")


def emit(
    client_name: str,
    valor_brl: str,
    valor_usd: str,
    competencia: str,
    env: str = "homologacao",
    intermediario: str | None = None,
    dry_run: bool = False,
) -> dict:
    """Full emission flow: build → sign → encode → send.

    Returns a dict with keys:
        - dps_xml: the signed DPS XML string
        - response: the SEFIN API response (None if dry_run)
        - n_dps: the sequence number used
    """
    emitter = Emitter.from_dict(load_emitter())
    client = Client.from_dict(load_client(client_name))

    intermediary = None
    if intermediario:
        intermediary = Intermediary.from_dict(load_client(intermediario))

    n_dps = peek_next_n_dps() if dry_run else next_n_dps()
    tp_amb = TP_AMB[env]

    invoice = Invoice(
        valor_brl=valor_brl,
        valor_usd=valor_usd,
        competencia=competencia,
        n_dps=n_dps,
        dh_emi=_now_brt(),
    )

    dps = build_dps(emitter, client, invoice, tp_amb, intermediary)

    pfx_path = get_cert_path()
    pfx_password = get_cert_password()
    key_pem, cert_pem, _ = load_pfx(pfx_path, pfx_password)

    signed_dps = sign_dps(dps, key_pem, cert_pem)
    signed_xml = etree.tostring(signed_dps, xml_declaration=True, encoding="utf-8")

    result = {
        "dps_xml": signed_xml.decode("utf-8"),
        "n_dps": n_dps,
        "response": None,
    }

    if dry_run:
        out_path = DATA_DIR / "issued" / f"dry_run_dps_{n_dps}.xml"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(signed_xml)
        result["saved_to"] = str(out_path)
        return result

    encoded = encode_dps(signed_dps)
    response = emit_nfse(encoded, pfx_path, pfx_password, env)
    result["response"] = response

    # Save NFS-e XML from response if present
    nfse_xml = response.get("nfseXmlGZipB64") or response.get("xml")
    if nfse_xml:
        try:
            nfse_bytes = gzip.decompress(base64.b64decode(nfse_xml))
            chave = response.get("chNFSe", f"nfse_{n_dps}")
            out_path = DATA_DIR / "issued" / f"{chave}.xml"
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(nfse_bytes)
            result["saved_to"] = str(out_path)
        except Exception:
            logger.warning("Failed to save NFS-e XML from response", exc_info=True)

    return result
