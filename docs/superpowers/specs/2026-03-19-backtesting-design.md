# Backtesting Engine Design Spec

## Overview

A standalone backtesting engine that replays historical market data through the existing event-driven pipeline (strategies, risk checks, portfolio tracker) with explicit time control. Outputs performance metrics to terminal and database.

## Goals

- Test existing strategies (iron condor, credit spread, debit spread) against historical/synthetic data
- Compare strategy performance across different parameter settings
- Reuse existing pipeline components with minimal modifications (see datetime.now() audit)
- CLI-first, but designed so an API endpoint can call the same function later
- Start with synthetic data (PaperDataSource), upgradeable to real historical data

## Non-Goals (for this build)

- Parameter sweep automation (manual config changes for now)
- Dashboard UI for triggering/viewing backtests (future)
- Real historical data loading from Polygon/CBOE (future)
- Commission modeling (can add later via BacktestBroker)

---

## Architecture

```
BacktestEngine
  ├── SimulatedClock         # Controls "now" for the entire system
  ├── HistoricalDataSource   # Serves data at each simulated timestamp
  ├── BacktestBroker         # Fills orders at realistic bid/ask prices
  ├── EventBus               # Same event bus as live (reused as-is)
  ├── Strategies             # Same strategy instances (reused as-is)
  ├── RiskManager            # Risk checks wired with live portfolio refs
  ├── PortfolioTracker       # Same tracker (reused as-is)
  └── ResultsCollector       # Captures trades, snapshots, metrics
```

### Data Flow

For each simulated timestamp:

1. Engine advances `SimulatedClock` to the timestamp
2. Engine calls `HistoricalDataSource.get_market_event()` — returns a `MarketEvent` with the simulated timestamp on the `Bar`
3. Engine updates `BacktestBroker` with current options chain (for realistic fills)
4. Engine publishes `MarketEvent` to `EventBus`
5. Event bus processes: Strategy → SignalEvent → RiskManager → OrderEvent → OrderManager → FillEvent → PortfolioTracker
6. Engine records the portfolio state after processing

At end of each simulated day:
7. Engine records a daily snapshot (NAV, P&L, drawdown)
8. Engine resets strategy position flags for the next day (0DTE positions expire)

After all days:
9. Engine computes aggregate metrics from collected data
10. Engine saves results to database and prints terminal summary

---

## Components

### SimulatedClock (`backtest/clock.py`)

```python
class Clock:
    """Returns current time. Default uses real time."""
    def now(self) -> datetime:
        return datetime.now()

class SimulatedClock(Clock):
    """Manually advanced clock for backtesting."""
    def __init__(self, start: datetime):
        self._now = start

    def now(self) -> datetime:
        return self._now

    def advance_to(self, dt: datetime) -> None:
        self._now = dt
```

Time control rationale: The existing strategies use `event.bar.timestamp.time()` for their own time window checks. However, several other components use `datetime.now()` or `date.today()` — see the datetime.now() Audit section below for the full list and how each is handled.

### HistoricalDataSource (`backtest/data_source.py`)

Wraps any existing `DataSource` (initially `PaperDataSource`) and stamps the resulting data with simulated time.

```python
class HistoricalDataSource:
    def __init__(self, source: DataSource, clock: SimulatedClock):
        self._source = source
        self._clock = clock

    async def get_market_event(self, symbol: str, expiration: date) -> MarketEvent:
        bar = await self._source.get_quote(symbol)
        chain = await self._source.get_options_chain(symbol, expiration)
        # Replace bar timestamp with simulated time
        timed_bar = Bar(
            symbol=bar.symbol,
            timestamp=self._clock.now(),
            open=bar.open, high=bar.high, low=bar.low,
            close=bar.close, volume=bar.volume,
        )
        return MarketEvent(bar=timed_bar, options_chain=chain, timestamp=self._clock.now())
```

Note: `MarketEvent.timestamp` defaults to `datetime.now()`. We must pass the simulated time explicitly so downstream observers see the correct timestamp.

Data source upgrade path:
- Phase 1 (now): `PaperDataSource` — synthetic random-walk data, seeded for reproducibility
- Phase 2: Load recorded JSON from `DataRecorder` — real market snapshots
- Phase 3: Download from Polygon/CBOE — full historical depth

### BacktestBroker (`backtest/broker.py`)

Extends `PaperBroker` with realistic fill behavior.

```python
class BacktestBroker(PaperBroker):
    def __init__(self, starting_balance: Decimal, slippage_pct: Decimal = Decimal("0")):
        super().__init__(starting_balance=starting_balance)
        self._slippage_pct = slippage_pct
        self._current_chain: OptionsChain | None = None

    def update_market_data(self, chain: OptionsChain) -> None:
        """Called by engine before processing signals for this timestamp."""
        self._current_chain = chain

    async def submit_multileg_order(self, legs, price) -> OrderResult:
        # Fill at actual bid/ask from current chain instead of target price
        # Apply slippage if configured
        # Fall back to parent behavior if chain not available
```

Key differences from PaperBroker:
- Fills at actual bid/ask from the options chain, not at the requested target price
- Optional slippage percentage (e.g., 0.5% worse than mid)
- Engine feeds it current market data via `update_market_data()` before each timestamp

### BacktestEngine (`backtest/engine.py`)

Orchestrates the entire run.

```python
async def run_backtest(
    strategy_config_path: Path,
    start_date: date,
    end_date: date,
    interval_minutes: int = 15,
    starting_capital: Decimal = Decimal("2500"),
    slippage_pct: Decimal = Decimal("0"),
) -> BacktestResult:
    """Run a backtest and return results. Called by CLI or API."""
    ...
```

Engine responsibilities:
1. Generate simulation timestamps: for each trading day in range, create timestamps at the configured interval (e.g., 9:30, 9:45, 10:00, ... 15:45, 16:00)
2. Use `exchange_calendars` (already a dependency) to determine valid trading days
3. For each timestamp: advance clock, fetch data, update broker, publish event, drain bus
4. At end of each day: record snapshot, reset strategy `_has_position` flags
5. After all days: compute metrics, build BacktestResult

Trading day detection: Use `exchange_calendars.get_calendar("XNYS")` to get NYSE trading days, skipping weekends and holidays.

### BacktestResult (`backtest/results.py`)

```python
@dataclass
class BacktestResult:
    # Config
    strategy_name: str
    start_date: date
    end_date: date
    starting_capital: Decimal
    interval_minutes: int

    # Performance
    ending_nav: Decimal
    total_return_pct: Decimal
    max_drawdown_pct: Decimal

    # Trade stats
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: Decimal
    avg_win: Decimal
    avg_loss: Decimal
    profit_factor: Decimal        # gross profit / gross loss

    # Daily data
    daily_snapshots: list[dict]   # date, nav, pnl, drawdown
    trades: list[dict]            # entry/exit details

    def print_summary(self) -> None:
        """Print formatted summary to terminal."""
        ...
```

Terminal output format:
```
═══════════════════════════════════════════════════
  Backtest: xsp_0dte_iron_condor
  Period:   2026-01-02 → 2026-03-01 (40 trading days)
  Capital:  $2,500.00 → $2,715.00
═══════════════════════════════════════════════════
  Total Return:    +8.60%
  Max Drawdown:    -3.20%
  Total Trades:    38
  Win Rate:        68.4%  (26W / 12L)
  Avg Win:         $18.50
  Avg Loss:        -$12.30
  Profit Factor:   2.31
═══════════════════════════════════════════════════
  Results saved to database. View on dashboard.
═══════════════════════════════════════════════════
```

### CLI Entry Point (`backtest/__main__.py`)

```
uv run python -m tradebot.backtest \
  --strategy config/strategies/xsp_iron_condor.yaml \
  --start 2026-01-01 \
  --end 2026-03-01 \
  --interval 15 \
  --capital 2500 \
  --slippage 0
```

Uses `argparse` for argument parsing. Calls `run_backtest()` and prints results.

---

## Persistence

### New Table: BacktestRunRecord

```python
class BacktestRunRecord(Base):
    __tablename__ = "backtest_runs"
    id: int                    # auto-increment PK
    strategy_name: str
    start_date: date
    end_date: date
    starting_capital: Decimal
    interval_minutes: int
    slippage_pct: Decimal
    ending_nav: Decimal
    total_return_pct: Decimal
    max_drawdown_pct: Decimal
    total_trades: int
    win_rate: Decimal
    profit_factor: Decimal
    created_at: datetime       # when the backtest was run
```

### Repository Methods

```python
def save_backtest_run(self, result: BacktestResult) -> BacktestRunRecord
def get_backtest_runs(self, limit: int = 20) -> list[BacktestRunRecord]
```

Trade records from backtests are saved with `strategy` field prefixed by `backtest:` (e.g., `backtest:xsp_0dte_iron_condor`) to distinguish from live/paper trades.

### Alembic Migration

New migration to create the `backtest_runs` table.

---

## Strategy Reset Between Days

0DTE strategies set `_has_position = True` after entering a trade and never reset it. In live trading this is fine (bot restarts daily). In backtesting, we need to reset at end of each simulated day since 0DTE positions expire.

The engine will call a `reset()` method on each strategy at end of day:

```python
# Add to TradingStrategy base class
def reset(self) -> None:
    """Reset state for a new trading day. Override if needed."""
    pass
```

Each strategy overrides to reset `_has_position = False`. This is a minimal change to the base class — a no-op default that existing code doesn't need to call.

All three strategies need `reset()` overrides:
- `IronCondorStrategy` — resets `_has_position = False`
- `CreditSpreadStrategy` — resets `_has_position = False`
- `DebitSpreadStrategy` — resets `_has_position = False`

---

## datetime.now() Audit

Every call site in the pipeline that uses real time, and how we handle it for backtesting:

| Location | Current behavior | Backtest fix |
|---|---|---|
| `MarketEvent.timestamp` (`events.py:12`) | Defaults to `datetime.now()` | Engine passes `timestamp=clock.now()` explicitly when constructing events via HistoricalDataSource |
| `SignalEvent.timestamp` (`events.py:21`) | Defaults to `datetime.now()` | Acceptable — signal timestamp doesn't affect logic, only logging. The `bar.timestamp` is what strategies use for time checks. |
| `OrderEvent.timestamp` (`events.py:26`) | Defaults to `datetime.now()` | Acceptable — same as SignalEvent, only for logging |
| `FillEvent.timestamp` (`events.py:34`) | Defaults to `datetime.now()` | Acceptable — same as above |
| `TimeWindowCheck` (`risk/checks.py:100-102`) | Falls back to `datetime.now().time()` if `current_time` not passed | **Fix needed:** The engine must pass `current_time` from the simulated bar timestamp. The check already accepts an optional `current_time` parameter. However, `RiskManager.on_signal()` calls `check.check(signal)` without passing time. **Solution:** Modify the engine's risk manager wiring to use a `TimeWindowCheck` that extracts time from the signal. Or simpler: create a `BacktestTimeWindowCheck` subclass that takes a clock reference. |
| `PDTCheck` (`risk/checks.py:17`) | Uses `date.today()` | **Fix needed:** For backtesting, PDT tracking is less critical (synthetic trades). But if we want accuracy: pass simulated date. **Solution:** The engine can skip PDTCheck entirely for backtests (no real day trade tracking in synthetic mode), or create a backtest-aware version. For now, simply omit PDTCheck from backtest risk checks. |
| `MaxDailyLossCheck` (`risk/checks.py:37-42`) | Captures `current_daily_pnl` and `account_value` at init time — never updates | **Fix needed:** These are stale references. **Solution:** The engine re-creates risk checks each day with current portfolio values, OR (simpler) make the check accept a portfolio reference and read live values. **Chosen approach:** Pass portfolio reference so checks always read current values. |
| `MaxDrawdownCheck` (`risk/checks.py:117-119`) | Same issue — captures `current_drawdown_pct` at init | **Same solution:** Pass portfolio reference. |
| `PaperBroker._positions` (`paper.py:53`) | Uses `date.today()` for position records | **Fix needed in BacktestBroker:** Override to use `clock.now()` for position timestamps |
| `DailySnapshotRecord.snapshot_date` (`models.py:44`) | Has unique constraint | **Fix needed:** Backtest snapshots from multiple runs on the same simulated date will conflict. **Solution:** Add a nullable `backtest_run_id` column to `DailySnapshotRecord`, or (simpler) don't persist backtest daily snapshots to the shared table — keep them only in `BacktestResult.daily_snapshots` in memory. **Chosen approach:** Keep backtest snapshots in memory only (in `BacktestResult`), don't write to `DailySnapshotRecord`. Only the `BacktestRunRecord` summary gets persisted. |

### Summary of Required Code Changes

**Existing files to modify:**
- `strategy/base.py` — add `reset()` method
- `strategy/strategies/iron_condor.py` — override `reset()`
- `strategy/strategies/credit_spread.py` — override `reset()`
- `strategy/strategies/debit_spread.py` — override `reset()`
- `risk/checks.py` — make `MaxDailyLossCheck` and `MaxDrawdownCheck` accept portfolio reference (read current values instead of init-time snapshots)
- `persistence/models.py` — add `BacktestRunRecord`
- `persistence/repository.py` — add backtest run methods

**What stays unchanged:**
- `core/events.py` — event timestamp defaults are acceptable
- `core/event_bus.py` — works as-is
- `main.py` — backtest is a separate entry point
- `portfolio/tracker.py` — works as-is

---

## Position Expiry & Trade Tracking

0DTE positions expire at end of day. The engine must handle this for accurate trade statistics.

At end of each simulated day, before resetting strategies:

1. Check portfolio for open positions
2. For each open position: calculate P&L based on final bar price of the day (the position expired)
3. Call `portfolio.close_position()` with the expiry P&L
4. Record the trade as a win or loss

This gives us accurate trade counts, win rates, and P&L for the results.

The P&L for an expired position:
- **Credit spread/iron condor:** If expired OTM, P&L = credit received (full win). If ITM, P&L = credit - intrinsic value of short leg.
- **Debit spread:** If expired ITM past break-even, P&L = intrinsic value - debit paid. If expired OTM, P&L = -debit paid (full loss).

For simplicity in Phase 1 with synthetic data: assume all 0DTE positions expire at end of day. The engine marks them to the final bar's price and closes them.

---

## File Layout

```
src/tradebot/backtest/
├── __init__.py
├── engine.py          # run_backtest() + BacktestEngine class
├── clock.py           # Clock, SimulatedClock
├── broker.py          # BacktestBroker (extends PaperBroker)
├── data_source.py     # HistoricalDataSource
├── results.py         # BacktestResult + print_summary()
└── __main__.py        # CLI entry point

src/tradebot/persistence/
├── models.py          # Add BacktestRunRecord
└── repository.py      # Add save_backtest_run(), get_backtest_runs()

src/tradebot/strategy/
└── base.py            # Add reset() method

tests/unit/
├── test_backtest_engine.py
├── test_backtest_broker.py
├── test_backtest_clock.py
└── test_backtest_results.py

alembic/versions/
└── xxxx_add_backtest_runs.py
```

**Modified files:** `persistence/models.py`, `persistence/repository.py`, `strategy/base.py`, `strategy/strategies/iron_condor.py`, `strategy/strategies/credit_spread.py`, `strategy/strategies/debit_spread.py`, `risk/checks.py`
**Everything else:** new files only

---

## Testing Strategy

- **test_backtest_clock.py**: Clock returns real time, SimulatedClock advances correctly
- **test_backtest_broker.py**: Fills at bid/ask from chain, slippage applied correctly, falls back when no chain
- **test_backtest_engine.py**: Full end-to-end run with synthetic data — verify trades happen, NAV changes, snapshots recorded, result metrics are correct
- **test_backtest_results.py**: Metric calculations (win rate, profit factor, drawdown) with known inputs

---

## Future Extensions (not in this build)

- **Parameter sweeps**: YAML config specifying parameter ranges, engine runs all combinations
- **API endpoint**: `POST /api/backtest` triggers background run, returns run ID
- **Dashboard views**: Backtest run list, equity curve comparison, trade-by-trade analysis
- **Real data loading**: Parse DataRecorder JSON, Polygon API download
- **Commission modeling**: Per-contract fee in BacktestBroker
- **Walk-forward analysis**: Train on one period, test on next
