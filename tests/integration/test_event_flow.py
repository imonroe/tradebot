"""Integration test: full event pipeline with mocked broker."""
from datetime import date, datetime, time
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from tradebot.core.enums import OptionType, OrderStatus, SpreadType
from tradebot.core.event_bus import EventBus
from tradebot.core.events import MarketEvent
from tradebot.core.models import (
    Bar,
    Greeks,
    OptionContract,
    OptionsChain,
    OrderResult,
)
from tradebot.execution.order_manager import OrderManager
from tradebot.portfolio.tracker import PortfolioTracker
from tradebot.risk.checks import DuplicateCheck, TimeWindowCheck
from tradebot.risk.manager import RiskManager
from tradebot.strategy.strategies.iron_condor import IronCondorStrategy


def _make_chain() -> OptionsChain:
    def opt(sym, otype, strike, delta, bid, ask):
        return OptionContract(
            symbol=sym,
            underlying="XSP",
            option_type=otype,
            strike=Decimal(str(strike)),
            expiration=date(2026, 3, 16),
            bid=Decimal(str(bid)),
            ask=Decimal(str(ask)),
            last=Decimal(str((bid + ask) / 2)),
            volume=100,
            open_interest=500,
            greeks=Greeks(
                delta=Decimal(str(delta)),
                gamma=Decimal("0.05"),
                theta=Decimal("-0.10"),
                vega=Decimal("0.08"),
                implied_volatility=Decimal("0.20"),
            ),
        )

    return OptionsChain(
        underlying="XSP",
        expiration=date(2026, 3, 16),
        underlying_price=Decimal("570.00"),
        calls=[
            opt("XSP_C580", OptionType.CALL, 580, 0.15, 0.80, 1.00),
            opt("XSP_C585", OptionType.CALL, 585, 0.08, 0.30, 0.45),
        ],
        puts=[
            opt("XSP_P555", OptionType.PUT, 555, -0.08, 0.25, 0.40),
            opt("XSP_P560", OptionType.PUT, 560, -0.15, 0.70, 0.90),
        ],
    )


@pytest.mark.asyncio
async def test_full_pipeline_market_to_fill():
    """MarketEvent → Strategy → Risk → Order → Fill → Portfolio"""
    # Setup components
    strategy = IronCondorStrategy(
        name="test_ic",
        symbol="XSP",
        short_call_delta=Decimal("0.15"),
        short_put_delta=Decimal("-0.15"),
        wing_width=Decimal("5"),
        min_credit=Decimal("0.10"),
        entry_earliest=time(9, 0),
        entry_latest=time(15, 0),
    )

    risk_manager = RiskManager()
    risk_manager.add_check(TimeWindowCheck(earliest=time(0, 0), latest=time(23, 59, 59)))
    risk_manager.add_check(DuplicateCheck(open_symbols=set()))

    broker = AsyncMock()
    broker.submit_multileg_order.return_value = OrderResult(
        broker_order_id="ord_integration_test",
        status=OrderStatus.FILLED,
    )
    order_manager = OrderManager(broker=broker)
    portfolio = PortfolioTracker(starting_capital=Decimal("2500.00"))

    # Wire up event bus
    bus = EventBus()

    async def on_market(event: MarketEvent) -> list:
        return strategy.evaluate(event)

    bus.register_handler(MarketEvent, on_market)

    # Manual pipeline test (not using bus dispatch for clarity)
    bar = Bar(
        symbol="XSP",
        timestamp=datetime(2026, 3, 16, 10, 30),
        open=Decimal("570"),
        high=Decimal("572"),
        low=Decimal("569"),
        close=Decimal("571"),
        volume=5000,
    )
    market_event = MarketEvent(bar=bar, options_chain=_make_chain())

    # Step 1: Strategy evaluates
    signals = strategy.evaluate(market_event)
    assert len(signals) == 1, "Strategy should produce one signal"
    assert signals[0].spread_type == SpreadType.IRON_CONDOR

    # Step 2: Risk manager checks
    risk_events = await risk_manager.on_signal(signals[0])
    order_events = [e for e in risk_events if hasattr(e, "signal")]
    assert len(order_events) == 1, "Risk manager should approve the signal"

    # Step 3: Order manager submits
    fill_events = await order_manager.on_order(order_events[0])
    assert len(fill_events) == 1
    assert fill_events[0].status == OrderStatus.FILLED

    # Step 4: Portfolio records
    await portfolio.on_fill(fill_events[0])
    assert len(portfolio.open_positions) == 1
