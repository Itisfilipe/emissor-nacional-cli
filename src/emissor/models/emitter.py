from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Emitter:
    """Emitter (prestador) — the company issuing the NFS-e."""

    cnpj: str
    razao_social: str
    logradouro: str
    numero: str
    bairro: str
    cod_municipio: str
    uf: str
    cep: str
    fone: str
    email: str
    op_simp_nac: str  # 1 = Simples Nacional
    reg_esp_trib: str  # 0 = nenhum
    serie: str
    ver_aplic: str
    c_trib_nac: str = "010101"
    x_desc_serv: str = "Desenvolvimento de Software"
    c_nbs: str = "115022000"
    tp_moeda: str = "220"
    c_pais_result: str = "US"

    @classmethod
    def from_dict(cls, d: dict) -> Emitter:
        """Create an Emitter from a YAML-loaded dict, applying defaults for optional fields."""
        servico = d.get("servico", {})
        return cls(
            cnpj=d["cnpj"],
            razao_social=d["razao_social"],
            logradouro=d["logradouro"],
            numero=d["numero"],
            bairro=d["bairro"],
            cod_municipio=d["cod_municipio"],
            uf=d["uf"],
            cep=d["cep"],
            fone=d["fone"],
            email=d["email"],
            op_simp_nac=str(d.get("op_simp_nac", "1")),
            reg_esp_trib=str(d.get("reg_esp_trib", "0")),
            serie=str(d.get("serie", "900")),
            ver_aplic=d.get("ver_aplic", "emissor-nacional_0.1.0"),
            c_trib_nac=str(servico.get("cTribNac", "010101")),
            x_desc_serv=servico.get("xDescServ", "Desenvolvimento de Software"),
            c_nbs=str(servico.get("cNBS", "115022000")),
            tp_moeda=str(servico.get("tpMoeda", "220")),
            c_pais_result=servico.get("cPaisResult", "US"),
        )
