"""Journal entry model."""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class JournalEntry(Base):
    """Daily or trade-linked journal notes."""

    __tablename__ = "journal_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trade_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("trades.id", ondelete="SET NULL"), nullable=True, index=True
    )
    entry_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    market: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    setup: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    lesson: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    mistakes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    emotional_state: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    followed_plan: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    tags: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    trade = relationship("Trade", back_populates="journal_entries")
