from __future__ import annotations

import base64
import gzip

from lxml import etree


def encode_dps(signed_dps: etree._Element) -> str:
    """GZip compress and Base64 encode the signed DPS XML.

    Returns the Base64-encoded string ready for the SEFIN API payload.
    """
    xml_bytes = etree.tostring(
        signed_dps,
        xml_declaration=True,
        encoding="utf-8",
    )
    compressed = gzip.compress(xml_bytes)
    return base64.b64encode(compressed).decode("ascii")
