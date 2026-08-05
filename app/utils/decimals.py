"""Decimal helpers for money-safe arithmetic."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

ZERO = Decimal("0")
ONE = Decimal("1")
HUNDRED = Decimal("100")


def to_decimal(value: Any, default: Decimal | None = None) -> Decimal | None:
    """Convert a value to Decimal; return default on empty/invalid input."""
    if value is None or value == "":
        return default
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, ValueError, TypeError):
        return default


def money(value: Any, places: int = 2) -> Decimal:
    """Quantize a value to money precision."""
    d = to_decimal(value, ZERO) or ZERO
    quant = Decimal("1").scaleb(-places)
    return d.quantize(quant, rounding=ROUND_HALF_UP)


def safe_div(numerator: Decimal, denominator: Decimal, default: Decimal | None = None) -> Decimal | None:
    """Divide safely; return default when denominator is zero."""
    if denominator == ZERO:
        return default
    return numerator / denominator


def percent(part: Decimal, whole: Decimal, places: int = 2) -> Decimal | None:
    """Return part/whole as a percentage."""
    ratio = safe_div(part, whole)
    if ratio is None:
        return None
    return money(ratio * HUNDRED, places)


def abs_decimal(value: Decimal) -> Decimal:
    return abs(value)
