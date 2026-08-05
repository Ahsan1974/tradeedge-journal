"""Authentication helpers using bcrypt and signed sessions."""

from __future__ import annotations

import logging
from typing import Any

import bcrypt
from starlette.requests import Request

from app.config import get_settings

logger = logging.getLogger(__name__)

SESSION_USER_KEY = "authenticated_user"


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    if not plain_password or not password_hash:
        return False
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            password_hash.encode("utf-8"),
        )
    except (ValueError, TypeError) as exc:
        logger.warning("Password verification failed: %s", type(exc).__name__)
        return False


def hash_password(plain_password: str) -> str:
    """Generate a bcrypt hash for the given password."""
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt(rounds=12))
    return hashed.decode("utf-8")


def authenticate_user(username: str, password: str) -> bool:
    """Authenticate against ADMIN_USERNAME / ADMIN_PASSWORD_HASH."""
    settings = get_settings()
    if not settings.admin_password_hash:
        logger.error("ADMIN_PASSWORD_HASH is not configured")
        return False
    if username != settings.admin_username:
        return False
    return verify_password(password, settings.admin_password_hash)


def login_user(request: Request, username: str) -> None:
    request.session[SESSION_USER_KEY] = username


def logout_user(request: Request) -> None:
    request.session.clear()


def get_current_user(request: Request) -> str | None:
    user = request.session.get(SESSION_USER_KEY)
    return str(user) if user else None


def is_authenticated(request: Request) -> bool:
    return get_current_user(request) is not None


def session_flash(request: Request, message: str, category: str = "info") -> None:
    """Store a flash message in the session."""
    flashes: list[dict[str, Any]] = request.session.get("_flashes", [])
    flashes.append({"message": message, "category": category})
    request.session["_flashes"] = flashes


def pop_flashes(request: Request) -> list[dict[str, Any]]:
    return list(request.session.pop("_flashes", []))
