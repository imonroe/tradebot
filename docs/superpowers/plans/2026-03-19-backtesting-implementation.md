# Backtesting Engine Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone backtesting engine that replays synthetic market data through the existing event pipeline (strategies, risk checks, portfolio tracker) with time control, outputting performance metrics to terminal and database.

**Architecture:** A new `src/tradebot/backtest/` package with a `BacktestEngine` that wraps a `SimulatedClock`, `HistoricalDataSource`, and `BacktestBroker`. It reuses the existing `EventBus`, strategies, `RiskManager`, and `PortfolioTracker` unchanged. Minimal modifications to existing code: add `reset()` to strategies, make risk checks read live portfolio values, add `BacktestRunRecord` to persistence.

**Tech Stack:** Python 3.12, asyncio, exchange-calendars, SQLAlchemy, Alembic, argparse, pytest

**Spec:** `docs/superpowers/specs/2026-03-19-backtesting-design.md`

---

## Chunk 1: Foundation (Clock, Strategy Reset, Risk Check Fixes)

### Task 1: SimulatedClock

**Files:**
- Create: `src/tradebot/backtest/__init__.py`
- Create: `src/tradebot/backtest/clock.py`
- Create: `tests/unit/test_backtest_clock.py`

- [ ] **Step 1: Write failing tests for Clock and SimulatedClock**

`tests/unit/test_backtest_clock.py`:
```python
"""Tests for Clock and SimulatedClock."""
from datetime import datetime

from tradebot.backtest.clock import Clock, SimulatedClock


def test_clock_returns_current_time():
    clock = Clock()
    before = datetime.now()
    result = clock.now()
    after = datetime.now()
    assert before <= result <= after


def test_simulated_clock_returns_fixed_time():
    t = datetime(2026, 1, 15, 10, 30)
    clock = SimulatedClock(start=t)
    assert clock.now() == t


def test_simulated_clock_advance_to():
    t1 = datetime(2026, 1, 15, 10, 30)
    t2 = datetime(2026, 1, 15, 11, 0)
    clock = SimulatedClock(start=t1)
    clock.advance_to(t2)
    assert clock.now() == t2


def test_simulated_clock_is_subclass_of_clock():
    clock = SimulatedClock(start=datetime(2026, 1, 1))
    assert isinstance(clock, Clock)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_backtest_clock.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tradebot.backtest'`

- [ ] **Step 3: Implement Clock and SimulatedClock**

`src/tradebot/backtest/__init__.py`:
```python
```

`src/tradebot/backtest/clock.py`:
```python
"""Time control for backtesting."""
from datetime import datetime


class Clock:
    """Returns current time. Uses real time by default."""

    def now(self) -> datetime:
        return datetime.now()


class SimulatedClock(Clock):
    """Manually advanced clock for backtesting."""

    def __init__(self, start: datetime) -> None:
        self._now = start

    def now(self) -> datetime:
        return self._now

    def advance_to(self, dt: datetime) -> None:
        self._now = dt
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_backtest_clock.py -v`
Expected: PASS — all 4 tests

- [ ] **Step 5: Commit**

```bash
git add src/tradebot/backtest/__init__.py src/tradebot/backtest/clock.py tests/unit/test_backtest_clock.py
git commit -m "feat: add Clock and SimulatedClock for backtesting"
```

---

### Task 2: Strategy reset() Method

**Files:**
- Modify: `src/tradebot/strategy/base.py`
- Modify: `src/tradebot/strategy/strategies/iron_condor.py`
- Modify: `src/tradebot/strategy/strategies/credit_spread.py`
- Modify: `src/tradebot/strategy/strategies/debit_spread.py`

- [ ] **Step 1: Add reset() to TradingStrategy base class**

Read `src/tradebot/strategy/base.py`. Add after the `evaluate` abstract method:

```python
def reset(self) -> None:
    """Reset state for a new trading day. Override if needed."""
    pass
```

- [ ] **Step 2: Add reset() override to all three strategies**

Read each strategy file. Each has `self._has_position = False` in `__init__`. Add a `reset()` method to each:

For `iron_condor.py`, `credit_spread.py`, and `debit_spread.py`:
```python
def reset(self) -> None:
    """Reset position state for a new trading day."""
    self._has_position = False
```

- [ ] **Step 3: Write a test for reset behavior**

Add to `tests/unit/test_backtest_clock.py` (or create a new file — keep it simple, add to existing strategy tests):

Add to `tests/unit/test_strategies.py`:
```python
def test_iron_condor_reset_clears_position():
    strategy = IronCondorStrategy(
        name="test_ic", symbol="XSP",
        short_call_delta=Decimal("0.15"), short_put_delta=Decimal("-0.15"),
        wing_width=Decimal("5"), min_credit=Decimal("0.30"),
        entry_earliest=time(9, 45), entry_latest=time(14, 0),
    )
    # Directly set _has_position to test reset deterministically
    strategy._has_position = True
    strategy.reset()
    assert strategy._has_position is False
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/unit/test_strategies.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/tradebot/strategy/base.py src/tradebot/strategy/strategies/iron_condor.py src/tradebot/strategy/strategies/credit_spread.py src/tradebot/strategy/strategies/debit_spread.py tests/unit/test_strategies.py
git commit -m "feat: add reset() method to strategies for backtesting"
```

---

### Task 3: Fix Risk Checks for Dynamic Portfolio Values

**Files:**
- Modify: `src/tradebot/risk/checks.py`
- Modify: `tests/unit/test_risk_checks.py`

- [ ] **Step 1: Read current risk checks and tests**

Read `src/tradebot/risk/checks.py` and `tests/unit/test_risk_checks.py` to understand the current interfaces.

Key issue: `MaxDailyLossCheck` and `MaxDrawdownCheck` capture snapshot values at init time. They need to accept a `PortfolioTracker` reference and read current values instead.

- [ ] **Step 2: Update MaxDailyLossCheck to accept portfolio reference**

Change `MaxDailyLossCheck` from:
```python
@dataclass
class MaxDailyLossCheck:
    max_daily_loss_pct: Decimal
    current_daily_pnl: Decimal
    account_value: Decimal
```

To:
```python
@dataclass
class MaxDailyLossCheck:
    max_daily_loss_pct: Decimal
    current_daily_pnl: Decimal = Decimal("0")
    account_value: Decimal = Decimal("0")
    portfolio: object | None = None  # PortfolioTracker reference

    def check(self, signal: SignalEvent) -> RiskEvent:
        daily_pnl = self.portfolio.daily_pnl if self.portfolio else self.current_daily_pnl
        nav = self.portfolio.nav if self.portfolio else self.account_value
        if nav == 0:
            nav = Decimal("1")  # avoid division by zero
        loss_pct = abs(daily_pnl) / nav * 100
        passed = daily_pnl >= 0 or loss_pct < self.max_daily_loss_pct
        return RiskEvent(
            check_name="MaxDailyLossCheck",
            passed=passed,
            message=(
                f"Daily P&L: ${daily_pnl} ({loss_pct:.1f}%)"
                if passed
                else f"Daily loss limit hit: ${daily_pnl} ({loss_pct:.1f}% >= {self.max_daily_loss_pct}%)"
            ),
        )
```

This is backwards-compatible: old callers passing `current_daily_pnl` and `account_value` still work. New callers (backtest engine) pass `portfolio` instead.

- [ ] **Step 3: Update MaxDrawdownCheck similarly**

Change to accept optional `portfolio` reference:
```python
@dataclass
class MaxDrawdownCheck:
    max_drawdown_pct: Decimal
    current_drawdown_pct: Decimal = Decimal("0")
    portfolio: object | None = None

    def check(self, signal: SignalEvent) -> RiskEvent:
        drawdown = self.portfolio.drawdown_pct if self.portfolio else self.current_drawdown_pct
        passed = drawdown < self.max_drawdown_pct
        return RiskEvent(
            check_name="MaxDrawdownCheck",
            passed=passed,
            message=(
                f"Drawdown OK: {drawdown:.1f}%"
                if passed
                else f"Max drawdown hit: {drawdown:.1f}% >= {self.max_drawdown_pct}%"
            ),
        )
```

- [ ] **Step 4: Update tests for the new portfolio reference mode**

Add tests to `tests/unit/test_risk_checks.py`:
```python
def test_max_daily_loss_with_portfolio_ref():
    portfolio = PortfolioTracker(starting_capital=Decimal("2500"))
    check = MaxDailyLossCheck(max_daily_loss_pct=Decimal("3.0"), portfolio=portfolio)
    signal = _make_signal()
    result = check.check(signal)
    assert result.passed is True


def test_max_drawdown_with_portfolio_ref():
    portfolio = PortfolioTracker(starting_capital=Decimal("2500"))
    check = MaxDrawdownCheck(max_drawdown_pct=Decimal("10.0"), portfolio=portfolio)
    signal = _make_signal()
    result = check.check(signal)
    assert result.passed is True
```

You'll need to add the necessary imports (`PortfolioTracker`, and a `_make_signal` helper if one doesn't exist). Read the test file first to see existing patterns.

- [ ] **Step 5: Run all risk check tests**

Run: `uv run pytest tests/unit/test_risk_checks.py -v`
Expected: PASS — all existing + new tests

- [ ] **Step 6: Run full test suite**

Run: `uv run pytest -v`
Expected: All tests pass

- [ ] **Step 7: Commit**

```bash
git add src/tradebot/risk/checks.py tests/unit/test_risk_checks.py
git commit -m "feat: make risk checks accept portfolio reference for live values"
```

---

## Chunk 2: BacktestBroker and HistoricalDataSource

### Task 4: BacktestBroker

**Files:**
- Create: `src/tradebot/backtest/broker.py`
- Create: `src/tradebot/backtest/risk.py`
- Create: `tests/unit/test_backtest_broker.py`

- [ ] **Step 1: Write failing tests for BacktestBroker**

`tests/unit/test_backtest_broker.py`:
```python
"""Tests for BacktestBroker."""
from datetime import date
from decimal import Decimal

import pytest

from tradebot.backtest.broker import BacktestBroker
from tradebot.core.enums import OptionType, OrderSide
from tradebot.core.models import Greeks, OptionContract, OptionsChain, OrderLeg


def _make_chain(underlying_price: Decimal = Decimal("570")) -> OptionsChain:
    """Build a minimal chain with known bid/ask."""
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

    legs = [
        OrderLeg(option_symbol="XSP260115C00575000", side=OrderSide.SELL_TO_OPEN, quantity=1),
        OrderLeg(option_symbol="XSP260115C00580000", side=OrderSide.BUY_TO_OPEN, quantity=1),
    ]
    result = await broker.submit_multileg_order(legs, price=Decimal("0.50"))
    assert result.broker_order_id.startswith("PAPER-")
    # Balance should reflect actual bid/ask, not the requested price
    account = await broker.get_account()
    assert account.balance != Decimal("2500")  # something changed


@pytest.mark.asyncio
async def test_falls_back_to_target_price_without_chain():
    broker = BacktestBroker(starting_balance=Decimal("2500"))
    # No update_market_data call — chain is None
    legs = [
        OrderLeg(option_symbol="XSP260115C00575000", side=OrderSide.SELL_TO_OPEN, quantity=1),
    ]
    result = await broker.submit_multileg_order(legs, price=Decimal("0.50"))
    assert result.broker_order_id.startswith("PAPER-")
    account = await broker.get_account()
    assert account.balance == Decimal("2500") + Decimal("0.50") * 100


@pytest.mark.asyncio
async def test_slippage_applied():
    broker = BacktestBroker(starting_balance=Decimal("2500"), slippage_pct=Decimal("10"))
    chain = _make_chain()
    broker.update_market_data(chain)

    legs = [
        OrderLeg(option_symbol="XSP260115C00575000", side=OrderSide.SELL_TO_OPEN, quantity=1),
    ]
    await broker.submit_multileg_order(legs, price=Decimal("0.50"))
    account = await broker.get_account()
    # With 10% slippage on a sell, we get less than bid price
    # bid is 0.80, 10% slippage = 0.72, so balance = 2500 + 0.72 * 100 = 2572
    assert account.balance == Decimal("2500") + Decimal("0.72") * 100
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_backtest_broker.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tradebot.backtest.broker'`

- [ ] **Step 3: Implement BacktestBroker**

`src/tradebot/backtest/broker.py`:
```python
"""Backtest broker with realistic fill simulation."""
from decimal import Decimal

from tradebot.core.enums import OrderSide
from tradebot.core.models import OptionsChain, OrderLeg, OrderResult
from tradebot.execution.brokers.paper import PaperBroker


class BacktestBroker(PaperBroker):
    """Paper broker that fills at actual bid/ask from current market data."""

    def __init__(
        self,
        starting_balance: Decimal,
        slippage_pct: Decimal = Decimal("0"),
    ) -> None:
        super().__init__(starting_balance=starting_balance)
        self._slippage_pct = slippage_pct
        self._current_chain: OptionsChain | None = None

    def update_market_data(self, chain: OptionsChain) -> None:
        """Set current market data for realistic fills."""
        self._current_chain = chain

    async def submit_multileg_order(
        self, legs: list[OrderLeg], price: Decimal
    ) -> OrderResult:
        if self._current_chain is None:
            return await super().submit_multileg_order(legs, price)

        # Calculate actual fill price from bid/ask
        fill_price = self._calculate_fill_price(legs)
        return await super().submit_multileg_order(legs, fill_price)

    def _calculate_fill_price(self, legs: list[OrderLeg]) -> Decimal:
        """Calculate net fill price from actual bid/ask in current chain."""
        all_contracts = {
            c.symbol: c
            for c in self._current_chain.calls + self._current_chain.puts
        }
        net_credit = Decimal("0")
        for leg in legs:
            contract = all_contracts.get(leg.option_symbol)
            if contract is None:
                continue
            if leg.side in (OrderSide.SELL_TO_OPEN, OrderSide.SELL_TO_CLOSE):
                fill = contract.bid
                if self._slippage_pct > 0:
                    fill = fill * (1 - self._slippage_pct / 100)
                net_credit += fill
            else:
                fill = contract.ask
                if self._slippage_pct > 0:
                    fill = fill * (1 + self._slippage_pct / 100)
                net_credit -= fill
        return net_credit
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_backtest_broker.py -v`
Expected: PASS — all 3 tests

- [ ] **Step 5: Commit**

```bash
git add src/tradebot/backtest/broker.py tests/unit/test_backtest_broker.py
git commit -m "feat: add BacktestBroker with bid/ask fills and slippage"
```

- [ ] **Step 6: Create BacktestTimeWindowCheck**

`src/tradebot/backtest/risk.py`:
```python
"""Backtest-specific risk check overrides."""
from datetime import time

from tradebot.backtest.clock import SimulatedClock
from tradebot.core.events import RiskEvent, SignalEvent
from tradebot.risk.checks import TimeWindowCheck


class BacktestTimeWindowCheck(TimeWindowCheck):
    """TimeWindowCheck that uses simulated time instead of wall-clock time."""

    def __init__(self, earliest: time, latest: time, clock: SimulatedClock) -> None:
        super().__init__(earliest=earliest, latest=latest)
        self._clock = clock

    def check(self, signal: SignalEvent, current_time: time | None = None) -> RiskEvent:
        return super().check(signal, current_time=self._clock.now().time())
```

- [ ] **Step 7: Commit**

```bash
git add src/tradebot/backtest/risk.py
git commit -m "feat: add BacktestTimeWindowCheck using simulated clock"
```

---

### Task 5: HistoricalDataSource

**Files:**
- Create: `src/tradebot/backtest/data_source.py`
- Create: `tests/unit/test_backtest_data_source.py`

- [ ] **Step 1: Write failing tests**

`tests/unit/test_backtest_data_source.py`:
```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_backtest_data_source.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement HistoricalDataSource**

`src/tradebot/backtest/data_source.py`:
```python
"""Historical data source for backtesting."""
from datetime import date

from tradebot.backtest.clock import SimulatedClock
from tradebot.core.events import MarketEvent
from tradebot.core.models import Bar
from tradebot.data.sources.base import DataSource


class HistoricalDataSource:
    """Wraps a DataSource and stamps data with simulated time."""

    def __init__(self, source: DataSource, clock: SimulatedClock) -> None:
        self._source = source
        self._clock = clock

    async def get_market_event(self, symbol: str, expiration: date) -> MarketEvent:
        """Fetch data and return a MarketEvent with simulated timestamp."""
        bar = await self._source.get_quote(symbol)
        chain = await self._source.get_options_chain(symbol, expiration)

        timed_bar = Bar(
            symbol=bar.symbol,
            timestamp=self._clock.now(),
            open=bar.open,
            high=bar.high,
            low=bar.low,
            close=bar.close,
            volume=bar.volume,
        )

        return MarketEvent(
            bar=timed_bar,
            options_chain=chain,
            timestamp=self._clock.now(),
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_backtest_data_source.py -v`
Expected: PASS — all 3 tests

- [ ] **Step 5: Commit**

```bash
git add src/tradebot/backtest/data_source.py tests/unit/test_backtest_data_source.py
git commit -m "feat: add HistoricalDataSource for backtesting"
```

---

## Chunk 3: BacktestResult and Persistence

### Task 6: BacktestResult Dataclass and Metrics

**Files:**
- Create: `src/tradebot/backtest/results.py`
- Create: `tests/unit/test_backtest_results.py`

- [ ] **Step 1: Write failing tests for BacktestResult**

`tests/unit/test_backtest_results.py`:
```python
"""Tests for BacktestResult and metric calculations."""
from datetime import date
from decimal import Decimal

from tradebot.backtest.results import BacktestResult, compute_metrics


def test_compute_metrics_with_wins_and_losses():
    trades = [
        {"pnl": Decimal("50")},
        {"pnl": Decimal("30")},
        {"pnl": Decimal("-20")},
        {"pnl": Decimal("40")},
        {"pnl": Decimal("-10")},
    ]
    metrics = compute_metrics(trades)
    assert metrics["total_trades"] == 5
    assert metrics["winning_trades"] == 3
    assert metrics["losing_trades"] == 2
    assert metrics["win_rate"] == Decimal("60.0")
    assert metrics["avg_win"] == Decimal("40.00")  # (50+30+40)/3
    assert metrics["avg_loss"] == Decimal("-15.00")  # (-20+-10)/2
    assert metrics["profit_factor"] == Decimal("4.00")  # 120/30


def test_compute_metrics_all_wins():
    trades = [{"pnl": Decimal("50")}, {"pnl": Decimal("30")}]
    metrics = compute_metrics(trades)
    assert metrics["win_rate"] == Decimal("100.0")
    assert metrics["profit_factor"] == Decimal("Infinity")


def test_compute_metrics_no_trades():
    metrics = compute_metrics([])
    assert metrics["total_trades"] == 0
    assert metrics["win_rate"] == Decimal("0")
    assert metrics["profit_factor"] == Decimal("0")


def test_backtest_result_print_summary(capsys):
    result = BacktestResult(
        strategy_name="test_strategy",
        start_date=date(2026, 1, 2),
        end_date=date(2026, 3, 1),
        starting_capital=Decimal("2500"),
        interval_minutes=15,
        ending_nav=Decimal("2715"),
        total_return_pct=Decimal("8.60"),
        max_drawdown_pct=Decimal("3.20"),
        total_trades=38,
        winning_trades=26,
        losing_trades=12,
        win_rate=Decimal("68.4"),
        avg_win=Decimal("18.50"),
        avg_loss=Decimal("-12.30"),
        profit_factor=Decimal("2.31"),
        daily_snapshots=[],
        trades=[],
    )
    result.print_summary()
    output = capsys.readouterr().out
    assert "test_strategy" in output
    assert "8.60%" in output
    assert "68.4%" in output
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_backtest_results.py -v`
Expected: FAIL

- [ ] **Step 3: Implement BacktestResult and compute_metrics**

`src/tradebot/backtest/results.py`:
```python
"""Backtest results and metrics."""
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal


def compute_metrics(trades: list[dict]) -> dict:
    """Compute trade statistics from a list of trades with 'pnl' field."""
    if not trades:
        return {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "win_rate": Decimal("0"),
            "avg_win": Decimal("0"),
            "avg_loss": Decimal("0"),
            "profit_factor": Decimal("0"),
        }

    wins = [t for t in trades if t["pnl"] > 0]
    losses = [t for t in trades if t["pnl"] < 0]
    total = len(trades)
    n_wins = len(wins)
    n_losses = len(losses)

    win_rate = Decimal(str(round(n_wins / total * 100, 1)))
    avg_win = (
        sum(t["pnl"] for t in wins) / n_wins if n_wins else Decimal("0")
    )
    avg_loss = (
        sum(t["pnl"] for t in losses) / n_losses if n_losses else Decimal("0")
    )

    gross_profit = sum(t["pnl"] for t in wins)
    gross_loss = abs(sum(t["pnl"] for t in losses))

    if gross_loss == 0:
        profit_factor = Decimal("Infinity") if gross_profit > 0 else Decimal("0")
    else:
        profit_factor = Decimal(str(round(gross_profit / gross_loss, 2)))

    return {
        "total_trades": total,
        "winning_trades": n_wins,
        "losing_trades": n_losses,
        "win_rate": win_rate,
        "avg_win": avg_win.quantize(Decimal("0.01")),
        "avg_loss": avg_loss.quantize(Decimal("0.01")),
        "profit_factor": profit_factor,
    }


@dataclass
class BacktestResult:
    """Complete results from a backtest run."""

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
    profit_factor: Decimal

    # Daily data
    daily_snapshots: list[dict] = field(default_factory=list)
    trades: list[dict] = field(default_factory=list)

    def print_summary(self) -> None:
        """Print formatted summary to terminal."""
        ret_sign = "+" if self.total_return_pct >= 0 else ""
        w = self.winning_trades
        l = self.losing_trades
        print()
        print("=" * 51)
        print(f"  Backtest: {self.strategy_name}")
        print(f"  Period:   {self.start_date} -> {self.end_date}")
        print(f"  Capital:  ${self.starting_capital:,.2f} -> ${self.ending_nav:,.2f}")
        print("=" * 51)
        print(f"  Total Return:    {ret_sign}{self.total_return_pct}%")
        print(f"  Max Drawdown:    -{self.max_drawdown_pct}%")
        print(f"  Total Trades:    {self.total_trades}")
        print(f"  Win Rate:        {self.win_rate}%  ({w}W / {l}L)")
        print(f"  Avg Win:         ${self.avg_win}")
        print(f"  Avg Loss:        ${self.avg_loss}")
        print(f"  Profit Factor:   {self.profit_factor}")
        print("=" * 51)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_backtest_results.py -v`
Expected: PASS — all 4 tests

- [ ] **Step 5: Commit**

```bash
git add src/tradebot/backtest/results.py tests/unit/test_backtest_results.py
git commit -m "feat: add BacktestResult and compute_metrics"
```

---

### Task 7: BacktestRunRecord Persistence

**Files:**
- Modify: `src/tradebot/persistence/models.py`
- Modify: `src/tradebot/persistence/repository.py`
- Modify: `tests/unit/test_persistence.py`

- [ ] **Step 1: Add BacktestRunRecord to ORM models**

Read `src/tradebot/persistence/models.py`. Add after `DailySnapshotRecord`:

```python
class BacktestRunRecord(Base):
    __tablename__ = "backtest_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    strategy_name: Mapped[str] = mapped_column(String(100))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    starting_capital: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    interval_minutes: Mapped[int] = mapped_column(Integer)
    slippage_pct: Mapped[Decimal] = mapped_column(Numeric(6, 4), default=0)
    ending_nav: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    total_return_pct: Mapped[Decimal] = mapped_column(Numeric(8, 2))
    max_drawdown_pct: Mapped[Decimal] = mapped_column(Numeric(8, 2))
    total_trades: Mapped[int] = mapped_column(Integer)
    win_rate: Mapped[Decimal] = mapped_column(Numeric(6, 2))
    profit_factor: Mapped[Decimal] = mapped_column(Numeric(8, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
```

- [ ] **Step 2: Add repository methods**

Read `src/tradebot/persistence/repository.py`. Add import for `BacktestRunRecord`. Add methods:

```python
def save_backtest_run(self, result) -> BacktestRunRecord:
    """Save a backtest run summary."""
    record = BacktestRunRecord(
        strategy_name=result.strategy_name,
        start_date=result.start_date,
        end_date=result.end_date,
        starting_capital=result.starting_capital,
        interval_minutes=result.interval_minutes,
        ending_nav=result.ending_nav,
        total_return_pct=result.total_return_pct,
        max_drawdown_pct=result.max_drawdown_pct,
        total_trades=result.total_trades,
        win_rate=result.win_rate,
        profit_factor=result.profit_factor,
    )
    self._session.add(record)
    self._session.flush()
    return record

def get_backtest_runs(self, limit: int = 20) -> list[BacktestRunRecord]:
    """Get recent backtest runs."""
    stmt = (
        select(BacktestRunRecord)
        .order_by(BacktestRunRecord.created_at.desc())
        .limit(limit)
    )
    return list(self._session.execute(stmt).scalars().all())
```

- [ ] **Step 3: Write tests**

Add to `tests/unit/test_persistence.py`:
```python
from tradebot.backtest.results import BacktestResult


def test_save_backtest_run(repo):
    result = BacktestResult(
        strategy_name="test_ic", start_date=date(2026, 1, 2),
        end_date=date(2026, 3, 1), starting_capital=Decimal("2500"),
        interval_minutes=15, ending_nav=Decimal("2715"),
        total_return_pct=Decimal("8.60"), max_drawdown_pct=Decimal("3.20"),
        total_trades=38, winning_trades=26, losing_trades=12,
        win_rate=Decimal("68.4"), avg_win=Decimal("18.50"),
        avg_loss=Decimal("-12.30"), profit_factor=Decimal("2.31"),
    )
    record = repo.save_backtest_run(result)
    assert record.id is not None
    assert record.strategy_name == "test_ic"


def test_get_backtest_runs(repo):
    result = BacktestResult(
        strategy_name="test_ic", start_date=date(2026, 1, 2),
        end_date=date(2026, 3, 1), starting_capital=Decimal("2500"),
        interval_minutes=15, ending_nav=Decimal("2715"),
        total_return_pct=Decimal("8.60"), max_drawdown_pct=Decimal("3.20"),
        total_trades=38, winning_trades=26, losing_trades=12,
        win_rate=Decimal("68.4"), avg_win=Decimal("18.50"),
        avg_loss=Decimal("-12.30"), profit_factor=Decimal("2.31"),
    )
    repo.save_backtest_run(result)
    runs = repo.get_backtest_runs()
    assert len(runs) == 1
    assert runs[0].strategy_name == "test_ic"
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/unit/test_persistence.py -v`
Expected: PASS

- [ ] **Step 5: Generate Alembic migration**

Run: `uv run alembic revision --autogenerate -m "add backtest_runs table"`
Verify the generated migration creates the `backtest_runs` table.

- [ ] **Step 6: Commit**

```bash
git add src/tradebot/persistence/models.py src/tradebot/persistence/repository.py tests/unit/test_persistence.py alembic/versions/
git commit -m "feat: add BacktestRunRecord persistence"
```

---

## Chunk 4: BacktestEngine and CLI

### Task 8: BacktestEngine

**Files:**
- Create: `src/tradebot/backtest/engine.py`
- Create: `tests/unit/test_backtest_engine.py`

- [ ] **Step 1: Write failing end-to-end test**

`tests/unit/test_backtest_engine.py`:
```python
"""Tests for BacktestEngine."""
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from tradebot.backtest.engine import run_backtest


@pytest.mark.asyncio
async def test_backtest_runs_and_returns_result():
    """End-to-end test: run backtest with iron condor on synthetic data."""
    config_path = Path(__file__).resolve().parent.parent.parent / "config" / "strategies" / "xsp_iron_condor.yaml"
    if not config_path.exists():
        pytest.skip("Strategy config not found")

    result = await run_backtest(
        strategy_config_path=config_path,
        start_date=date(2026, 1, 2),
        end_date=date(2026, 1, 10),
        interval_minutes=30,
        starting_capital=Decimal("2500"),
    )

    assert result.strategy_name == "xsp_0dte_iron_condor"
    assert result.starting_capital == Decimal("2500")
    assert result.ending_nav > 0
    assert result.total_trades > 0  # synthetic data should produce trades
    assert len(result.daily_snapshots) > 0


@pytest.mark.asyncio
async def test_backtest_with_short_period():
    """Test that a 1-day backtest works."""
    config_path = Path(__file__).resolve().parent.parent.parent / "config" / "strategies" / "xsp_iron_condor.yaml"
    if not config_path.exists():
        pytest.skip("Strategy config not found")

    result = await run_backtest(
        strategy_config_path=config_path,
        start_date=date(2026, 1, 2),
        end_date=date(2026, 1, 2),
        interval_minutes=15,
        starting_capital=Decimal("2500"),
    )

    assert result.start_date == date(2026, 1, 2)
    assert result.end_date == date(2026, 1, 2)
    assert len(result.daily_snapshots) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_backtest_engine.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement run_backtest and BacktestEngine**

`src/tradebot/backtest/engine.py`:

This is the most complex file. Key implementation points:

```python
"""Backtesting engine."""
import asyncio
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
from tradebot.risk.checks import (
    MaxDailyLossCheck,
    MaxDrawdownCheck,
)
from tradebot.risk.manager import RiskManager
from tradebot.strategy.registry import load_strategy

logger = structlog.get_logger()


def _generate_timestamps(
    start_date: date,
    end_date: date,
    interval_minutes: int,
) -> list[datetime]:
    """Generate simulation timestamps for each trading day."""
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
        # Credit spread/iron condor: fill_price > 0, expire worthless = full win
        # Debit spread: fill_price < 0 (we paid), expire worthless = full loss
        # In both cases, the P&L when expiring worthless equals fill_price * 100
        # (positive for credits, negative for debits)
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
    # Note: PDTCheck and DuplicateCheck omitted for backtesting.
    # PDT is not meaningful with synthetic data.
    # DuplicateCheck would need dynamic open_symbols tracking (future enhancement).

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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_backtest_engine.py -v`
Expected: PASS — both tests

- [ ] **Step 5: Run full test suite**

Run: `uv run pytest -v`
Expected: All tests pass

- [ ] **Step 6: Commit**

```bash
git add src/tradebot/backtest/engine.py tests/unit/test_backtest_engine.py
git commit -m "feat: add BacktestEngine with end-to-end synthetic data run"
```

---

### Task 9: CLI Entry Point

**Files:**
- Create: `src/tradebot/backtest/__main__.py`

- [ ] **Step 1: Implement CLI**

`src/tradebot/backtest/__main__.py`:
```python
"""CLI entry point for backtesting: python -m tradebot.backtest"""
import argparse
import asyncio
from datetime import date
from decimal import Decimal
from pathlib import Path

from tradebot.backtest.engine import run_backtest
from tradebot.utils.logging import setup_logging


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a backtest")
    parser.add_argument("--strategy", required=True, help="Path to strategy YAML config")
    parser.add_argument("--start", required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", required=True, help="End date (YYYY-MM-DD)")
    parser.add_argument("--interval", type=int, default=15, help="Minutes between data points (default: 15)")
    parser.add_argument("--capital", type=Decimal, default=Decimal("2500"), help="Starting capital (default: 2500)")
    parser.add_argument("--slippage", type=Decimal, default=Decimal("0"), help="Slippage percent (default: 0)")
    parser.add_argument("--save", action="store_true", help="Save results to database")

    args = parser.parse_args()

    setup_logging()

    result = asyncio.run(run_backtest(
        strategy_config_path=Path(args.strategy),
        start_date=date.fromisoformat(args.start),
        end_date=date.fromisoformat(args.end),
        interval_minutes=args.interval,
        starting_capital=args.capital,
        slippage_pct=args.slippage,
    ))

    result.print_summary()

    if args.save:
        from tradebot.persistence.database import Base, create_db_engine, create_session
        from tradebot.persistence.repository import Repository
        from tradebot.utils.config import Settings

        settings = Settings()
        engine = create_db_engine(settings.database_url)
        Base.metadata.create_all(engine)
        session = create_session(engine)
        repo = Repository(session)
        repo.save_backtest_run(result)
        repo.commit()
        print("  Results saved to database.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Test CLI manually**

Run: `uv run python -m tradebot.backtest --strategy config/strategies/xsp_iron_condor.yaml --start 2026-01-02 --end 2026-01-16 --interval 30`

Expected: Backtest runs and prints summary to terminal.

- [ ] **Step 3: Commit**

```bash
git add src/tradebot/backtest/__main__.py
git commit -m "feat: add CLI entry point for backtesting"
```

---

### Task 10: Final Integration Verification

- [ ] **Step 1: Run full backend test suite**

Run: `uv run pytest -v --tb=short`
Expected: All tests pass

- [ ] **Step 2: Run ruff linter**

Run: `uv run ruff check src/ tests/`
Expected: No new errors (pre-existing E402 in test_api.py is acceptable)

- [ ] **Step 3: Run a full backtest end-to-end**

Run: `uv run python -m tradebot.backtest --strategy config/strategies/xsp_iron_condor.yaml --start 2026-01-02 --end 2026-03-01 --interval 15`

Expected: Runs to completion, prints results summary with trades and metrics.

- [ ] **Step 4: Run with --save flag to test DB persistence**

Run: `uv run python -m tradebot.backtest --strategy config/strategies/xsp_iron_condor.yaml --start 2026-01-02 --end 2026-01-16 --interval 30 --save`

Expected: Results saved to database.

- [ ] **Step 5: Test with credit spread strategy**

Run: `uv run python -m tradebot.backtest --strategy config/strategies/xsp_credit_spread_put.yaml --start 2026-01-02 --end 2026-01-16 --interval 30`

Expected: Runs successfully with credit spread strategy.

- [ ] **Step 6: Commit any remaining fixes**

```bash
git add -A
git commit -m "chore: integration verification and fixes"
```
