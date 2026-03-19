"""Tests for HistoricalDataSource."""
from datetime import date, datetime
from decimal import Decimal

import pytest

from tradebot.backtest.clock import SimulatedClock
from tradebot.backtest.data_source import HistoricalDataSource
from tradebot.data.sources.paper import PaperDataSource


@pytest.mark.asyncio
async def test_market_event_uses_simulated_time():
    clock = SimulatedClock(start=datetime(2026, 1, 15, 10, 30))
    source = PaperDataSource(base_price=Decimal("570"), seed=42)
    hist = HistoricalDataSource(source=source, clock=clock)

    event = await hist.get_market_event("XSP", date(2026, 1, 15))
    assert event.bar.timestamp == datetime(2026, 1, 15, 10, 30)
    assert event.bar.symbol == "XSP"
    assert event.options_chain is not None


@pytest.mark.asyncio
async def test_advancing_clock_changes_bar_timestamp():
    clock = SimulatedClock(start=datetime(2026, 1, 15, 10, 30))
    source = PaperDataSource(base_price=Decimal("570"), seed=42)
    hist = HistoricalDataSource(source=source, clock=clock)

    event1 = await hist.get_market_event("XSP", date(2026, 1, 15))
    assert event1.bar.timestamp == datetime(2026, 1, 15, 10, 30)

    clock.advance_to(datetime(2026, 1, 15, 10, 45))
    event2 = await hist.get_market_event("XSP", date(2026, 1, 15))
    assert event2.bar.timestamp == datetime(2026, 1, 15, 10, 45)


@pytest.mark.asyncio
async def test_market_event_has_options_chain_with_contracts():
    clock = SimulatedClock(start=datetime(2026, 1, 15, 10, 30))
    source = PaperDataSource(base_price=Decimal("570"), seed=42)
    hist = HistoricalDataSource(source=source, clock=clock)

    event = await hist.get_market_event("XSP", date(2026, 1, 15))
    assert len(event.options_chain.calls) > 0
    assert len(event.options_chain.puts) > 0
