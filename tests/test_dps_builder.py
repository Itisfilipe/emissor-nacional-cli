from __future__ import annotations

from emissor.models.invoice import Invoice
from emissor.services.dps_builder import build_dps
from tests.conftest import xml_text


def test_devstride_dps_structure(emitter, client):
    invoice = Invoice(
        valor_brl="19684.93",
        valor_usd="3640.00",
        competencia="2025-12-30",
        n_dps=3,
        dh_emi="2025-12-30T15:57:03-03:00",
    )

    dps = build_dps(emitter, client, invoice, tp_amb="1")

    # Check root element
    assert dps.tag == "DPS"
    assert dps.get("versao") == "1.00"

    inf = dps.find("infDPS")
    assert inf is not None
    assert inf.get("Id") == "DPS420540721234567800019900900000000000000003"

    # Basic fields
    assert xml_text(dps, "infDPS/tpAmb") == "1"
    assert xml_text(dps, "infDPS/serie") == "900"
    assert xml_text(dps, "infDPS/nDPS") == "3"
    assert xml_text(dps, "infDPS/dCompet") == "2025-12-30"
    assert xml_text(dps, "infDPS/tpEmit") == "1"
    assert xml_text(dps, "infDPS/cLocEmi") == "4205407"

    # Prestador
    assert xml_text(dps, "infDPS/prest/CNPJ") == "12345678000199"
    assert xml_text(dps, "infDPS/prest/regTrib/opSimpNac") == "1"

    # Tomador
    assert xml_text(dps, "infDPS/toma/NIF") == "123456789"
    assert xml_text(dps, "infDPS/toma/xNome") == "Acme Corp"
    assert xml_text(dps, "infDPS/toma/end/endExt/cPais") == "US"
    assert xml_text(dps, "infDPS/toma/end/endExt/xCidade") == "New York"
    assert xml_text(dps, "infDPS/toma/end/xLgr") == "100 Main St, Ste"
    assert xml_text(dps, "infDPS/toma/end/nro") == "100"

    # No intermediary
    assert dps.find("infDPS/interm") is None

    # Service
    assert xml_text(dps, "infDPS/serv/cServ/cTribNac") == "010101"
    assert xml_text(dps, "infDPS/serv/cServ/cNBS") == "115022000"
    assert xml_text(dps, "infDPS/serv/comExt/tpMoeda") == "220"
    assert xml_text(dps, "infDPS/serv/comExt/vServMoeda") == "3640.00"
    assert xml_text(dps, "infDPS/serv/comExt/mecAFComexP") == "02"
    assert xml_text(dps, "infDPS/serv/comExt/mecAFComexT") == "02"

    # Values
    assert xml_text(dps, "infDPS/valores/vServPrest/vServ") == "19684.93"
    assert xml_text(dps, "infDPS/valores/trib/tribMun/tribISSQN") == "3"
    assert xml_text(dps, "infDPS/valores/trib/tribMun/cPaisResult") == "US"
    assert xml_text(dps, "infDPS/valores/trib/tribFed/piscofins/CST") == "08"


def test_drchrono_dps_with_intermediary(emitter, client_with_complement, intermediary):
    invoice = Invoice(
        valor_brl="53526.58",
        valor_usd="10221.04",
        competencia="2025-12-23",
        n_dps=1,
        dh_emi="2025-12-25T10:54:33-03:00",
    )

    dps = build_dps(
        emitter,
        client_with_complement,
        invoice,
        tp_amb="1",
        intermediary=intermediary,
    )

    inf = dps.find("infDPS")
    assert inf.get("Id") == "DPS420540721234567800019900900000000000000001"

    assert xml_text(dps, "infDPS/nDPS") == "1"
    assert xml_text(dps, "infDPS/dCompet") == "2025-12-23"

    # Tomador
    assert xml_text(dps, "infDPS/toma/NIF") == "987654321"
    assert xml_text(dps, "infDPS/toma/xNome") == "Example Corp"
    assert xml_text(dps, "infDPS/toma/end/xCpl") == "ste 400"

    # Intermediary
    interm = dps.find("infDPS/interm")
    assert interm is not None
    assert xml_text(dps, "infDPS/interm/NIF") == "9876543"
    assert xml_text(dps, "infDPS/interm/xNome") == "GLOBAL PAYMENTS INC"
    assert xml_text(dps, "infDPS/interm/end/endExt/cPais") == "US"
    assert xml_text(dps, "infDPS/interm/end/endExt/xCidade") == "San Francisco"

    # Values
    assert xml_text(dps, "infDPS/valores/vServPrest/vServ") == "53526.58"
    assert xml_text(dps, "infDPS/serv/comExt/vServMoeda") == "10221.04"
    assert xml_text(dps, "infDPS/serv/comExt/mecAFComexP") == "01"
    assert xml_text(dps, "infDPS/serv/comExt/mecAFComexT") == "01"


def test_custom_service_fields_in_xml(client):
    """Custom servico fields from Emitter appear in the output XML."""
    from emissor.models.emitter import Emitter

    emitter_dict = {
        "cnpj": "12345678000199",
        "razao_social": "ACME SOFTWARE LTDA",
        "logradouro": "RUA DAS FLORES",
        "numero": "100",
        "bairro": "CENTRO",
        "cod_municipio": "4205407",
        "uf": "SC",
        "cep": "88000000",
        "fone": "48999999999",
        "email": "contato@acme-software.com.br",
        "servico": {
            "cTribNac": "020202",
            "xDescServ": "Consultoria em TI",
            "cNBS": "999999999",
            "tpMoeda": "978",
            "cPaisResult": "DE",
        },
    }
    custom_emitter = Emitter.from_dict(emitter_dict)
    invoice = Invoice(
        valor_brl="5000.00",
        valor_usd="1000.00",
        competencia="2025-06-01",
        n_dps=1,
        dh_emi="2025-06-01T10:00:00-03:00",
    )
    dps = build_dps(custom_emitter, client, invoice, tp_amb="2")

    assert xml_text(dps, "infDPS/serv/cServ/cTribNac") == "020202"
    assert xml_text(dps, "infDPS/serv/cServ/xDescServ") == "Consultoria em TI"
    assert xml_text(dps, "infDPS/serv/cServ/cNBS") == "999999999"
    assert xml_text(dps, "infDPS/serv/comExt/tpMoeda") == "978"
    assert xml_text(dps, "infDPS/valores/trib/tribMun/cPaisResult") == "DE"


def test_dps_element_order_matches_reference(emitter, client_with_complement, intermediary):
    """Verify the element order in infDPS matches the SEFIN schema."""
    invoice = Invoice(
        valor_brl="53526.58",
        valor_usd="10221.04",
        competencia="2025-12-23",
        n_dps=1,
        dh_emi="2025-12-25T10:54:33-03:00",
    )

    dps = build_dps(
        emitter,
        client_with_complement,
        invoice,
        tp_amb="1",
        intermediary=intermediary,
    )
    inf = dps.find("infDPS")
    child_tags = [child.tag for child in inf]

    expected_order = [
        "tpAmb",
        "dhEmi",
        "verAplic",
        "serie",
        "nDPS",
        "dCompet",
        "tpEmit",
        "cLocEmi",
        "prest",
        "toma",
        "interm",
        "serv",
        "valores",
    ]
    assert child_tags == expected_order
