"""MT5 sync routes."""

from __future__ import annotations

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse

from app.config import get_settings
from app.csrf import validate_csrf_token
from app.dependencies import DbSession
from app.security import session_flash
from app.services.mt5_service import mt5_account_info, sync_closed_trades

router = APIRouter(tags=["mt5"])

CLOUD_SYNC_MSG = (
    "MT5 Sync only works on your Windows PC (Exness terminal), not on the live website. "
    "On your PC run:  .\\.venv\\Scripts\\python.exe scripts\\sync_mt5.py  "
    "with DATABASE_URL pointing at Neon — then refresh this site."
)


@router.post("/trades/sync-mt5")
async def sync_mt5_post(request: Request, db: DbSession, csrf_token: str = Form("")):
    try:
        validate_csrf_token(request, csrf_token)
    except HTTPException:
        session_flash(request, "Session expired. Refresh the page and try Sync again.", "error")
        return RedirectResponse("/dashboard", status_code=303)

    settings = get_settings()
    if not settings.mt5_sync_available:
        session_flash(request, CLOUD_SYNC_MSG, "warning")
        return RedirectResponse("/dashboard", status_code=303)

    try:
        result = sync_closed_trades(db)
    except Exception as exc:  # noqa: BLE001
        session_flash(request, f"MT5 sync failed: {exc}", "error")
        return RedirectResponse("/dashboard", status_code=303)

    if result.connected and not result.errors:
        category = "success"
    elif result.connected:
        category = "warning"
    else:
        category = "error"
    session_flash(request, result.message or "Sync finished.", category)
    return RedirectResponse("/dashboard", status_code=303)


@router.post("/api/mt5/sync")
async def api_mt5_sync(request: Request, db: DbSession):
    settings = get_settings()
    if not settings.mt5_sync_available:
        return JSONResponse(
            {"connected": False, "ok": False, "message": CLOUD_SYNC_MSG, "errors": [CLOUD_SYNC_MSG]},
            status_code=503,
        )
    try:
        result = sync_closed_trades(db)
    except Exception as exc:  # noqa: BLE001
        return JSONResponse(
            {"connected": False, "ok": False, "message": str(exc), "errors": [str(exc)]},
            status_code=500,
        )
    status = 200 if result.connected else 503
    return JSONResponse(result.to_dict(), status_code=status)


@router.get("/api/mt5/status")
async def api_mt5_status():
    settings = get_settings()
    if not settings.mt5_enabled or settings.is_production:
        return {
            "ok": False,
            "enabled": settings.mt5_enabled,
            "sync_available": False,
            "error": "MT5 sync runs only on your Windows PC, not on Vercel.",
            "hint": CLOUD_SYNC_MSG,
        }
    info = mt5_account_info(settings)
    info["enabled"] = True
    info["sync_available"] = settings.mt5_sync_available
    info["symbols"] = {
        "xau": settings.mt5_symbol_xau,
        "btc": settings.mt5_symbol_btc,
    }
    info["history_days"] = settings.mt5_history_days
    return info
