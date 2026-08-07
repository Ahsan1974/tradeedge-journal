"""Goals progress and trading streaks helpers."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Sequence

from app.models.journal import JournalEntry
from app.models.risk_settings import RiskSettings
from app.models.trade import Trade
from app.services.analytics_service import analyze_performance, compute_streaks
from app.utils.decimals import ZERO, HUNDRED, money, safe_div


@dataclass
class GoalProgress:
    key: str
    label: str
    current: Decimal
    target: Decimal
    unit: str  # money | pct
    pct_complete: float
    met: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "current": float(self.current),
            "target": float(self.target),
            "unit": self.unit,
            "pct_complete": self.pct_complete,
            "met": self.met,
        }


def _clamp_pct(current: Decimal, target: Decimal) -> float:
    if target <= ZERO:
        return 100.0 if current >= ZERO else 0.0
    # For money goals, progress is current/target (capped at 100 for display bar)
    # Negative current → 0%
    if current <= ZERO and target > ZERO:
        return 0.0
    raw = float(safe_div(current, target, default=ZERO) * HUNDRED)
    return max(0.0, min(150.0, raw))  # allow slight overshoot on bar


def followed_plan_rate(trades: Sequence[Trade], entries: Sequence[JournalEntry] | None = None) -> Decimal | None:
    """Prefer trade.followed_plan; fall back to journal entries."""
    planned = [t for t in trades if t.followed_plan is not None]
    if planned:
        yes = sum(1 for t in planned if t.followed_plan)
        return money(Decimal(yes) / Decimal(len(planned)) * HUNDRED, 1)
    if entries:
        planned_e = [e for e in entries if e.followed_plan is not None]
        if planned_e:
            yes = sum(1 for e in planned_e if e.followed_plan)
            return money(Decimal(yes) / Decimal(len(planned_e)) * HUNDRED, 1)
    return None


def build_goals_progress(
    settings: RiskSettings,
    *,
    week_trades: Sequence[Trade],
    month_trades: Sequence[Trade],
    week_entries: Sequence[JournalEntry] | None = None,
    month_entries: Sequence[JournalEntry] | None = None,
) -> list[GoalProgress]:
    week_stats = analyze_performance(week_trades, settings.starting_balance)
    month_stats = analyze_performance(month_trades, settings.starting_balance)
    week_plan = followed_plan_rate(week_trades, week_entries)
    # Win rate uses month for a more stable target read
    wr = month_stats.win_rate if month_stats.win_rate is not None else ZERO
    plan = week_plan if week_plan is not None else followed_plan_rate(month_trades, month_entries)

    goals = [
        GoalProgress(
            key="weekly_pnl",
            label="Weekly P/L",
            current=week_stats.net_pnl,
            target=Decimal(str(getattr(settings, "weekly_pnl_goal", 50) or 50)),
            unit="money",
            pct_complete=_clamp_pct(
                week_stats.net_pnl, Decimal(str(getattr(settings, "weekly_pnl_goal", 50) or 50))
            ),
            met=week_stats.net_pnl >= Decimal(str(getattr(settings, "weekly_pnl_goal", 50) or 50)),
        ),
        GoalProgress(
            key="monthly_pnl",
            label="Monthly P/L",
            current=month_stats.net_pnl,
            target=Decimal(str(getattr(settings, "monthly_pnl_goal", 200) or 200)),
            unit="money",
            pct_complete=_clamp_pct(
                month_stats.net_pnl, Decimal(str(getattr(settings, "monthly_pnl_goal", 200) or 200))
            ),
            met=month_stats.net_pnl >= Decimal(str(getattr(settings, "monthly_pnl_goal", 200) or 200)),
        ),
        GoalProgress(
            key="win_rate",
            label="Win rate (month)",
            current=wr or ZERO,
            target=Decimal(str(getattr(settings, "win_rate_goal", 50) or 50)),
            unit="pct",
            pct_complete=_clamp_pct(wr or ZERO, Decimal(str(getattr(settings, "win_rate_goal", 50) or 50))),
            met=(wr or ZERO) >= Decimal(str(getattr(settings, "win_rate_goal", 50) or 50)),
        ),
        GoalProgress(
            key="followed_plan",
            label="Followed plan (week)",
            current=plan if plan is not None else ZERO,
            target=Decimal(str(getattr(settings, "followed_plan_goal", 80) or 80)),
            unit="pct",
            pct_complete=_clamp_pct(
                plan or ZERO, Decimal(str(getattr(settings, "followed_plan_goal", 80) or 80))
            ),
            met=(plan or ZERO) >= Decimal(str(getattr(settings, "followed_plan_goal", 80) or 80))
            if plan is not None
            else False,
        ),
    ]
    return goals


def build_streak_summary(trades: Sequence[Trade]) -> dict[str, Any]:
    cur_win, cur_loss, max_win, max_loss = compute_streaks(trades)
    return {
        "current_win_streak": cur_win,
        "current_loss_streak": cur_loss,
        "max_win_streak": max_win,
        "max_loss_streak": max_loss,
        "active": "win" if cur_win else ("loss" if cur_loss else "none"),
    }
