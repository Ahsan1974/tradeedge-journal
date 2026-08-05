"""Risk management page routes."""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.dependencies import DbSession, template_context
from app.repositories.settings_repository import SettingsRepository
from app.repositories.trade_repository import TradeRepository
from app.services.analytics_service import analyze_performance
from app.services.risk_service import daily_risk_monitor, risk_discipline_score
from app.utils.dates import now_tz, period_range

router = APIRouter(tags=["risk"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/risk-management", response_class=HTMLResponse)
async def risk_page(request: Request, db: DbSession):

    settings_repo = SettingsRepository(db)
    settings = settings_repo.get_risk_settings()
    symbols = {s.market: s for s in settings_repo.ensure_symbols()}
    monitor = daily_risk_monitor(db, settings)
    score = risk_discipline_score(db, settings)

    month_from, month_to = period_range("month", tz_name=settings.timezone)
    month_stats = analyze_performance(
        TradeRepository(db).all_filtered(date_from=month_from, date_to=month_to),
        settings.starting_balance,
    )

    # Prefill calculator from settings / symbol
    xau = symbols.get("XAU/USD")
    ctx = template_context(
        request,
        active_page="risk",
        settings=settings,
        symbols=symbols,
        monitor=monitor,
        risk_score=score,
        sidebar_balance=settings.current_balance,
        sidebar_month_pnl=month_stats.net_pnl,
        pakistan_time=now_tz(settings.timezone),
        calc_defaults={
            "account_balance": settings.current_balance,
            "risk_percent": settings.default_risk_percent,
            "tick_size": xau.tick_size if xau else Decimal("0.01"),
            "tick_value_per_lot": xau.tick_value_per_lot if xau else Decimal("1"),
            "contract_size": xau.contract_size if xau else Decimal("100"),
        },
    )
    return templates.TemplateResponse("risk/index.html", ctx)
