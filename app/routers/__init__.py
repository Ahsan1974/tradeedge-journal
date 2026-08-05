"""Router package."""

from app.routers import analytics, api, calendar, dashboard, journal, risk, settings, trades

__all__ = [
    "dashboard",
    "trades",
    "journal",
    "analytics",
    "risk",
    "calendar",
    "settings",
    "api",
]
