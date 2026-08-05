"""Trade tests — trades come from MT5 sync; manual create is disabled."""

from decimal import Decimal

from app.models.trade import Trade
from app.utils.dates import now_tz


def _seed_trade(db_session, **overrides):
    now = now_tz()
    data = dict(
        trade_date=now,
        close_date=now,
        market="XAU/USD",
        direction="BUY",
        status="WIN",
        entry_price=Decimal("2650"),
        exit_price=Decimal("2660"),
        lot_size=Decimal("0.1"),
        commission=Decimal("0"),
        swap=Decimal("0"),
        fees=Decimal("0"),
        profit_loss=Decimal("100"),
        net_profit_loss=Decimal("100"),
        source="TEST",
        external_ticket="TEST-1",
    )
    data.update(overrides)
    trade = Trade(**data)
    db_session.add(trade)
    db_session.commit()
    db_session.refresh(trade)
    return trade


def test_manual_create_disabled(client, csrf_token):
    resp = client.post(
        "/trades/new",
        data={
            "csrf_token": csrf_token,
            "trade_date": "2026-03-01T10:00",
            "market": "XAU/USD",
            "direction": "BUY",
            "status": "WIN",
            "entry_price": "2650",
            "lot_size": "0.1",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert resp.headers["location"] == "/trades"


def test_edit_trade(client, csrf_token, db_session, db_engine):
    # Use app DB via HTTP seed is hard — insert through overridden session by posting sync-less:
    # Create via shared engine used by client
    from sqlalchemy.orm import sessionmaker

    Session = sessionmaker(bind=db_engine)
    s = Session()
    trade = _seed_trade(s, external_ticket="EDIT-1")
    trade_id = trade.id
    s.close()

    edit = client.post(
        f"/trades/{trade_id}/edit",
        data={
            "csrf_token": csrf_token,
            "trade_date": "2026-03-02T10:00",
            "close_date": "2026-03-02T11:00",
            "market": "XAU/USD",
            "direction": "BUY",
            "status": "WIN",
            "entry_price": "2650",
            "exit_price": "2665",
            "lot_size": "0.1",
            "profit_loss": "120",
            "commission": "0",
            "swap": "0",
            "fees": "0",
            "net_profit_loss": "120",
            "net_profit_loss_manual": "1",
            "status_manual": "1",
            "lesson": "Synced trade note",
        },
        follow_redirects=False,
    )
    assert edit.status_code == 303
    detail = client.get(f"/trades/{trade_id}")
    assert detail.status_code == 200


def test_delete_trade(client, csrf_token, db_engine):
    from sqlalchemy.orm import sessionmaker

    Session = sessionmaker(bind=db_engine)
    s = Session()
    trade = _seed_trade(s, external_ticket="DEL-1", net_profit_loss=Decimal("10"))
    trade_id = trade.id
    s.close()

    deleted = client.post(
        f"/trades/{trade_id}/delete",
        data={"csrf_token": csrf_token},
        follow_redirects=False,
    )
    assert deleted.status_code == 303
    missing = client.get(f"/trades/{trade_id}")
    assert missing.status_code == 404


def test_trades_list(client, db_engine):
    from sqlalchemy.orm import sessionmaker

    Session = sessionmaker(bind=db_engine)
    s = Session()
    _seed_trade(s, external_ticket="LIST-1", market="XAU/USD")
    _seed_trade(s, external_ticket="LIST-2", market="BTC/USD", net_profit_loss=Decimal("-20"), status="LOSS")
    s.close()
    listing = client.get("/trades?market=XAU/USD")
    assert listing.status_code == 200
    assert "XAU/USD" in listing.text


def test_new_trade_redirects(client):
    resp = client.get("/trades/new", follow_redirects=False)
    assert resp.status_code == 303
