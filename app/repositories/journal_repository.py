"""Journal repository."""

from __future__ import annotations

from datetime import date

from sqlalchemy import Select, and_, desc, func, or_, select
from sqlalchemy.orm import Session

from app.models.journal import JournalEntry
from app.utils.pagination import Page, clamp_page


class JournalRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, entry_id: int) -> JournalEntry | None:
        return self.db.get(JournalEntry, entry_id)

    def add(self, entry: JournalEntry) -> JournalEntry:
        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)
        return entry

    def update(self, entry: JournalEntry) -> JournalEntry:
        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)
        return entry

    def delete(self, entry: JournalEntry) -> None:
        self.db.delete(entry)
        self.db.commit()

    def build_query(
        self,
        *,
        q: str | None = None,
        market: str | None = None,
        setup: str | None = None,
        tags: str | None = None,
        followed_plan: bool | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        trade_id: int | None = None,
    ) -> Select:
        stmt = select(JournalEntry)
        filters = []
        if q:
            like = f"%{q.strip()}%"
            filters.append(
                or_(
                    JournalEntry.title.ilike(like),
                    JournalEntry.notes.ilike(like),
                    JournalEntry.lesson.ilike(like),
                    JournalEntry.mistakes.ilike(like),
                    JournalEntry.tags.ilike(like),
                )
            )
        if market and market != "ALL":
            filters.append(JournalEntry.market == market)
        if setup and setup != "ALL":
            filters.append(JournalEntry.setup == setup)
        if tags:
            filters.append(JournalEntry.tags.ilike(f"%{tags.strip()}%"))
        if followed_plan is not None:
            filters.append(JournalEntry.followed_plan.is_(followed_plan))
        if date_from:
            filters.append(JournalEntry.entry_date >= date_from)
        if date_to:
            filters.append(JournalEntry.entry_date <= date_to)
        if trade_id is not None:
            filters.append(JournalEntry.trade_id == trade_id)
        if filters:
            stmt = stmt.where(and_(*filters))
        return stmt

    def list_filtered(self, *, page: int = 1, per_page: int = 20, **filters) -> Page:
        page = clamp_page(page)
        stmt = self.build_query(**filters)
        total = int(self.db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
        items = list(
            self.db.scalars(
                stmt.order_by(desc(JournalEntry.entry_date), desc(JournalEntry.id))
                .offset((page - 1) * per_page)
                .limit(per_page)
            ).all()
        )
        return Page(items=items, page=page, per_page=per_page, total=total)

    def recent(self, limit: int = 5) -> list[JournalEntry]:
        stmt = select(JournalEntry).order_by(desc(JournalEntry.entry_date)).limit(limit)
        return list(self.db.scalars(stmt).all())

    def for_date(self, day: date) -> list[JournalEntry]:
        stmt = (
            select(JournalEntry)
            .where(JournalEntry.entry_date == day)
            .order_by(desc(JournalEntry.id))
        )
        return list(self.db.scalars(stmt).all())

    def all(self) -> list[JournalEntry]:
        return list(
            self.db.scalars(select(JournalEntry).order_by(desc(JournalEntry.entry_date))).all()
        )

    def delete_demo_linked(self) -> int:
        # Demo journal entries tagged in title or via linked demo trades handled separately
        return 0
