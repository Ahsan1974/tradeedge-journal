"""TradeEdge Journal application package.

Do not import ``app.main`` here — that creates a circular import when Vercel
(or uvicorn) loads ``app.main`` and ``app.main`` imports other ``app.*`` modules.
Use ``from app.main import app`` or ``uvicorn app.main:app``.
"""

__version__ = "1.0.0"
__all__ = ["__version__"]
