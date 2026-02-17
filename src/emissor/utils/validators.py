from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, InvalidOperation

_VALID_CST_PIS_COFINS = frozenset({
    "01", "02", "03", "04", "05", "06", "07", "08", "09",
    "49", "50", "51", "52", "53", "54", "55", "56",
    "60", "61", "62", "63", "64", "65", "66", "67",
    "70", "71", "72", "73", "74", "75",
    "98", "99",
})


def validate_monetary(value: str) -> str:
    """Validate and normalize a monetary value string.

    Returns the value with at least 2 decimal places (SEFIN XML requirement).
    Raises ValueError for invalid or non-positive values.
    """
    try:
        d = Decimal(value)
        if not d.is_finite():
            raise InvalidOperation
        if d <= 0:
            raise ValueError(f"Valor deve ser positivo: '{value}'")
    except InvalidOperation:
        raise ValueError(f"Valor numerico invalido: '{value}'") from None
    return f"{d:.2f}"


def validate_date(value: str) -> str:
    """Validate an ISO date string (YYYY-MM-DD).

    Returns the value unchanged if valid.
    Raises ValueError for invalid dates.
    """
    try:
        date.fromisoformat(value)
    except ValueError:
        raise ValueError(f"Data invalida: '{value}'. Use YYYY-MM-DD.") from None
    return value


def validate_c_trib_nac(value: str) -> str:
    """Validate cTribNac: exactly 6 numeric digits."""
    if not re.fullmatch(r"\d{6}", value):
        raise ValueError("cTribNac: deve ter 6 digitos numericos")
    return value


def validate_c_nbs(value: str) -> str:
    """Validate cNBS: exactly 9 numeric digits."""
    if not re.fullmatch(r"\d{9}", value):
        raise ValueError("cNBS: deve ter 9 digitos numericos")
    return value


def validate_tp_moeda(value: str) -> str:
    """Validate tpMoeda: exactly 3 numeric digits (ISO 4217)."""
    if not re.fullmatch(r"\d{3}", value):
        raise ValueError("tpMoeda: deve ter 3 digitos numericos (ISO 4217)")
    return value


def validate_c_pais_result(value: str) -> str:
    """Validate cPaisResult: exactly 2 uppercase letters (ISO 3166-1 alpha-2)."""
    if not re.fullmatch(r"[A-Z]{2}", value):
        raise ValueError("cPaisResult: deve ter 2 letras maiusculas (ISO 3166-1)")
    return value


def validate_cst_pis_cofins(value: str) -> str:
    """Validate CST PIS/COFINS against known valid codes."""
    if value not in _VALID_CST_PIS_COFINS:
        raise ValueError("CST PIS/COFINS: codigo invalido")
    return value


def validate_access_key(value: str) -> str:
    """Validate an NFS-e access key: exactly 50 alphanumeric characters."""
    if not re.fullmatch(r"[A-Za-z0-9]{50}", value):
        raise ValueError(
            "Chave de acesso: deve ter exatamente 50 caracteres alfanuméricos"
        )
    return value


def validate_percent(value: str) -> str:
    """Validate and normalize a percentage value (0.00-100.00)."""
    try:
        d = Decimal(value)
        if not d.is_finite():
            raise InvalidOperation
    except InvalidOperation:
        raise ValueError(f"Percentual invalido: '{value}'") from None
    if d < 0 or d > 100:
        raise ValueError("Percentual deve estar entre 0.00 e 100.00")
    return f"{d:.2f}"
