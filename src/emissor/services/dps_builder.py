from __future__ import annotations

from lxml import etree

from emissor.config import NFSE_NS
from emissor.models.client import Client, Intermediary
from emissor.models.emitter import Emitter
from emissor.models.invoice import Invoice
from emissor.utils.dps_id import generate_dps_id

NSMAP = {None: NFSE_NS}


def _sub(parent: etree._Element, tag: str, text: str | None = None) -> etree._Element:
    el = etree.SubElement(parent, tag)
    if text is not None:
        el.text = text
    return el


def build_dps(
    emitter: Emitter,
    client: Client,
    invoice: Invoice,
    tp_amb: str,
    intermediary: Intermediary | None = None,
) -> etree._Element:
    """Build a DPS XML element ready for signing.

    Returns the <DPS> root element with namespace.
    """
    dps_id = generate_dps_id(
        cod_municipio=emitter.cod_municipio,
        cnpj=emitter.cnpj,
        serie=emitter.serie,
        n_dps=invoice.n_dps,
    )

    dps = etree.Element("DPS", nsmap=NSMAP)  # type: ignore[arg-type]  # lxml stubs don't model None key for default ns
    dps.set("versao", "1.00")

    inf = _sub(dps, "infDPS")
    inf.set("Id", dps_id)

    _sub(inf, "tpAmb", tp_amb)
    _sub(inf, "dhEmi", invoice.dh_emi)
    _sub(inf, "verAplic", emitter.ver_aplic)
    _sub(inf, "serie", emitter.serie)
    _sub(inf, "nDPS", str(invoice.n_dps))
    _sub(inf, "dCompet", invoice.competencia)
    _sub(inf, "tpEmit", "1")
    _sub(inf, "cLocEmi", emitter.cod_municipio)

    # prest (prestador)
    prest = _sub(inf, "prest")
    _sub(prest, "CNPJ", emitter.cnpj)
    _sub(prest, "fone", emitter.fone)
    _sub(prest, "email", emitter.email)
    reg = _sub(prest, "regTrib")
    _sub(reg, "opSimpNac", emitter.op_simp_nac)
    _sub(reg, "regEspTrib", emitter.reg_esp_trib)

    # toma (tomador)
    toma = _sub(inf, "toma")
    _sub(toma, "NIF", client.nif)
    _sub(toma, "xNome", client.nome)
    end = _sub(toma, "end")
    end_ext = _sub(end, "endExt")
    _sub(end_ext, "cPais", client.pais)
    _sub(end_ext, "cEndPost", client.cep)
    _sub(end_ext, "xCidade", client.cidade)
    _sub(end_ext, "xEstProvReg", client.estado)
    _sub(end, "xLgr", client.logradouro)
    _sub(end, "nro", client.numero)
    if client.complemento:
        _sub(end, "xCpl", client.complemento)
    _sub(end, "xBairro", client.bairro)

    # interm (intermediário) — optional
    if intermediary is not None:
        interm = _sub(inf, "interm")
        _sub(interm, "NIF", intermediary.nif)
        _sub(interm, "xNome", intermediary.nome)
        i_end = _sub(interm, "end")
        i_ext = _sub(i_end, "endExt")
        _sub(i_ext, "cPais", intermediary.pais)
        _sub(i_ext, "cEndPost", intermediary.cep)
        _sub(i_ext, "xCidade", intermediary.cidade)
        _sub(i_ext, "xEstProvReg", intermediary.estado)
        _sub(i_end, "xLgr", intermediary.logradouro)
        _sub(i_end, "nro", intermediary.numero)
        _sub(i_end, "xBairro", intermediary.bairro)

    # serv (serviço)
    serv = _sub(inf, "serv")
    loc = _sub(serv, "locPrest")
    _sub(loc, "cLocPrestacao", emitter.cod_municipio)
    cserv = _sub(serv, "cServ")
    _sub(cserv, "cTribNac", "010101")
    _sub(cserv, "xDescServ", "Desenvolvimento de Software")
    _sub(cserv, "cNBS", "115022000")
    com_ext = _sub(serv, "comExt")
    _sub(com_ext, "mdPrestacao", "4")
    _sub(com_ext, "vincPrest", "0")
    _sub(com_ext, "tpMoeda", "220")
    _sub(com_ext, "vServMoeda", invoice.valor_usd)
    _sub(com_ext, "mecAFComexP", client.mec_af_comex_p)
    _sub(com_ext, "mecAFComexT", client.mec_af_comex_t)
    _sub(com_ext, "movTempBens", "1")
    _sub(com_ext, "mdic", "0")

    # valores
    valores = _sub(inf, "valores")
    v_serv_prest = _sub(valores, "vServPrest")
    _sub(v_serv_prest, "vServ", invoice.valor_brl)
    trib = _sub(valores, "trib")
    trib_mun = _sub(trib, "tribMun")
    _sub(trib_mun, "tribISSQN", "3")
    _sub(trib_mun, "cPaisResult", "US")
    _sub(trib_mun, "tpRetISSQN", "1")
    trib_fed = _sub(trib, "tribFed")
    piscofins = _sub(trib_fed, "piscofins")
    _sub(piscofins, "CST", "08")
    tot_trib = _sub(trib, "totTrib")
    p_tot = _sub(tot_trib, "pTotTrib")
    _sub(p_tot, "pTotTribFed", "0.00")
    _sub(p_tot, "pTotTribEst", "0.00")
    _sub(p_tot, "pTotTribMun", "0.00")

    return dps
