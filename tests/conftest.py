"""Pytest fixtures — isolated temporary SQLite database."""

from __future__ import annotations

import os
import re
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["APP_ENV"] = "test"
os.environ["DEBUG"] = "true"
os.environ["SECRET_KEY"] = "test-secret-key-not-for-production"
os.environ["ADMIN_USERNAME"] = "ahsan"
os.environ["ADMIN_PASSWORD_HASH"] = ""
os.environ["DATABASE_URL"] = ""
os.environ["SESSION_HTTPS_ONLY"] = "false"
os.environ["SEED_DEMO_DATA"] = "false"

from app.config import get_settings

get_settings.cache_clear()


@pytest.fixture()
def db_engine(tmp_path: Path):
    from app.database import Base

    db_path = tmp_path / "test.db"
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _fk(dbapi_connection, _):  # noqa: ANN001
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture()
def db_session(db_engine):
    from app.repositories.settings_repository import SettingsRepository

    Session = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)
    session = Session()
    SettingsRepository(session).get_risk_settings()
    SettingsRepository(session).ensure_symbols()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_engine):
    from app.database import get_db
    from app.main import app as application

    get_settings.cache_clear()

    TestingSession = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)

    def _override_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    application.dependency_overrides[get_db] = _override_db
    with TestClient(application) as c:
        yield c
    application.dependency_overrides.clear()


@pytest.fixture()
def auth_client(client):
    """Alias kept for older tests — no login required."""
    return client


def _csrf(client) -> str:
    page = client.get("/dashboard")
    m = re.search(r'name="csrf_token" value="([^"]+)"', page.text)
    if m:
        return m.group(1)
    m = re.search(r'content="([^"]+)"[^>]*name="csrf-token"|name="csrf-token"[^>]*content="([^"]+)"', page.text)
    if m:
        return m.group(1) or m.group(2)
    m = re.search(r'data-csrf="([^"]+)"', page.text)
    return m.group(1) if m else ""


@pytest.fixture()
def csrf_token(client):
    return _csrf(client)


@pytest.fixture()
def sample_trades(db_session):
    from app.models.trade import Trade
    from app.utils.dates import now_tz

    now = now_tz()
    trades = []
    specs = [
        ("WIN", Decimal("100"), "XAU/USD", "BUY"),
        ("WIN", Decimal("50"), "XAU/USD", "SELL"),
        ("LOSS", Decimal("-40"), "BTC/USD", "BUY"),
        ("LOSS", Decimal("-20"), "BTC/USD", "SELL"),
        ("BREAKEVEN", Decimal("0"), "XAU/USD", "BUY"),
        ("OPEN", None, "BTC/USD", "BUY"),
    ]
    for i, (status, net, market, direction) in enumerate(specs):
        t = Trade(
            trade_date=now - timedelta(days=i + 1),
            close_date=None if status == "OPEN" else now - timedelta(days=i),
            market=market,
            direction=direction,
            status=status,
            entry_price=Decimal("100"),
            exit_price=None if status == "OPEN" else Decimal("101"),
            lot_size=Decimal("0.1"),
            commission=Decimal("0"),
            swap=Decimal("0"),
            fees=Decimal("0"),
            profit_loss=net,
            net_profit_loss=net,
            risk_amount=Decimal("50"),
            risk_reward_ratio=Decimal("2"),
            setup="Pullback",
            timeframe="H1",
            trading_session="London",
            source="TEST",
            external_ticket=f"T-{i}",
            followed_plan=True,
        )
        db_session.add(t)
        trades.append(t)
    db_session.commit()
    for t in trades:
        db_session.refresh(t)
    return trades
