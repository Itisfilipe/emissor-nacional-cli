from __future__ import annotations

from decimal import Decimal


def format_brl(value: str) -> str:
    """Format a numeric string as R$ X.XXX,XX."""
    d = Decimal(value)
    formatted = f"{d:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {formatted}"


def format_usd(value: str) -> str:
    """Format a numeric string as US$ X,XXX.XX."""
    d = Decimal(value)
    return f"US$ {d:,.2f}"
