#!/usr/bin/env python3
"""
Seed fictional demo trades and journal entries.

Usage:
  python scripts/seed_demo_data.py
  python scripts/seed_demo_data.py --clear-demo
"""

from __future__ import annotations

import argparse
import random
import sys
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from zoneinfo import ZoneInfo

from sqlalchemy import delete, select

from app.database import SessionLocal, init_db
from app.models.journal import JournalEntry
from app.models.trade import Trade
from app.repositories.settings_repository import SettingsRepository
from app.repositories.trade_repository import TradeRepository

TZ = ZoneInfo("Asia/Karachi")
DEMO = "DEMO"

SETUPS = [
    "Breakout",
    "Pullback",
    "Trend Continuation",
    "Reversal",
    "Range Trade",
    "Support/Resistance",
    "Liquidity Sweep",
    "News Trade",
    "Other",
]
TIMEFRAMES = ["M5", "M15", "M30", "H1", "H4", "D1"]
SESSIONS = ["Asian", "London", "New York", "London/New York Overlap", "Other"]
EMOTIONS = ["Calm", "Confident", "Anxious", "FOMO", "Revenge", "Focused", "Tired"]


def _clear_demo(db) -> None:
    # Delete journal entries linked to demo trades or tagged DEMO
    demo_ids = list(db.scalars(select(Trade.id).where(Trade.source == DEMO)).all())
    if demo_ids:
        db.execute(delete(JournalEntry).where(JournalEntry.trade_id.in_(demo_ids)))
    db.execute(delete(JournalEntry).where(JournalEntry.tags.ilike("%DEMO%")))
    count = TradeRepository(db).delete_by_source(DEMO)
    print(f"Removed {count} demo trades (and linked journal rows).")


def _make_trade(
    rng: random.Random,
    *,
    market: str,
    day: datetime,
    ticket: int,
) -> Trade:
    direction = rng.choice(["BUY", "SELL"])
    if market == "XAU/USD":
        entry = Decimal(str(round(rng.uniform(2300, 2750), 2)))
        move = Decimal(str(round(rng.uniform(0.5, 18), 2)))
    else:
        entry = Decimal(str(round(rng.uniform(55000, 98000), 2)))
        move = Decimal(str(round(rng.uniform(50, 1200), 2)))

    roll = rng.random()
    if roll < 0.08:
        status = "OPEN"
        exit_p = None
        close = None
        net = None
        gross = None
    elif roll < 0.18:
        status = "BREAKEVEN"
        exit_p = entry
        close = day + timedelta(hours=rng.randint(1, 8))
        gross = Decimal("0")
        net = Decimal("-2.00")
    elif roll < 0.58:
        status = "WIN"
        exit_p = entry + move if direction == "BUY" else entry - move
        close = day + timedelta(hours=rng.randint(1, 12))
        gross = Decimal(str(round(rng.uniform(40, 280), 2)))
        net = gross - Decimal("2.50")
    else:
        status = "LOSS"
        exit_p = entry - move if direction == "BUY" else entry + move
        close = day + timedelta(hours=rng.randint(1, 10))
        gross = Decimal(str(round(-rng.uniform(30, 180), 2)))
        net = gross - Decimal("2.50")

    lot = Decimal(str(round(rng.choice([0.05, 0.1, 0.15, 0.2, 0.25]), 2)))
    risk = Decimal(str(round(rng.uniform(50, 150), 2)))
    rr = Decimal(str(round(rng.uniform(1.0, 3.5), 2)))
    realized = (net / risk).quantize(Decimal("0.01")) if net is not None and risk else None
    sl = entry - Decimal("5") if direction == "BUY" else entry + Decimal("5")
    tp = entry + Decimal("10") if direction == "BUY" else entry - Decimal("10")
    if market == "BTC/USD":
        sl = entry - Decimal("200") if direction == "BUY" else entry + Decimal("200")
        tp = entry + Decimal("400") if direction == "BUY" else entry - Decimal("400")

    return Trade(
        trade_date=day,
        close_date=close,
        market=market,
        direction=direction,
        status=status,
        entry_price=entry,
        exit_price=exit_p,
        lot_size=lot,
        stop_loss=sl,
        take_profit=tp,
        profit_loss=gross,
        commission=Decimal("2.00"),
        swap=Decimal("0"),
        fees=Decimal("0.50"),
        net_profit_loss=net,
        pips=move if status != "OPEN" else None,
        risk_amount=risk,
        planned_reward=risk * rr,
        risk_reward_ratio=rr,
        realized_r_multiple=realized,
        setup=rng.choice(SETUPS),
        timeframe=rng.choice(TIMEFRAMES),
        trading_session=rng.choice(SESSIONS),
        entry_reason="Demo setup based on structure and momentum.",
        exit_reason="Target hit / stop hit / manual exit (demo).",
        mistake=rng.choice([None, "Early entry", "Moved stop", "Oversize", None, None]),
        lesson=rng.choice([None, "Wait for confirmation", "Respect daily loss limit", None]),
        emotion_before=rng.choice(EMOTIONS),
        emotion_after=rng.choice(EMOTIONS),
        followed_plan=rng.choice([True, True, True, False]),
        confidence_score=rng.randint(4, 9),
        source=DEMO,
        external_ticket=f"DEMO-{ticket}",
    )


def seed(db) -> None:
    existing = TradeRepository(db).all_filtered(source=DEMO)
    if existing:
        print(f"Demo data already present ({len(existing)} trades). Use --clear-demo first.")
        return

    SettingsRepository(db).get_risk_settings()
    SettingsRepository(db).ensure_symbols()

    rng = random.Random(42)
    now = datetime.now(TZ)
    start = now - timedelta(days=120)
    trades: list[Trade] = []
    ticket = 1000

    # 40 XAU + 30 BTC across ~4 months
    for i in range(40):
        day = start + timedelta(days=rng.randint(0, 119), hours=rng.randint(1, 20))
        trades.append(_make_trade(rng, market="XAU/USD", day=day, ticket=ticket))
        ticket += 1
    for i in range(30):
        day = start + timedelta(days=rng.randint(0, 119), hours=rng.randint(1, 20))
        trades.append(_make_trade(rng, market="BTC/USD", day=day, ticket=ticket))
        ticket += 1

    for t in trades:
        db.add(t)
    db.commit()

    # Refresh IDs
    demo_trades = TradeRepository(db).all_filtered(source=DEMO)
    journal_count = 0
    for i in range(12):
        t = rng.choice(demo_trades)
        entry = JournalEntry(
            trade_id=t.id if i < 8 else None,
            entry_date=(t.trade_date.astimezone(TZ).date()),
            title=rng.choice(
                [
                    "London session review",
                    "Gold pullback notes",
                    "BTC volatility lesson",
                    "Discipline check-in",
                    "Pre-news checklist",
                ]
            ),
            market=t.market if i % 2 == 0 else None,
            setup=t.setup,
            notes="Fictional demo journal note for process review.",
            lesson=rng.choice(
                ["Stick to 1% risk", "No revenge trades", "Journal before re-entry", "Wait for NY open"]
            ),
            mistakes=rng.choice(["None", "Skipped checklist", "Sized up emotionally", None]),
            emotional_state=rng.choice(EMOTIONS),
            followed_plan=rng.choice([True, False, True]),
            tags="DEMO,review,process",
        )
        db.add(entry)
        journal_count += 1
    db.commit()

    # Update current balance roughly
    settings = SettingsRepository(db).get_risk_settings()
    closed_net = sum((t.net_profit_loss or Decimal("0")) for t in demo_trades if t.status != "OPEN")
    settings.current_balance = settings.starting_balance + closed_net
    SettingsRepository(db).save_risk_settings(settings)

    print(f"Seeded {len(demo_trades)} demo trades and {journal_count} journal entries.")
    print(f"Updated current balance to {settings.current_balance}.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed or clear DEMO trading data")
    parser.add_argument("--clear-demo", action="store_true", help="Delete DEMO-sourced data only")
    args = parser.parse_args()
    init_db()
    db = SessionLocal()
    try:
        if args.clear_demo:
            _clear_demo(db)
        else:
            seed(db)
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
