from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation


def validate_monetary(value: str) -> str:
    """Validate and normalize a monetary value string.

    Returns the normalized decimal string (no trailing zeros).
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
    return format(d.normalize(), "f")


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
