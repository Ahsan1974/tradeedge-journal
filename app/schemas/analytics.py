"""Analytics response schemas."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, Field


class MetricValue(BaseModel):
    value: Optional[Decimal | float | int | str] = None
    display: str = "—"
    change_pct: Optional[float] = None
    change_label: Optional[str] = None
    tone: str = "neutral"  # positive | negative | neutral


class DashboardSummary(BaseModel):
    gross_profit: MetricValue
    gross_loss: MetricValue
    net_pnl: MetricValue
    win_rate: MetricValue
    total_trades: MetricValue
    avg_rr: MetricValue
    best_trade: MetricValue
    worst_trade: MetricValue
    month_pnl: MetricValue
    secondary: dict[str, Any] = Field(default_factory=dict)
    market_stats: dict[str, Any] = Field(default_factory=dict)
    better_market: Optional[str] = None


class SeriesPoint(BaseModel):
    label: str
    value: float
    extra: Optional[dict[str, Any]] = None


class ChartSeries(BaseModel):
    labels: list[str] = Field(default_factory=list)
    datasets: list[dict[str, Any]] = Field(default_factory=list)
