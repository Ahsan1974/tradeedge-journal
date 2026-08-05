"""TradeEdge Journal — FastAPI application factory and ASGI app."""

from __future__ import annotations

import logging
import traceback
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.config import get_settings
from app.dependencies import template_context
from app.routers import analytics, api, calendar, dashboard, journal, mt5, risk, trades
from app.routers import settings as settings_router
from app.utils.formatting import (
    fmt_date,
    fmt_datetime,
    fmt_money,
    fmt_number,
    fmt_pct,
    fmt_ratio,
    holding_time_label,
    market_class,
    pnl_class,
    status_badge_class,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("tradeedge")

app_settings = get_settings()

app = FastAPI(
    title=app_settings.app_name,
    docs_url="/docs" if app_settings.debug else None,
    redoc_url=None,
)

app.add_middleware(
    SessionMiddleware,
    secret_key=app_settings.secret_key,
    session_cookie="tradeedge_session",
    same_site="lax",
    https_only=app_settings.session_https_only,
    max_age=60 * 60 * 24 * 14,
)

# Project root / public (works whether loaded as package or via root app.py)
PUBLIC_DIR = Path(__file__).resolve().parents[1] / "public"
if PUBLIC_DIR.exists():
    app.mount("/public", StaticFiles(directory=str(PUBLIC_DIR)), name="public")

templates = Jinja2Templates(directory="app/templates")
templates.env.filters["money"] = fmt_money
templates.env.filters["pct"] = fmt_pct
templates.env.filters["number"] = fmt_number
templates.env.filters["ratio"] = fmt_ratio
templates.env.filters["dt"] = fmt_datetime
templates.env.filters["d"] = fmt_date
templates.env.filters["pnl_class"] = pnl_class
templates.env.filters["badge"] = status_badge_class
templates.env.filters["market_class"] = market_class
templates.env.filters["holding"] = holding_time_label


def _configure_templates(mod_templates: Jinja2Templates) -> None:
    mod_templates.env.filters.update(templates.env.filters)


for mod in (dashboard, trades, journal, analytics, risk, calendar, settings_router):
    if hasattr(mod, "templates"):
        _configure_templates(mod.templates)


app.include_router(dashboard.router)
app.include_router(trades.router)
app.include_router(mt5.router)
app.include_router(journal.router)
app.include_router(analytics.router)
app.include_router(risk.router)
app.include_router(calendar.router)
app.include_router(settings_router.router)
app.include_router(api.router)


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):  # noqa: ANN001
    if request.url.path.startswith("/api/"):
        return JSONResponse({"error": "Not found"}, status_code=404)
    return templates.TemplateResponse(
        "errors/404.html",
        template_context(request, active_page=""),
        status_code=404,
    )


@app.exception_handler(500)
async def server_error_handler(request: Request, exc):  # noqa: ANN001
    logger.error("Unhandled error on %s: %s", request.url.path, type(exc).__name__)
    if app_settings.debug:
        logger.debug(traceback.format_exc())
    if request.url.path.startswith("/api/"):
        return JSONResponse({"error": "Internal server error"}, status_code=500)
    return templates.TemplateResponse(
        "errors/500.html",
        template_context(request, active_page=""),
        status_code=500,
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    from fastapi import HTTPException
    from starlette.exceptions import HTTPException as StarletteHTTPException

    if isinstance(exc, HTTPException | StarletteHTTPException):
        if exc.status_code == 303 and exc.headers and "Location" in exc.headers:
            return RedirectResponse(exc.headers["Location"], status_code=303)
        raise exc
    logger.error("Unhandled exception: %s", type(exc).__name__)
    if app_settings.debug:
        logger.debug(traceback.format_exc())
    if request.url.path.startswith("/api/"):
        return JSONResponse({"error": "Internal server error"}, status_code=500)
    return templates.TemplateResponse(
        "errors/500.html",
        template_context(request, active_page=""),
        status_code=500,
    )


@app.on_event("startup")
async def on_startup() -> None:
    if app_settings.using_sqlite:
        logger.warning(
            "SQLite fallback active — suitable for local development only. "
            "Set DATABASE_URL for production PostgreSQL."
        )
    if app_settings.app_env in ("development", "test") or app_settings.using_sqlite:
        try:
            from app.database import SessionLocal, init_db
            from app.repositories.settings_repository import SettingsRepository

            init_db()
            db = SessionLocal()
            try:
                SettingsRepository(db).get_risk_settings()
                SettingsRepository(db).ensure_symbols()
            finally:
                db.close()
        except Exception as exc:  # noqa: BLE001
            logger.error("Startup DB init failed: %s", type(exc).__name__)

    # Optional local MT5 sync (never on Vercel / test)
    if (
        app_settings.mt5_enabled
        and app_settings.mt5_auto_sync
        and app_settings.app_env != "test"
        and not app_settings.is_production
    ):
        try:
            from app.database import SessionLocal
            from app.services.mt5_service import sync_closed_trades

            db = SessionLocal()
            try:
                result = sync_closed_trades(db)
                logger.info("Startup MT5 sync: %s", result.message)
            finally:
                db.close()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Startup MT5 sync skipped: %s", type(exc).__name__)


@app.get("/health")
async def health():
    from app.database import check_db_connection

    ok = check_db_connection()
    return {"status": "ok" if ok else "degraded", "app": app_settings.app_name}
