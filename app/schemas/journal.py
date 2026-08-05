"""Journal schemas."""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class JournalBase(BaseModel):
    entry_date: date
    title: str = Field(min_length=1, max_length=200)
    market: Optional[str] = None
    setup: Optional[str] = None
    notes: Optional[str] = None
    lesson: Optional[str] = None
    mistakes: Optional[str] = None
    emotional_state: Optional[str] = None
    followed_plan: Optional[bool] = None
    tags: Optional[str] = None
    trade_id: Optional[int] = None


class JournalCreate(JournalBase):
    pass


class JournalUpdate(JournalBase):
    pass


class JournalRead(JournalBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
