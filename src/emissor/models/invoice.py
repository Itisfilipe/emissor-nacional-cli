from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Invoice:
    valor_brl: str
    valor_usd: str
    competencia: str  # YYYY-MM-DD
    n_dps: int
    dh_emi: str  # ISO datetime with timezone

    # Service overrides (Step 2) — None means use emitter/client/default
    x_desc_serv: str | None = None
    c_trib_nac: str | None = None
    c_nbs: str | None = None
    md_prestacao: str | None = None
    vinc_prest: str | None = None
    tp_moeda: str | None = None
    mec_af_comex_p: str | None = None
    mec_af_comex_t: str | None = None
    mov_temp_bens: str | None = None
    mdic: str | None = None
    c_pais_result: str | None = None

    # Tax overrides (Step 3) — None means use defaults
    trib_issqn: str | None = None
    tp_ret_issqn: str | None = None
    cst_pis_cofins: str | None = None
    p_tot_trib_fed: str | None = None
    p_tot_trib_est: str | None = None
    p_tot_trib_mun: str | None = None
