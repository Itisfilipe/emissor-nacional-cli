from __future__ import annotations

import base64
import gzip
import logging
from dataclasses import dataclass, fields
from datetime import datetime

from lxml import etree

from emissor.config import (
    BRT,
    TP_AMB,
    get_cert_password,
    get_cert_path,
    get_issued_dir,
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
from emissor.utils.registry import add_invoice
from emissor.utils.sequence import next_n_dps

logger = logging.getLogger(__name__)


def _now_brt() -> str:
    return datetime.now(BRT).strftime("%Y-%m-%dT%H:%M:%S-03:00")


@dataclass
class PreparedDPS:
    """All data needed for preview and submission."""

    emitter: Emitter
    client: Client
    intermediary: Intermediary | None
    invoice: Invoice
    signed_dps: etree._Element
    signed_xml: bytes
    n_dps: int
    env: str
    pfx_path: str
    pfx_password: str
    client_slug: str = ""


def prepare(
    client_name: str,
    valor_brl: str,
    valor_usd: str,
    competencia: str,
    env: str = "homologacao",
    intermediario: str | None = None,
    overrides: dict[str, str] | None = None,
) -> PreparedDPS:
    """Build, sign, and atomically reserve the sequence number for DPS."""
    emitter = Emitter.from_dict(load_emitter())
    client = Client.from_dict(load_client(client_name))

    intermediary = None
    if intermediario:
        intermediary = Intermediary.from_dict(load_client(intermediario))

    n_dps = next_n_dps(env)
    tp_amb = TP_AMB[env]

    extra = overrides or {}
    invoice = Invoice(
        valor_brl=valor_brl,
        valor_usd=valor_usd,
        competencia=competencia,
        n_dps=n_dps,
        dh_emi=_now_brt(),
        **extra,
    )

    dps = build_dps(emitter, client, invoice, tp_amb, intermediary)

    pfx_path = get_cert_path()
    pfx_password = get_cert_password()
    key_pem, cert_pem, _ = load_pfx(pfx_path, pfx_password)

    signed_dps = sign_dps(dps, key_pem, cert_pem)
    signed_xml = etree.tostring(signed_dps, xml_declaration=True, encoding="utf-8")

    return PreparedDPS(
        emitter=emitter,
        client=client,
        intermediary=intermediary,
        invoice=invoice,
        signed_dps=signed_dps,
        signed_xml=signed_xml,
        n_dps=n_dps,
        env=env,
        pfx_path=pfx_path,
        pfx_password=pfx_password,
        client_slug=client_name,
    )


def _extract_overrides(invoice: Invoice) -> dict[str, str] | None:
    """Extract non-None override fields from an Invoice for registry storage.

    Override fields are all Invoice fields that default to None (i.e. every
    field beyond the five required ones: valor_brl, valor_usd, competencia,
    n_dps, dh_emi).
    """
    overrides = {
        f.name: getattr(invoice, f.name)
        for f in fields(invoice)
        if f.default is None and getattr(invoice, f.name) is not None
    }
    return overrides or None


def submit(prepared: PreparedDPS) -> dict:
    """Encode and send prepared DPS to SEFIN.

    Sequence was already reserved by prepare(), so no increment here.
    """
    encoded = encode_dps(prepared.signed_dps)
    response = emit_nfse(encoded, prepared.pfx_path, prepared.pfx_password, prepared.env)

    result = {
        "n_dps": prepared.n_dps,
        "response": response,
    }

    # Save NFS-e XML from response if present
    nfse_xml = response.get("nfseXmlGZipB64") or response.get("xml")
    if nfse_xml:
        try:
            nfse_bytes = gzip.decompress(base64.b64decode(nfse_xml))
            chave = response.get("chNFSe", f"nfse_{prepared.n_dps}")
            out_path = get_issued_dir(prepared.env) / f"{chave}.xml"
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(nfse_bytes)
            result["saved_to"] = str(out_path)
        except Exception:
            logger.warning("Failed to save NFS-e XML from response", exc_info=True)

    # Register in local invoice registry
    chave = response.get("chNFSe")
    if chave:
        try:
            overrides = _extract_overrides(prepared.invoice)
            add_invoice(
                chave,
                n_dps=prepared.n_dps,
                client=prepared.client.nome,
                client_slug=prepared.client_slug,
                valor_brl=prepared.invoice.valor_brl,
                valor_usd=prepared.invoice.valor_usd,
                competencia=prepared.invoice.competencia,
                emitted_at=prepared.invoice.dh_emi,
                env=prepared.env,
                overrides=overrides,
            )
        except Exception:
            logger.warning("Failed to register invoice", exc_info=True)

    return result


def save_xml(prepared: PreparedDPS) -> str:
    """Save prepared DPS XML to disk without submitting.

    Sequence was already reserved by prepare(), so no increment here.
    """
    out_path = get_issued_dir(prepared.env) / f"dry_run_dps_{prepared.n_dps}.xml"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(prepared.signed_xml)
    return str(out_path)
