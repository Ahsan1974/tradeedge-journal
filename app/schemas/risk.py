"""Risk calculator schemas."""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class PositionSizeRequest(BaseModel):
    market: str
    account_balance: Decimal = Field(gt=0)
    risk_percent: Decimal = Field(gt=0)
    entry_price: Decimal = Field(gt=0)
    stop_loss_price: Decimal = Field(gt=0)
    tick_size: Optional[Decimal] = None
    tick_value_per_lot: Optional[Decimal] = None
    contract_size: Optional[Decimal] = None


class PositionSizeResult(BaseModel):
    risk_amount: Optional[Decimal] = None
    stop_distance: Optional[Decimal] = None
    number_of_ticks: Optional[Decimal] = None
    suggested_lot_size: Optional[Decimal] = None
    position_value: Optional[Decimal] = None
    exceeds_max_risk: bool = False
    max_risk_percent: Optional[Decimal] = None
    error: Optional[str] = None
    warning: Optional[str] = None


class RiskRewardRequest(BaseModel):
    direction: str
    entry: Decimal = Field(gt=0)
    stop_loss: Decimal = Field(gt=0)
    take_profit: Decimal = Field(gt=0)


class RiskRewardResult(BaseModel):
    risk_distance: Optional[Decimal] = None
    reward_distance: Optional[Decimal] = None
    risk_reward_ratio: Optional[Decimal] = None
    min_breakeven_win_rate: Optional[Decimal] = None
    error: Optional[str] = None
