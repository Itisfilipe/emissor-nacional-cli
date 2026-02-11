from __future__ import annotations

from unittest.mock import patch

import pytest
from lxml import etree

from emissor.services.xml_signer import sign_dps


def _make_dps(dps_id: str = "DPS420540721234567800019900900000000000000001") -> etree._Element:
    """Build a minimal DPS element for signing tests."""
    dps = etree.Element("DPS")
    dps.set("versao", "1.00")
    inf = etree.SubElement(dps, "infDPS")
    inf.set("Id", dps_id)
    etree.SubElement(inf, "tpAmb").text = "2"
    etree.SubElement(inf, "serie").text = "900"
    return dps


class TestSignDps:
    @patch("emissor.services.xml_signer.XMLSigner")
    def test_adds_signature(self, mock_signer_cls, self_signed_pem):
        key_pem, cert_pem = self_signed_pem
        dps = _make_dps()
        # Make mock signer return element with a Signature child
        signed_el = etree.Element("DPS")
        etree.SubElement(signed_el, "infDPS").set("Id", "DPS1")
        etree.SubElement(signed_el, "{http://www.w3.org/2000/09/xmldsig#}Signature")
        mock_signer_cls.return_value.sign.return_value = signed_el

        result = sign_dps(dps, key_pem, cert_pem)
        sig = result.find("{http://www.w3.org/2000/09/xmldsig#}Signature")
        assert sig is not None

    @patch("emissor.services.xml_signer.XMLSigner")
    def test_reference_uri_matches_id(self, mock_signer_cls, self_signed_pem):
        key_pem, cert_pem = self_signed_pem
        dps_id = "DPS420540721234567800019900900000000000000099"
        dps = _make_dps(dps_id)
        mock_signer_cls.return_value.sign.return_value = dps

        sign_dps(dps, key_pem, cert_pem)
        _, kwargs = mock_signer_cls.return_value.sign.call_args
        assert kwargs["reference_uri"] == f"#{dps_id}"

    @patch("emissor.services.xml_signer.XMLSigner")
    def test_preserves_content(self, mock_signer_cls, self_signed_pem):
        key_pem, cert_pem = self_signed_pem
        dps = _make_dps()
        # Return the same element (signer preserves content)
        mock_signer_cls.return_value.sign.return_value = dps

        result = sign_dps(dps, key_pem, cert_pem)
        inf = result.find("infDPS")
        assert inf is not None
        tp_amb = inf.find("tpAmb")
        assert tp_amb is not None and tp_amb.text == "2"

    def test_raises_no_inf_dps(self, self_signed_pem):
        key_pem, cert_pem = self_signed_pem
        dps = etree.Element("DPS")
        with pytest.raises(ValueError, match="infDPS element not found"):
            sign_dps(dps, key_pem, cert_pem)

    def test_raises_no_id(self, self_signed_pem):
        key_pem, cert_pem = self_signed_pem
        dps = etree.Element("DPS")
        etree.SubElement(dps, "infDPS")  # no Id attribute
        with pytest.raises(ValueError, match="missing Id attribute"):
            sign_dps(dps, key_pem, cert_pem)
