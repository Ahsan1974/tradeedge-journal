"""Journal analytics helpers."""

from __future__ import annotations

from collections import Counter
from typing import Any

from app.models.journal import JournalEntry
from app.models.trade import Trade
from app.services.analytics_service import analyze_performance, closed_trades


def journal_analytics(entries: list[JournalEntry], trades: list[Trade] | None = None) -> dict[str, Any]:
    """Summary analytics for the journal page."""
    if not entries:
        return {
            "followed_plan_pct": None,
            "most_frequent_mistake": None,
            "most_frequent_setup": None,
            "most_common_emotion": None,
            "performance_followed": None,
            "performance_not_followed": None,
        }

    planned = [e for e in entries if e.followed_plan is not None]
    followed_pct = (
        round(sum(1 for e in planned if e.followed_plan) / len(planned) * 100, 1) if planned else None
    )

    mistakes = [e.mistakes.strip() for e in entries if e.mistakes and e.mistakes.strip()]
    setups = [e.setup for e in entries if e.setup]
    emotions = [e.emotional_state for e in entries if e.emotional_state]

    most_mistake = Counter(mistakes).most_common(1)[0][0] if mistakes else None
    most_setup = Counter(setups).most_common(1)[0][0] if setups else None
    most_emotion = Counter(emotions).most_common(1)[0][0] if emotions else None

    perf_followed = perf_not = None
    if trades:
        closed = closed_trades(trades)
        followed_trades = [t for t in closed if t.followed_plan is True]
        not_followed = [t for t in closed if t.followed_plan is False]
        if followed_trades:
            perf_followed = analyze_performance(followed_trades).to_dict()
        if not_followed:
            perf_not = analyze_performance(not_followed).to_dict()

    return {
        "followed_plan_pct": followed_pct,
        "most_frequent_mistake": most_mistake,
        "most_frequent_setup": most_setup,
        "most_common_emotion": most_emotion,
        "performance_followed": perf_followed,
        "performance_not_followed": perf_not,
    }
