"""Trade business logic: validation helpers and form mapping."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.models.trade import Direction, Trade, TradeStatus
from app.utils.dates import parse_datetime
from app.utils.decimals import ZERO, money, to_decimal


def suggest_status(net_pnl: Decimal | None, current: str | None = None) -> str:
    """Suggest trade status from net P/L; OPEN preserved if explicitly open with no exit."""
    if current == TradeStatus.OPEN.value and net_pnl is None:
        return TradeStatus.OPEN.value
    if net_pnl is None:
        return current or TradeStatus.OPEN.value
    if net_pnl > ZERO:
        return TradeStatus.WIN.value
    if net_pnl < ZERO:
        return TradeStatus.LOSS.value
    return TradeStatus.BREAKEVEN.value


def compute_net_pnl(
    profit_loss: Decimal | None,
    commission: Decimal,
    swap: Decimal,
    fees: Decimal,
    net_override: Decimal | None = None,
) -> Decimal | None:
    """Net P/L = gross − costs, unless an explicit net override is provided."""
    if net_override is not None:
        return money(net_override)
    if profit_loss is None:
        return None
    return money(profit_loss - commission - swap - fees)


def compute_rr(
    entry: Decimal,
    stop_loss: Decimal | None,
    take_profit: Decimal | None,
    direction: str,
) -> Decimal | None:
    if stop_loss is None or take_profit is None:
        return None
    risk = abs(entry - stop_loss)
    reward = abs(take_profit - entry)
    if risk == ZERO:
        return None
    return money(reward / risk, 2)


def price_warnings(data: dict[str, Any]) -> list[str]:
    """Soft warnings for unusual SL/TP placement (do not block submission)."""
    warnings: list[str] = []
    entry = to_decimal(data.get("entry_price"))
    sl = to_decimal(data.get("stop_loss"))
    tp = to_decimal(data.get("take_profit"))
    direction = str(data.get("direction", "")).upper()
    if entry is None:
        return warnings
    if direction == Direction.BUY.value:
        if sl is not None and sl > entry:
            warnings.append("BUY stop loss is usually below entry price.")
        if tp is not None and tp < entry:
            warnings.append("BUY take profit is usually above entry price.")
    elif direction == Direction.SELL.value:
        if sl is not None and sl < entry:
            warnings.append("SELL stop loss is usually above entry price.")
        if tp is not None and tp > entry:
            warnings.append("SELL take profit is usually below entry price.")
    return warnings


def form_to_trade_dict(form: dict[str, Any], *, overrides_locked: set[str] | None = None) -> dict[str, Any]:
    """Map form values to Trade kwargs with Decimal-safe conversions."""
    locked = overrides_locked or set()

    trade_date = parse_datetime(form.get("trade_date"))
    close_date = parse_datetime(form.get("close_date"))
    entry = to_decimal(form.get("entry_price"))
    exit_p = to_decimal(form.get("exit_price"))
    lot = to_decimal(form.get("lot_size"))
    sl = to_decimal(form.get("stop_loss"))
    tp = to_decimal(form.get("take_profit"))
    commission = to_decimal(form.get("commission"), ZERO) or ZERO
    swap = to_decimal(form.get("swap"), ZERO) or ZERO
    fees = to_decimal(form.get("fees"), ZERO) or ZERO
    profit_loss = to_decimal(form.get("profit_loss"))
    net_raw = to_decimal(form.get("net_profit_loss"))

    # Calculate net unless user explicitly provided it
    if "net_profit_loss" in locked or form.get("net_profit_loss_manual") == "1":
        net = net_raw
    else:
        net = compute_net_pnl(profit_loss, commission, swap, fees, None)

    status = str(form.get("status") or "").upper()
    if form.get("status_manual") != "1" and status != TradeStatus.OPEN.value:
        status = suggest_status(net, status)

    direction = str(form.get("direction", "BUY")).upper()
    rr = to_decimal(form.get("risk_reward_ratio"))
    if form.get("rr_manual") != "1" and entry and sl and tp:
        rr = compute_rr(entry, sl, tp, direction)

    risk_amount = to_decimal(form.get("risk_amount"))
    realized_r = to_decimal(form.get("realized_r_multiple"))
    if form.get("r_manual") != "1" and net is not None and risk_amount and risk_amount > ZERO:
        realized_r = money(net / risk_amount, 2)

    followed = form.get("followed_plan")
    if followed in ("1", "true", "on", True):
        followed_plan = True
    elif followed in ("0", "false", False):
        followed_plan = False
    else:
        followed_plan = None

    confidence = form.get("confidence_score")
    confidence_score = int(confidence) if confidence not in (None, "") else None

    return {
        "trade_date": trade_date,
        "close_date": close_date,
        "market": form.get("market"),
        "direction": direction,
        "status": status or TradeStatus.OPEN.value,
        "entry_price": entry,
        "exit_price": exit_p,
        "lot_size": lot,
        "stop_loss": sl,
        "take_profit": tp,
        "profit_loss": profit_loss,
        "commission": commission,
        "swap": swap,
        "fees": fees,
        "net_profit_loss": net,
        "pips": to_decimal(form.get("pips")),
        "risk_amount": risk_amount,
        "planned_reward": to_decimal(form.get("planned_reward")),
        "risk_reward_ratio": rr,
        "realized_r_multiple": realized_r,
        "account_balance_after": to_decimal(form.get("account_balance_after")),
        "setup": form.get("setup") or None,
        "timeframe": form.get("timeframe") or None,
        "trading_session": form.get("trading_session") or None,
        "entry_reason": form.get("entry_reason") or None,
        "exit_reason": form.get("exit_reason") or None,
        "mistake": form.get("mistake") or None,
        "lesson": form.get("lesson") or None,
        "emotion_before": form.get("emotion_before") or None,
        "emotion_after": form.get("emotion_after") or None,
        "followed_plan": followed_plan,
        "confidence_score": confidence_score,
        "screenshot_url": form.get("screenshot_url") or None,
        "source": form.get("source") or "MANUAL",
        "external_ticket": form.get("external_ticket") or None,
    }


def validate_trade_dict(data: dict[str, Any]) -> list[str]:
    """Hard validation errors."""
    errors: list[str] = []
    if not data.get("trade_date"):
        errors.append("Open date is required.")
    if data.get("market") not in ("XAU/USD", "BTC/USD"):
        errors.append("Market must be XAU/USD or BTC/USD.")
    if data.get("direction") not in ("BUY", "SELL"):
        errors.append("Direction must be BUY or SELL.")
    if data.get("status") not in ("OPEN", "WIN", "LOSS", "BREAKEVEN"):
        errors.append("Invalid status.")
    entry = data.get("entry_price")
    if entry is None or entry <= ZERO:
        errors.append("Entry price must be positive.")
    lot = data.get("lot_size")
    if lot is None or lot <= ZERO:
        errors.append("Lot size must be positive.")
    exit_p = data.get("exit_price")
    if exit_p is not None and exit_p <= ZERO:
        errors.append("Exit price must be positive when supplied.")
    sl = data.get("stop_loss")
    tp = data.get("take_profit")
    if entry and sl is not None and sl == entry:
        errors.append("Stop loss cannot equal entry price.")
    if entry and tp is not None and tp == entry:
        errors.append("Take profit cannot equal entry price.")
    if data.get("close_date") and data.get("trade_date") and data["close_date"] < data["trade_date"]:
        errors.append("Close date cannot be before open date.")
    status = data.get("status")
    if status != "OPEN":
        if data.get("net_profit_loss") is None and data.get("profit_loss") is None and exit_p is None:
            errors.append("Closed trades require an exit price or P/L result.")
    conf = data.get("confidence_score")
    if conf is not None and not (1 <= conf <= 10):
        errors.append("Confidence score must be between 1 and 10.")
    return errors


def apply_dict_to_trade(trade: Trade, data: dict[str, Any]) -> Trade:
    for key, value in data.items():
        if hasattr(trade, key):
            setattr(trade, key, value)
    return trade


def create_trade_from_dict(data: dict[str, Any]) -> Trade:
    return Trade(**{k: v for k, v in data.items() if hasattr(Trade, k)})
