"""CSV import/export for trades."""

from __future__ import annotations

import csv
import io
from datetime import datetime
from decimal import Decimal
from typing import Any

from app.models.trade import Trade
from app.services.trade_service import form_to_trade_dict, validate_trade_dict
from app.utils.decimals import to_decimal

TRADE_CSV_FIELDS = [
    "id",
    "trade_date",
    "close_date",
    "market",
    "direction",
    "status",
    "entry_price",
    "exit_price",
    "lot_size",
    "stop_loss",
    "take_profit",
    "profit_loss",
    "commission",
    "swap",
    "fees",
    "net_profit_loss",
    "pips",
    "risk_amount",
    "planned_reward",
    "risk_reward_ratio",
    "realized_r_multiple",
    "account_balance_after",
    "setup",
    "timeframe",
    "trading_session",
    "entry_reason",
    "exit_reason",
    "mistake",
    "lesson",
    "emotion_before",
    "emotion_after",
    "followed_plan",
    "confidence_score",
    "screenshot_url",
    "source",
    "external_ticket",
]

# Common MT5 history column aliases → our fields
MT5_ALIASES = {
    "ticket": "external_ticket",
    "order": "external_ticket",
    "position": "external_ticket",
    "opentime": "trade_date",
    "open time": "trade_date",
    "time": "trade_date",
    "closetime": "close_date",
    "close time": "close_date",
    "type": "direction",
    "symbol": "market",
    "volume": "lot_size",
    "lots": "lot_size",
    "price": "entry_price",
    "openprice": "entry_price",
    "open price": "entry_price",
    "closeprice": "exit_price",
    "close price": "exit_price",
    "sl": "stop_loss",
    "s / l": "stop_loss",
    "tp": "take_profit",
    "t / p": "take_profit",
    "profit": "profit_loss",
    "commission": "commission",
    "swap": "swap",
    "fee": "fees",
    "fees": "fees",
    "comment": "entry_reason",
}


def _normalize_header(name: str) -> str:
    return name.strip().lower().replace("_", " ")


def detect_csv_format(headers: list[str]) -> str:
    normalized = {_normalize_header(h) for h in headers}
    if "market" in normalized and ("entry_price" in normalized or "entry price" in normalized):
        return "standard"
    if "symbol" in normalized or "ticket" in normalized or "profit" in normalized:
        return "mt5"
    return "unknown"


def map_row(row: dict[str, str], fmt: str) -> dict[str, Any]:
    if fmt == "mt5":
        mapped: dict[str, Any] = {}
        for key, value in row.items():
            canon = MT5_ALIASES.get(_normalize_header(key), key.strip().lower())
            mapped[canon] = value.strip() if isinstance(value, str) else value
        # Normalize market symbols
        market = str(mapped.get("market", "")).upper().replace(" ", "")
        if market in ("XAUUSD", "GOLD"):
            mapped["market"] = "XAU/USD"
        elif market in ("BTCUSD", "BITCOIN"):
            mapped["market"] = "BTC/USD"
        direction = str(mapped.get("direction", "")).upper()
        if direction in ("BUY", "0"):
            mapped["direction"] = "BUY"
        elif direction in ("SELL", "1"):
            mapped["direction"] = "SELL"
        # Status from profit
        pnl = to_decimal(mapped.get("profit_loss") or mapped.get("net_profit_loss"))
        if mapped.get("close_date") or mapped.get("exit_price"):
            if pnl is None:
                mapped["status"] = "BREAKEVEN"
            elif pnl > 0:
                mapped["status"] = "WIN"
            elif pnl < 0:
                mapped["status"] = "LOSS"
            else:
                mapped["status"] = "BREAKEVEN"
        else:
            mapped["status"] = "OPEN"
        mapped["source"] = mapped.get("source") or "MT5_IMPORT"
        return mapped

    # Standard format — keys already match
    return {k.strip().lower(): (v.strip() if isinstance(v, str) else v) for k, v in row.items()}


def parse_csv_content(content: str | bytes) -> tuple[str, list[dict[str, str]]]:
    if isinstance(content, bytes):
        # Strip BOM
        if content.startswith(b"\xef\xbb\xbf"):
            content = content[3:]
        text = content.decode("utf-8-sig", errors="replace")
    else:
        text = content
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ValueError("CSV has no header row.")
    fmt = detect_csv_format(list(reader.fieldnames))
    rows = [dict(r) for r in reader]
    return fmt, rows


def validate_import_rows(
    rows: list[dict[str, str]],
    fmt: str,
    *,
    existing_tickets: set[tuple[str, str, str]] | None = None,
) -> dict[str, Any]:
    """
    Validate and preview import rows without writing to DB.

    existing_tickets: set of (external_ticket, market, date_iso)
    """
    existing_tickets = existing_tickets or set()
    preview: list[dict[str, Any]] = []
    valid_count = 0
    invalid_count = 0
    duplicate_count = 0

    for idx, raw in enumerate(rows, start=2):  # header is line 1
        mapped = map_row(raw, fmt)
        # Coerce through form mapper for decimals/dates
        form_like = {
            **mapped,
            "trade_date": mapped.get("trade_date"),
            "close_date": mapped.get("close_date"),
            "followed_plan": mapped.get("followed_plan"),
        }
        data = form_to_trade_dict(form_like)
        errors = validate_trade_dict(data)
        ticket = data.get("external_ticket") or ""
        market = data.get("market") or ""
        td = data.get("trade_date")
        date_key = td.date().isoformat() if isinstance(td, datetime) else ""
        is_dup = bool(ticket and (ticket, market, date_key) in existing_tickets)
        if is_dup:
            errors.append("Duplicate external ticket for date/market.")
            duplicate_count += 1

        ok = not errors
        if ok:
            valid_count += 1
        else:
            invalid_count += 1

        preview.append(
            {
                "row": idx,
                "data": {
                    k: (str(v) if v is not None else "")
                    for k, v in data.items()
                    if k
                    in (
                        "trade_date",
                        "close_date",
                        "market",
                        "direction",
                        "status",
                        "entry_price",
                        "exit_price",
                        "lot_size",
                        "net_profit_loss",
                        "external_ticket",
                        "setup",
                    )
                },
                "full": {k: (v.isoformat() if isinstance(v, datetime) else (str(v) if isinstance(v, Decimal) else v)) for k, v in data.items()},
                "errors": errors,
                "valid": ok,
                "duplicate": is_dup,
            }
        )

    return {
        "format": fmt,
        "total": len(rows),
        "valid_count": valid_count,
        "invalid_count": invalid_count,
        "duplicate_count": duplicate_count,
        "rows": preview,
    }


def trades_to_csv(trades: list[Trade]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=TRADE_CSV_FIELDS, extrasaction="ignore")
    writer.writeheader()
    for t in trades:
        row = {}
        for f in TRADE_CSV_FIELDS:
            val = getattr(t, f, None)
            if isinstance(val, datetime):
                val = val.isoformat()
            elif isinstance(val, Decimal):
                val = str(val)
            elif isinstance(val, bool):
                val = "1" if val else "0"
            row[f] = val if val is not None else ""
        writer.writerow(row)
    return buf.getvalue()


def sample_template_csv() -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=TRADE_CSV_FIELDS)
    writer.writeheader()
    writer.writerow(
        {
            "trade_date": "2026-01-15T10:30:00",
            "close_date": "2026-01-15T14:00:00",
            "market": "XAU/USD",
            "direction": "BUY",
            "status": "WIN",
            "entry_price": "2650.50",
            "exit_price": "2662.00",
            "lot_size": "0.10",
            "stop_loss": "2645.00",
            "take_profit": "2665.00",
            "profit_loss": "115.00",
            "commission": "2.00",
            "swap": "0",
            "fees": "0",
            "net_profit_loss": "113.00",
            "pips": "115",
            "risk_amount": "55.00",
            "planned_reward": "145.00",
            "risk_reward_ratio": "2.64",
            "realized_r_multiple": "2.05",
            "setup": "Pullback",
            "timeframe": "H1",
            "trading_session": "London",
            "followed_plan": "1",
            "confidence_score": "7",
            "source": "CSV_IMPORT",
            "external_ticket": "100001",
        }
    )
    return buf.getvalue()
