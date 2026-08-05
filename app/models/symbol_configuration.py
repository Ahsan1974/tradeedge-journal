"""Broker-dependent symbol configuration."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

Money = Numeric(18, 8)


class SymbolConfiguration(Base):
    """
    Broker-specific contract specifications.

    Values differ between brokers — treat defaults as examples only.
    """

    __tablename__ = "symbol_configurations"
    __table_args__ = (UniqueConstraint("market", name="uq_symbol_market"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    market: Mapped[str] = mapped_column(String(16), nullable=False)
    contract_size: Mapped[Decimal] = mapped_column(Money, nullable=False)
    tick_size: Mapped[Decimal] = mapped_column(Money, nullable=False)
    tick_value_per_lot: Mapped[Decimal] = mapped_column(Money, nullable=False)
    pip_size: Mapped[Decimal] = mapped_column(Money, nullable=False)
    decimal_places: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
