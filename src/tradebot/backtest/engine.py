"""Backtesting engine."""
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path

import exchange_calendars as xcals
import structlog

from tradebot.backtest.broker import BacktestBroker
from tradebot.backtest.clock import SimulatedClock
from tradebot.backtest.data_source import HistoricalDataSource
from tradebot.backtest.results import BacktestResult, compute_metrics
from tradebot.backtest.risk import BacktestTimeWindowCheck
from tradebot.core.event_bus import EventBus
from tradebot.core.events import FillEvent, MarketEvent, OrderEvent, SignalEvent
from tradebot.data.sources.paper import PaperDataSource
from tradebot.execution.order_manager import OrderManager
from tradebot.portfolio.tracker import PortfolioTracker
from tradebot.risk.checks import MaxDailyLossCheck, MaxDrawdownCheck
from tradebot.risk.manager import RiskManager
from tradebot.strategy.registry import load_strategy

logger = structlog.get_logger()


def _generate_timestamps(
    start_date: date,
    end_date: date,
    interval_minutes: int,
) -> list[datetime]:
    """Generate simulation timestamps for each NYSE trading day."""
    nyse = xcals.get_calendar("XNYS")
    sessions = nyse.sessions_in_range(
        start_date.isoformat(), end_date.isoformat()
    )

    timestamps = []
    market_open = time(9, 30)
    market_close = time(16, 0)

    for session in sessions:
        trading_date = session.date()
        current = datetime.combine(trading_date, market_open)
        end = datetime.combine(trading_date, market_close)

        while current <= end:
            timestamps.append(current)
            current += timedelta(minutes=interval_minutes)

    return timestamps


def _expire_positions(
    portfolio: PortfolioTracker,
    trades: list[dict],
    trade_date: date,
) -> None:
    """Close all open positions at end of day (0DTE expiry).

    For credit strategies (positive fill_price): full win = credit * 100.
    For debit strategies (negative fill_price): full loss = debit * 100.
    Phase 1 simplification: assumes all positions expire OTM (worthless).
    """
    for pos in list(portfolio.open_positions):
        fill_price = pos["fill_price"]
        pnl = fill_price * 100
        portfolio.close_position(pos["broker_order_id"], pnl)
        trades.append({
            "date": trade_date.isoformat(),
            "strategy": pos["strategy"],
            "symbol": pos["symbol"],
            "spread_type": pos["spread_type"],
            "entry_price": str(fill_price),
            "pnl": pnl,
        })


async def run_backtest(
    strategy_config_path: Path,
    start_date: date,
    end_date: date,
    interval_minutes: int = 15,
    starting_capital: Decimal = Decimal("2500"),
    slippage_pct: Decimal = Decimal("0"),
) -> BacktestResult:
    """Run a backtest and return results."""
    # Load strategy
    strategy = load_strategy(strategy_config_path)
    strategy_name = strategy.name

    # Initialize components
    clock = SimulatedClock(start=datetime.combine(start_date, time(9, 30)))
    paper_source = PaperDataSource(base_price=Decimal("570"), seed=42)
    data_source = HistoricalDataSource(source=paper_source, clock=clock)
    broker = BacktestBroker(starting_balance=starting_capital, slippage_pct=slippage_pct)
    portfolio = PortfolioTracker(starting_capital=starting_capital)
    order_manager = OrderManager(broker)

    # Risk manager with portfolio references and simulated clock
    risk_manager = RiskManager()
    risk_manager.add_check(BacktestTimeWindowCheck(
        earliest=time(9, 45), latest=time(14, 0), clock=clock,
    ))
    risk_manager.add_check(MaxDailyLossCheck(
        max_daily_loss_pct=Decimal("3.0"), portfolio=portfolio,
    ))
    risk_manager.add_check(MaxDrawdownCheck(
        max_drawdown_pct=Decimal("10.0"), portfolio=portfolio,
    ))

    # Wire event bus
    bus = EventBus()

    async def on_market(event: MarketEvent) -> list:
        return strategy.evaluate(event)

    bus.register_handler(MarketEvent, on_market)
    bus.register_handler(SignalEvent, risk_manager.on_signal)
    bus.register_handler(OrderEvent, order_manager.on_order)
    bus.register_handler(FillEvent, portfolio.on_fill)

    # Generate timestamps and run
    timestamps = _generate_timestamps(start_date, end_date, interval_minutes)
    daily_snapshots = []
    trades = []
    current_day = None

    logger.info("backtest_start", strategy=strategy_name,
                start=str(start_date), end=str(end_date),
                timestamps=len(timestamps))

    for ts in timestamps:
        ts_day = ts.date()

        # New day? Close previous day's positions and reset
        if current_day is not None and ts_day != current_day:
            _expire_positions(portfolio, trades, current_day)

            # Record daily snapshot
            daily_snapshots.append({
                "date": current_day.isoformat(),
                "nav": str(portfolio.nav),
                "daily_pnl": str(portfolio.daily_pnl),
                "drawdown": str(portfolio.drawdown_pct),
            })

            # Reset for new day
            portfolio.reset_daily()
            strategy.reset()

        current_day = ts_day

        # Advance clock and fetch data
        clock.advance_to(ts)
        event = await data_source.get_market_event(strategy.symbol, ts_day)

        # Update broker with current chain for realistic fills
        if event.options_chain:
            broker.update_market_data(event.options_chain)

        # Publish and process
        await bus.publish(event)
        while await bus.process_one():
            pass

    # Final day cleanup
    if current_day is not None:
        _expire_positions(portfolio, trades, current_day)

        daily_snapshots.append({
            "date": current_day.isoformat(),
            "nav": str(portfolio.nav),
            "daily_pnl": str(portfolio.daily_pnl),
            "drawdown": str(portfolio.drawdown_pct),
        })

    # Compute metrics
    metrics = compute_metrics(trades)
    total_return = (
        (portfolio.nav - starting_capital) / starting_capital * 100
    )

    result = BacktestResult(
        strategy_name=strategy_name,
        start_date=start_date,
        end_date=end_date,
        starting_capital=starting_capital,
        interval_minutes=interval_minutes,
        ending_nav=portfolio.nav,
        total_return_pct=total_return.quantize(Decimal("0.01")),
        max_drawdown_pct=portfolio.drawdown_pct.quantize(Decimal("0.01")),
        **metrics,
        daily_snapshots=daily_snapshots,
        trades=trades,
    )

    logger.info("backtest_complete", strategy=strategy_name,
                nav=str(portfolio.nav), trades=len(trades))

    return result
