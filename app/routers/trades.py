"""Trade CRUD, import, and export routes."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, File, Form, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from app.csrf import validate_csrf_token
from app.dependencies import DbSession, template_context
from app.models.trade import Setup, Timeframe, TradingSession
from app.repositories.settings_repository import SettingsRepository
from app.repositories.trade_repository import TradeRepository
from app.security import session_flash
from app.services import csv_service
from app.services.analytics_service import analyze_performance
from app.services.trade_service import (
    apply_dict_to_trade,
    create_trade_from_dict,
    form_to_trade_dict,
    price_warnings,
    validate_trade_dict,
)
from app.utils.dates import now_tz, parse_datetime, period_range
from app.utils.decimals import to_decimal

router = APIRouter(tags=["trades"])
templates = Jinja2Templates(directory="app/templates")

MAX_UPLOAD_BYTES = 2 * 1024 * 1024  # 2 MB


def _common(db):
    settings = SettingsRepository(db).get_risk_settings()
    return {
        "settings": settings,
        "setups": [s.value for s in Setup],
        "timeframes": [t.value for t in Timeframe],
        "sessions": [s.value for s in TradingSession],
        "sidebar_balance": settings.current_balance,
        "pakistan_time": now_tz(settings.timezone),
    }


@router.get("/trades", response_class=HTMLResponse)
async def trades_list(request: Request, db: DbSession):
    qp = request.query_params
    page = int(qp.get("page", 1) or 1)
    sort = qp.get("sort", "trade_date")
    order = qp.get("order", "desc")
    date_from = parse_datetime(qp.get("date_from")) if qp.get("date_from") else None
    date_to = parse_datetime(qp.get("date_to")) if qp.get("date_to") else None
    if date_to and qp.get("date_to") and "T" not in qp.get("date_to", ""):
        date_to = date_to.replace(hour=23, minute=59, second=59)

    result = TradeRepository(db).list_filtered(
        page=page,
        per_page=int(qp.get("per_page", 25) or 25),
        sort=sort,
        order=order,
        q=qp.get("q"),
        market=qp.get("market"),
        status=qp.get("status"),
        direction=qp.get("direction"),
        setup=qp.get("setup"),
        timeframe=qp.get("timeframe"),
        session=qp.get("session"),
        date_from=date_from,
        date_to=date_to,
        min_pnl=to_decimal(qp.get("min_pnl")),
        max_pnl=to_decimal(qp.get("max_pnl")),
    )
    common = _common(db)
    month_from, month_to = period_range("month", tz_name=common["settings"].timezone)
    month_stats = analyze_performance(
        TradeRepository(db).all_filtered(date_from=month_from, date_to=month_to),
        common["settings"].starting_balance,
    )
    ctx = template_context(
        request,
        active_page="trades",
        page_data=result,
        filters=dict(qp),
        sort=sort,
        order=order,
        sidebar_month_pnl=month_stats.net_pnl,
        **common,
    )
    return templates.TemplateResponse("trades/list.html", ctx)


@router.get("/trades/new", response_class=HTMLResponse)
async def trade_new(request: Request, db: DbSession):
    session_flash(
        request,
        "Manual trade entry is disabled. Use Sync from MT5 to import closed Exness trades.",
        "info",
    )
    return RedirectResponse("/trades", status_code=303)


@router.post("/trades/new")
async def trade_create(request: Request, db: DbSession):
    session_flash(
        request,
        "Manual trade entry is disabled. Sync closed trades from MetaTrader 5 instead.",
        "warning",
    )
    return RedirectResponse("/trades", status_code=303)


@router.get("/trades/export")
async def trades_export_early(
    request: Request,
    db: DbSession,
    scope: str = Query("all"),
):
    """Registered before /trades/{id} so 'export' is never captured as an id."""
    return await _export_trades(request, db, scope)


@router.get("/trades/import", response_class=HTMLResponse)
async def import_page_early(request: Request, db: DbSession):
    common = _common(db)
    ctx = template_context(request, active_page="trades", **common)
    return templates.TemplateResponse("trades/import.html", ctx)


@router.get("/trades/import/template")
async def import_template_early(request: Request):
    return Response(
        content=csv_service.sample_template_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="tradeedge_template.csv"'},
    )


@router.get("/trades/{trade_id:int}", response_class=HTMLResponse)
async def trade_detail(request: Request, trade_id: int, db: DbSession):
    repo = TradeRepository(db)
    trade = repo.get(trade_id)
    if not trade:
        return templates.TemplateResponse(
            "errors/404.html", template_context(request, active_page="trades"), status_code=404
        )
    prev_t, next_t = repo.neighbors(trade_id)
    common = _common(db)
    ctx = template_context(
        request,
        active_page="trades",
        trade=trade,
        prev_trade=prev_t,
        next_trade=next_t,
        **common,
    )
    return templates.TemplateResponse("trades/detail.html", ctx)


@router.get("/trades/{trade_id:int}/edit", response_class=HTMLResponse)
async def trade_edit(request: Request, trade_id: int, db: DbSession):
    trade = TradeRepository(db).get(trade_id)
    if not trade:
        return templates.TemplateResponse(
            "errors/404.html", template_context(request, active_page="trades"), status_code=404
        )
    common = _common(db)
    ctx = template_context(
        request,
        active_page="trades",
        trade=trade,
        form_data={},
        errors=[],
        warnings=[],
        mode="edit",
        **common,
    )
    return templates.TemplateResponse("trades/form.html", ctx)


@router.post("/trades/{trade_id:int}/edit")
async def trade_update(request: Request, trade_id: int, db: DbSession):
    repo = TradeRepository(db)
    trade = repo.get(trade_id)
    if not trade:
        return RedirectResponse("/trades", status_code=303)
    form = dict(await request.form())
    validate_csrf_token(request, form.get("csrf_token"))
    data = form_to_trade_dict(form)
    errors = validate_trade_dict(data)
    warnings = price_warnings(data)
    common = _common(db)
    if errors:
        ctx = template_context(
            request,
            active_page="trades",
            trade=trade,
            form_data=form,
            errors=errors,
            warnings=warnings,
            mode="edit",
            **common,
        )
        return templates.TemplateResponse("trades/form.html", ctx, status_code=400)
    apply_dict_to_trade(trade, data)
    repo.update(trade)
    session_flash(request, "Trade updated.", "success")
    return RedirectResponse(f"/trades/{trade.id}", status_code=303)


@router.post("/trades/{trade_id:int}/delete")
async def trade_delete(request: Request, trade_id: int, db: DbSession, csrf_token: str = Form("")):
    validate_csrf_token(request, csrf_token)
    repo = TradeRepository(db)
    trade = repo.get(trade_id)
    if trade:
        repo.delete(trade)
        session_flash(request, "Trade deleted.", "success")
    return RedirectResponse("/trades", status_code=303)


async def _export_trades(request: Request, db: DbSession, scope: str = "all"):
    repo = TradeRepository(db)
    qp = request.query_params
    if scope == "xau":
        trades = repo.all_filtered(market="XAU/USD")
    elif scope == "btc":
        trades = repo.all_filtered(market="BTC/USD")
    elif scope == "month":
        settings = SettingsRepository(db).get_risk_settings()
        df, dt = period_range("month", tz_name=settings.timezone)
        trades = repo.all_filtered(date_from=df, date_to=dt)
    elif scope == "filtered":
        trades = repo.all_filtered(
            q=qp.get("q"),
            market=qp.get("market"),
            status=qp.get("status"),
            direction=qp.get("direction"),
            setup=qp.get("setup"),
            timeframe=qp.get("timeframe"),
            session=qp.get("session"),
            date_from=parse_datetime(qp.get("date_from")) if qp.get("date_from") else None,
            date_to=parse_datetime(qp.get("date_to")) if qp.get("date_to") else None,
            min_pnl=to_decimal(qp.get("min_pnl")),
            max_pnl=to_decimal(qp.get("max_pnl")),
        )
    else:
        trades = repo.all_filtered()
    content = csv_service.trades_to_csv(trades)
    filename = f"trades_{scope}_{datetime.utcnow().strftime('%Y%m%d')}.csv"
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/trades/import/preview")
async def import_preview(
    request: Request,
    db: DbSession,
    csrf_token: str = Form(""),
    file: UploadFile = File(...),
):
    validate_csrf_token(request, csrf_token)
    if not file.filename or not file.filename.lower().endswith(".csv"):
        session_flash(request, "Please upload a .csv file.", "error")
        return RedirectResponse("/trades/import", status_code=303)
    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        session_flash(request, "File exceeds 2 MB limit.", "error")
        return RedirectResponse("/trades/import", status_code=303)
    try:
        fmt, rows = csv_service.parse_csv_content(content)
    except Exception as exc:  # noqa: BLE001
        session_flash(request, f"Could not parse CSV: {exc}", "error")
        return RedirectResponse("/trades/import", status_code=303)

    # Build existing ticket set for duplicate detection
    existing = set()
    for t in TradeRepository(db).all_filtered():
        if t.external_ticket:
            existing.add(
                (
                    t.external_ticket,
                    t.market,
                    t.trade_date.date().isoformat(),
                )
            )
    preview = csv_service.validate_import_rows(rows, fmt, existing_tickets=existing)
    # Store preview in session (signed cookie session — keep payload reasonable)
    # Store only valid full rows + metadata to avoid huge cookies; cap at 200 rows
    session_payload = {
        "format": preview["format"],
        "valid_count": preview["valid_count"],
        "invalid_count": preview["invalid_count"],
        "duplicate_count": preview["duplicate_count"],
        "total": preview["total"],
        "rows": preview["rows"][:200],
    }
    request.session["import_preview"] = session_payload
    common = _common(db)
    ctx = template_context(request, active_page="trades", preview=preview, **common)
    return templates.TemplateResponse("trades/import_preview.html", ctx)


@router.post("/trades/import/confirm")
async def import_confirm(
    request: Request,
    db: DbSession,
    csrf_token: str = Form(""),
    skip_invalid: str = Form("1"),
):
    validate_csrf_token(request, csrf_token)
    preview = request.session.get("import_preview")
    if not preview:
        session_flash(request, "No import preview found. Upload again.", "error")
        return RedirectResponse("/trades/import", status_code=303)

    repo = TradeRepository(db)
    imported = 0
    skipped = 0
    for row in preview.get("rows", []):
        if not row.get("valid"):
            skipped += 1
            continue
        full = row.get("full", {})
        # Rehydrate datetimes/decimals
        data = form_to_trade_dict(full)
        errors = validate_trade_dict(data)
        if errors:
            skipped += 1
            continue
        data["source"] = data.get("source") or "CSV_IMPORT"
        trade = create_trade_from_dict(data)
        repo.add(trade)
        imported += 1

    request.session.pop("import_preview", None)
    session_flash(
        request,
        f"Imported {imported} trade(s). Skipped {skipped}.",
        "success" if imported else "warning",
    )
    return RedirectResponse("/trades", status_code=303)


@router.post("/trades/import/cancel")
async def import_cancel(request: Request, csrf_token: str = Form("")):
    validate_csrf_token(request, csrf_token)
    request.session.pop("import_preview", None)
    session_flash(request, "Import cancelled.", "info")
    return RedirectResponse("/trades/import", status_code=303)
