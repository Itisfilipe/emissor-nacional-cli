from __future__ import annotations

import base64
import gzip

from lxml import etree

from emissor.services.xml_encoder import encode_dps


def test_encode_roundtrip():
    root = etree.Element("test")
    root.text = "hello world"

    encoded = encode_dps(root)

    # Should be valid base64
    decoded = base64.b64decode(encoded)
    # Should be valid gzip
    xml_bytes = gzip.decompress(decoded)
    # Should contain original content
    assert b"hello world" in xml_bytes
    assert b"<test>" in xml_bytes
