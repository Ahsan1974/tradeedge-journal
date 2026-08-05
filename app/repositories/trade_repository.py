"""Trade repository — query helpers."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Select, and_, asc, desc, func, or_, select
from sqlalchemy.orm import Session

from app.models.trade import Trade
from app.utils.pagination import Page, clamp_page

SORTABLE = {
    "trade_date": Trade.trade_date,
    "market": Trade.market,
    "profit_loss": Trade.net_profit_loss,
    "lot_size": Trade.lot_size,
    "risk_reward": Trade.risk_reward_ratio,
    "status": Trade.status,
    "created_at": Trade.created_at,
}


def _holding_order(order: str):
    # Approximate holding time as close - open; nulls last-ish
    expr = func.julianday(Trade.close_date) - func.julianday(Trade.trade_date)
    return desc(expr) if order == "desc" else asc(expr)


class TradeRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, trade_id: int) -> Trade | None:
        return self.db.get(Trade, trade_id)

    def add(self, trade: Trade) -> Trade:
        self.db.add(trade)
        self.db.commit()
        self.db.refresh(trade)
        return trade

    def update(self, trade: Trade) -> Trade:
        self.db.add(trade)
        self.db.commit()
        self.db.refresh(trade)
        return trade

    def delete(self, trade: Trade) -> None:
        self.db.delete(trade)
        self.db.commit()

    def neighbors(self, trade_id: int) -> tuple[Trade | None, Trade | None]:
        current = self.get(trade_id)
        if not current:
            return None, None
        prev_q = (
            select(Trade)
            .where(
                or_(
                    Trade.trade_date < current.trade_date,
                    and_(Trade.trade_date == current.trade_date, Trade.id < current.id),
                )
            )
            .order_by(Trade.trade_date.desc(), Trade.id.desc())
            .limit(1)
        )
        next_q = (
            select(Trade)
            .where(
                or_(
                    Trade.trade_date > current.trade_date,
                    and_(Trade.trade_date == current.trade_date, Trade.id > current.id),
                )
            )
            .order_by(Trade.trade_date.asc(), Trade.id.asc())
            .limit(1)
        )
        prev_t = self.db.scalar(prev_q)
        next_t = self.db.scalar(next_q)
        return prev_t, next_t

    def build_query(
        self,
        *,
        q: str | None = None,
        market: str | None = None,
        status: str | None = None,
        direction: str | None = None,
        setup: str | None = None,
        timeframe: str | None = None,
        session: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        min_pnl: Decimal | None = None,
        max_pnl: Decimal | None = None,
        source: str | None = None,
        exclude_open: bool = False,
    ) -> Select:
        stmt = select(Trade)
        filters = []
        if q:
            like = f"%{q.strip()}%"
            filters.append(
                or_(
                    Trade.external_ticket.ilike(like),
                    Trade.setup.ilike(like),
                    Trade.entry_reason.ilike(like),
                    Trade.lesson.ilike(like),
                    Trade.mistake.ilike(like),
                    Trade.market.ilike(like),
                )
            )
        if market and market.upper() != "ALL":
            filters.append(Trade.market == market)
        if status and status.upper() != "ALL":
            filters.append(Trade.status == status.upper())
        if direction and direction.upper() != "ALL":
            filters.append(Trade.direction == direction.upper())
        if setup and setup != "ALL":
            filters.append(Trade.setup == setup)
        if timeframe and timeframe != "ALL":
            filters.append(Trade.timeframe == timeframe)
        if session and session != "ALL":
            filters.append(Trade.trading_session == session)
        if date_from:
            filters.append(Trade.trade_date >= date_from)
        if date_to:
            filters.append(Trade.trade_date <= date_to)
        if min_pnl is not None:
            filters.append(Trade.net_profit_loss >= min_pnl)
        if max_pnl is not None:
            filters.append(Trade.net_profit_loss <= max_pnl)
        if source:
            filters.append(Trade.source == source)
        if exclude_open:
            filters.append(Trade.status != "OPEN")
        if filters:
            stmt = stmt.where(and_(*filters))
        return stmt

    def list_filtered(
        self,
        *,
        page: int = 1,
        per_page: int = 25,
        sort: str = "trade_date",
        order: str = "desc",
        **filters,
    ) -> Page:
        page = clamp_page(page)
        per_page = max(1, min(per_page, 200))
        stmt = self.build_query(**filters)
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = int(self.db.scalar(count_stmt) or 0)

        if sort == "holding_time":
            stmt = stmt.order_by(_holding_order(order))
        else:
            col = SORTABLE.get(sort, Trade.trade_date)
            stmt = stmt.order_by(desc(col) if order == "desc" else asc(col), desc(Trade.id))

        offset = (page - 1) * per_page
        items = list(self.db.scalars(stmt.offset(offset).limit(per_page)).all())
        return Page(items=items, page=page, per_page=per_page, total=total)

    def all_filtered(self, **filters) -> list[Trade]:
        stmt = self.build_query(**filters).order_by(Trade.trade_date.asc(), Trade.id.asc())
        return list(self.db.scalars(stmt).all())

    def recent(self, limit: int = 10, **filters) -> list[Trade]:
        stmt = (
            self.build_query(**filters)
            .order_by(Trade.trade_date.desc(), Trade.id.desc())
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def find_duplicate(self, external_ticket: str, trade_date: datetime, market: str) -> Trade | None:
        if not external_ticket:
            return None
        stmt = (
            select(Trade)
            .where(
                Trade.external_ticket == external_ticket,
                Trade.market == market,
                func.date(Trade.trade_date) == trade_date.date(),
            )
            .limit(1)
        )
        return self.db.scalar(stmt)

    def delete_by_source(self, source: str) -> int:
        trades = list(self.db.scalars(select(Trade).where(Trade.source == source)).all())
        count = len(trades)
        for t in trades:
            self.db.delete(t)
        self.db.commit()
        return count
