"""Calendar heatmap data builders."""

from __future__ import annotations

import calendar
from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Any

from app.models.trade import Trade
from app.services.analytics_service import _net, closed_trades
from app.utils.dates import ensure_aware, get_tz, month_bounds
from app.utils.decimals import ZERO, money


def build_month_calendar(
    trades: list[Trade],
    year: int,
    month: int,
    tz_name: str = "Asia/Karachi",
) -> dict[str, Any]:
    """Build monthly heatmap cells and summary stats."""
    start, end = month_bounds(year, month, tz_name)
    tz = get_tz(tz_name)
    closed = []
    for t in closed_trades(trades):
        trade_dt = ensure_aware(t.close_date or t.trade_date, tz_name)
        if start <= trade_dt <= end:
            closed.append(t)

    by_day: dict[date, list[Trade]] = defaultdict(list)
    for t in closed:
        trade_dt = ensure_aware(t.close_date or t.trade_date, tz_name)
        by_day[trade_dt.astimezone(tz).date()].append(t)

    weeks = calendar.Calendar(firstweekday=0).monthdatescalendar(year, month)
    cells: list[list[dict[str, Any]]] = []
    daily_pnls: list[tuple[date, Decimal]] = []

    for week in weeks:
        row = []
        for day in week:
            in_month = day.month == month
            day_trades = by_day.get(day, []) if in_month else []
            pnl = sum((_net(t) for t in day_trades), ZERO) if day_trades else None
            wins = sum(1 for t in day_trades if _net(t) > ZERO)
            losses = sum(1 for t in day_trades if _net(t) < ZERO)
            if pnl is None:
                tone = "empty"
            elif pnl > ZERO:
                tone = "profit"
            elif pnl < ZERO:
                tone = "loss"
            else:
                tone = "breakeven"
            if in_month and pnl is not None:
                daily_pnls.append((day, pnl))
            row.append(
                {
                    "date": day.isoformat(),
                    "day": day.day,
                    "in_month": in_month,
                    "pnl": float(pnl) if pnl is not None else None,
                    "trades": len(day_trades),
                    "wins": wins,
                    "losses": losses,
                    "tone": tone if in_month else "outside",
                }
            )
        cells.append(row)

    profitable_days = sum(1 for _, p in daily_pnls if p > ZERO)
    losing_days = sum(1 for _, p in daily_pnls if p < ZERO)
    month_pnl = sum((p for _, p in daily_pnls), ZERO)
    best = max(daily_pnls, key=lambda x: x[1]) if daily_pnls else None
    worst = min(daily_pnls, key=lambda x: x[1]) if daily_pnls else None
    avg_daily = money(month_pnl / len(daily_pnls)) if daily_pnls else None

    return {
        "year": year,
        "month": month,
        "month_name": calendar.month_name[month],
        "cells": cells,
        "summary": {
            "month_pnl": month_pnl,
            "profitable_days": profitable_days,
            "losing_days": losing_days,
            "best_day": {"date": best[0].isoformat(), "pnl": best[1]} if best else None,
            "worst_day": {"date": worst[0].isoformat(), "pnl": worst[1]} if worst else None,
            "avg_daily_pnl": avg_daily,
            "total_trades": len(closed),
        },
    }
