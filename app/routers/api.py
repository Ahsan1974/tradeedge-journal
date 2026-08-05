"""JSON analytics and risk API endpoints."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.dependencies import DbSession
from app.repositories.settings_repository import SettingsRepository
from app.repositories.trade_repository import TradeRepository
from app.services import analytics_service as analytics
from app.services.risk_service import calculate_position_size, calculate_risk_reward
from app.utils.dates import period_range
from app.utils.decimals import to_decimal

router = APIRouter(prefix="/api", tags=["api"])


def _filtered_trades(request: Request, db: DbSession):
    settings = SettingsRepository(db).get_risk_settings()
    period = request.query_params.get("period", "30d")
    market = request.query_params.get("market", "ALL")
    setup = request.query_params.get("setup")
    session = request.query_params.get("session")
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
        market=market if market and market != "ALL" else None,
        setup=setup if setup and setup != "ALL" else None,
        session=session if session and session != "ALL" else None,
        date_from=date_from,
        date_to=date_to,
    )
    return trades, settings


@router.get("/dashboard/summary")
async def api_dashboard_summary(request: Request, db: DbSession):
    trades, settings = _filtered_trades(request, db)
    stats = analytics.analyze_performance(trades, settings.starting_balance)
    return {
        "stats": stats.to_dict(),
        "distribution": analytics.distribution_counts(trades),
        "market_stats": analytics.group_by_market(trades),
    }


@router.get("/analytics/cumulative-pnl")
async def api_cumulative_pnl(request: Request, db: DbSession):
    trades, settings = _filtered_trades(request, db)
    _, _, _, equity = analytics.compute_drawdown(trades, settings.starting_balance)
    return {"labels": [p["label"] for p in equity], "values": [p["value"] for p in equity]}


@router.get("/analytics/distribution")
async def api_distribution(request: Request, db: DbSession):
    trades, _ = _filtered_trades(request, db)
    dist = analytics.distribution_counts(trades)
    return {
        "labels": list(dist.keys()),
        "values": list(dist.values()),
        "colors": ["#22c55e", "#ef4444", "#94a3b8"],
    }


@router.get("/analytics/frequency")
async def api_frequency(request: Request, db: DbSession):
    trades, _ = _filtered_trades(request, db)
    freq = analytics.weekday_frequency(trades)
    return {"labels": list(freq.keys()), "values": list(freq.values())}


@router.get("/analytics/daily-pnl")
async def api_daily_pnl(request: Request, db: DbSession):
    trades, _ = _filtered_trades(request, db)
    data = analytics.daily_pnl(trades)
    return {
        "labels": [d["label"] for d in data],
        "values": [d["value"] for d in data],
    }


@router.get("/analytics/monthly-pnl")
async def api_monthly_pnl(request: Request, db: DbSession):
    trades, _ = _filtered_trades(request, db)
    data = analytics.monthly_pnl(trades)
    return {
        "labels": [d["label"] for d in data],
        "values": [d["value"] for d in data],
    }


@router.get("/analytics/drawdown")
async def api_drawdown(request: Request, db: DbSession):
    trades, settings = _filtered_trades(request, db)
    max_dd, max_dd_pct, dd_series, _ = analytics.compute_drawdown(trades, settings.starting_balance)
    return {
        "max_drawdown": float(max_dd) if max_dd is not None else None,
        "max_drawdown_pct": float(max_dd_pct) if max_dd_pct is not None else None,
        "labels": [p["label"] for p in dd_series],
        "values": [p["value"] for p in dd_series],
    }


@router.get("/analytics/market-comparison")
async def api_market_comparison(request: Request, db: DbSession):
    trades, _ = _filtered_trades(request, db)
    stats = analytics.group_by_market(trades)
    return {
        "labels": ["XAU/USD", "BTC/USD"],
        "net_pnl": [stats["XAU/USD"]["net_pnl"], stats["BTC/USD"]["net_pnl"]],
        "win_rate": [stats["XAU/USD"]["win_rate"], stats["BTC/USD"]["win_rate"]],
        "trades": [stats["XAU/USD"]["total_trades"], stats["BTC/USD"]["total_trades"]],
        "colors": ["#d4a017", "#f7931a"],
    }


@router.get("/analytics/profit-by-setup")
async def api_profit_by_setup(request: Request, db: DbSession):
    trades, _ = _filtered_trades(request, db)
    rows = analytics.group_by_setup(trades)
    return {
        "labels": [r["setup"] for r in rows],
        "values": [r["net_pnl"] for r in rows],
    }


@router.get("/analytics/profit-by-session")
async def api_profit_by_session(request: Request, db: DbSession):
    trades, _ = _filtered_trades(request, db)
    rows = analytics.group_by_session(trades)
    return {
        "labels": [r["session"] for r in rows],
        "values": [r["net_pnl"] for r in rows],
    }


@router.get("/analytics/winrate-by-timeframe")
async def api_winrate_by_timeframe(request: Request, db: DbSession):
    trades, _ = _filtered_trades(request, db)
    rows = analytics.group_by_timeframe(trades)
    return {
        "labels": [r["timeframe"] for r in rows],
        "values": [r["win_rate"] or 0 for r in rows],
    }


@router.post("/risk/position-size")
async def api_position_size(request: Request, db: DbSession):
    body = await request.json()
    settings = SettingsRepository(db).get_risk_settings()
    market = body.get("market", "XAU/USD")
    symbol = SettingsRepository(db).get_symbol(market)
    tick_size = to_decimal(body.get("tick_size")) or (symbol.tick_size if symbol else None)
    tick_value = to_decimal(body.get("tick_value_per_lot")) or (
        symbol.tick_value_per_lot if symbol else None
    )
    contract = to_decimal(body.get("contract_size")) or (symbol.contract_size if symbol else None)
    result = calculate_position_size(
        account_balance=to_decimal(body.get("account_balance")) or Decimal("0"),
        risk_percent=to_decimal(body.get("risk_percent")) or Decimal("0"),
        entry_price=to_decimal(body.get("entry_price")) or Decimal("0"),
        stop_loss_price=to_decimal(body.get("stop_loss_price")) or Decimal("0"),
        tick_size=tick_size or Decimal("0"),
        tick_value_per_lot=tick_value or Decimal("0"),
        contract_size=contract,
        maximum_risk_percent=settings.maximum_risk_percent,
    )
    # Serialize Decimals
    out = {}
    for k, v in result.items():
        out[k] = float(v) if isinstance(v, Decimal) else v
    return out


@router.post("/risk/risk-reward")
async def api_risk_reward(request: Request, db: DbSession):
    body = await request.json()
    result = calculate_risk_reward(
        direction=str(body.get("direction", "BUY")),
        entry=to_decimal(body.get("entry")) or Decimal("0"),
        stop_loss=to_decimal(body.get("stop_loss")) or Decimal("0"),
        take_profit=to_decimal(body.get("take_profit")) or Decimal("0"),
    )
    out = {}
    for k, v in result.items():
        out[k] = float(v) if isinstance(v, Decimal) else v
    return out


@router.get("/symbols/{market}")
async def api_symbol(request: Request, market: str, db: DbSession):
    # Accept XAUUSD style
    market_map = {"XAUUSD": "XAU/USD", "BTCUSD": "BTC/USD"}
    market = market_map.get(market.upper().replace("/", ""), market)
    if market.upper() in ("XAUUSD",):
        market = "XAU/USD"
    if "XAU" in market.upper():
        market = "XAU/USD"
    if "BTC" in market.upper():
        market = "BTC/USD"
    sym = SettingsRepository(db).get_symbol(market)
    if not sym:
        return JSONResponse({"error": "Symbol not found"}, status_code=404)
    return {
        "market": sym.market,
        "contract_size": float(sym.contract_size),
        "tick_size": float(sym.tick_size),
        "tick_value_per_lot": float(sym.tick_value_per_lot),
        "pip_size": float(sym.pip_size),
        "decimal_places": sym.decimal_places,
    }
