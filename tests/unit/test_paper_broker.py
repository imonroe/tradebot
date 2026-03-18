"""Tests for paper broker."""
from datetime import date
from decimal import Decimal

import pytest

from tradebot.core.enums import OrderSide, OrderStatus
from tradebot.core.models import OrderLeg
from tradebot.execution.brokers.paper import PaperBroker


@pytest.fixture
def broker():
    return PaperBroker(starting_balance=Decimal("2500.00"))


async def test_get_account_returns_starting_balance(broker):
    account = await broker.get_account()
    assert account.balance == Decimal("2500.00")
    assert account.buying_power == Decimal("2500.00")
    assert account.day_trade_count == 0


async def test_get_positions_initially_empty(broker):
    positions = await broker.get_positions()
    assert positions == []


async def test_submit_multileg_order_fills_immediately(broker):
    legs = [
        OrderLeg(option_symbol="XSP260317P00560000", side=OrderSide.SELL_TO_OPEN, quantity=1),
        OrderLeg(option_symbol="XSP260317P00555000", side=OrderSide.BUY_TO_OPEN, quantity=1),
    ]
    result = await broker.submit_multileg_order(legs=legs, price=Decimal("0.50"))
    assert result.status == OrderStatus.FILLED
    assert result.broker_order_id.startswith("PAPER-")


async def test_submit_multileg_order_adjusts_balance(broker):
    legs = [
        OrderLeg(option_symbol="XSP260317P00560000", side=OrderSide.SELL_TO_OPEN, quantity=1),
        OrderLeg(option_symbol="XSP260317P00555000", side=OrderSide.BUY_TO_OPEN, quantity=1),
    ]
    await broker.submit_multileg_order(legs=legs, price=Decimal("0.50"))
    account = await broker.get_account()
    # Credit of $0.50 * 100 shares = $50
    assert account.balance == Decimal("2550.00")


async def test_submit_multileg_order_adds_positions(broker):
    legs = [
        OrderLeg(option_symbol="XSP260317P00560000", side=OrderSide.SELL_TO_OPEN, quantity=1),
        OrderLeg(option_symbol="XSP260317P00555000", side=OrderSide.BUY_TO_OPEN, quantity=1),
    ]
    await broker.submit_multileg_order(legs=legs, price=Decimal("0.50"))
    positions = await broker.get_positions()
    assert len(positions) == 2
    symbols = {p["symbol"] for p in positions}
    assert "XSP260317P00560000" in symbols
    assert "XSP260317P00555000" in symbols


async def test_submit_order_delegates_to_multileg(broker):
    leg = OrderLeg(option_symbol="XSP260317C00580000", side=OrderSide.BUY_TO_OPEN, quantity=1)
    result = await broker.submit_order(leg=leg, price=Decimal("1.20"))
    assert result.status == OrderStatus.FILLED
    positions = await broker.get_positions()
    assert len(positions) == 1


async def test_get_order_status(broker):
    legs = [
        OrderLeg(option_symbol="XSP260317P00560000", side=OrderSide.SELL_TO_OPEN, quantity=1),
    ]
    result = await broker.submit_multileg_order(legs=legs, price=Decimal("0.30"))
    status = await broker.get_order_status(result.broker_order_id)
    assert status == "filled"


async def test_cancel_order(broker):
    legs = [
        OrderLeg(option_symbol="XSP260317P00560000", side=OrderSide.SELL_TO_OPEN, quantity=1),
    ]
    result = await broker.submit_multileg_order(legs=legs, price=Decimal("0.30"))
    await broker.cancel_order(result.broker_order_id)
    status = await broker.get_order_status(result.broker_order_id)
    assert status == "cancelled"


async def test_get_options_chain_raises(broker):
    with pytest.raises(NotImplementedError):
        await broker.get_options_chain("XSP", date(2026, 3, 17))


async def test_order_ids_increment(broker):
    leg = OrderLeg(option_symbol="XSP260317C00580000", side=OrderSide.BUY_TO_OPEN, quantity=1)
    r1 = await broker.submit_multileg_order([leg], Decimal("1.00"))
    r2 = await broker.submit_multileg_order([leg], Decimal("1.00"))
    assert r1.broker_order_id != r2.broker_order_id
