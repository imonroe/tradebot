"""Main entry point for the trading bot."""
import asyncio
import sys
from datetime import date, time
from pathlib import Path

import structlog
import uvicorn

from tradebot.api.app import create_app
from tradebot.api.state import AppState
from tradebot.core.event_bus import EventBus
from tradebot.core.events import FillEvent, MarketEvent, OrderEvent, SignalEvent
from tradebot.data.handler import MarketDataHandler
from tradebot.data.sources.tradier import TradierDataSource
from tradebot.execution.brokers.tradier import TradierBroker
from tradebot.execution.order_manager import OrderManager
from tradebot.persistence.database import Base, create_db_engine, create_session
from tradebot.persistence.repository import Repository
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


async def bot_loop(
    state: AppState,
    market_data: MarketDataHandler,
    bus: EventBus,
    shutdown: asyncio.Event,
) -> None:
    """Run the trading bot polling loop."""
    state.bot_running = True
    logger.info("bot_loop_started", strategies=len(state.strategies))

    try:
        while not shutdown.is_set():
            for strategy in state.strategies:
                try:
                    today = date.today()
                    event = await market_data.fetch_market_data(strategy.symbol, today)
                    await bus.publish(event)
                except Exception as e:
                    logger.error("market_data_error", symbol=strategy.symbol, error=str(e))

            while await bus.process_one():
                pass

            # Broadcast portfolio update to WebSocket clients
            try:
                ws_manager = state.ws_manager
                if ws_manager and ws_manager.connection_count > 0:
                    await ws_manager.broadcast({
                        "type": "update",
                        "nav": str(state.portfolio.nav),
                        "daily_pnl": str(state.portfolio.daily_pnl),
                        "drawdown_pct": str(state.portfolio.drawdown_pct),
                        "positions": len(state.portfolio.open_positions),
                        "bot_running": state.bot_running,
                        "pdt_day_trades_used": state.pdt_day_trades_used,
                    })
            except Exception:
                pass

            try:
                await asyncio.wait_for(shutdown.wait(), timeout=60)
            except asyncio.TimeoutError:
                pass
    finally:
        state.bot_running = False
        logger.info("bot_loop_stopped")


async def run_bot(settings: Settings) -> None:
    """Run the trading bot and API server."""
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

    # Initialize database
    engine = create_db_engine(settings.database_url)
    Base.metadata.create_all(engine)
    session = create_session(engine)
    repo = Repository(session)

    # Initialize components
    data_source = TradierDataSource(broker)
    market_data = MarketDataHandler(data_source)
    order_manager = OrderManager(broker)
    portfolio = PortfolioTracker(starting_capital=settings.starting_capital)
    risk_manager = RiskManager()

    # Wire risk checks
    risk_manager.add_check(TimeWindowCheck(earliest=time(9, 45), latest=time(14, 0)))
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

    # Load strategies
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

    # Create shared state
    state = AppState(
        portfolio=portfolio,
        strategies=strategies,
        mode=settings.mode,
        repository=repo,
    )

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

    async def log_observer(event):
        logger.debug("event", type=type(event).__name__)

    bus.add_observer(log_observer)

    # Create FastAPI app
    app = create_app(state)
    state.ws_manager = app.state.ws_manager

    # Run API server and bot loop concurrently
    shutdown = asyncio.Event()

    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config)

    try:
        await asyncio.gather(
            server.serve(),
            bot_loop(state, market_data, bus, shutdown),
        )
    except KeyboardInterrupt:
        shutdown.set()


def main() -> None:
    """CLI entry point."""
    setup_logging()
    settings = Settings()
    asyncio.run(run_bot(settings))


if __name__ == "__main__":
    main()
