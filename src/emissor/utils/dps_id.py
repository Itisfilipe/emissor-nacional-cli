from __future__ import annotations


def generate_dps_id(
    cod_municipio: str,
    cnpj: str,
    serie: str,
    n_dps: int,
    tp_insc: str = "2",
) -> str:
    """Generate the 45-character DPS ID.

    Format: DPS + cMun(7) + tpInsc(1) + CNPJ(14) + serie(5) + nDPS(15)
    Example: DPS420540721234567800019900900000000000000003
    """
    parts = [
        "DPS",
        cod_municipio.zfill(7),
        tp_insc,
        cnpj.zfill(14),
        serie.zfill(5),
        str(n_dps).zfill(15),
    ]
    dps_id = "".join(parts)
    if len(dps_id) != 45:
        raise ValueError(f"DPS ID must be 45 chars, got {len(dps_id)}: {dps_id}")
    return dps_id
