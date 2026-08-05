"""Risk calculator tests."""

from decimal import Decimal

from app.services.risk_service import calculate_position_size, calculate_risk_reward


def test_position_size():
    result = calculate_position_size(
        account_balance=Decimal("10000"),
        risk_percent=Decimal("1"),
        entry_price=Decimal("2650"),
        stop_loss_price=Decimal("2640"),
        tick_size=Decimal("0.01"),
        tick_value_per_lot=Decimal("1"),
        contract_size=Decimal("100"),
        maximum_risk_percent=Decimal("2"),
    )
    assert result["error"] is None
    assert result["risk_amount"] == Decimal("100.00")
    assert result["suggested_lot_size"] is not None
    assert result["suggested_lot_size"] > 0


def test_position_size_zero_distance():
    result = calculate_position_size(
        account_balance=Decimal("10000"),
        risk_percent=Decimal("1"),
        entry_price=Decimal("100"),
        stop_loss_price=Decimal("100"),
        tick_size=Decimal("0.01"),
        tick_value_per_lot=Decimal("1"),
    )
    assert result["error"]


def test_position_size_exceeds_max():
    result = calculate_position_size(
        account_balance=Decimal("10000"),
        risk_percent=Decimal("5"),
        entry_price=Decimal("100"),
        stop_loss_price=Decimal("99"),
        tick_size=Decimal("0.01"),
        tick_value_per_lot=Decimal("1"),
        maximum_risk_percent=Decimal("2"),
    )
    assert result["exceeds_max_risk"] is True


def test_risk_reward():
    result = calculate_risk_reward(
        direction="BUY",
        entry=Decimal("100"),
        stop_loss=Decimal("90"),
        take_profit=Decimal("120"),
    )
    assert result["error"] is None
    assert result["risk_distance"] == Decimal("10.00000000")
    assert result["reward_distance"] == Decimal("20.00000000")
    assert result["risk_reward_ratio"] == Decimal("2.00")
    assert result["min_breakeven_win_rate"] == Decimal("33.33")


def test_risk_reward_invalid():
    result = calculate_risk_reward(
        direction="BUY",
        entry=Decimal("100"),
        stop_loss=Decimal("100"),
        take_profit=Decimal("120"),
    )
    assert result["error"]
