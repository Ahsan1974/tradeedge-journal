"""Database engine and session management."""

from __future__ import annotations

import logging
from collections.abc import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""


def _build_engine():
    settings = get_settings()
    url = settings.resolved_database_url()
    connect_args: dict = {}
    engine_kwargs: dict = {
        "pool_pre_ping": True,
        "future": True,
    }

    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    else:
        # Managed providers (e.g. Neon) usually need SSL; skip for local plain URLs
        if "sslmode" not in url and ("neon.tech" in url or "ssl=true" in url.lower()):
            connect_args["sslmode"] = "require"
        engine_kwargs["pool_size"] = 5
        engine_kwargs["max_overflow"] = 5

    engine = create_engine(url, connect_args=connect_args, **engine_kwargs)

    if url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, _connection_record):  # noqa: ANN001
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


engine = _build_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Generator[Session, None, None]:
    """Yield a short-lived database session with rollback on error."""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db() -> None:
    """Create all tables (used for local bootstrap / tests)."""
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    logger.info("Database tables ensured.")


def check_db_connection() -> bool:
    """Return True when the database responds to a simple query."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error("Database health check failed: %s", type(exc).__name__)
        return False
