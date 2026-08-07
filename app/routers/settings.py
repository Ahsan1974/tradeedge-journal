"""Settings routes."""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.csrf import validate_csrf_token
from app.dependencies import DbSession, template_context
from app.repositories.settings_repository import SettingsRepository
from app.repositories.trade_repository import TradeRepository
from app.security import session_flash
from app.services.analytics_service import analyze_performance
from app.templating import templates
from app.utils.dates import now_tz, period_range
from app.utils.decimals import to_decimal

router = APIRouter(tags=["settings"])


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, db: DbSession):
    repo = SettingsRepository(db)
    settings = repo.get_risk_settings()
    symbols = {s.market: s for s in repo.ensure_symbols()}
    month_from, month_to = period_range("month", tz_name=settings.timezone)
    month_stats = analyze_performance(
        TradeRepository(db).all_filtered(date_from=month_from, date_to=month_to),
        settings.starting_balance,
    )
    ctx = template_context(
        request,
        active_page="settings",
        settings=settings,
        symbols=symbols,
        sidebar_balance=settings.current_balance,
        sidebar_month_pnl=month_stats.net_pnl,
        pakistan_time=now_tz(settings.timezone),
        errors=[],
    )
    return templates.TemplateResponse("settings/index.html", ctx)


@router.post("/settings")
async def settings_save(request: Request, db: DbSession):
    form = dict(await request.form())
    validate_csrf_token(request, form.get("csrf_token"))
    repo = SettingsRepository(db)
    settings = repo.get_risk_settings()

    def d(key, default=None):
        return to_decimal(form.get(key), default)

    settings.starting_balance = d("starting_balance", settings.starting_balance) or settings.starting_balance
    settings.current_balance = d("current_balance", settings.current_balance) or settings.current_balance
    settings.default_risk_percent = d("default_risk_percent", settings.default_risk_percent) or Decimal("1")
    settings.maximum_risk_percent = d("maximum_risk_percent", settings.maximum_risk_percent) or Decimal("2")
    settings.daily_loss_limit_percent = d("daily_loss_limit_percent", settings.daily_loss_limit_percent) or Decimal("3")
    settings.weekly_loss_limit_percent = d("weekly_loss_limit_percent", settings.weekly_loss_limit_percent) or Decimal("6")
    settings.maximum_trades_per_day = int(form.get("maximum_trades_per_day") or settings.maximum_trades_per_day)
    settings.maximum_consecutive_losses = int(
        form.get("maximum_consecutive_losses") or settings.maximum_consecutive_losses
    )
    settings.maximum_total_open_risk_percent = (
        d("maximum_total_open_risk_percent", settings.maximum_total_open_risk_percent) or Decimal("3")
    )
    settings.weekly_pnl_goal = d("weekly_pnl_goal", settings.weekly_pnl_goal) or Decimal("50")
    settings.monthly_pnl_goal = d("monthly_pnl_goal", settings.monthly_pnl_goal) or Decimal("200")
    settings.win_rate_goal = d("win_rate_goal", settings.win_rate_goal) or Decimal("50")
    settings.followed_plan_goal = d("followed_plan_goal", settings.followed_plan_goal) or Decimal("80")
    settings.base_currency = form.get("base_currency") or "USD"
    settings.timezone = form.get("timezone") or "Asia/Karachi"
    settings.default_dashboard_period = form.get("default_dashboard_period") or "30d"
    settings.default_market_filter = form.get("default_market_filter") or "ALL"
    settings.number_format = form.get("number_format") or "en_US"
    settings.date_format = form.get("date_format") or "%Y-%m-%d %H:%M"
    settings.table_density = form.get("table_density") or "comfortable"
    repo.save_risk_settings(settings)

    for market in ("XAU/USD", "BTC/USD"):
        prefix = "xau_" if market == "XAU/USD" else "btc_"
        sym = repo.get_symbol(market)
        if not sym:
            continue
        sym.contract_size = d(f"{prefix}contract_size", sym.contract_size) or sym.contract_size
        sym.tick_size = d(f"{prefix}tick_size", sym.tick_size) or sym.tick_size
        sym.tick_value_per_lot = d(f"{prefix}tick_value_per_lot", sym.tick_value_per_lot) or sym.tick_value_per_lot
        sym.pip_size = d(f"{prefix}pip_size", sym.pip_size) or sym.pip_size
        sym.decimal_places = int(form.get(f"{prefix}decimal_places") or sym.decimal_places)
        sym.enabled = form.get(f"{prefix}enabled") == "1"
        repo.save_symbol(sym)

    session_flash(request, "Settings saved.", "success")
    return RedirectResponse("/settings", status_code=303)
