"""Trade model and related enums."""

from __future__ import annotations

import enum
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Market(str, enum.Enum):
    XAUUSD = "XAU/USD"
    BTCUSD = "BTC/USD"


class Direction(str, enum.Enum):
    BUY = "BUY"
    SELL = "SELL"


class TradeStatus(str, enum.Enum):
    OPEN = "OPEN"
    WIN = "WIN"
    LOSS = "LOSS"
    BREAKEVEN = "BREAKEVEN"


class Setup(str, enum.Enum):
    BREAKOUT = "Breakout"
    PULLBACK = "Pullback"
    TREND_CONTINUATION = "Trend Continuation"
    REVERSAL = "Reversal"
    RANGE_TRADE = "Range Trade"
    SUPPORT_RESISTANCE = "Support/Resistance"
    LIQUIDITY_SWEEP = "Liquidity Sweep"
    NEWS_TRADE = "News Trade"
    OTHER = "Other"


class Timeframe(str, enum.Enum):
    M1 = "M1"
    M5 = "M5"
    M15 = "M15"
    M30 = "M30"
    H1 = "H1"
    H4 = "H4"
    D1 = "D1"


class TradingSession(str, enum.Enum):
    ASIAN = "Asian"
    LONDON = "London"
    NEW_YORK = "New York"
    OVERLAP = "London/New York Overlap"
    OTHER = "Other"


Money = Numeric(18, 8)
Ratio = Numeric(12, 4)


class Trade(Base):
    """Individual trade record for XAU/USD or BTC/USD."""

    __tablename__ = "trades"
    __table_args__ = (
        Index("ix_trades_trade_date", "trade_date"),
        Index("ix_trades_market", "market"),
        Index("ix_trades_status", "status"),
        Index("ix_trades_setup", "setup"),
        Index("ix_trades_external_ticket", "external_ticket"),
        Index("ix_trades_source", "source"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trade_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    close_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    market: Mapped[str] = mapped_column(String(16), nullable=False)
    direction: Mapped[str] = mapped_column(String(8), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=TradeStatus.OPEN.value)

    entry_price: Mapped[Decimal] = mapped_column(Money, nullable=False)
    exit_price: Mapped[Optional[Decimal]] = mapped_column(Money, nullable=True)
    lot_size: Mapped[Decimal] = mapped_column(Money, nullable=False)
    stop_loss: Mapped[Optional[Decimal]] = mapped_column(Money, nullable=True)
    take_profit: Mapped[Optional[Decimal]] = mapped_column(Money, nullable=True)

    profit_loss: Mapped[Optional[Decimal]] = mapped_column(Money, nullable=True)
    commission: Mapped[Decimal] = mapped_column(Money, nullable=False, default=Decimal("0"))
    swap: Mapped[Decimal] = mapped_column(Money, nullable=False, default=Decimal("0"))
    fees: Mapped[Decimal] = mapped_column(Money, nullable=False, default=Decimal("0"))
    net_profit_loss: Mapped[Optional[Decimal]] = mapped_column(Money, nullable=True)
    pips: Mapped[Optional[Decimal]] = mapped_column(Money, nullable=True)

    risk_amount: Mapped[Optional[Decimal]] = mapped_column(Money, nullable=True)
    planned_reward: Mapped[Optional[Decimal]] = mapped_column(Money, nullable=True)
    risk_reward_ratio: Mapped[Optional[Decimal]] = mapped_column(Ratio, nullable=True)
    realized_r_multiple: Mapped[Optional[Decimal]] = mapped_column(Ratio, nullable=True)
    account_balance_after: Mapped[Optional[Decimal]] = mapped_column(Money, nullable=True)

    setup: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    timeframe: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    trading_session: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    entry_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    exit_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    mistake: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    lesson: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    emotion_before: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    emotion_after: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    followed_plan: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    confidence_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    screenshot_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    source: Mapped[str] = mapped_column(String(32), nullable=False, default="MANUAL")
    external_ticket: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    journal_entries = relationship("JournalEntry", back_populates="trade", lazy="selectin")

    @property
    def is_closed(self) -> bool:
        return self.status != TradeStatus.OPEN.value

    @property
    def holding_seconds(self) -> Optional[int]:
        if not self.close_date or not self.trade_date:
            return None
        delta = self.close_date - self.trade_date
        return int(delta.total_seconds())
