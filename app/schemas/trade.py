"""Pydantic schemas for trades."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.trade import Direction, Market, Setup, Timeframe, TradeStatus, TradingSession

ALLOWED_MARKETS = {m.value for m in Market}
ALLOWED_DIRECTIONS = {d.value for d in Direction}
ALLOWED_STATUSES = {s.value for s in TradeStatus}
ALLOWED_SETUPS = {s.value for s in Setup}
ALLOWED_TIMEFRAMES = {t.value for t in Timeframe}
ALLOWED_SESSIONS = {s.value for s in TradingSession}


class TradeBase(BaseModel):
    trade_date: datetime
    close_date: Optional[datetime] = None
    market: str
    direction: str
    status: str = TradeStatus.OPEN.value
    entry_price: Decimal
    exit_price: Optional[Decimal] = None
    lot_size: Decimal
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None
    profit_loss: Optional[Decimal] = None
    commission: Decimal = Decimal("0")
    swap: Decimal = Decimal("0")
    fees: Decimal = Decimal("0")
    net_profit_loss: Optional[Decimal] = None
    pips: Optional[Decimal] = None
    risk_amount: Optional[Decimal] = None
    planned_reward: Optional[Decimal] = None
    risk_reward_ratio: Optional[Decimal] = None
    realized_r_multiple: Optional[Decimal] = None
    account_balance_after: Optional[Decimal] = None
    setup: Optional[str] = None
    timeframe: Optional[str] = None
    trading_session: Optional[str] = None
    entry_reason: Optional[str] = None
    exit_reason: Optional[str] = None
    mistake: Optional[str] = None
    lesson: Optional[str] = None
    emotion_before: Optional[str] = None
    emotion_after: Optional[str] = None
    followed_plan: Optional[bool] = None
    confidence_score: Optional[int] = Field(default=None, ge=1, le=10)
    screenshot_url: Optional[str] = None
    source: str = "MANUAL"
    external_ticket: Optional[str] = None

    @field_validator("market")
    @classmethod
    def validate_market(cls, v: str) -> str:
        if v not in ALLOWED_MARKETS:
            raise ValueError(f"Market must be one of {sorted(ALLOWED_MARKETS)}")
        return v

    @field_validator("direction")
    @classmethod
    def validate_direction(cls, v: str) -> str:
        v = v.upper()
        if v not in ALLOWED_DIRECTIONS:
            raise ValueError(f"Direction must be one of {sorted(ALLOWED_DIRECTIONS)}")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        v = v.upper()
        if v not in ALLOWED_STATUSES:
            raise ValueError(f"Status must be one of {sorted(ALLOWED_STATUSES)}")
        return v

    @field_validator("entry_price", "lot_size")
    @classmethod
    def validate_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Must be positive")
        return v

    @field_validator("exit_price")
    @classmethod
    def validate_exit(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and v <= 0:
            raise ValueError("Exit price must be positive")
        return v

    @model_validator(mode="after")
    def validate_dates_and_sl_tp(self) -> TradeBase:
        if self.close_date and self.close_date < self.trade_date:
            raise ValueError("Close date cannot be before open date")
        if self.stop_loss is not None and self.stop_loss == self.entry_price:
            raise ValueError("Stop loss cannot equal entry price")
        if self.take_profit is not None and self.take_profit == self.entry_price:
            raise ValueError("Take profit cannot equal entry price")
        return self


class TradeCreate(TradeBase):
    pass


class TradeUpdate(TradeBase):
    pass


class TradeRead(TradeBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class TradeFilterParams(BaseModel):
    q: Optional[str] = None
    market: Optional[str] = None
    status: Optional[str] = None
    direction: Optional[str] = None
    setup: Optional[str] = None
    timeframe: Optional[str] = None
    session: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    min_pnl: Optional[Decimal] = None
    max_pnl: Optional[Decimal] = None
    sort: str = "trade_date"
    order: str = "desc"
    page: int = 1
    per_page: int = 25
