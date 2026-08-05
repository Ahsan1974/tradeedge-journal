"""Shared FastAPI dependencies."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.csrf import generate_csrf_token
from app.database import get_db
from app.security import pop_flashes


DbSession = Annotated[Session, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]


def template_context(request: Request, **extra) -> dict:
    """Build common template context (no authentication)."""
    settings = get_settings()
    return {
        "request": request,
        "app_name": settings.app_name,
        "app_subtitle": settings.app_subtitle,
        "profile_name": settings.profile_name,
        "current_user": settings.profile_name,
        "csrf_token": generate_csrf_token(request),
        "flashes": pop_flashes(request),
        "timezone": settings.default_timezone,
        **extra,
    }
