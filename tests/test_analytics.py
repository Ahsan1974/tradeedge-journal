"""Analytics calculation unit tests."""

from datetime import datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from app.models.trade import Trade
from app.services import analytics_service as A

TZ = ZoneInfo("Asia/Karachi")


def _t(status, net, day_offset=0, risk=None, rr=None):
    now = datetime(2026, 4, 1, 12, 0, tzinfo=TZ)
    return Trade(
        trade_date=now - timedelta(days=day_offset + 1),
        close_date=now - timedelta(days=day_offset),
        market="XAU/USD",
        direction="BUY",
        status=status,
        entry_price=Decimal("100"),
        exit_price=Decimal("101"),
        lot_size=Decimal("0.1"),
        commission=Decimal("0"),
        swap=Decimal("0"),
        fees=Decimal("0"),
        profit_loss=net,
        net_profit_loss=net,
        risk_amount=risk,
        risk_reward_ratio=rr,
        source="TEST",
    )


def test_gross_profit_loss_net():
    trades = [
        _t("WIN", Decimal("100")),
        _t("WIN", Decimal("50")),
        _t("LOSS", Decimal("-40")),
        _t("OPEN", None),
    ]
    assert A.compute_gross_profit(trades) == Decimal("150")
    assert A.compute_gross_loss(trades) == Decimal("40")
    assert A.compute_net_pnl(trades) == Decimal("110")


def test_win_rate_excludes_open_and_counts_be():
    trades = [
        _t("WIN", Decimal("10")),
        _t("LOSS", Decimal("-5")),
        _t("BREAKEVEN", Decimal("0")),
        _t("OPEN", None),
    ]
    # 1 win / 3 closed
    assert A.compute_win_rate(trades) == Decimal("33.33")


def test_profit_factor_and_zero_loss():
    trades = [_t("WIN", Decimal("100")), _t("WIN", Decimal("50"))]
    pf = A.compute_profit_factor(trades)
    assert pf == Decimal("999.99")
    empty = A.compute_profit_factor([])
    assert empty is None


def test_expectancy_avg_win_loss_payoff():
    trades = [
        _t("WIN", Decimal("100")),
        _t("WIN", Decimal("50")),
        _t("LOSS", Decimal("-50")),
        _t("LOSS", Decimal("-50")),
    ]
    assert A.compute_avg_win(trades) == Decimal("75.00")
    assert A.compute_avg_loss(trades) == Decimal("50.00")
    assert A.compute_payoff_ratio(trades) == Decimal("1.50")
    exp = A.compute_expectancy(trades)
    assert exp is not None
    # 0.5*75 - 0.5*50 = 12.5
    assert exp == Decimal("12.50")


def test_streaks_and_breakeven_breaks():
    trades = [
        _t("WIN", Decimal("10"), 5),
        _t("WIN", Decimal("10"), 4),
        _t("BREAKEVEN", Decimal("0"), 3),
        _t("LOSS", Decimal("-5"), 2),
        _t("LOSS", Decimal("-5"), 1),
        _t("LOSS", Decimal("-5"), 0),
    ]
    cw, cl, mw, ml = A.compute_streaks(trades)
    assert mw == 2
    assert ml == 3
    assert cl == 3
    assert cw == 0


def test_drawdown():
    trades = [
        _t("WIN", Decimal("100"), 3),
        _t("LOSS", Decimal("-150"), 2),
        _t("WIN", Decimal("50"), 1),
    ]
    max_dd, max_dd_pct, series, equity = A.compute_drawdown(trades, Decimal("1000"))
    assert max_dd == Decimal("150.00")
    assert series
    assert equity


def test_realized_r_and_empty():
    t = _t("WIN", Decimal("100"), risk=Decimal("50"))
    assert A.realized_r_multiple(t) == Decimal("2.00")
    stats = A.analyze_performance([])
    assert stats.total_trades == 0
    assert stats.win_rate is None
    assert stats.net_pnl == Decimal("0")


def test_market_comparison():
    trades = [
        Trade(
            trade_date=datetime(2026, 1, 1, tzinfo=TZ),
            close_date=datetime(2026, 1, 1, 2, tzinfo=TZ),
            market="XAU/USD",
            direction="BUY",
            status="WIN",
            entry_price=Decimal("1"),
            lot_size=Decimal("0.1"),
            commission=Decimal("0"),
            swap=Decimal("0"),
            fees=Decimal("0"),
            net_profit_loss=Decimal("100"),
            source="TEST",
        ),
        Trade(
            trade_date=datetime(2026, 1, 2, tzinfo=TZ),
            close_date=datetime(2026, 1, 2, 2, tzinfo=TZ),
            market="BTC/USD",
            direction="BUY",
            status="LOSS",
            entry_price=Decimal("1"),
            lot_size=Decimal("0.1"),
            commission=Decimal("0"),
            swap=Decimal("0"),
            fees=Decimal("0"),
            net_profit_loss=Decimal("-20"),
            source="TEST",
        ),
    ]
    grouped = A.group_by_market(trades)
    assert grouped["XAU/USD"]["net_pnl"] == 100.0
    assert grouped["BTC/USD"]["net_pnl"] == -20.0


def test_min_breakeven_win_rate():
    assert A.minimum_breakeven_win_rate(Decimal("2")) == Decimal("33.33")
    assert A.minimum_breakeven_win_rate(Decimal("0")) is None
