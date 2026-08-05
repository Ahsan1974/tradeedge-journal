"""Risk management calculators and monitors."""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.models.risk_settings import RiskSettings
from app.repositories.settings_repository import SettingsRepository
from app.repositories.trade_repository import TradeRepository
from app.services.analytics_service import (
    analyze_performance,
    closed_trades,
    compute_streaks,
    minimum_breakeven_win_rate,
)
from app.utils.dates import get_tz, now_tz, today_tz
from app.utils.decimals import HUNDRED, ZERO, money


def calculate_position_size(
    *,
    account_balance: Decimal,
    risk_percent: Decimal,
    entry_price: Decimal,
    stop_loss_price: Decimal,
    tick_size: Decimal,
    tick_value_per_lot: Decimal,
    contract_size: Decimal | None = None,
    maximum_risk_percent: Decimal | None = None,
) -> dict[str, Any]:
    """
    Position size calculator.

    risk_amount = account_balance × risk_percent / 100
    number_of_ticks = abs(entry − stop) / tick_size
    suggested_lot_size = risk_amount / (number_of_ticks × tick_value_per_lot)
    """
    if account_balance <= ZERO:
        return {"error": "Account balance must be positive."}
    if risk_percent <= ZERO:
        return {"error": "Risk percentage must be positive."}
    if entry_price <= ZERO or stop_loss_price <= ZERO:
        return {"error": "Entry and stop-loss prices must be positive."}
    if entry_price == stop_loss_price:
        return {"error": "Stop loss cannot equal entry price."}
    if tick_size <= ZERO or tick_value_per_lot <= ZERO:
        return {"error": "Tick size and tick value per lot must be positive."}

    risk_amount = money(account_balance * risk_percent / HUNDRED)
    stop_distance = money(abs(entry_price - stop_loss_price), 8)
    number_of_ticks = stop_distance / tick_size
    if number_of_ticks <= ZERO:
        return {"error": "Stop distance is too small to calculate a valid lot size."}

    denominator = number_of_ticks * tick_value_per_lot
    suggested = money(risk_amount / denominator, 4)
    position_value = None
    if contract_size and contract_size > ZERO:
        position_value = money(suggested * contract_size * entry_price)

    exceeds = False
    warning = None
    if maximum_risk_percent is not None and risk_percent > maximum_risk_percent:
        exceeds = True
        warning = (
            f"Risk {risk_percent}% exceeds configured maximum of {maximum_risk_percent}%."
        )

    return {
        "risk_amount": risk_amount,
        "stop_distance": stop_distance,
        "number_of_ticks": money(number_of_ticks, 4),
        "suggested_lot_size": suggested,
        "position_value": position_value,
        "exceeds_max_risk": exceeds,
        "max_risk_percent": maximum_risk_percent,
        "error": None,
        "warning": warning,
    }


def calculate_risk_reward(
    *,
    direction: str,
    entry: Decimal,
    stop_loss: Decimal,
    take_profit: Decimal,
) -> dict[str, Any]:
    if entry <= ZERO or stop_loss <= ZERO or take_profit <= ZERO:
        return {"error": "All prices must be positive."}
    if entry == stop_loss or entry == take_profit:
        return {"error": "Stop loss and take profit must differ from entry."}

    risk_distance = money(abs(entry - stop_loss), 8)
    reward_distance = money(abs(take_profit - entry), 8)
    if risk_distance == ZERO:
        return {"error": "Risk distance cannot be zero."}

    rr = money(reward_distance / risk_distance, 2)
    min_wr = minimum_breakeven_win_rate(rr)
    return {
        "risk_distance": risk_distance,
        "reward_distance": reward_distance,
        "risk_reward_ratio": rr,
        "min_breakeven_win_rate": min_wr,
        "error": None,
        "direction": direction.upper(),
    }


def daily_risk_monitor(db: Session, settings: RiskSettings | None = None) -> dict[str, Any]:
    """Build today's risk monitor snapshot."""
    repo = TradeRepository(db)
    settings_repo = SettingsRepository(db)
    settings = settings or settings_repo.get_risk_settings()
    tz = settings.timezone or "Asia/Karachi"
    today = today_tz(tz)
    start = datetime.combine(today, datetime.min.time(), tzinfo=get_tz(tz))
    end = now_tz(tz)

    today_trades = repo.all_filtered(date_from=start, date_to=end)
    closed_today = closed_trades(today_trades)
    stats = analyze_performance(closed_today, settings.starting_balance)

    # Include all open trades regardless of open date
    all_open = repo.all_filtered(status="OPEN")
    open_risk = sum((Decimal(str(t.risk_amount or 0)) for t in all_open), ZERO)
    balance = Decimal(str(settings.current_balance or settings.starting_balance))
    open_risk_pct = money(open_risk / balance * HUNDRED, 2) if balance > ZERO else ZERO

    daily_limit = money(balance * Decimal(str(settings.daily_loss_limit_percent)) / HUNDRED)
    today_pnl = stats.net_pnl
    remaining_loss = money(daily_limit + today_pnl) if today_pnl < ZERO else daily_limit
    if today_pnl < ZERO:
        remaining_loss = money(daily_limit - abs(today_pnl))

    # Consecutive losses across all recent closed trades
    all_recent = repo.all_filtered(exclude_open=True)
    _, current_loss_streak, _, _ = compute_streaks(all_recent)

    remaining_trades = max(0, settings.maximum_trades_per_day - len(today_trades))

    warnings: list[str] = []
    if today_pnl < ZERO and abs(today_pnl) >= daily_limit:
        warnings.append("Daily loss limit reached.")
    if len(today_trades) >= settings.maximum_trades_per_day:
        warnings.append("Maximum trades per day reached.")
    if current_loss_streak >= settings.maximum_consecutive_losses:
        warnings.append("Maximum consecutive losses reached.")
    if open_risk_pct > Decimal(str(settings.maximum_total_open_risk_percent)):
        warnings.append("Total open risk is too high.")

    # Over-risk trades today
    max_risk_amt = money(balance * Decimal(str(settings.maximum_risk_percent)) / HUNDRED)
    for t in today_trades:
        if t.risk_amount and Decimal(str(t.risk_amount)) > max_risk_amt:
            warnings.append("One or more trades exceed maximum risk per trade.")
            break

    return {
        "trades_today": len(today_trades),
        "today_pnl": today_pnl,
        "today_risk": sum((Decimal(str(t.risk_amount or 0)) for t in today_trades), ZERO),
        "current_losing_streak": current_loss_streak,
        "remaining_allowed_loss": remaining_loss,
        "remaining_allowed_trades": remaining_trades,
        "total_open_risk": open_risk,
        "total_open_risk_pct": open_risk_pct,
        "open_trades": len(all_open),
        "warnings": list(dict.fromkeys(warnings)),
        "daily_loss_limit": daily_limit,
        "max_trades": settings.maximum_trades_per_day,
    }


def risk_discipline_score(db: Session, settings: RiskSettings | None = None) -> dict[str, Any]:
    """
    Simple 0–100 risk-discipline score (informational, not financial advice).

    Components (equal weight approx):
    - Followed-plan percentage
    - Average risk vs max risk compliance
    - Daily-loss-limit compliance (recent 30 days)
    - Over-risk trade rate (inverse)
    - Consecutive-loss discipline
    """
    settings = settings or SettingsRepository(db).get_risk_settings()
    repo = TradeRepository(db)
    end = now_tz(settings.timezone)
    start = end - timedelta(days=30)
    trades = repo.all_filtered(date_from=start, date_to=end)
    closed = closed_trades(trades)

    components: dict[str, float] = {}

    # Followed plan
    planned = [t for t in closed if t.followed_plan is not None]
    if planned:
        followed_pct = sum(1 for t in planned if t.followed_plan) / len(planned) * 100
        components["followed_plan"] = followed_pct
    else:
        components["followed_plan"] = 70.0  # neutral default when unknown

    # Average risk percentage
    balance = Decimal(str(settings.current_balance or settings.starting_balance or 103))
    max_risk = Decimal(str(settings.maximum_risk_percent))
    risk_scores = []
    over_risk = 0
    for t in closed:
        if not t.risk_amount or balance <= ZERO:
            continue
        risk_pct = Decimal(str(t.risk_amount)) / balance * HUNDRED
        if risk_pct > max_risk:
            over_risk += 1
            risk_scores.append(40.0)
        elif risk_pct <= Decimal(str(settings.default_risk_percent)):
            risk_scores.append(100.0)
        else:
            # Linear scale between default and max
            risk_scores.append(75.0)
    components["risk_sizing"] = sum(risk_scores) / len(risk_scores) if risk_scores else 80.0
    over_rate = (over_risk / len(closed) * 100) if closed else 0
    components["over_risk"] = max(0.0, 100.0 - over_rate * 5)

    # Daily loss limit compliance
    from collections import defaultdict

    by_day: dict[str, Decimal] = defaultdict(lambda: ZERO)
    for t in closed:
        day = (t.close_date or t.trade_date).strftime("%Y-%m-%d")
        from app.services.analytics_service import _net

        by_day[day] += _net(t)
    daily_limit = balance * Decimal(str(settings.daily_loss_limit_percent)) / HUNDRED
    violations = sum(1 for v in by_day.values() if v < ZERO and abs(v) > daily_limit)
    day_count = max(len(by_day), 1)
    components["daily_limit"] = max(0.0, 100.0 - (violations / day_count) * 100)

    # Consecutive loss discipline
    _, cur_loss, _, max_loss = compute_streaks(closed)
    max_allowed = settings.maximum_consecutive_losses
    if max_loss <= max_allowed:
        components["streak"] = 100.0
    else:
        components["streak"] = max(0.0, 100.0 - (max_loss - max_allowed) * 20)

    score = int(round(sum(components.values()) / len(components)))
    score = max(0, min(100, score))

    return {
        "score": score,
        "components": {k: round(v, 1) for k, v in components.items()},
        "explanation": (
            "Score combines followed-plan rate, risk sizing vs your max risk, "
            "daily loss-limit compliance, over-risk frequency, and consecutive-loss discipline "
            "over the last 30 days. Informational only — not financial advice."
        ),
    }
