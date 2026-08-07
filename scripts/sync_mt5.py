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
    quiet = "--quiet" in sys.argv or "-q" in sys.argv
    get_settings.cache_clear()
    init_db()
    db = SessionLocal()
    try:
        result = sync_closed_trades(db)
        print(result.message)
        for err in result.errors:
            print("ERROR:", err, file=sys.stderr)
        ok = bool(result.connected and not result.errors)
        if not quiet and sys.platform == "win32" and sys.stdout.isatty():
            try:
                import ctypes

                ctypes.windll.user32.MessageBoxW(
                    0,
                    (result.message or "Done")[:500],
                    "TradeEdge MT5 Sync" + (" — OK" if ok else " — Check errors"),
                    0x40 if ok else 0x30,
                )
            except Exception:  # noqa: BLE001
                pass
        return 0 if ok else 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
