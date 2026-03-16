"""Tests for order management."""
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from tradebot.core.enums import OrderSide, OrderStatus, SpreadType
from tradebot.core.events import FillEvent, OrderEvent, SignalEvent
from tradebot.core.models import OrderLeg, OrderResult
from tradebot.execution.order_manager import OrderManager


def _make_order_event() -> OrderEvent:
    signal = SignalEvent(
        strategy_name="test",
        spread_type=SpreadType.CREDIT_SPREAD,
        symbol="XSP",
        legs=[
            OrderLeg(option_symbol="XSP250316P00565000", side=OrderSide.SELL_TO_OPEN, quantity=1),
            OrderLeg(option_symbol="XSP250316P00560000", side=OrderSide.BUY_TO_OPEN, quantity=1),
        ],
        target_price=Decimal("0.50"),
    )
    return OrderEvent(signal=signal)


@pytest.mark.asyncio
async def test_on_order_submits_to_broker():
    broker = AsyncMock()
    broker.submit_multileg_order.return_value = OrderResult(
        broker_order_id="ord_456",
        status=OrderStatus.FILLED,
    )
    manager = OrderManager(broker=broker)
    events = await manager.on_order(_make_order_event())

    broker.submit_multileg_order.assert_called_once()
    assert len(events) == 1
    assert isinstance(events[0], FillEvent)
    assert events[0].broker_order_id == "ord_456"
    assert events[0].fill_price == Decimal("0.50")


@pytest.mark.asyncio
async def test_on_order_handles_rejection():
    broker = AsyncMock()
    broker.submit_multileg_order.return_value = OrderResult(
        broker_order_id="ord_789",
        status=OrderStatus.REJECTED,
    )
    manager = OrderManager(broker=broker)
    events = await manager.on_order(_make_order_event())

    # Rejected orders still produce a FillEvent with rejected status
    assert len(events) == 1
    assert events[0].status == OrderStatus.REJECTED
