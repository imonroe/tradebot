"""Integration test: full pipeline with paper broker and synthetic data."""
from datetime import date, time
from decimal import Decimal

from tradebot.core.event_bus import EventBus
from tradebot.core.events import FillEvent, MarketEvent, OrderEvent, SignalEvent
from tradebot.data.handler import MarketDataHandler
from tradebot.data.sources.paper import PaperDataSource
from tradebot.execution.brokers.paper import PaperBroker
from tradebot.execution.order_manager import OrderManager
from tradebot.portfolio.tracker import PortfolioTracker
from tradebot.risk.checks import DuplicateCheck, TimeWindowCheck
from tradebot.risk.manager import RiskManager
from tradebot.strategy.strategies.iron_condor import IronCondorStrategy


async def test_paper_pipeline_end_to_end():
    """Full pipeline: synthetic data -> strategy -> risk -> paper broker -> portfolio."""
    # Setup components
    data_source = PaperDataSource(base_price=Decimal("570.00"), seed=42)
    broker = PaperBroker(starting_balance=Decimal("2500.00"))
    market_data = MarketDataHandler(data_source)
    order_manager = OrderManager(broker)
    portfolio = PortfolioTracker(starting_capital=Decimal("2500.00"))

    # Use 0.40/-0.40 deltas with narrow wings because the synthetic chain only
    # spans +/-20 strikes. Wider deltas (0.15) or larger wings (5) would require
    # strikes outside that range.
    strategy = IronCondorStrategy(
        name="test_paper_ic",
        symbol="XSP",
        short_call_delta=Decimal("0.40"),
        short_put_delta=Decimal("-0.40"),
        wing_width=Decimal("3"),
        min_credit=Decimal("0.01"),
        entry_earliest=time(0, 0),
        entry_latest=time(23, 59, 59),
    )

    risk_manager = RiskManager()
    risk_manager.add_check(TimeWindowCheck(earliest=time(0, 0), latest=time(23, 59, 59)))
    risk_manager.add_check(DuplicateCheck(open_symbols=set()))

    # Wire event bus
    bus = EventBus()

    async def on_market(event: MarketEvent) -> list:
        return strategy.evaluate(event)

    bus.register_handler(MarketEvent, on_market)
    bus.register_handler(SignalEvent, risk_manager.on_signal)
    bus.register_handler(OrderEvent, order_manager.on_order)
    bus.register_handler(FillEvent, portfolio.on_fill)

    # Fetch synthetic market data and publish
    event = await market_data.fetch_market_data("XSP", date.today())
    await bus.publish(event)

    # Process all events through the pipeline
    while await bus.process_one():
        pass

    # Verify the pipeline produced a trade
    assert len(portfolio.open_positions) == 1
    position = portfolio.open_positions[0]
    assert position["strategy"] == "test_paper_ic"
    assert position["symbol"] == "XSP"

    # Verify broker state
    account = await broker.get_account()
    # Balance should have changed (credit received from iron condor)
    assert account.balance != Decimal("2500.00")

    positions = await broker.get_positions()
    # Iron condor has 4 legs
    assert len(positions) == 4
