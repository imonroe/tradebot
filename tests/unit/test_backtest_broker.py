"""Tests for BacktestBroker and BacktestTimeWindowCheck."""
from datetime import date, datetime, time
from decimal import Decimal

import pytest

from tradebot.backtest.broker import BacktestBroker
from tradebot.backtest.clock import SimulatedClock
from tradebot.backtest.risk import BacktestTimeWindowCheck
from tradebot.core.enums import OptionType, OrderSide, SpreadType
from tradebot.core.events import SignalEvent
from tradebot.core.models import Greeks, OptionContract, OptionsChain, OrderLeg


def _make_chain(underlying_price: Decimal = Decimal("570")) -> OptionsChain:
    calls = [
        OptionContract(
            symbol="XSP260115C00575000", underlying="XSP",
            option_type=OptionType.CALL, strike=Decimal("575"),
            expiration=date(2026, 1, 15),
            bid=Decimal("0.80"), ask=Decimal("1.00"), last=Decimal("0.90"),
            volume=100, open_interest=500,
            greeks=Greeks(delta=Decimal("0.15"), gamma=Decimal("0.05"),
                         theta=Decimal("-0.10"), vega=Decimal("0.08"),
                         implied_volatility=Decimal("0.20")),
        ),
        OptionContract(
            symbol="XSP260115C00580000", underlying="XSP",
            option_type=OptionType.CALL, strike=Decimal("580"),
            expiration=date(2026, 1, 15),
            bid=Decimal("0.30"), ask=Decimal("0.45"), last=Decimal("0.37"),
            volume=100, open_interest=500,
            greeks=Greeks(delta=Decimal("0.08"), gamma=Decimal("0.03"),
                         theta=Decimal("-0.05"), vega=Decimal("0.04"),
                         implied_volatility=Decimal("0.22")),
        ),
    ]
    return OptionsChain(
        underlying="XSP", expiration=date(2026, 1, 15),
        underlying_price=underlying_price, calls=calls, puts=[],
    )


@pytest.mark.asyncio
async def test_fills_at_market_price_when_chain_available():
    broker = BacktestBroker(starting_balance=Decimal("2500"))
    chain = _make_chain()
    broker.update_market_data(chain)
    # Sell 575 call (bid=0.80), buy 580 call (ask=0.45) = net credit 0.35
    legs = [
        OrderLeg(option_symbol="XSP260115C00575000", side=OrderSide.SELL_TO_OPEN, quantity=1),
        OrderLeg(option_symbol="XSP260115C00580000", side=OrderSide.BUY_TO_OPEN, quantity=1),
    ]
    await broker.submit_multileg_order(legs, price=Decimal("0.50"))
    account = await broker.get_account()
    # Expected: 2500 + 0.35 * 100 = 2535 (bid/ask fill, not target price 0.50)
    assert account.balance == Decimal("2535.00")


@pytest.mark.asyncio
async def test_falls_back_to_target_price_without_chain():
    broker = BacktestBroker(starting_balance=Decimal("2500"))
    legs = [
        OrderLeg(option_symbol="XSP260115C00575000", side=OrderSide.SELL_TO_OPEN, quantity=1),
    ]
    await broker.submit_multileg_order(legs, price=Decimal("0.50"))
    account = await broker.get_account()
    assert account.balance == Decimal("2500") + Decimal("0.50") * 100


@pytest.mark.asyncio
async def test_slippage_applied():
    broker = BacktestBroker(starting_balance=Decimal("2500"), slippage_pct=Decimal("10"))
    chain = _make_chain()
    broker.update_market_data(chain)
    # Sell 575 call: bid=0.80, 10% slippage = 0.80 * 0.90 = 0.72
    legs = [
        OrderLeg(option_symbol="XSP260115C00575000", side=OrderSide.SELL_TO_OPEN, quantity=1),
    ]
    await broker.submit_multileg_order(legs, price=Decimal("0.50"))
    account = await broker.get_account()
    assert account.balance == Decimal("2500") + Decimal("0.72") * 100


def test_backtest_time_window_uses_simulated_clock():
    clock = SimulatedClock(start=datetime(2026, 1, 15, 10, 30))
    check = BacktestTimeWindowCheck(earliest=time(9, 45), latest=time(14, 0), clock=clock)
    signal = SignalEvent(
        strategy_name="test", spread_type=SpreadType.CREDIT_SPREAD,
        symbol="XSP", legs=[], target_price=Decimal("0.50"),
    )
    result = check.check(signal)
    assert result.passed is True  # 10:30 is within 9:45-14:00


def test_backtest_time_window_rejects_outside_hours():
    clock = SimulatedClock(start=datetime(2026, 1, 15, 15, 30))
    check = BacktestTimeWindowCheck(earliest=time(9, 45), latest=time(14, 0), clock=clock)
    signal = SignalEvent(
        strategy_name="test", spread_type=SpreadType.CREDIT_SPREAD,
        symbol="XSP", legs=[], target_price=Decimal("0.50"),
    )
    result = check.check(signal)
    assert result.passed is False  # 15:30 is outside 9:45-14:00
