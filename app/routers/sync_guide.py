"""MT5 sync guide page (cloud + local instructions)."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.config import get_settings
from app.dependencies import DbSession, template_context
from app.repositories.settings_repository import SettingsRepository
from app.repositories.trade_repository import TradeRepository
from app.services.analytics_service import analyze_performance
from app.templating import templates
from app.utils.dates import now_tz, period_range

router = APIRouter(tags=["sync"])


@router.get("/sync", response_class=HTMLResponse)
async def sync_guide(request: Request, db: DbSession):
    settings = SettingsRepository(db).get_risk_settings()
    app_settings = get_settings()
    month_from, month_to = period_range("month", tz_name=settings.timezone)
    month_stats = analyze_performance(
        TradeRepository(db).all_filtered(date_from=month_from, date_to=month_to),
        settings.starting_balance,
    )
    ctx = template_context(
        request,
        active_page="sync",
        settings=settings,
        mt5_local=app_settings.mt5_sync_available,
        sidebar_balance=settings.current_balance,
        sidebar_month_pnl=month_stats.net_pnl,
        pakistan_time=now_tz(settings.timezone),
        market_status="Open",
    )
    return templates.TemplateResponse("sync/index.html", ctx)
