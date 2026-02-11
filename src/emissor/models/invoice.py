from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Invoice:
    valor_brl: str
    valor_usd: str
    competencia: str  # YYYY-MM-DD
    n_dps: int
    dh_emi: str  # ISO datetime with timezone
