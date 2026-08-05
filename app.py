"""
Vercel / compatibility entry point.

Python prefers the `app/` package over this file when you `import app`,
so the real ASGI application lives in `app.main` and is re-exported from
`app/__init__.py`. This file keeps a root `app.py` for Vercel's build config.
"""

from app.main import app

__all__ = ["app"]
