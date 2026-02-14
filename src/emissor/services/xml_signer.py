from __future__ import annotations

from lxml import etree
from signxml.algorithms import (
    DigestAlgorithm,
    SignatureConstructionMethod,
    SignatureMethod,
)
from signxml.signer import XMLSigner

from emissor.config import NFSE_NS


def sign_dps(dps: etree._Element, key_pem: bytes, cert_pem: bytes) -> etree._Element:
    """Sign the DPS XML element with enveloped RSA-SHA256 signature.

    Uses Exclusive XML Canonicalization 1.0 WITH Comments as required by SEFIN.
    Returns the signed DPS element.
    """
    inf_dps = dps.find(f"{{{NFSE_NS}}}infDPS")
    if inf_dps is None:
        inf_dps = dps.find("infDPS")
    if inf_dps is None:
        raise ValueError("infDPS element not found in DPS")

    dps_id = inf_dps.get("Id")
    if not dps_id:
        raise ValueError("infDPS is missing Id attribute")

    signer = XMLSigner(
        method=SignatureConstructionMethod.enveloped,
        signature_algorithm=SignatureMethod.RSA_SHA256,
        digest_algorithm=DigestAlgorithm.SHA256,
        c14n_algorithm="http://www.w3.org/2001/10/xml-exc-c14n#WithComments",
    )

    signed = signer.sign(
        dps,
        key=key_pem,
        cert=cert_pem.decode(),
        reference_uri=f"#{dps_id}",
    )

    return signed
