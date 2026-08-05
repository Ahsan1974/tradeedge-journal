"""Dashboard routes."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.dependencies import DbSession, template_context
from app.repositories.journal_repository import JournalRepository
from app.repositories.settings_repository import SettingsRepository
from app.repositories.trade_repository import TradeRepository
from app.services import analytics_service as analytics
from app.services.risk_service import daily_risk_monitor
from app.utils.dates import (
    format_duration,
    now_tz,
    period_range,
    previous_equivalent_period,
)
from app.utils.formatting import format_duration as _fd  # noqa: F401

router = APIRouter(tags=["dashboard"])
templates = Jinja2Templates(directory="app/templates")


def _filter_kwargs(request: Request, settings_tz: str):
    period = request.query_params.get("period", "30d")
    market = request.query_params.get("market", "ALL")
    setup = request.query_params.get("setup", "ALL")
    session = request.query_params.get("session", "ALL")
    start_s = request.query_params.get("start")
    end_s = request.query_params.get("end")
    start = end = None
    if period == "custom" and start_s and end_s:
        try:
            start = datetime.fromisoformat(start_s).date()
            end = datetime.fromisoformat(end_s).date()
        except ValueError:
            period = "30d"
    date_from, date_to = period_range(period, start, end, settings_tz)
    return {
        "period": period,
        "market": market,
        "setup": setup if setup != "ALL" else None,
        "session": session if session != "ALL" else None,
        "date_from": date_from,
        "date_to": date_to,
        "start": start_s,
        "end": end_s,
        "market_filter": market,
        "setup_filter": setup,
        "session_filter": session,
    }


@router.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return RedirectResponse("/dashboard", status_code=303)


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: DbSession):

    settings = SettingsRepository(db).get_risk_settings()
    SettingsRepository(db).ensure_symbols()
    filters = _filter_kwargs(request, settings.timezone)
    trade_repo = TradeRepository(db)

    trades = trade_repo.all_filtered(
        market=filters["market"] if filters["market"] != "ALL" else None,
        setup=filters["setup"],
        session=filters["session"],
        date_from=filters["date_from"],
        date_to=filters["date_to"],
    )
    stats = analytics.analyze_performance(trades, settings.starting_balance)

    # Previous period comparison
    prev_from, prev_to = previous_equivalent_period(filters["date_from"], filters["date_to"])
    prev_trades = []
    if prev_from and prev_to:
        prev_trades = trade_repo.all_filtered(
            market=filters["market"] if filters["market"] != "ALL" else None,
            setup=filters["setup"],
            session=filters["session"],
            date_from=prev_from,
            date_to=prev_to,
        )
    prev_stats = analytics.analyze_performance(prev_trades, settings.starting_balance)

    # Current month P/L
    month_from, month_to = period_range("month", tz_name=settings.timezone)
    month_trades = trade_repo.all_filtered(date_from=month_from, date_to=month_to)
    month_stats = analytics.analyze_performance(month_trades, settings.starting_balance)

    market_stats = analytics.group_by_market(trades)
    xau_net = Decimal(str(market_stats["XAU/USD"]["net_pnl"]))
    btc_net = Decimal(str(market_stats["BTC/USD"]["net_pnl"]))
    better = None
    if xau_net != btc_net:
        better = "XAU/USD" if xau_net > btc_net else "BTC/USD"

    kpis = {
        "gross_profit": analytics.metric(stats.gross_profit, kind="money", prev=prev_stats.gross_profit),
        # Gross loss is stored as absolute; display as negative for clarity
        "gross_loss": analytics.metric(
            -stats.gross_loss if stats.gross_loss else None,
            kind="money",
            prev=(-prev_stats.gross_loss if prev_stats.gross_loss else None),
        ),
        "net_pnl": analytics.metric(stats.net_pnl, kind="money", prev=prev_stats.net_pnl),
        "win_rate": analytics.metric(stats.win_rate, kind="pct", prev=prev_stats.win_rate),
        "total_trades": analytics.metric(stats.total_trades, kind="count", prev=prev_stats.total_trades),
        "avg_rr": analytics.metric(stats.avg_rr, kind="ratio", prev=prev_stats.avg_rr),
        "best_trade": analytics.metric(stats.best_trade, kind="money"),
        "worst_trade": analytics.metric(stats.worst_trade, kind="money"),
        "month_pnl": analytics.metric(month_stats.net_pnl, kind="money"),
    }

    secondary = {
        "avg_holding": format_duration(int(stats.avg_holding_seconds) if stats.avg_holding_seconds else None),
        "max_drawdown": analytics.metric(stats.max_drawdown, kind="money", invert_tone=True),
        "max_drawdown_pct": analytics.metric(stats.max_drawdown_pct, kind="pct", invert_tone=True),
        "expectancy": analytics.metric(stats.expectancy, kind="money"),
        "avg_risk": analytics.metric(stats.avg_risk, kind="money"),
        "profit_factor": analytics.metric(stats.profit_factor, kind="ratio"),
        "max_win_streak": stats.max_win_streak,
        "max_loss_streak": stats.max_loss_streak,
        "avg_win": analytics.metric(stats.avg_win, kind="money"),
        "avg_loss": analytics.metric(stats.avg_loss, kind="money"),
        "payoff_ratio": analytics.metric(stats.payoff_ratio, kind="ratio"),
        "breakeven_rate": analytics.metric(stats.breakeven_rate, kind="pct"),
        "longest_holding": format_duration(stats.longest_holding_seconds),
        "shortest_holding": format_duration(stats.shortest_holding_seconds),
        "total_costs": analytics.metric(
            stats.total_commission + stats.total_swap + stats.total_fees, kind="money", invert_tone=True
        ),
        "avg_r_multiple": analytics.metric(stats.avg_r_multiple, kind="ratio"),
    }

    recent = trade_repo.recent(
        10,
        market=filters["market"] if filters["market"] != "ALL" else None,
        setup=filters["setup"],
        session=filters["session"],
        date_from=filters["date_from"],
        date_to=filters["date_to"],
    )
    journal = JournalRepository(db).recent(5)
    monitor = daily_risk_monitor(db, settings)

    ctx = template_context(
        request,
        active_page="dashboard",
        kpis=kpis,
        secondary=secondary,
        market_stats=market_stats,
        better_market=better,
        recent_trades=recent,
        journal_entries=journal,
        filters=filters,
        settings=settings,
        sidebar_balance=settings.current_balance,
        sidebar_month_pnl=month_stats.net_pnl,
        market_status="Open",
        pakistan_time=now_tz(settings.timezone),
        setups=[s.value for s in __import__("app.models.trade", fromlist=["Setup"]).Setup],
        sessions=[s.value for s in __import__("app.models.trade", fromlist=["TradingSession"]).TradingSession],
        monitor=monitor,
        stats=stats,
    )
    return templates.TemplateResponse("dashboard.html", ctx)
