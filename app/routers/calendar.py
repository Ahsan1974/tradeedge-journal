"""Calendar routes."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.dependencies import DbSession, template_context
from app.repositories.journal_repository import JournalRepository
from app.repositories.settings_repository import SettingsRepository
from app.repositories.trade_repository import TradeRepository
from app.services.analytics_service import analyze_performance
from app.services.calendar_service import build_month_calendar
from app.templating import templates
from app.utils.dates import get_tz, month_bounds, now_tz, period_range

router = APIRouter(tags=["calendar"])


@router.get("/calendar", response_class=HTMLResponse)
async def calendar_page(request: Request, db: DbSession):

    settings = SettingsRepository(db).get_risk_settings()
    now = now_tz(settings.timezone)
    year = int(request.query_params.get("year", now.year))
    month = int(request.query_params.get("month", now.month))
    if month < 1:
        month = 12
        year -= 1
    if month > 12:
        month = 1
        year += 1

    start, end = month_bounds(year, month, settings.timezone)
    # Load a wider window for open-date edge cases
    trades = TradeRepository(db).all_filtered()
    cal = build_month_calendar(trades, year, month, settings.timezone)

    prev_month = month - 1 or 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1

    month_from, month_to = period_range("month", tz_name=settings.timezone)
    month_stats = analyze_performance(
        TradeRepository(db).all_filtered(date_from=month_from, date_to=month_to),
        settings.starting_balance,
    )

    ctx = template_context(
        request,
        active_page="calendar",
        cal=cal,
        prev={"year": prev_year, "month": prev_month},
        next={"year": next_year, "month": next_month},
        settings=settings,
        sidebar_balance=settings.current_balance,
        sidebar_month_pnl=month_stats.net_pnl,
        pakistan_time=now,
    )
    return templates.TemplateResponse("calendar/index.html", ctx)


@router.get("/calendar/{day}", response_class=HTMLResponse)
async def calendar_day(request: Request, day: str, db: DbSession):
    settings = SettingsRepository(db).get_risk_settings()
    try:
        day_date = date.fromisoformat(day)
    except ValueError:
        return templates.TemplateResponse(
            "errors/404.html", template_context(request, active_page="calendar"), status_code=404
        )

    start, end = month_bounds(day_date.year, day_date.month, settings.timezone)
    # Filter trades closed/opened on this day
    all_trades = TradeRepository(db).all_filtered()
    tz = get_tz(settings.timezone)
    from app.utils.dates import ensure_aware

    day_trades = [
        t
        for t in all_trades
        if ensure_aware(t.close_date or t.trade_date, settings.timezone).astimezone(tz).date()
        == day_date
    ]
    entries = JournalRepository(db).for_date(day_date)
    stats = analyze_performance(day_trades, settings.starting_balance)

    month_from, month_to = period_range("month", tz_name=settings.timezone)
    month_stats = analyze_performance(
        TradeRepository(db).all_filtered(date_from=month_from, date_to=month_to),
        settings.starting_balance,
    )

    ctx = template_context(
        request,
        active_page="calendar",
        day=day_date,
        trades=day_trades,
        journal_entries=entries,
        stats=stats,
        settings=settings,
        sidebar_balance=settings.current_balance,
        sidebar_month_pnl=month_stats.net_pnl,
        pakistan_time=now_tz(settings.timezone),
    )
    return templates.TemplateResponse("calendar/day_detail.html", ctx)
