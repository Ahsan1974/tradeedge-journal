"""MT5 sync routes."""

from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse

from app.config import get_settings
from app.csrf import validate_csrf_token
from app.dependencies import DbSession, template_context
from app.security import session_flash
from app.services.mt5_service import mt5_account_info, sync_closed_trades

router = APIRouter(tags=["mt5"])


@router.post("/trades/sync-mt5")
async def sync_mt5_post(request: Request, db: DbSession, csrf_token: str = Form("")):
    validate_csrf_token(request, csrf_token)
    result = sync_closed_trades(db)
    category = "success" if result.connected and not result.errors else "error"
    if result.connected and not result.errors:
        category = "success"
    elif result.connected:
        category = "warning"
    session_flash(request, result.message or "Sync finished.", category)
    return RedirectResponse("/trades", status_code=303)


@router.post("/api/mt5/sync")
async def api_mt5_sync(request: Request, db: DbSession):
    result = sync_closed_trades(db)
    status = 200 if result.connected else 503
    return JSONResponse(result.to_dict(), status_code=status)


@router.get("/api/mt5/status")
async def api_mt5_status():
    settings = get_settings()
    if not settings.mt5_enabled:
        return {"ok": False, "error": "MT5 sync disabled", "enabled": False}
    info = mt5_account_info(settings)
    info["enabled"] = True
    info["symbols"] = {
        "xau": settings.mt5_symbol_xau,
        "btc": settings.mt5_symbol_btc,
    }
    info["history_days"] = settings.mt5_history_days
    return info
