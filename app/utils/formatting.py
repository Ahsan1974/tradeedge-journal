"""Display formatting helpers."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from app.utils.dates import format_duration, get_tz
from app.utils.decimals import money, to_decimal


def fmt_money(value: Any, currency: str = "USD", places: int = 2, show_sign: bool = False) -> str:
    d = to_decimal(value)
    if d is None:
        return "—"
    quantized = money(d, places)
    sign = ""
    if show_sign and quantized > 0:
        sign = "+"
    elif quantized < 0:
        sign = "-"
        quantized = abs(quantized)
    return f"{sign}${quantized:,.{places}f}"


def fmt_pct(value: Any, places: int = 1) -> str:
    d = to_decimal(value)
    if d is None:
        return "—"
    return f"{d:.{places}f}%"


def fmt_number(value: Any, places: int = 2) -> str:
    d = to_decimal(value)
    if d is None:
        return "—"
    return f"{d:,.{places}f}"


def fmt_ratio(value: Any, places: int = 2) -> str:
    d = to_decimal(value)
    if d is None:
        return "—"
    return f"{d:.{places}f}"


def fmt_datetime(value: datetime | None, tz_name: str | None = None, fmt: str = "%Y-%m-%d %H:%M") -> str:
    if value is None:
        return "—"
    tz = get_tz(tz_name)
    local = value.astimezone(tz) if value.tzinfo else value.replace(tzinfo=tz)
    return local.strftime(fmt)


def fmt_date(value: date | datetime | None, fmt: str = "%Y-%m-%d") -> str:
    if value is None:
        return "—"
    if isinstance(value, datetime):
        return value.date().strftime(fmt)
    return value.strftime(fmt)


def pnl_class(value: Any) -> str:
    d = to_decimal(value, Decimal("0")) or Decimal("0")
    if d > 0:
        return "positive"
    if d < 0:
        return "negative"
    return "neutral"


def status_badge_class(status: str) -> str:
    mapping = {
        "WIN": "badge-win",
        "LOSS": "badge-loss",
        "BREAKEVEN": "badge-be",
        "OPEN": "badge-open",
        "BUY": "badge-buy",
        "SELL": "badge-sell",
    }
    return mapping.get(status, "badge-neutral")


def market_class(market: str) -> str:
    if market == "XAU/USD":
        return "market-xau"
    if market == "BTC/USD":
        return "market-btc"
    return ""


def holding_time_label(seconds: int | None) -> str:
    return format_duration(seconds)
