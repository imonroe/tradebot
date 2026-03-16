"""Tests for portfolio tracking."""
from decimal import Decimal

import pytest

from tradebot.core.enums import OrderSide, OrderStatus, SpreadType
from tradebot.core.events import FillEvent, SignalEvent
from tradebot.core.models import OrderLeg
from tradebot.portfolio.tracker import PortfolioTracker


@pytest.fixture
def tracker():
    return PortfolioTracker(starting_capital=Decimal("2500.00"))


def _make_fill(
    price: Decimal = Decimal("0.50"),
    strategy: str = "test",
    spread_type: SpreadType = SpreadType.CREDIT_SPREAD,
) -> FillEvent:
    signal = SignalEvent(
        strategy_name=strategy,
        spread_type=spread_type,
        symbol="XSP",
        legs=[
            OrderLeg(option_symbol="XSP250316P00565000", side=OrderSide.SELL_TO_OPEN, quantity=1),
            OrderLeg(option_symbol="XSP250316P00560000", side=OrderSide.BUY_TO_OPEN, quantity=1),
        ],
        target_price=price,
    )
    return FillEvent(
        broker_order_id="ord_123",
        signal=signal,
        fill_price=price,
        status=OrderStatus.FILLED,
    )


def test_initial_state(tracker):
    assert tracker.nav == Decimal("2500.00")
    assert tracker.daily_pnl == Decimal("0")
    assert len(tracker.open_positions) == 0


def test_record_fill_opens_position(tracker):
    fill = _make_fill(Decimal("0.50"))
    tracker.record_fill(fill)
    assert len(tracker.open_positions) == 1
    assert tracker.open_positions[0]["fill_price"] == Decimal("0.50")


def test_daily_pnl_tracking(tracker):
    tracker.record_realized_pnl(Decimal("30.00"))
    assert tracker.daily_pnl == Decimal("30.00")
    tracker.record_realized_pnl(Decimal("-10.00"))
    assert tracker.daily_pnl == Decimal("20.00")


def test_nav_updates_with_pnl(tracker):
    tracker.record_realized_pnl(Decimal("50.00"))
    assert tracker.nav == Decimal("2550.00")


def test_drawdown_calculation(tracker):
    assert tracker.drawdown_pct == Decimal("0")
    tracker.record_realized_pnl(Decimal("100.00"))  # NAV = 2600, peak = 2600
    tracker.record_realized_pnl(Decimal("-150.00"))  # NAV = 2450, peak = 2600
    expected = (Decimal("2600") - Decimal("2450")) / Decimal("2600") * 100
    assert tracker.drawdown_pct == expected


def test_reset_daily(tracker):
    tracker.record_realized_pnl(Decimal("50.00"))
    tracker.reset_daily()
    assert tracker.daily_pnl == Decimal("0")
    assert tracker.nav == Decimal("2550.00")  # NAV persists
