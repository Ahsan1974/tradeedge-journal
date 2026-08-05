"""Analytics page routes."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.dependencies import DbSession, template_context
from app.models.trade import Setup, TradingSession
from app.repositories.settings_repository import SettingsRepository
from app.repositories.trade_repository import TradeRepository
from app.services import analytics_service as analytics
from app.templating import templates
from app.utils.dates import now_tz, period_range

router = APIRouter(tags=["analytics"])


@router.get("/analytics", response_class=HTMLResponse)
async def analytics_page(request: Request, db: DbSession):

    settings = SettingsRepository(db).get_risk_settings()
    period = request.query_params.get("period", "30d")
    market = request.query_params.get("market", "ALL")
    start_s = request.query_params.get("start")
    end_s = request.query_params.get("end")
    start = end = None
    if period == "custom" and start_s and end_s:
        try:
            start = datetime.fromisoformat(start_s).date()
            end = datetime.fromisoformat(end_s).date()
        except ValueError:
            period = "30d"
    date_from, date_to = period_range(period, start, end, settings.timezone)

    trades = TradeRepository(db).all_filtered(
        market=market if market != "ALL" else None,
        date_from=date_from,
        date_to=date_to,
    )
    stats = analytics.analyze_performance(trades, settings.starting_balance)
    market_stats = analytics.group_by_market(trades)
    setup_rows = analytics.group_by_setup(trades)
    session_rows = analytics.group_by_session(trades)
    timeframe_rows = analytics.group_by_timeframe(trades)
    direction_rows = analytics.group_by_direction(trades)
    weekday = analytics.weekday_frequency(trades)
    by_hour = analytics.hour_pnl(trades)
    monthly = analytics.monthly_pnl(trades)

    month_from, month_to = period_range("month", tz_name=settings.timezone)
    month_stats = analytics.analyze_performance(
        TradeRepository(db).all_filtered(date_from=month_from, date_to=month_to),
        settings.starting_balance,
    )

    ctx = template_context(
        request,
        active_page="analytics",
        stats=stats,
        market_stats=market_stats,
        setup_rows=setup_rows,
        session_rows=session_rows,
        timeframe_rows=timeframe_rows,
        direction_rows=direction_rows,
        weekday=weekday,
        by_hour=by_hour,
        monthly=monthly,
        filters={"period": period, "market": market, "start": start_s, "end": end_s},
        settings=settings,
        sidebar_balance=settings.current_balance,
        sidebar_month_pnl=month_stats.net_pnl,
        pakistan_time=now_tz(settings.timezone),
        setups=[s.value for s in Setup],
        sessions=[s.value for s in TradingSession],
    )
    return templates.TemplateResponse("analytics/index.html", ctx)
