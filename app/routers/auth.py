"""Authentication routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.csrf import generate_csrf_token, validate_csrf_token
from app.dependencies import template_context
from app.security import authenticate_user, is_authenticated, login_user, logout_user, session_flash

logger = logging.getLogger(__name__)
router = APIRouter(tags=["auth"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if is_authenticated(request):
        return RedirectResponse("/dashboard", status_code=303)
    ctx = template_context(request, next=request.query_params.get("next", "/dashboard"))
    ctx["csrf_token"] = generate_csrf_token(request)
    return templates.TemplateResponse("login.html", ctx)


@router.post("/login")
async def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    csrf_token: str = Form(""),
    next: str = Form("/dashboard"),
):
    validate_csrf_token(request, csrf_token)
    if authenticate_user(username.strip(), password):
        login_user(request, username.strip())
        session_flash(request, "Welcome back.", "success")
        target = next if next.startswith("/") else "/dashboard"
        logger.info("User logged in successfully")
        return RedirectResponse(target, status_code=303)
    session_flash(request, "Invalid username or password.", "error")
    ctx = template_context(request, next=next, error="Invalid username or password.")
    ctx["csrf_token"] = generate_csrf_token(request)
    return templates.TemplateResponse("login.html", ctx, status_code=401)


@router.post("/logout")
async def logout(request: Request, csrf_token: str = Form("")):
    validate_csrf_token(request, csrf_token)
    logout_user(request)
    return RedirectResponse("/login", status_code=303)


@router.get("/logout")
async def logout_get(request: Request):
    logout_user(request)
    return RedirectResponse("/login", status_code=303)
