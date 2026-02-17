from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Client:
    """Service taker (tomador) — the international client receiving the NFS-e."""

    nif: str
    nome: str
    pais: str
    logradouro: str
    numero: str
    bairro: str
    cidade: str
    estado: str
    cep: str
    complemento: str | None = None
    mec_af_comex_p: str = "02"
    mec_af_comex_t: str = "02"

    @classmethod
    def from_dict(cls, d: dict) -> Client:
        """Create a Client from a YAML-loaded dict, applying defaults for optional fields."""
        return cls(
            nif=d["nif"],
            nome=d["nome"],
            pais=d.get("pais", "US"),
            logradouro=d["logradouro"],
            numero=d["numero"],
            bairro=d.get("bairro", "n/a"),
            cidade=d["cidade"],
            estado=d["estado"],
            cep=d["cep"],
            complemento=d.get("complemento"),
            mec_af_comex_p=str(d.get("mec_af_comex_p", "02")).zfill(2),
            mec_af_comex_t=str(d.get("mec_af_comex_t", "02")).zfill(2),
        )


@dataclass(frozen=True)
class Intermediary:
    nif: str
    nome: str
    pais: str
    logradouro: str
    numero: str
    bairro: str
    cidade: str
    estado: str
    cep: str

    @classmethod
    def from_dict(cls, d: dict) -> Intermediary:
        return cls(
            nif=d["nif"],
            nome=d["nome"],
            pais=d.get("pais", "US"),
            logradouro=d["logradouro"],
            numero=d["numero"],
            bairro=d.get("bairro", "NA"),
            cidade=d["cidade"],
            estado=d["estado"],
            cep=d["cep"],
        )
