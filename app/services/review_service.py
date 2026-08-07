"""Daily and weekly trading review summaries."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any, Sequence

from app.models.journal import JournalEntry
from app.models.risk_settings import RiskSettings
from app.models.trade import Trade
from app.services.analytics_service import (
    _net,
    analyze_performance,
    closed_trades,
    group_by_market,
    group_by_setup,
)
from app.services.goals_service import build_goals_progress, build_streak_summary, followed_plan_rate
from app.utils.decimals import ZERO


@dataclass
class ReviewSummary:
    scope: str
    title: str
    period_label: str
    stats: Any
    streaks: dict[str, Any]
    goals: list[Any] = field(default_factory=list)
    best_trade: Trade | None = None
    worst_trade: Trade | None = None
    top_setup: str | None = None
    better_market: str | None = None
    followed_plan_pct: Decimal | None = None
    lessons: list[str] = field(default_factory=list)
    mistakes: list[str] = field(default_factory=list)
    emotions: list[str] = field(default_factory=list)
    journal_count: int = 0
    highlights: list[str] = field(default_factory=list)
    trades: list[Trade] = field(default_factory=list)


def _pick_best_worst(trades: Sequence[Trade]) -> tuple[Trade | None, Trade | None]:
    closed = list(closed_trades(trades))
    if not closed:
        return None, None
    best = max(closed, key=lambda t: _net(t))
    worst = min(closed, key=lambda t: _net(t))
    return best, worst


def _top_setup(trades: Sequence[Trade]) -> str | None:
    rows = group_by_setup(trades)
    scored = [(r["setup"], Decimal(str(r.get("net_pnl", 0)))) for r in rows if r.get("closed_trades") or r.get("total_trades")]
    if not scored:
        return None
    return max(scored, key=lambda x: x[1])[0]


def _collect_notes(trades: Sequence[Trade], entries: Sequence[JournalEntry]) -> tuple[list[str], list[str], list[str]]:
    lessons: list[str] = []
    mistakes: list[str] = []
    emotions: list[str] = []
    for t in trades:
        if t.lesson:
            lessons.append(str(t.lesson).strip())
        if t.mistake:
            mistakes.append(str(t.mistake).strip())
        if t.emotion_after or t.emotion_before:
            emotions.append(str(t.emotion_after or t.emotion_before).strip())
    for e in entries:
        if e.lesson:
            lessons.append(str(e.lesson).strip())
        if e.mistakes:
            mistakes.append(str(e.mistakes).strip())
        if e.emotional_state:
            emotions.append(str(e.emotional_state).strip())

    def uniq(items: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for i in items:
            key = i.lower()
            if i and key not in seen:
                seen.add(key)
                out.append(i)
        return out[:8]

    return uniq(lessons), uniq(mistakes), uniq(emotions)


def build_review(
    *,
    scope: str,
    settings: RiskSettings,
    trades: Sequence[Trade],
    entries: Sequence[JournalEntry],
    week_trades: Sequence[Trade],
    month_trades: Sequence[Trade],
    period_label: str,
    all_goals_week_entries: Sequence[JournalEntry] | None = None,
) -> ReviewSummary:
    stats = analyze_performance(trades, settings.starting_balance)
    streaks = build_streak_summary(trades)
    goals = build_goals_progress(
        settings,
        week_trades=week_trades,
        month_trades=month_trades,
        week_entries=all_goals_week_entries or entries,
    )
    best, worst = _pick_best_worst(trades)
    markets = group_by_market(trades)
    xau = Decimal(str(markets["XAU/USD"]["net_pnl"]))
    btc = Decimal(str(markets["BTC/USD"]["net_pnl"]))
    better = None
    if xau != btc:
        better = "XAU/USD" if xau > btc else "BTC/USD"

    lessons, mistakes, emotions = _collect_notes(trades, entries)
    plan_pct = followed_plan_rate(trades, entries)

    highlights: list[str] = []
    if stats.closed_trades == 0:
        highlights.append("No closed trades in this period — good time to review your plan.")
    else:
        highlights.append(
            f"{stats.closed_trades} closed trade(s), net {stats.net_pnl:+.2f} USD, "
            f"win rate {stats.win_rate or 0:.1f}%."
        )
        if plan_pct is not None:
            highlights.append(f"Followed plan on {plan_pct:.0f}% of reviewed trades.")
        if streaks["current_win_streak"]:
            highlights.append(f"On a {streaks['current_win_streak']}-trade win streak.")
        elif streaks["current_loss_streak"]:
            highlights.append(
                f"On a {streaks['current_loss_streak']}-trade losing streak — protect capital."
            )
        if better:
            highlights.append(f"{better} outperformed the other market this period.")
        if best and _net(best) > ZERO:
            highlights.append(f"Best trade: {best.market} {_net(best):+.2f}.")
        if worst and _net(worst) < ZERO:
            highlights.append(f"Biggest loss: {worst.market} {_net(worst):+.2f}.")

    title = "Daily Review" if scope == "daily" else "Weekly Review"
    return ReviewSummary(
        scope=scope,
        title=title,
        period_label=period_label,
        stats=stats,
        streaks=streaks,
        goals=goals,
        best_trade=best,
        worst_trade=worst,
        top_setup=_top_setup(trades),
        better_market=better,
        followed_plan_pct=plan_pct,
        lessons=lessons,
        mistakes=mistakes,
        emotions=emotions,
        journal_count=len(entries),
        highlights=highlights,
        trades=list(closed_trades(trades)),
    )
