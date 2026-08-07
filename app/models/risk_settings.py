"""Risk settings model."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

Money = Numeric(18, 8)
Percent = Numeric(8, 4)


class RiskSettings(Base):
    """Singleton-style risk and account configuration (single personal user)."""

    __tablename__ = "risk_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    starting_balance: Mapped[Decimal] = mapped_column(Money, nullable=False, default=Decimal("103"))
    current_balance: Mapped[Decimal] = mapped_column(Money, nullable=False, default=Decimal("103"))
    default_risk_percent: Mapped[Decimal] = mapped_column(Percent, nullable=False, default=Decimal("1"))
    maximum_risk_percent: Mapped[Decimal] = mapped_column(Percent, nullable=False, default=Decimal("2"))
    daily_loss_limit_percent: Mapped[Decimal] = mapped_column(
        Percent, nullable=False, default=Decimal("3")
    )
    weekly_loss_limit_percent: Mapped[Decimal] = mapped_column(
        Percent, nullable=False, default=Decimal("6")
    )
    maximum_trades_per_day: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    maximum_consecutive_losses: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    maximum_total_open_risk_percent: Mapped[Decimal] = mapped_column(
        Percent, nullable=False, default=Decimal("3")
    )
    # Trading goals (USD / percent)
    weekly_pnl_goal: Mapped[Decimal] = mapped_column(Money, nullable=False, default=Decimal("50"))
    monthly_pnl_goal: Mapped[Decimal] = mapped_column(Money, nullable=False, default=Decimal("200"))
    win_rate_goal: Mapped[Decimal] = mapped_column(Percent, nullable=False, default=Decimal("50"))
    followed_plan_goal: Mapped[Decimal] = mapped_column(Percent, nullable=False, default=Decimal("80"))

    base_currency: Mapped[str] = mapped_column(String(8), nullable=False, default="USD")
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Asia/Karachi")

    # Display preferences stored alongside risk settings for simplicity
    default_dashboard_period: Mapped[str] = mapped_column(String(32), nullable=False, default="30d")
    default_market_filter: Mapped[str] = mapped_column(String(16), nullable=False, default="ALL")
    number_format: Mapped[str] = mapped_column(String(32), nullable=False, default="en_US")
    date_format: Mapped[str] = mapped_column(String(32), nullable=False, default="%Y-%m-%d %H:%M")
    table_density: Mapped[str] = mapped_column(String(16), nullable=False, default="comfortable")

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
