"""Settings schemas."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field


class RiskSettingsUpdate(BaseModel):
    starting_balance: Decimal = Field(gt=0)
    current_balance: Decimal = Field(gt=0)
    default_risk_percent: Decimal = Field(ge=0)
    maximum_risk_percent: Decimal = Field(ge=0)
    daily_loss_limit_percent: Decimal = Field(ge=0)
    weekly_loss_limit_percent: Decimal = Field(ge=0)
    maximum_trades_per_day: int = Field(ge=1)
    maximum_consecutive_losses: int = Field(ge=1)
    maximum_total_open_risk_percent: Decimal = Field(ge=0)
    base_currency: str = "USD"
    timezone: str = "Asia/Karachi"
    default_dashboard_period: str = "30d"
    default_market_filter: str = "ALL"
    number_format: str = "en_US"
    date_format: str = "%Y-%m-%d %H:%M"
    table_density: str = "comfortable"


class SymbolSettingsUpdate(BaseModel):
    contract_size: Decimal = Field(gt=0)
    tick_size: Decimal = Field(gt=0)
    tick_value_per_lot: Decimal = Field(gt=0)
    pip_size: Decimal = Field(gt=0)
    decimal_places: int = Field(ge=0, le=8)
    enabled: bool = True
