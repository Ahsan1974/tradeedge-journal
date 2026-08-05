"""Settings repository with defaults bootstrap."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.risk_settings import RiskSettings
from app.models.symbol_configuration import SymbolConfiguration

# Example broker-dependent defaults — users must align with their broker.
DEFAULT_SYMBOLS = {
    "XAU/USD": {
        "contract_size": Decimal("100"),
        "tick_size": Decimal("0.01"),
        "tick_value_per_lot": Decimal("1"),
        "pip_size": Decimal("0.1"),
        "decimal_places": 2,
    },
    "BTC/USD": {
        "contract_size": Decimal("1"),
        "tick_size": Decimal("0.01"),
        "tick_value_per_lot": Decimal("0.01"),
        "pip_size": Decimal("1"),
        "decimal_places": 2,
    },
}


class SettingsRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_risk_settings(self) -> RiskSettings:
        settings = self.db.scalar(select(RiskSettings).limit(1))
        if settings is None:
            settings = RiskSettings()
            self.db.add(settings)
            self.db.commit()
            self.db.refresh(settings)
        return settings

    def save_risk_settings(self, settings: RiskSettings) -> RiskSettings:
        self.db.add(settings)
        self.db.commit()
        self.db.refresh(settings)
        return settings

    def ensure_symbols(self) -> list[SymbolConfiguration]:
        existing = {
            s.market: s
            for s in self.db.scalars(select(SymbolConfiguration)).all()
        }
        created = False
        for market, vals in DEFAULT_SYMBOLS.items():
            if market not in existing:
                sym = SymbolConfiguration(market=market, enabled=True, **vals)
                self.db.add(sym)
                created = True
        if created:
            self.db.commit()
        return list(self.db.scalars(select(SymbolConfiguration)).all())

    def get_symbol(self, market: str) -> SymbolConfiguration | None:
        self.ensure_symbols()
        return self.db.scalar(
            select(SymbolConfiguration).where(SymbolConfiguration.market == market)
        )

    def save_symbol(self, symbol: SymbolConfiguration) -> SymbolConfiguration:
        self.db.add(symbol)
        self.db.commit()
        self.db.refresh(symbol)
        return symbol
