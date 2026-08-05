#!/usr/bin/env python3
"""Initialize database tables and default settings/symbols."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database import SessionLocal, init_db
from app.repositories.settings_repository import SettingsRepository


def main() -> int:
    print("Initializing database…")
    init_db()
    db = SessionLocal()
    try:
        settings = SettingsRepository(db).get_risk_settings()
        symbols = SettingsRepository(db).ensure_symbols()
        print(f"Risk settings ready (balance={settings.current_balance}).")
        print(f"Symbols: {', '.join(s.market for s in symbols)}")
        print("Done.")
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
