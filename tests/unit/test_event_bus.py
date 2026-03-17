"""Tests for the event system."""
from datetime import datetime
from decimal import Decimal
import pytest
from tradebot.core.enums import OrderSide, SpreadType
from tradebot.core.events import MarketEvent, SignalEvent, RiskEvent
from tradebot.core.event_bus import EventBus
from tradebot.core.models import Bar, OrderLeg

def test_market_event_creation():
    bar = Bar(symbol="XSP", timestamp=datetime(2026, 3, 16, 10, 0),
        open=Decimal("570"), high=Decimal("572"),
        low=Decimal("569"), close=Decimal("571"), volume=1000)
    event = MarketEvent(bar=bar)
    assert event.bar.symbol == "XSP"

def test_signal_event_creation():
    legs = [
        OrderLeg(option_symbol="XSP250316C00580000", side=OrderSide.SELL_TO_OPEN, quantity=1),
        OrderLeg(option_symbol="XSP250316C00585000", side=OrderSide.BUY_TO_OPEN, quantity=1),
    ]
    event = SignalEvent(strategy_name="xsp_credit_spread", spread_type=SpreadType.CREDIT_SPREAD,
        symbol="XSP", legs=legs, target_price=Decimal("0.50"))
    assert event.strategy_name == "xsp_credit_spread"
    assert len(event.legs) == 2

def test_risk_event_creation():
    event = RiskEvent(check_name="PDTCheck", passed=False, message="PDT limit reached: 3/3 day trades used")
    assert not event.passed

@pytest.mark.asyncio
async def test_event_bus_dispatch():
    bus = EventBus()
    received = []
    async def on_market(event: MarketEvent) -> list:
        received.append(("market", event))
        return []
    bus.register_handler(MarketEvent, on_market)
    bar = Bar(symbol="XSP", timestamp=datetime(2026, 3, 16, 10, 0),
        open=Decimal("570"), high=Decimal("572"), low=Decimal("569"), close=Decimal("571"), volume=1000)
    await bus.publish(MarketEvent(bar=bar))
    await bus.process_one()
    assert len(received) == 1
    assert received[0][0] == "market"

@pytest.mark.asyncio
async def test_event_bus_observers():
    bus = EventBus()
    observed = []
    async def observer(event):
        observed.append(type(event).__name__)
    async def handler(event) -> list:
        return []
    bus.add_observer(observer)
    bus.register_handler(MarketEvent, handler)
    bar = Bar(symbol="XSP", timestamp=datetime(2026, 3, 16, 10, 0),
        open=Decimal("570"), high=Decimal("572"), low=Decimal("569"), close=Decimal("571"), volume=1000)
    await bus.publish(MarketEvent(bar=bar))
    await bus.process_one()
    assert observed == ["MarketEvent"]

@pytest.mark.asyncio
async def test_event_bus_handler_produces_new_events():
    bus = EventBus()
    results = []
    async def on_market(event: MarketEvent) -> list:
        return [RiskEvent(check_name="test", passed=True, message="ok")]
    async def on_risk(event: RiskEvent) -> list:
        results.append(event.message)
        return []
    bus.register_handler(MarketEvent, on_market)
    bus.register_handler(RiskEvent, on_risk)
    bar = Bar(symbol="XSP", timestamp=datetime(2026, 3, 16, 10, 0),
        open=Decimal("570"), high=Decimal("572"), low=Decimal("569"), close=Decimal("571"), volume=1000)
    await bus.publish(MarketEvent(bar=bar))
    await bus.process_one()  # processes MarketEvent, queues RiskEvent
    await bus.process_one()  # processes RiskEvent
    assert results == ["ok"]
