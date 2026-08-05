#!/usr/bin/env python3
"""Sync closed Exness MT5 trades into TradeEdge Journal."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import get_settings
from app.database import SessionLocal, init_db
from app.services.mt5_service import sync_closed_trades


def main() -> int:
    get_settings.cache_clear()
    init_db()
    db = SessionLocal()
    try:
        result = sync_closed_trades(db)
        print(result.message)
        for err in result.errors:
            print("ERROR:", err, file=sys.stderr)
        return 0 if result.connected and not result.errors else 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
