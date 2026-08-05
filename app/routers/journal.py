"""Journal routes."""

from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.csrf import validate_csrf_token
from app.dependencies import DbSession, template_context
from app.models.journal import JournalEntry
from app.models.trade import Setup
from app.repositories.journal_repository import JournalRepository
from app.repositories.settings_repository import SettingsRepository
from app.repositories.trade_repository import TradeRepository
from app.security import session_flash
from app.services.analytics_service import analyze_performance
from app.services.journal_service import journal_analytics
from app.utils.dates import now_tz, parse_date, period_range

router = APIRouter(tags=["journal"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/journal", response_class=HTMLResponse)
async def journal_list(request: Request, db: DbSession):
    qp = request.query_params
    followed = qp.get("followed_plan")
    followed_bool = None
    if followed == "1":
        followed_bool = True
    elif followed == "0":
        followed_bool = False

    page_data = JournalRepository(db).list_filtered(
        page=int(qp.get("page", 1) or 1),
        q=qp.get("q"),
        market=qp.get("market"),
        setup=qp.get("setup"),
        tags=qp.get("tags"),
        followed_plan=followed_bool,
        date_from=parse_date(qp.get("date_from")),
        date_to=parse_date(qp.get("date_to")),
    )
    settings = SettingsRepository(db).get_risk_settings()
    all_entries = JournalRepository(db).all()
    trades = TradeRepository(db).all_filtered(exclude_open=True)
    analytics = journal_analytics(all_entries, trades)
    month_from, month_to = period_range("month", tz_name=settings.timezone)
    month_stats = analyze_performance(
        TradeRepository(db).all_filtered(date_from=month_from, date_to=month_to),
        settings.starting_balance,
    )
    ctx = template_context(
        request,
        active_page="journal",
        page_data=page_data,
        filters=dict(qp),
        analytics=analytics,
        setups=[s.value for s in Setup],
        settings=settings,
        sidebar_balance=settings.current_balance,
        sidebar_month_pnl=month_stats.net_pnl,
        pakistan_time=now_tz(settings.timezone),
        trades=TradeRepository(db).recent(50),
    )
    return templates.TemplateResponse("journal/list.html", ctx)


@router.get("/journal/new", response_class=HTMLResponse)
async def journal_new(request: Request, db: DbSession):
    settings = SettingsRepository(db).get_risk_settings()
    ctx = template_context(
        request,
        active_page="journal",
        entry=None,
        mode="create",
        errors=[],
        form_data={},
        setups=[s.value for s in Setup],
        trades=TradeRepository(db).recent(100),
        settings=settings,
        sidebar_balance=settings.current_balance,
        pakistan_time=now_tz(settings.timezone),
    )
    return templates.TemplateResponse("journal/form.html", ctx)


def _entry_from_form(form: dict) -> tuple[dict, list[str]]:
    errors = []
    title = (form.get("title") or "").strip()
    if not title:
        errors.append("Title is required.")
    entry_date = parse_date(form.get("entry_date"))
    if not entry_date:
        errors.append("Entry date is required.")
    followed = form.get("followed_plan")
    if followed == "1":
        followed_plan = True
    elif followed == "0":
        followed_plan = False
    else:
        followed_plan = None
    trade_id = form.get("trade_id")
    data = {
        "title": title,
        "entry_date": entry_date,
        "market": form.get("market") or None,
        "setup": form.get("setup") or None,
        "notes": form.get("notes") or None,
        "lesson": form.get("lesson") or None,
        "mistakes": form.get("mistakes") or None,
        "emotional_state": form.get("emotional_state") or None,
        "followed_plan": followed_plan,
        "tags": form.get("tags") or None,
        "trade_id": int(trade_id) if trade_id else None,
    }
    return data, errors


@router.post("/journal/new")
async def journal_create(request: Request, db: DbSession):
    form = dict(await request.form())
    validate_csrf_token(request, form.get("csrf_token"))
    data, errors = _entry_from_form(form)
    settings = SettingsRepository(db).get_risk_settings()
    if errors:
        ctx = template_context(
            request,
            active_page="journal",
            entry=None,
            mode="create",
            errors=errors,
            form_data=form,
            setups=[s.value for s in Setup],
            trades=TradeRepository(db).recent(100),
            settings=settings,
            sidebar_balance=settings.current_balance,
            pakistan_time=now_tz(settings.timezone),
        )
        return templates.TemplateResponse("journal/form.html", ctx, status_code=400)
    entry = JournalEntry(**data)
    JournalRepository(db).add(entry)
    session_flash(request, "Journal entry created.", "success")
    return RedirectResponse("/journal", status_code=303)


@router.get("/journal/{entry_id}/edit", response_class=HTMLResponse)
async def journal_edit(request: Request, entry_id: int, db: DbSession):
    entry = JournalRepository(db).get(entry_id)
    if not entry:
        return RedirectResponse("/journal", status_code=303)
    settings = SettingsRepository(db).get_risk_settings()
    ctx = template_context(
        request,
        active_page="journal",
        entry=entry,
        mode="edit",
        errors=[],
        form_data={},
        setups=[s.value for s in Setup],
        trades=TradeRepository(db).recent(100),
        settings=settings,
        sidebar_balance=settings.current_balance,
        pakistan_time=now_tz(settings.timezone),
    )
    return templates.TemplateResponse("journal/form.html", ctx)


@router.post("/journal/{entry_id}/edit")
async def journal_update(request: Request, entry_id: int, db: DbSession):
    repo = JournalRepository(db)
    entry = repo.get(entry_id)
    if not entry:
        return RedirectResponse("/journal", status_code=303)
    form = dict(await request.form())
    validate_csrf_token(request, form.get("csrf_token"))
    data, errors = _entry_from_form(form)
    settings = SettingsRepository(db).get_risk_settings()
    if errors:
        ctx = template_context(
            request,
            active_page="journal",
            entry=entry,
            mode="edit",
            errors=errors,
            form_data=form,
            setups=[s.value for s in Setup],
            trades=TradeRepository(db).recent(100),
            settings=settings,
            sidebar_balance=settings.current_balance,
            pakistan_time=now_tz(settings.timezone),
        )
        return templates.TemplateResponse("journal/form.html", ctx, status_code=400)
    for k, v in data.items():
        setattr(entry, k, v)
    repo.update(entry)
    session_flash(request, "Journal entry updated.", "success")
    return RedirectResponse("/journal", status_code=303)


@router.post("/journal/{entry_id}/delete")
async def journal_delete(request: Request, entry_id: int, db: DbSession, csrf_token: str = Form("")):
    validate_csrf_token(request, csrf_token)
    repo = JournalRepository(db)
    entry = repo.get(entry_id)
    if entry:
        repo.delete(entry)
        session_flash(request, "Journal entry deleted.", "success")
    return RedirectResponse("/journal", status_code=303)
