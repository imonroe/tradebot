"""Tests for risk management checks."""
from datetime import date, time
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from tradebot.core.enums import OrderSide, SpreadType
from tradebot.core.events import SignalEvent
from tradebot.core.models import OrderLeg
from tradebot.risk.checks import (
    PDTCheck,
    MaxDailyLossCheck,
    MaxDrawdownCheck,
    PositionSizeCheck,
    SpreadWidthCheck,
    TimeWindowCheck,
    DuplicateCheck,
)


def _make_signal(spread_type=SpreadType.CREDIT_SPREAD, symbol="XSP") -> SignalEvent:
    return SignalEvent(
        strategy_name="test",
        spread_type=spread_type,
        symbol=symbol,
        legs=[
            OrderLeg(option_symbol="XSP250316P00565000", side=OrderSide.SELL_TO_OPEN, quantity=1),
            OrderLeg(option_symbol="XSP250316P00560000", side=OrderSide.BUY_TO_OPEN, quantity=1),
        ],
        target_price=Decimal("0.50"),
    )


class TestPDTCheck:
    def test_passes_when_under_limit(self):
        repo = MagicMock()
        repo.get_day_trade_count.return_value = 2
        check = PDTCheck(repo=repo, pdt_limit=3)
        result = check.check(_make_signal())
        assert result.passed

    def test_fails_when_at_limit(self):
        repo = MagicMock()
        repo.get_day_trade_count.return_value = 3
        check = PDTCheck(repo=repo, pdt_limit=3)
        result = check.check(_make_signal())
        assert not result.passed
        assert "3/3" in result.message


class TestMaxDailyLossCheck:
    def test_passes_when_under_threshold(self):
        check = MaxDailyLossCheck(
            max_daily_loss_pct=Decimal("3.0"),
            current_daily_pnl=Decimal("-50.00"),
            account_value=Decimal("2500.00"),
        )
        result = check.check(_make_signal())
        assert result.passed

    def test_fails_when_over_threshold(self):
        check = MaxDailyLossCheck(
            max_daily_loss_pct=Decimal("3.0"),
            current_daily_pnl=Decimal("-80.00"),
            account_value=Decimal("2500.00"),
        )
        result = check.check(_make_signal())
        assert not result.passed


class TestMaxDrawdownCheck:
    def test_passes_under_threshold(self):
        check = MaxDrawdownCheck(
            max_drawdown_pct=Decimal("10.0"),
            current_drawdown_pct=Decimal("5.0"),
        )
        result = check.check(_make_signal())
        assert result.passed

    def test_fails_over_threshold(self):
        check = MaxDrawdownCheck(
            max_drawdown_pct=Decimal("10.0"),
            current_drawdown_pct=Decimal("12.0"),
        )
        result = check.check(_make_signal())
        assert not result.passed


class TestPositionSizeCheck:
    def test_passes_within_limits(self):
        check = PositionSizeCheck(
            max_risk_per_trade=Decimal("250.00"),
            account_value=Decimal("2500.00"),
        )
        signal = _make_signal()  # 2 legs, $5 wide = $500 max risk for 1 contract
        # But we pass max_risk_per_trade which the check uses
        result = check.check(signal, trade_max_loss=Decimal("200.00"))
        assert result.passed

    def test_fails_over_limit(self):
        check = PositionSizeCheck(
            max_risk_per_trade=Decimal("250.00"),
            account_value=Decimal("2500.00"),
        )
        result = check.check(_make_signal(), trade_max_loss=Decimal("500.00"))
        assert not result.passed


class TestTimeWindowCheck:
    def test_passes_within_window(self):
        check = TimeWindowCheck(earliest=time(9, 45), latest=time(14, 0))
        result = check.check(_make_signal(), current_time=time(10, 30))
        assert result.passed

    def test_fails_before_window(self):
        check = TimeWindowCheck(earliest=time(9, 45), latest=time(14, 0))
        result = check.check(_make_signal(), current_time=time(9, 30))
        assert not result.passed

    def test_fails_after_window(self):
        check = TimeWindowCheck(earliest=time(9, 45), latest=time(14, 0))
        result = check.check(_make_signal(), current_time=time(14, 30))
        assert not result.passed


class TestDuplicateCheck:
    def test_passes_no_existing_position(self):
        check = DuplicateCheck(open_symbols=set())
        result = check.check(_make_signal())
        assert result.passed

    def test_fails_with_existing_position(self):
        check = DuplicateCheck(open_symbols={"XSP"})
        result = check.check(_make_signal())
        assert not result.passed
