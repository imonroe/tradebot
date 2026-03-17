"""Main entry point for the trading bot."""
import asyncio
import sys
from datetime import date, time
from pathlib import Path

import structlog

from tradebot.core.event_bus import EventBus
from tradebot.core.events import FillEvent, MarketEvent, OrderEvent, SignalEvent
from tradebot.data.handler import MarketDataHandler
from tradebot.data.sources.tradier import TradierDataSource
from tradebot.execution.brokers.tradier import TradierBroker
from tradebot.execution.order_manager import OrderManager
from tradebot.portfolio.tracker import PortfolioTracker
from tradebot.risk.checks import (
    DuplicateCheck,
    MaxDailyLossCheck,
    MaxDrawdownCheck,
    TimeWindowCheck,
)
from tradebot.risk.manager import RiskManager
from tradebot.strategy.registry import load_strategy
from tradebot.utils.config import Settings
from tradebot.utils.logging import setup_logging

logger = structlog.get_logger()


async def run_bot(settings: Settings) -> None:
    """Run the trading bot main loop."""
    mode_banner = "PAPER" if settings.mode == "paper" else "LIVE"
    logger.info(f">>> {mode_banner} MODE <<<")

    if settings.mode == "live" and "--confirm-live" not in sys.argv:
        logger.critical("Live mode requires --confirm-live flag. Exiting.")
        return

    # Initialize broker
    broker = TradierBroker(
        base_url=settings.broker_base_url,
        api_token=settings.tradier_api_token,
    )

    # Initialize components
    data_source = TradierDataSource(broker)
    market_data = MarketDataHandler(data_source)
    order_manager = OrderManager(broker)
    portfolio = PortfolioTracker(starting_capital=settings.starting_capital)
    risk_manager = RiskManager()

    # Wire risk checks
    risk_manager.add_check(TimeWindowCheck(
        earliest=time(9, 45), latest=time(14, 0),
    ))
    risk_manager.add_check(MaxDailyLossCheck(
        max_daily_loss_pct=settings.max_daily_loss_pct,
        current_daily_pnl=portfolio.daily_pnl,
        account_value=portfolio.nav,
    ))
    risk_manager.add_check(MaxDrawdownCheck(
        max_drawdown_pct=settings.max_drawdown_pct,
        current_drawdown_pct=portfolio.drawdown_pct,
    ))
    risk_manager.add_check(DuplicateCheck(open_symbols=set()))

    # Load strategies from config/strategies/
    project_root = Path(__file__).resolve().parent.parent.parent
    strategies_dir = project_root / "config" / "strategies"
    strategies = []
    if strategies_dir.exists():
        for config_file in strategies_dir.glob("*.yaml"):
            try:
                strategy = load_strategy(config_file)
                strategies.append(strategy)
                logger.info("strategy_loaded", name=strategy.name, file=str(config_file))
            except Exception as e:
                logger.error("strategy_load_failed", file=str(config_file), error=str(e))

    # Wire event bus
    bus = EventBus()

    async def on_market(event: MarketEvent) -> list:
        signals = []
        for strategy in strategies:
            signals.extend(strategy.evaluate(event))
        return signals

    bus.register_handler(MarketEvent, on_market)
    bus.register_handler(SignalEvent, risk_manager.on_signal)
    bus.register_handler(OrderEvent, order_manager.on_order)
    bus.register_handler(FillEvent, portfolio.on_fill)

    # Event observer for logging
    async def log_observer(event):
        logger.debug("event", type=type(event).__name__)

    bus.add_observer(log_observer)

    # Main polling loop
    logger.info("bot_started", strategies=len(strategies))
    shutdown = asyncio.Event()

    try:
        while not shutdown.is_set():
            for strategy in strategies:
                try:
                    today = date.today()
                    event = await market_data.fetch_market_data(strategy.symbol, today)
                    await bus.publish(event)
                except Exception as e:
                    logger.error("market_data_error", symbol=strategy.symbol, error=str(e))

            # Process all queued events
            while await bus.process_one():
                pass

            # Wait before next poll
            await asyncio.sleep(60)  # Poll every 60 seconds
    except KeyboardInterrupt:
        logger.info("bot_shutdown_requested")
    finally:
        logger.info("bot_stopped")


def main() -> None:
    """CLI entry point."""
    setup_logging()
    settings = Settings()
    asyncio.run(run_bot(settings))


if __name__ == "__main__":
    main()
