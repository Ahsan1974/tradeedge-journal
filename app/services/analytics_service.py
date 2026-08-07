"""
Analytics calculations for TradeEdge Journal.

All financial metrics use Decimal. Stored net_profit_loss is authoritative.
Open trades are excluded from closed-trade statistics (win rate, etc.).
Breakeven trades are excluded from win/loss counts but included in totals
where noted. Breakeven breaks winning/losing streaks.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Optional, Sequence

from app.models.trade import Trade, TradeStatus
from app.utils.decimals import HUNDRED, ZERO, money, percent, to_decimal
from app.utils.formatting import fmt_money, fmt_number, fmt_pct, fmt_ratio


def _net(trade: Trade) -> Decimal:
    """Authoritative net P/L for a trade."""
    if trade.net_profit_loss is not None:
        return Decimal(str(trade.net_profit_loss))
    if trade.profit_loss is not None:
        gross = Decimal(str(trade.profit_loss))
        costs = (
            Decimal(str(trade.commission or 0))
            + Decimal(str(trade.swap or 0))
            + Decimal(str(trade.fees or 0))
        )
        return gross - costs
    return ZERO


def closed_trades(trades: Sequence[Trade]) -> list[Trade]:
    return [t for t in trades if t.status != TradeStatus.OPEN.value]


def winning_trades(trades: Sequence[Trade]) -> list[Trade]:
    return [t for t in closed_trades(trades) if t.status == TradeStatus.WIN.value or _net(t) > ZERO]


def losing_trades(trades: Sequence[Trade]) -> list[Trade]:
    return [t for t in closed_trades(trades) if t.status == TradeStatus.LOSS.value or (_net(t) < ZERO and t.status != TradeStatus.BREAKEVEN.value)]


def breakeven_trades(trades: Sequence[Trade]) -> list[Trade]:
    return [t for t in closed_trades(trades) if t.status == TradeStatus.BREAKEVEN.value or _net(t) == ZERO]


def classify_closed(trade: Trade) -> str:
    """Return WIN, LOSS, or BREAKEVEN for a closed trade."""
    if trade.status == TradeStatus.BREAKEVEN.value:
        return "BREAKEVEN"
    if trade.status == TradeStatus.WIN.value:
        return "WIN"
    if trade.status == TradeStatus.LOSS.value:
        return "LOSS"
    n = _net(trade)
    if n > ZERO:
        return "WIN"
    if n < ZERO:
        return "LOSS"
    return "BREAKEVEN"


@dataclass
class PerformanceStats:
    """Complete performance snapshot for a set of trades."""

    total_trades: int = 0
    open_trades: int = 0
    closed_trades: int = 0
    wins: int = 0
    losses: int = 0
    breakevens: int = 0
    gross_profit: Decimal = ZERO
    gross_loss: Decimal = ZERO
    net_pnl: Decimal = ZERO
    win_rate: Optional[Decimal] = None
    profit_factor: Optional[Decimal] = None
    avg_win: Optional[Decimal] = None
    avg_loss: Optional[Decimal] = None
    payoff_ratio: Optional[Decimal] = None
    expectancy: Optional[Decimal] = None
    avg_rr: Optional[Decimal] = None
    avg_r_multiple: Optional[Decimal] = None
    best_trade: Optional[Decimal] = None
    worst_trade: Optional[Decimal] = None
    max_drawdown: Optional[Decimal] = None
    max_drawdown_pct: Optional[Decimal] = None
    current_win_streak: int = 0
    current_loss_streak: int = 0
    max_win_streak: int = 0
    max_loss_streak: int = 0
    avg_holding_seconds: Optional[float] = None
    longest_holding_seconds: Optional[int] = None
    shortest_holding_seconds: Optional[int] = None
    total_commission: Decimal = ZERO
    total_swap: Decimal = ZERO
    total_fees: Decimal = ZERO
    avg_risk: Optional[Decimal] = None
    breakeven_rate: Optional[Decimal] = None
    drawdown_series: list[dict[str, Any]] = field(default_factory=list)
    equity_series: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_trades": self.total_trades,
            "open_trades": self.open_trades,
            "closed_trades": self.closed_trades,
            "wins": self.wins,
            "losses": self.losses,
            "breakevens": self.breakevens,
            "gross_profit": float(self.gross_profit),
            "gross_loss": float(self.gross_loss),
            "net_pnl": float(self.net_pnl),
            "win_rate": float(self.win_rate) if self.win_rate is not None else None,
            "profit_factor": float(self.profit_factor) if self.profit_factor is not None else None,
            "avg_win": float(self.avg_win) if self.avg_win is not None else None,
            "avg_loss": float(self.avg_loss) if self.avg_loss is not None else None,
            "payoff_ratio": float(self.payoff_ratio) if self.payoff_ratio is not None else None,
            "expectancy": float(self.expectancy) if self.expectancy is not None else None,
            "avg_rr": float(self.avg_rr) if self.avg_rr is not None else None,
            "avg_r_multiple": float(self.avg_r_multiple) if self.avg_r_multiple is not None else None,
            "best_trade": float(self.best_trade) if self.best_trade is not None else None,
            "worst_trade": float(self.worst_trade) if self.worst_trade is not None else None,
            "max_drawdown": float(self.max_drawdown) if self.max_drawdown is not None else None,
            "max_drawdown_pct": float(self.max_drawdown_pct) if self.max_drawdown_pct is not None else None,
            "current_win_streak": self.current_win_streak,
            "current_loss_streak": self.current_loss_streak,
            "max_win_streak": self.max_win_streak,
            "max_loss_streak": self.max_loss_streak,
            "avg_holding_seconds": self.avg_holding_seconds,
            "longest_holding_seconds": self.longest_holding_seconds,
            "shortest_holding_seconds": self.shortest_holding_seconds,
            "total_commission": float(self.total_commission),
            "total_swap": float(self.total_swap),
            "total_fees": float(self.total_fees),
            "avg_risk": float(self.avg_risk) if self.avg_risk is not None else None,
            "breakeven_rate": float(self.breakeven_rate) if self.breakeven_rate is not None else None,
            "drawdown_series": self.drawdown_series,
            "equity_series": self.equity_series,
        }


def compute_gross_profit(trades: Sequence[Trade]) -> Decimal:
    """Sum of positive net P/L from closed trades."""
    total = ZERO
    for t in closed_trades(trades):
        n = _net(t)
        if n > ZERO:
            total += n
    return total


def compute_gross_loss(trades: Sequence[Trade]) -> Decimal:
    """Absolute sum of negative net P/L from closed trades."""
    total = ZERO
    for t in closed_trades(trades):
        n = _net(t)
        if n < ZERO:
            total += abs(n)
    return total


def compute_net_pnl(trades: Sequence[Trade]) -> Decimal:
    """Sum of net P/L from closed trades."""
    return sum((_net(t) for t in closed_trades(trades)), ZERO)


def compute_win_rate(trades: Sequence[Trade]) -> Optional[Decimal]:
    """
    Win rate = winning trades / total closed trades × 100.

    Breakeven trades count in the denominator but not as wins.
    Open trades are excluded.
    """
    closed = closed_trades(trades)
    if not closed:
        return None
    wins = sum(1 for t in closed if classify_closed(t) == "WIN")
    return percent(Decimal(wins), Decimal(len(closed)))


def compute_profit_factor(trades: Sequence[Trade]) -> Optional[Decimal]:
    """Gross profit / gross loss. None when no closed trades; inf-like large when no losses."""
    gp = compute_gross_profit(trades)
    gl = compute_gross_loss(trades)
    if not closed_trades(trades):
        return None
    if gl == ZERO:
        return Decimal("999.99") if gp > ZERO else ZERO
    return money(gp / gl, 2)


def compute_avg_win(trades: Sequence[Trade]) -> Optional[Decimal]:
    wins = [t for t in closed_trades(trades) if classify_closed(t) == "WIN"]
    if not wins:
        return None
    return money(sum((_net(t) for t in wins), ZERO) / len(wins))


def compute_avg_loss(trades: Sequence[Trade]) -> Optional[Decimal]:
    """Absolute average net P/L of losing trades."""
    losses = [t for t in closed_trades(trades) if classify_closed(t) == "LOSS"]
    if not losses:
        return None
    return money(sum((abs(_net(t)) for t in losses), ZERO) / len(losses))


def compute_payoff_ratio(trades: Sequence[Trade]) -> Optional[Decimal]:
    avg_w = compute_avg_win(trades)
    avg_l = compute_avg_loss(trades)
    if avg_w is None or avg_l is None or avg_l == ZERO:
        return None
    return money(avg_w / avg_l, 2)


def compute_expectancy(trades: Sequence[Trade]) -> Optional[Decimal]:
    """
    Expectancy = P(win)×avg_win − P(loss)×avg_loss.

    Probabilities are over closed trades (including breakevens in denominator).
    Breakeven contribution to expectancy is zero.
    """
    closed = closed_trades(trades)
    if not closed:
        return None
    n = Decimal(len(closed))
    wins = [t for t in closed if classify_closed(t) == "WIN"]
    losses = [t for t in closed if classify_closed(t) == "LOSS"]
    p_win = Decimal(len(wins)) / n
    p_loss = Decimal(len(losses)) / n
    avg_w = compute_avg_win(trades) or ZERO
    avg_l = compute_avg_loss(trades) or ZERO
    return money(p_win * avg_w - p_loss * avg_l)


def compute_avg_rr(trades: Sequence[Trade]) -> Optional[Decimal]:
    values = [
        Decimal(str(t.risk_reward_ratio))
        for t in trades
        if t.risk_reward_ratio is not None and Decimal(str(t.risk_reward_ratio)) > ZERO
    ]
    if not values:
        return None
    return money(sum(values) / len(values), 2)


def compute_avg_r_multiple(trades: Sequence[Trade]) -> Optional[Decimal]:
    values: list[Decimal] = []
    for t in closed_trades(trades):
        r = realized_r_multiple(t)
        if r is not None:
            values.append(r)
    if not values:
        return None
    return money(sum(values) / len(values), 2)


def realized_r_multiple(trade: Trade) -> Optional[Decimal]:
    """net_pnl / risk_amount when risk is valid and positive."""
    risk = to_decimal(trade.risk_amount)
    if risk is None or risk <= ZERO:
        if trade.realized_r_multiple is not None:
            return Decimal(str(trade.realized_r_multiple))
        return None
    return money(_net(trade) / risk, 2)


def compute_drawdown(
    trades: Sequence[Trade],
    starting_balance: Decimal | None = None,
) -> tuple[Optional[Decimal], Optional[Decimal], list[dict], list[dict]]:
    """
    Maximum drawdown from cumulative closed-trade equity.

    Drawdown = current cumulative equity − previous equity peak (negative or zero).
    Returns (max_dd_usd, max_dd_pct, drawdown_series, equity_series).
    """
    closed = sorted(
        closed_trades(trades),
        key=lambda t: (t.close_date or t.trade_date, t.id),
    )
    if not closed:
        return None, None, [], []

    start = starting_balance if starting_balance is not None else ZERO
    equity = start
    peak = start
    max_dd = ZERO
    max_dd_pct: Optional[Decimal] = None
    dd_series: list[dict] = []
    eq_series: list[dict] = []

    # Starting point
    eq_series.append({"label": "Start", "value": float(equity), "drawdown": 0.0})

    for t in closed:
        equity += _net(t)
        if equity > peak:
            peak = equity
        dd = equity - peak  # <= 0
        if dd < max_dd:
            max_dd = dd
            if peak > ZERO:
                max_dd_pct = percent(abs(max_dd), peak)
            elif starting_balance and starting_balance > ZERO:
                max_dd_pct = percent(abs(max_dd), starting_balance)
        label = (t.close_date or t.trade_date).strftime("%Y-%m-%d")
        eq_series.append({"label": label, "value": float(equity), "drawdown": float(dd)})
        dd_series.append({"label": label, "value": float(dd)})

    return money(abs(max_dd)), max_dd_pct, dd_series, eq_series


def compute_equity_vs_balance(
    trades: Sequence[Trade],
    starting_balance: Decimal | None = None,
    current_balance: Decimal | None = None,
) -> dict[str, Any]:
    """
    Two curves for charting:
    - trading_equity: starting_balance + cumulative closed trade net P/L
    - account_balance: trading_equity + implied non-trade cash
      (deposits/withdrawals/adjustments = current_balance - final trading equity)

    Without a deposit ledger, cash is modeled as a constant offset so the
    balance curve ends at the broker current_balance.
    """
    _, _, _, eq_series = compute_drawdown(trades, starting_balance)
    if not eq_series:
        start = float(starting_balance or ZERO)
        cur = float(current_balance if current_balance is not None else start)
        return {
            "labels": ["Start", "Now"],
            "trading_equity": [start, start],
            "account_balance": [start, cur],
            "cash_adjustment": cur - start,
            "final_trading_equity": start,
            "current_balance": cur,
        }

    labels = [p["label"] for p in eq_series]
    trading = [float(p["value"]) for p in eq_series]
    final_eq = trading[-1]
    cur = float(current_balance) if current_balance is not None else final_eq
    cash_adj = cur - final_eq
    balance = [v + cash_adj for v in trading]
    return {
        "labels": labels,
        "trading_equity": trading,
        "account_balance": balance,
        "cash_adjustment": cash_adj,
        "final_trading_equity": final_eq,
        "current_balance": cur,
    }


def compute_streaks(trades: Sequence[Trade]) -> tuple[int, int, int, int]:
    """
    Returns (current_win, current_loss, max_win, max_loss).

    Breakeven breaks both streaks.
    """
    closed = sorted(
        closed_trades(trades),
        key=lambda t: (t.close_date or t.trade_date, t.id),
    )
    max_win = max_loss = cur_win = cur_loss = 0
    for t in closed:
        result = classify_closed(t)
        if result == "WIN":
            cur_win += 1
            cur_loss = 0
            max_win = max(max_win, cur_win)
        elif result == "LOSS":
            cur_loss += 1
            cur_win = 0
            max_loss = max(max_loss, cur_loss)
        else:
            cur_win = cur_loss = 0

    # Current streaks from the end
    current_win = current_loss = 0
    for t in reversed(closed):
        result = classify_closed(t)
        if result == "WIN":
            if current_loss:
                break
            current_win += 1
        elif result == "LOSS":
            if current_win:
                break
            current_loss += 1
        else:
            break

    return current_win, current_loss, max_win, max_loss


def min_breakeven_win_rate(reward_to_risk: Decimal) -> Optional[Decimal]:
    """For R:R ratio R, minimum win rate = 1/(1+R)×100."""
    return minimum_breakeven_win_rate(reward_to_risk)


def minimum_breakeven_win_rate(r: Decimal) -> Optional[Decimal]:
    """Minimum win rate (%) required to break even given reward-to-risk R."""
    if r is None or r <= ZERO:
        return None
    return money(HUNDRED / (Decimal("1") + r), 2)


def compute_holding_stats(
    trades: Sequence[Trade],
) -> tuple[Optional[float], Optional[int], Optional[int]]:
    durations = [t.holding_seconds for t in closed_trades(trades) if t.holding_seconds is not None]
    if not durations:
        return None, None, None
    avg = sum(durations) / len(durations)
    return avg, max(durations), min(durations)


def analyze_performance(
    trades: Sequence[Trade],
    starting_balance: Decimal | None = None,
) -> PerformanceStats:
    """Compute a full PerformanceStats object for the given trades."""
    all_trades = list(trades)
    closed = closed_trades(all_trades)
    open_count = sum(1 for t in all_trades if t.status == TradeStatus.OPEN.value)

    wins = [t for t in closed if classify_closed(t) == "WIN"]
    losses = [t for t in closed if classify_closed(t) == "LOSS"]
    bes = [t for t in closed if classify_closed(t) == "BREAKEVEN"]

    gp = compute_gross_profit(all_trades)
    gl = compute_gross_loss(all_trades)
    net = compute_net_pnl(all_trades)
    avg_w = compute_avg_win(all_trades)
    avg_l = compute_avg_loss(all_trades)
    cw, cl, mw, ml = compute_streaks(all_trades)
    max_dd, max_dd_pct, dd_series, eq_series = compute_drawdown(all_trades, starting_balance)
    avg_hold, long_hold, short_hold = compute_holding_stats(all_trades)

    nets = [_net(t) for t in closed]
    best = max(nets) if nets else None
    worst = min(nets) if nets else None

    risks = [Decimal(str(t.risk_amount)) for t in all_trades if t.risk_amount]
    avg_risk = money(sum(risks) / len(risks)) if risks else None

    be_rate = percent(Decimal(len(bes)), Decimal(len(closed))) if closed else None

    return PerformanceStats(
        total_trades=len(all_trades),
        open_trades=open_count,
        closed_trades=len(closed),
        wins=len(wins),
        losses=len(losses),
        breakevens=len(bes),
        gross_profit=gp,
        gross_loss=gl,
        net_pnl=net,
        win_rate=compute_win_rate(all_trades),
        profit_factor=compute_profit_factor(all_trades),
        avg_win=avg_w,
        avg_loss=avg_l,
        payoff_ratio=compute_payoff_ratio(all_trades),
        expectancy=compute_expectancy(all_trades),
        avg_rr=compute_avg_rr(all_trades),
        avg_r_multiple=compute_avg_r_multiple(all_trades),
        best_trade=best,
        worst_trade=worst,
        max_drawdown=max_dd,
        max_drawdown_pct=max_dd_pct,
        current_win_streak=cw,
        current_loss_streak=cl,
        max_win_streak=mw,
        max_loss_streak=ml,
        avg_holding_seconds=avg_hold,
        longest_holding_seconds=long_hold,
        shortest_holding_seconds=short_hold,
        total_commission=sum((Decimal(str(t.commission or 0)) for t in all_trades), ZERO),
        total_swap=sum((Decimal(str(t.swap or 0)) for t in all_trades), ZERO),
        total_fees=sum((Decimal(str(t.fees or 0)) for t in all_trades), ZERO),
        avg_risk=avg_risk,
        breakeven_rate=be_rate,
        drawdown_series=dd_series,
        equity_series=eq_series,
    )


def period_change(current: Optional[Decimal], previous: Optional[Decimal]) -> Optional[float]:
    """Percent change vs previous period; None when previous is zero/missing."""
    if current is None or previous is None:
        return None
    if previous == ZERO:
        return None
    return float(money((current - previous) / abs(previous) * HUNDRED, 1))


def metric(
    value: Any,
    *,
    kind: str = "money",
    prev: Any = None,
    invert_tone: bool = False,
) -> dict[str, Any]:
    """Build a display metric dict with tone and optional period comparison."""
    d = to_decimal(value) if not isinstance(value, (int, str)) or kind != "count" else value
    display = "—"
    tone = "neutral"

    if kind == "money":
        dd = to_decimal(value)
        if dd is not None:
            display = fmt_money(dd, show_sign=True)
            tone = "positive" if dd > ZERO else ("negative" if dd < ZERO else "neutral")
    elif kind == "pct":
        dd = to_decimal(value)
        if dd is not None:
            display = fmt_pct(dd)
            tone = "positive" if dd >= 50 else "neutral"
    elif kind == "ratio":
        dd = to_decimal(value)
        if dd is not None:
            display = fmt_ratio(dd)
            tone = "positive" if dd >= 1 else "neutral"
    elif kind == "count":
        if value is not None:
            display = str(int(value))
    elif kind == "number":
        dd = to_decimal(value)
        if dd is not None:
            display = fmt_number(dd)

    if invert_tone and tone in ("positive", "negative"):
        tone = "negative" if tone == "positive" else "positive"

    change = period_change(to_decimal(value), to_decimal(prev)) if prev is not None else None
    return {
        "value": float(d) if isinstance(d, Decimal) else d,
        "display": display,
        "change_pct": change,
        "change_label": f"{change:+.1f}% vs prior" if change is not None else None,
        "tone": tone,
    }


def group_by_setup(trades: Sequence[Trade]) -> list[dict[str, Any]]:
    groups: dict[str, list[Trade]] = defaultdict(list)
    for t in closed_trades(trades):
        groups[t.setup or "Other"].append(t)
    rows = []
    for setup, items in sorted(groups.items()):
        stats = analyze_performance(items)
        rows.append({"setup": setup, **stats.to_dict()})
    return rows


def group_by_session(trades: Sequence[Trade]) -> list[dict[str, Any]]:
    groups: dict[str, list[Trade]] = defaultdict(list)
    for t in closed_trades(trades):
        groups[t.trading_session or "Other"].append(t)
    rows = []
    for session, items in sorted(groups.items()):
        stats = analyze_performance(items)
        rows.append({"session": session, **stats.to_dict()})
    return rows


def group_by_timeframe(trades: Sequence[Trade]) -> list[dict[str, Any]]:
    groups: dict[str, list[Trade]] = defaultdict(list)
    for t in closed_trades(trades):
        groups[t.timeframe or "Other"].append(t)
    rows = []
    for tf, items in sorted(groups.items()):
        stats = analyze_performance(items)
        rows.append({"timeframe": tf, **stats.to_dict()})
    return rows


def group_by_direction(trades: Sequence[Trade]) -> list[dict[str, Any]]:
    groups: dict[str, list[Trade]] = defaultdict(list)
    for t in closed_trades(trades):
        groups[t.direction].append(t)
    return [{"direction": d, **analyze_performance(items).to_dict()} for d, items in groups.items()]


def group_by_market(trades: Sequence[Trade]) -> dict[str, dict[str, Any]]:
    result = {}
    for market in ("XAU/USD", "BTC/USD"):
        subset = [t for t in trades if t.market == market]
        result[market] = analyze_performance(subset).to_dict()
    return result


def weekday_frequency(trades: Sequence[Trade]) -> dict[str, int]:
    labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    counts = {label: 0 for label in labels}
    for t in trades:
        counts[labels[t.trade_date.weekday()]] += 1
    return counts


def daily_pnl(trades: Sequence[Trade]) -> list[dict[str, Any]]:
    buckets: dict[str, Decimal] = defaultdict(lambda: ZERO)
    for t in closed_trades(trades):
        day = (t.close_date or t.trade_date).strftime("%Y-%m-%d")
        buckets[day] += _net(t)
    return [{"label": k, "value": float(v)} for k, v in sorted(buckets.items())]


def monthly_pnl(trades: Sequence[Trade]) -> list[dict[str, Any]]:
    buckets: dict[str, Decimal] = defaultdict(lambda: ZERO)
    for t in closed_trades(trades):
        month = (t.close_date or t.trade_date).strftime("%Y-%m")
        buckets[month] += _net(t)
    return [{"label": k, "value": float(v)} for k, v in sorted(buckets.items())]


def hour_pnl(trades: Sequence[Trade]) -> list[dict[str, Any]]:
    buckets: dict[int, Decimal] = defaultdict(lambda: ZERO)
    counts: dict[int, int] = defaultdict(int)
    for t in closed_trades(trades):
        h = t.trade_date.hour
        buckets[h] += _net(t)
        counts[h] += 1
    return [
        {"label": f"{h:02d}:00", "value": float(buckets[h]), "count": counts[h]}
        for h in range(24)
        if counts[h]
    ]


def distribution_counts(trades: Sequence[Trade]) -> dict[str, int]:
    closed = closed_trades(trades)
    return {
        "WIN": sum(1 for t in closed if classify_closed(t) == "WIN"),
        "LOSS": sum(1 for t in closed if classify_closed(t) == "LOSS"),
        "BREAKEVEN": sum(1 for t in closed if classify_closed(t) == "BREAKEVEN"),
    }
