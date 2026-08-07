"""Daily / weekly review routes."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.dependencies import DbSession, template_context
from app.repositories.journal_repository import JournalRepository
from app.repositories.settings_repository import SettingsRepository
from app.repositories.trade_repository import TradeRepository
from app.services.analytics_service import analyze_performance
from app.services.review_service import build_review
from app.templating import templates
from app.utils.dates import now_tz, period_range

router = APIRouter(tags=["review"])


@router.get("/review", response_class=HTMLResponse)
async def review_page(request: Request, db: DbSession):
    settings = SettingsRepository(db).get_risk_settings()
    scope = (request.query_params.get("scope") or "weekly").lower()
    if scope not in ("daily", "weekly"):
        scope = "weekly"

    period = "today" if scope == "daily" else "week"
    date_from, date_to = period_range(period, tz_name=settings.timezone)
    week_from, week_to = period_range("week", tz_name=settings.timezone)
    month_from, month_to = period_range("month", tz_name=settings.timezone)

    trade_repo = TradeRepository(db)
    journal_repo = JournalRepository(db)

    trades = trade_repo.all_filtered(date_from=date_from, date_to=date_to)
    week_trades = trade_repo.all_filtered(date_from=week_from, date_to=week_to)
    month_trades = trade_repo.all_filtered(date_from=month_from, date_to=month_to)

    d0 = date_from.date() if date_from else None
    d1 = date_to.date() if date_to else None
    w0 = week_from.date() if week_from else None
    w1 = week_to.date() if week_to else None

    entries = []
    week_entries = []
    if d0 and d1:
        page = journal_repo.list_filtered(page=1, per_page=100, date_from=d0, date_to=d1)
        entries = page.items
    if w0 and w1:
        page_w = journal_repo.list_filtered(page=1, per_page=100, date_from=w0, date_to=w1)
        week_entries = page_w.items

    now = now_tz(settings.timezone)
    if scope == "daily":
        period_label = now.strftime("%A, %d %b %Y")
    else:
        period_label = f"Week of {week_from.strftime('%d %b') if week_from else '—'} → {now.strftime('%d %b %Y')}"

    review = build_review(
        scope=scope,
        settings=settings,
        trades=trades,
        entries=entries,
        week_trades=week_trades,
        month_trades=month_trades,
        period_label=period_label,
        all_goals_week_entries=week_entries,
    )

    month_stats_net = analyze_performance(month_trades, settings.starting_balance).net_pnl

    ctx = template_context(
        request,
        active_page="review",
        review=review,
        scope=scope,
        settings=settings,
        sidebar_balance=settings.current_balance,
        sidebar_month_pnl=month_stats_net,
        pakistan_time=now,
        market_status="Open",
    )
    return templates.TemplateResponse("review/index.html", ctx)
