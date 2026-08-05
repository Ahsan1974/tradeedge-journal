"""Simple CSRF protection for form POSTs using signed session tokens."""

from __future__ import annotations

import secrets
from typing import Annotated

from fastapi import Form, HTTPException, Request, status

CSRF_SESSION_KEY = "_csrf_token"


def generate_csrf_token(request: Request) -> str:
    """Create or reuse a CSRF token stored in the session."""
    token = request.session.get(CSRF_SESSION_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        request.session[CSRF_SESSION_KEY] = token
    return str(token)


def validate_csrf_token(request: Request, token: str | None) -> None:
    """Raise 403 when the submitted CSRF token is missing or invalid."""
    expected = request.session.get(CSRF_SESSION_KEY)
    if not expected or not token or not secrets.compare_digest(str(expected), str(token)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing CSRF token. Please refresh and try again.",
        )


async def require_csrf(
    request: Request,
    csrf_token: Annotated[str | None, Form()] = None,
) -> None:
    """FastAPI dependency that validates CSRF from form body."""
    # Also accept header for API-ish form posts
    header_token = request.headers.get("X-CSRF-Token")
    token = csrf_token or header_token
    validate_csrf_token(request, token)


def csrf_form_field(request: Request) -> str:
    """Return HTML for a hidden CSRF input."""
    token = generate_csrf_token(request)
    return f'<input type="hidden" name="csrf_token" value="{token}">'
