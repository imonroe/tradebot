# Strategies, Alembic & NAV Chart Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add credit spread and debit spread strategies, initialize Alembic database migrations, and add a NAV history chart to the dashboard.

**Architecture:** New strategies follow the existing `TradingStrategy` base class pattern and register in the strategy registry. Alembic wraps the existing SQLAlchemy models. NAV chart reads from `DailySnapshotRecord` (already defined in ORM) via a new API endpoint, rendered with Recharts (already in frontend deps).

**Tech Stack:** Python 3.12, SQLAlchemy 2.0, Alembic, FastAPI, React, Recharts, pytest

**Spec:** `docs/superpowers/specs/2026-03-16-tradebot-design.md`

**Key interfaces (from existing code):**
- `MarketEvent` has `bar` (with `bar.symbol`), `options_chain`, `timestamp` — NO `symbol` field
- `SignalEvent` requires: `strategy_name`, `spread_type`, `symbol`, `legs`, `target_price`
- `OrderLeg` has ONLY: `option_symbol`, `side`, `quantity` — NO `strike` or `option_type`
- `TradingStrategy` base sets `self.name` and `self.symbol` (public, no underscore)
- `Bar.timestamp` is a `datetime` — use `event.bar.timestamp.time()` for time checks
- Iron condor pattern: check `event.bar.symbol != self.symbol` for symbol filtering

---

## Chunk 1: Credit & Debit Spread Strategies

### Task 1: Extend Config Models for New Strategy Parameters

**Files:**
- Modify: `src/tradebot/utils/config.py`

- [ ] **Step 1: Add new fields to config models**

Add `direction`, `short_delta`, `long_delta`, `max_debit` to the config models. The existing `StrikeSelection` model needs these optional fields. `EntryConfig` needs `direction` and `max_debit`.

In `src/tradebot/utils/config.py`, update `StrikeSelection`:
```python
class StrikeSelection(BaseModel):
    method: str = "delta"
    short_call_delta: float = 0.15
    short_put_delta: float = -0.15
    wing_width: int = 5
    short_delta: float = 0.15       # for credit spreads
    long_delta: float = 0.40        # for debit spreads
```

Update `EntryConfig`:
```python
class EntryConfig(BaseModel):
    time_window: TimeWindow = TimeWindow()
    strike_selection: StrikeSelection = StrikeSelection()
    iv_filter: IVFilter = IVFilter()
    min_credit: float = 0.0
    direction: str = "put"          # "call" or "put" for directional spreads
    max_debit: float = 3.0          # max debit for debit spreads
```

- [ ] **Step 2: Run existing tests to verify nothing breaks**

Run: `uv run pytest -v`
Expected: All 58 tests still pass (new fields have defaults)

- [ ] **Step 3: Commit**

```bash
git add src/tradebot/utils/config.py
git commit -m "feat: extend config models for credit and debit spread parameters"
```

---

### Task 2: Credit Spread Strategy Implementation

**Files:**
- Create: `src/tradebot/strategy/strategies/credit_spread.py`
- Create: `tests/unit/test_credit_spread.py`
- Create: `config/strategies/xsp_credit_spread_put.yaml`

- [ ] **Step 1: Write failing tests for CreditSpreadStrategy**

`tests/unit/test_credit_spread.py`:
```python
"""Tests for credit spread strategy."""
from datetime import date, datetime, time
from decimal import Decimal

import pytest

from tradebot.core.enums import OptionType, OrderSide, SpreadType
from tradebot.core.events import MarketEvent
from tradebot.core.models import Bar, Greeks, OptionContract, OptionsChain
from tradebot.strategy.strategies.credit_spread import CreditSpreadStrategy


def _make_option(
    symbol: str,
    option_type: OptionType,
    strike: Decimal,
    delta: Decimal,
    bid: Decimal = Decimal("1.00"),
    ask: Decimal = Decimal("1.20"),
) -> OptionContract:
    return OptionContract(
        symbol=symbol,
        underlying="XSP",
        option_type=option_type,
        strike=strike,
        expiration=date(2026, 3, 18),
        bid=bid,
        ask=ask,
        last=(bid + ask) / 2,
        volume=100,
        open_interest=500,
        greeks=Greeks(
            delta=delta,
            gamma=Decimal("0.05"),
            theta=Decimal("-0.10"),
            vega=Decimal("0.08"),
            implied_volatility=Decimal("0.20"),
        ),
    )


def _make_chain() -> OptionsChain:
    calls = [
        _make_option("XSP_C670", OptionType.CALL, Decimal("670"), Decimal("0.30"), Decimal("2.00"), Decimal("2.20")),
        _make_option("XSP_C675", OptionType.CALL, Decimal("675"), Decimal("0.15"), Decimal("0.80"), Decimal("1.00")),
        _make_option("XSP_C680", OptionType.CALL, Decimal("680"), Decimal("0.08"), Decimal("0.30"), Decimal("0.45")),
    ]
    puts = [
        _make_option("XSP_P650", OptionType.PUT, Decimal("650"), Decimal("-0.08"), Decimal("0.25"), Decimal("0.40")),
        _make_option("XSP_P655", OptionType.PUT, Decimal("655"), Decimal("-0.15"), Decimal("0.70"), Decimal("0.90")),
        _make_option("XSP_P660", OptionType.PUT, Decimal("660"), Decimal("-0.30"), Decimal("1.80"), Decimal("2.10")),
    ]
    return OptionsChain(
        underlying="XSP",
        expiration=date(2026, 3, 18),
        underlying_price=Decimal("665.00"),
        calls=calls,
        puts=puts,
    )


def _make_market_event(chain: OptionsChain | None = None) -> MarketEvent:
    bar = Bar(
        symbol="XSP",
        timestamp=datetime(2026, 3, 18, 10, 30),
        open=Decimal("665"), high=Decimal("666"),
        low=Decimal("664"), close=Decimal("665"), volume=5000,
    )
    return MarketEvent(bar=bar, options_chain=chain or _make_chain())


class TestCreditSpreadStrategy:
    def _make_strategy(self, direction: str = "put") -> CreditSpreadStrategy:
        return CreditSpreadStrategy(
            name="test_credit_spread",
            symbol="XSP",
            direction=direction,
            short_delta=Decimal("0.15"),
            wing_width=Decimal("5"),
            min_credit=Decimal("0.10"),
            entry_earliest=time(9, 45),
            entry_latest=time(14, 0),
        )

    def test_put_spread_generates_two_legs(self):
        strategy = self._make_strategy(direction="put")
        event = _make_market_event()
        signals = strategy.evaluate(event)
        assert len(signals) == 1
        signal = signals[0]
        assert signal.spread_type == SpreadType.CREDIT_SPREAD
        assert len(signal.legs) == 2
        assert signal.strategy_name == "test_credit_spread"
        assert signal.symbol == "XSP"

    def test_put_spread_has_sell_and_buy_legs(self):
        strategy = self._make_strategy(direction="put")
        event = _make_market_event()
        signals = strategy.evaluate(event)
        signal = signals[0]
        sides = {l.side for l in signal.legs}
        assert OrderSide.SELL_TO_OPEN in sides
        assert OrderSide.BUY_TO_OPEN in sides

    def test_call_spread_generates_signal(self):
        strategy = self._make_strategy(direction="call")
        event = _make_market_event()
        signals = strategy.evaluate(event)
        assert len(signals) == 1
        signal = signals[0]
        assert signal.spread_type == SpreadType.CREDIT_SPREAD
        assert len(signal.legs) == 2

    def test_no_signal_when_position_open(self):
        strategy = self._make_strategy()
        event = _make_market_event()
        strategy.evaluate(event)  # opens position
        signals = strategy.evaluate(event)  # should not open another
        assert len(signals) == 0

    def test_no_signal_when_no_chain(self):
        strategy = self._make_strategy()
        bar = Bar(
            symbol="XSP",
            timestamp=datetime(2026, 3, 18, 10, 30),
            open=Decimal("665"), high=Decimal("666"),
            low=Decimal("664"), close=Decimal("665"), volume=10000,
        )
        event = MarketEvent(bar=bar, options_chain=None)
        signals = strategy.evaluate(event)
        assert len(signals) == 0

    def test_no_signal_outside_time_window(self):
        strategy = self._make_strategy()
        bar = Bar(
            symbol="XSP",
            timestamp=datetime(2026, 3, 18, 15, 30),  # after 14:00
            open=Decimal("665"), high=Decimal("666"),
            low=Decimal("664"), close=Decimal("665"), volume=10000,
        )
        event = MarketEvent(bar=bar, options_chain=_make_chain())
        signals = strategy.evaluate(event)
        assert len(signals) == 0

    def test_no_signal_wrong_symbol(self):
        strategy = self._make_strategy()
        bar = Bar(
            symbol="SPY",
            timestamp=datetime(2026, 3, 18, 10, 30),
            open=Decimal("665"), high=Decimal("666"),
            low=Decimal("664"), close=Decimal("665"), volume=10000,
        )
        event = MarketEvent(bar=bar, options_chain=_make_chain())
        signals = strategy.evaluate(event)
        assert len(signals) == 0

    def test_direction_must_be_call_or_put(self):
        with pytest.raises(ValueError, match="direction"):
            CreditSpreadStrategy(
                name="bad",
                symbol="XSP",
                direction="diagonal",
                short_delta=Decimal("0.15"),
                wing_width=Decimal("5"),
                min_credit=Decimal("0.10"),
                entry_earliest=time(9, 45),
                entry_latest=time(14, 0),
            )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_credit_spread.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tradebot.strategy.strategies.credit_spread'`

- [ ] **Step 3: Implement CreditSpreadStrategy**

`src/tradebot/strategy/strategies/credit_spread.py`:
```python
"""Credit spread strategy — sells OTM vertical spread for a credit."""
from datetime import time
from decimal import Decimal

import structlog

from tradebot.core.enums import OrderSide, SpreadType
from tradebot.core.events import MarketEvent, SignalEvent
from tradebot.core.models import OptionContract, OptionsChain, OrderLeg
from tradebot.strategy.base import TradingStrategy

logger = structlog.get_logger()


class CreditSpreadStrategy(TradingStrategy):
    """Sell an OTM call or put spread, collecting premium from time decay.

    - direction="put": bull put spread (sell higher put, buy lower put)
    - direction="call": bear call spread (sell lower call, buy higher call)
    """

    def __init__(
        self,
        name: str,
        symbol: str,
        direction: str,
        short_delta: Decimal,
        wing_width: Decimal,
        min_credit: Decimal,
        entry_earliest: time,
        entry_latest: time,
    ) -> None:
        super().__init__(name=name, symbol=symbol)
        if direction not in ("call", "put"):
            raise ValueError(f"direction must be 'call' or 'put', got '{direction}'")
        self.direction = direction
        self.short_delta = short_delta
        self.wing_width = wing_width
        self.min_credit = min_credit
        self.entry_earliest = entry_earliest
        self.entry_latest = entry_latest
        self._has_position = False

    def evaluate(self, event: MarketEvent) -> list[SignalEvent]:
        if self._has_position:
            return []
        if event.options_chain is None:
            return []
        if event.bar.symbol != self.symbol:
            return []

        current_time = event.bar.timestamp.time()
        if not (self.entry_earliest <= current_time <= self.entry_latest):
            return []

        legs = self._select_strikes(event.options_chain)
        if legs is None:
            logger.info("credit_spread_skip", reason="no_valid_strikes_or_credit_too_low")
            return []

        credit = self._estimate_credit(event.options_chain, legs)

        self._has_position = True
        return [
            SignalEvent(
                strategy_name=self.name,
                spread_type=SpreadType.CREDIT_SPREAD,
                symbol=self.symbol,
                legs=legs,
                target_price=credit,
            )
        ]

    def _select_strikes(self, chain: OptionsChain) -> list[OrderLeg] | None:
        if self.direction == "put":
            return self._select_put_spread(chain)
        return self._select_call_spread(chain)

    def _find_closest_by_delta(
        self, contracts: list[OptionContract], target_delta: Decimal
    ) -> OptionContract | None:
        if not contracts:
            return None
        return min(contracts, key=lambda c: abs(c.greeks.delta - target_delta))

    def _find_by_strike(
        self, contracts: list[OptionContract], target_strike: Decimal
    ) -> OptionContract | None:
        if not contracts:
            return None
        exact = [c for c in contracts if c.strike == target_strike]
        if exact:
            return exact[0]
        return None

    def _select_put_spread(self, chain: OptionsChain) -> list[OrderLeg] | None:
        short_put = self._find_closest_by_delta(chain.puts, -self.short_delta)
        if short_put is None:
            return None

        long_strike = short_put.strike - self.wing_width
        long_put = self._find_by_strike(chain.puts, long_strike)
        if long_put is None:
            return None

        credit = short_put.bid - long_put.ask
        if credit < self.min_credit:
            return None

        return [
            OrderLeg(option_symbol=short_put.symbol, side=OrderSide.SELL_TO_OPEN, quantity=1),
            OrderLeg(option_symbol=long_put.symbol, side=OrderSide.BUY_TO_OPEN, quantity=1),
        ]

    def _select_call_spread(self, chain: OptionsChain) -> list[OrderLeg] | None:
        short_call = self._find_closest_by_delta(chain.calls, self.short_delta)
        if short_call is None:
            return None

        long_strike = short_call.strike + self.wing_width
        long_call = self._find_by_strike(chain.calls, long_strike)
        if long_call is None:
            return None

        credit = short_call.bid - long_call.ask
        if credit < self.min_credit:
            return None

        return [
            OrderLeg(option_symbol=short_call.symbol, side=OrderSide.SELL_TO_OPEN, quantity=1),
            OrderLeg(option_symbol=long_call.symbol, side=OrderSide.BUY_TO_OPEN, quantity=1),
        ]

    def _estimate_credit(self, chain: OptionsChain, legs: list[OrderLeg]) -> Decimal:
        """Estimate net credit from mid prices."""
        credit = Decimal("0")
        all_contracts = {c.symbol: c for c in chain.calls + chain.puts}
        for leg in legs:
            contract = all_contracts.get(leg.option_symbol)
            if contract is None:
                continue
            if leg.side in (OrderSide.SELL_TO_OPEN, OrderSide.SELL_TO_CLOSE):
                credit += contract.mid_price
            else:
                credit -= contract.mid_price
        return credit
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_credit_spread.py -v`
Expected: PASS — all 8 tests

- [ ] **Step 5: Create example strategy config**

`config/strategies/xsp_credit_spread_put.yaml`:
```yaml
strategy:
  name: "xsp_0dte_credit_spread_put"
  class: "CreditSpreadStrategy"
  enabled: true

market:
  symbol: "XSP"
  expiration: "0dte"

entry:
  direction: "put"
  time_window:
    earliest: "09:45"
    latest: "14:00"
  strike_selection:
    method: "delta"
    short_delta: 0.15
    wing_width: 5
  min_credit: 0.15

exit:
  profit_target_pct: 50
  stop_loss_pct: 200
  time_exit: "15:45"
  prefer_expire: true

position_sizing:
  method: "fixed_risk"
  max_risk_per_trade: 250
  max_contracts: 2

risk:
  max_daily_trades: 1
  pdt_aware: true
```

- [ ] **Step 6: Commit**

```bash
git add src/tradebot/strategy/strategies/credit_spread.py tests/unit/test_credit_spread.py config/strategies/xsp_credit_spread_put.yaml
git commit -m "feat: add credit spread strategy with tests and example config"
```

---

### Task 3: Debit Spread Strategy Implementation

**Files:**
- Create: `src/tradebot/strategy/strategies/debit_spread.py`
- Create: `tests/unit/test_debit_spread.py`
- Create: `config/strategies/xsp_debit_spread_call.yaml`

- [ ] **Step 1: Write failing tests for DebitSpreadStrategy**

`tests/unit/test_debit_spread.py`:
```python
"""Tests for debit spread strategy."""
from datetime import date, datetime, time
from decimal import Decimal

import pytest

from tradebot.core.enums import OptionType, OrderSide, SpreadType
from tradebot.core.events import MarketEvent
from tradebot.core.models import Bar, Greeks, OptionContract, OptionsChain
from tradebot.strategy.strategies.debit_spread import DebitSpreadStrategy


def _make_option(
    symbol: str,
    option_type: OptionType,
    strike: Decimal,
    delta: Decimal,
    bid: Decimal = Decimal("1.00"),
    ask: Decimal = Decimal("1.20"),
) -> OptionContract:
    return OptionContract(
        symbol=symbol,
        underlying="XSP",
        option_type=option_type,
        strike=strike,
        expiration=date(2026, 3, 18),
        bid=bid,
        ask=ask,
        last=(bid + ask) / 2,
        volume=100,
        open_interest=500,
        greeks=Greeks(
            delta=delta,
            gamma=Decimal("0.05"),
            theta=Decimal("-0.10"),
            vega=Decimal("0.08"),
            implied_volatility=Decimal("0.20"),
        ),
    )


def _make_chain() -> OptionsChain:
    calls = [
        _make_option("XSP_C660", OptionType.CALL, Decimal("660"), Decimal("0.50"), Decimal("5.00"), Decimal("5.20")),
        _make_option("XSP_C665", OptionType.CALL, Decimal("665"), Decimal("0.40"), Decimal("3.00"), Decimal("3.20")),
        _make_option("XSP_C670", OptionType.CALL, Decimal("670"), Decimal("0.30"), Decimal("1.80"), Decimal("2.00")),
        _make_option("XSP_C675", OptionType.CALL, Decimal("675"), Decimal("0.20"), Decimal("0.80"), Decimal("1.00")),
        _make_option("XSP_C680", OptionType.CALL, Decimal("680"), Decimal("0.10"), Decimal("0.30"), Decimal("0.45")),
    ]
    puts = [
        _make_option("XSP_P650", OptionType.PUT, Decimal("650"), Decimal("-0.10"), Decimal("0.30"), Decimal("0.45")),
        _make_option("XSP_P655", OptionType.PUT, Decimal("655"), Decimal("-0.20"), Decimal("0.80"), Decimal("1.00")),
        _make_option("XSP_P660", OptionType.PUT, Decimal("660"), Decimal("-0.30"), Decimal("1.80"), Decimal("2.00")),
        _make_option("XSP_P665", OptionType.PUT, Decimal("665"), Decimal("-0.40"), Decimal("3.00"), Decimal("3.20")),
        _make_option("XSP_P670", OptionType.PUT, Decimal("670"), Decimal("-0.50"), Decimal("5.00"), Decimal("5.20")),
    ]
    return OptionsChain(
        underlying="XSP",
        expiration=date(2026, 3, 18),
        underlying_price=Decimal("665.00"),
        calls=calls,
        puts=puts,
    )


def _make_market_event(chain: OptionsChain | None = None) -> MarketEvent:
    bar = Bar(
        symbol="XSP",
        timestamp=datetime(2026, 3, 18, 10, 30),
        open=Decimal("665"), high=Decimal("666"),
        low=Decimal("664"), close=Decimal("665"), volume=5000,
    )
    return MarketEvent(bar=bar, options_chain=chain or _make_chain())


class TestDebitSpreadStrategy:
    def _make_strategy(self, direction: str = "call") -> DebitSpreadStrategy:
        return DebitSpreadStrategy(
            name="test_debit_spread",
            symbol="XSP",
            direction=direction,
            long_delta=Decimal("0.40"),
            short_delta=Decimal("0.20"),
            max_debit=Decimal("3.00"),
            entry_earliest=time(9, 45),
            entry_latest=time(14, 0),
        )

    def test_call_spread_generates_two_legs(self):
        strategy = self._make_strategy(direction="call")
        event = _make_market_event()
        signals = strategy.evaluate(event)
        assert len(signals) == 1
        signal = signals[0]
        assert signal.spread_type == SpreadType.DEBIT_SPREAD
        assert len(signal.legs) == 2
        assert signal.strategy_name == "test_debit_spread"
        assert signal.symbol == "XSP"

    def test_put_spread_generates_signal(self):
        strategy = self._make_strategy(direction="put")
        event = _make_market_event()
        signals = strategy.evaluate(event)
        assert len(signals) == 1
        signal = signals[0]
        assert signal.spread_type == SpreadType.DEBIT_SPREAD
        assert len(signal.legs) == 2

    def test_no_signal_when_position_open(self):
        strategy = self._make_strategy()
        event = _make_market_event()
        strategy.evaluate(event)
        signals = strategy.evaluate(event)
        assert len(signals) == 0

    def test_no_signal_when_no_chain(self):
        strategy = self._make_strategy()
        bar = Bar(
            symbol="XSP",
            timestamp=datetime(2026, 3, 18, 10, 30),
            open=Decimal("665"), high=Decimal("666"),
            low=Decimal("664"), close=Decimal("665"), volume=10000,
        )
        event = MarketEvent(bar=bar, options_chain=None)
        signals = strategy.evaluate(event)
        assert len(signals) == 0

    def test_no_signal_outside_time_window(self):
        strategy = self._make_strategy()
        bar = Bar(
            symbol="XSP",
            timestamp=datetime(2026, 3, 18, 15, 30),
            open=Decimal("665"), high=Decimal("666"),
            low=Decimal("664"), close=Decimal("665"), volume=10000,
        )
        event = MarketEvent(bar=bar, options_chain=_make_chain())
        signals = strategy.evaluate(event)
        assert len(signals) == 0

    def test_no_signal_wrong_symbol(self):
        strategy = self._make_strategy()
        bar = Bar(
            symbol="SPY",
            timestamp=datetime(2026, 3, 18, 10, 30),
            open=Decimal("665"), high=Decimal("666"),
            low=Decimal("664"), close=Decimal("665"), volume=10000,
        )
        event = MarketEvent(bar=bar, options_chain=_make_chain())
        signals = strategy.evaluate(event)
        assert len(signals) == 0

    def test_direction_must_be_call_or_put(self):
        with pytest.raises(ValueError, match="direction"):
            DebitSpreadStrategy(
                name="bad",
                symbol="XSP",
                direction="butterfly",
                long_delta=Decimal("0.40"),
                short_delta=Decimal("0.20"),
                max_debit=Decimal("3.00"),
                entry_earliest=time(9, 45),
                entry_latest=time(14, 0),
            )

    def test_no_signal_when_debit_too_expensive(self):
        strategy = DebitSpreadStrategy(
            name="test_expensive",
            symbol="XSP",
            direction="call",
            long_delta=Decimal("0.40"),
            short_delta=Decimal("0.20"),
            max_debit=Decimal("0.01"),  # impossibly low
            entry_earliest=time(9, 45),
            entry_latest=time(14, 0),
        )
        event = _make_market_event()
        signals = strategy.evaluate(event)
        assert len(signals) == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_debit_spread.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tradebot.strategy.strategies.debit_spread'`

- [ ] **Step 3: Implement DebitSpreadStrategy**

`src/tradebot/strategy/strategies/debit_spread.py`:
```python
"""Debit spread strategy — buys a vertical spread for directional exposure."""
from datetime import time
from decimal import Decimal

import structlog

from tradebot.core.enums import OrderSide, SpreadType
from tradebot.core.events import MarketEvent, SignalEvent
from tradebot.core.models import OptionContract, OptionsChain, OrderLeg
from tradebot.strategy.base import TradingStrategy

logger = structlog.get_logger()


class DebitSpreadStrategy(TradingStrategy):
    """Buy a vertical spread for directional exposure with defined risk.

    - direction="call": bull call spread (buy lower call, sell higher call)
    - direction="put": bear put spread (buy higher put, sell lower put)
    """

    def __init__(
        self,
        name: str,
        symbol: str,
        direction: str,
        long_delta: Decimal,
        short_delta: Decimal,
        max_debit: Decimal,
        entry_earliest: time,
        entry_latest: time,
    ) -> None:
        super().__init__(name=name, symbol=symbol)
        if direction not in ("call", "put"):
            raise ValueError(f"direction must be 'call' or 'put', got '{direction}'")
        self.direction = direction
        self.long_delta = long_delta
        self.short_delta = short_delta
        self.max_debit = max_debit
        self.entry_earliest = entry_earliest
        self.entry_latest = entry_latest
        self._has_position = False

    def evaluate(self, event: MarketEvent) -> list[SignalEvent]:
        if self._has_position:
            return []
        if event.options_chain is None:
            return []
        if event.bar.symbol != self.symbol:
            return []

        current_time = event.bar.timestamp.time()
        if not (self.entry_earliest <= current_time <= self.entry_latest):
            return []

        legs = self._select_strikes(event.options_chain)
        if legs is None:
            logger.info("debit_spread_skip", reason="no_valid_strikes_or_debit_too_high")
            return []

        debit = self._estimate_debit(event.options_chain, legs)

        self._has_position = True
        return [
            SignalEvent(
                strategy_name=self.name,
                spread_type=SpreadType.DEBIT_SPREAD,
                symbol=self.symbol,
                legs=legs,
                target_price=debit,
            )
        ]

    def _select_strikes(self, chain: OptionsChain) -> list[OrderLeg] | None:
        if self.direction == "call":
            return self._select_call_spread(chain)
        return self._select_put_spread(chain)

    def _find_closest_by_delta(
        self, contracts: list[OptionContract], target_delta: Decimal
    ) -> OptionContract | None:
        if not contracts:
            return None
        return min(contracts, key=lambda c: abs(c.greeks.delta - target_delta))

    def _select_call_spread(self, chain: OptionsChain) -> list[OrderLeg] | None:
        # Buy call closer to ATM (higher delta), sell call further OTM (lower delta)
        long_call = self._find_closest_by_delta(chain.calls, self.long_delta)
        short_call = self._find_closest_by_delta(chain.calls, self.short_delta)
        if long_call is None or short_call is None:
            return None
        if long_call.strike >= short_call.strike:
            return None

        debit = long_call.ask - short_call.bid
        if debit > self.max_debit:
            return None

        return [
            OrderLeg(option_symbol=long_call.symbol, side=OrderSide.BUY_TO_OPEN, quantity=1),
            OrderLeg(option_symbol=short_call.symbol, side=OrderSide.SELL_TO_OPEN, quantity=1),
        ]

    def _select_put_spread(self, chain: OptionsChain) -> list[OrderLeg] | None:
        # Buy put closer to ATM (higher absolute delta), sell put further OTM
        long_put = self._find_closest_by_delta(chain.puts, -self.long_delta)
        short_put = self._find_closest_by_delta(chain.puts, -self.short_delta)
        if long_put is None or short_put is None:
            return None
        if long_put.strike <= short_put.strike:
            return None

        debit = long_put.ask - short_put.bid
        if debit > self.max_debit:
            return None

        return [
            OrderLeg(option_symbol=long_put.symbol, side=OrderSide.BUY_TO_OPEN, quantity=1),
            OrderLeg(option_symbol=short_put.symbol, side=OrderSide.SELL_TO_OPEN, quantity=1),
        ]

    def _estimate_debit(self, chain: OptionsChain, legs: list[OrderLeg]) -> Decimal:
        """Estimate net debit from mid prices."""
        debit = Decimal("0")
        all_contracts = {c.symbol: c for c in chain.calls + chain.puts}
        for leg in legs:
            contract = all_contracts.get(leg.option_symbol)
            if contract is None:
                continue
            if leg.side in (OrderSide.BUY_TO_OPEN, OrderSide.BUY_TO_CLOSE):
                debit += contract.mid_price
            else:
                debit -= contract.mid_price
        return debit
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_debit_spread.py -v`
Expected: PASS — all 8 tests

- [ ] **Step 5: Create example strategy config**

`config/strategies/xsp_debit_spread_call.yaml`:
```yaml
strategy:
  name: "xsp_0dte_debit_spread_call"
  class: "DebitSpreadStrategy"
  enabled: true

market:
  symbol: "XSP"
  expiration: "0dte"

entry:
  direction: "call"
  time_window:
    earliest: "09:45"
    latest: "14:00"
  strike_selection:
    method: "delta"
    long_delta: 0.40
    short_delta: 0.20
  max_debit: 3.00

exit:
  profit_target_pct: 100
  stop_loss_pct: 75
  time_exit: "15:45"
  prefer_expire: true

position_sizing:
  method: "fixed_risk"
  max_risk_per_trade: 250
  max_contracts: 2

risk:
  max_daily_trades: 1
  pdt_aware: true
```

- [ ] **Step 6: Commit**

```bash
git add src/tradebot/strategy/strategies/debit_spread.py tests/unit/test_debit_spread.py config/strategies/xsp_debit_spread_call.yaml
git commit -m "feat: add debit spread strategy with tests and example config"
```

---

### Task 4: Register New Strategies in Registry

**Files:**
- Modify: `src/tradebot/strategy/registry.py`
- Create: `tests/unit/test_registry_new_strategies.py`

- [ ] **Step 1: Write failing tests for new strategy registration**

`tests/unit/test_registry_new_strategies.py`:
```python
"""Tests for loading credit and debit spread strategies from YAML."""
from pathlib import Path

from tradebot.strategy.registry import load_strategy
from tradebot.strategy.strategies.credit_spread import CreditSpreadStrategy
from tradebot.strategy.strategies.debit_spread import DebitSpreadStrategy


def test_load_credit_spread(tmp_path: Path):
    config = tmp_path / "credit.yaml"
    config.write_text("""
strategy:
  name: "test_credit"
  class: "CreditSpreadStrategy"
  enabled: true
market:
  symbol: "XSP"
  expiration: "0dte"
entry:
  direction: "put"
  time_window:
    earliest: "09:45"
    latest: "14:00"
  strike_selection:
    method: "delta"
    short_delta: 0.15
    wing_width: 5
  min_credit: 0.15
exit:
  profit_target_pct: 50
  stop_loss_pct: 200
  time_exit: "15:45"
  prefer_expire: true
position_sizing:
  method: "fixed_risk"
  max_risk_per_trade: 250
  max_contracts: 2
risk:
  max_daily_trades: 1
  pdt_aware: true
""")
    strategy = load_strategy(config)
    assert isinstance(strategy, CreditSpreadStrategy)
    assert strategy.name == "test_credit"
    assert strategy.symbol == "XSP"
    assert strategy.direction == "put"


def test_load_debit_spread(tmp_path: Path):
    config = tmp_path / "debit.yaml"
    config.write_text("""
strategy:
  name: "test_debit"
  class: "DebitSpreadStrategy"
  enabled: true
market:
  symbol: "XSP"
  expiration: "0dte"
entry:
  direction: "call"
  time_window:
    earliest: "09:45"
    latest: "14:00"
  strike_selection:
    method: "delta"
    long_delta: 0.40
    short_delta: 0.20
  max_debit: 3.00
exit:
  profit_target_pct: 100
  stop_loss_pct: 75
  time_exit: "15:45"
  prefer_expire: true
position_sizing:
  method: "fixed_risk"
  max_risk_per_trade: 250
  max_contracts: 2
risk:
  max_daily_trades: 1
  pdt_aware: true
""")
    strategy = load_strategy(config)
    assert isinstance(strategy, DebitSpreadStrategy)
    assert strategy.name == "test_debit"
    assert strategy.symbol == "XSP"
    assert strategy.direction == "call"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_registry_new_strategies.py -v`
Expected: FAIL — registry doesn't know about new strategy classes

- [ ] **Step 3: Update registry.py with new strategy loaders**

Update `src/tradebot/strategy/registry.py` to:

```python
"""Strategy factory that loads strategies from config."""
from datetime import time
from decimal import Decimal
from pathlib import Path

from tradebot.strategy.base import TradingStrategy
from tradebot.strategy.strategies.credit_spread import CreditSpreadStrategy
from tradebot.strategy.strategies.debit_spread import DebitSpreadStrategy
from tradebot.strategy.strategies.iron_condor import IronCondorStrategy
from tradebot.utils.config import load_strategy_config

STRATEGY_CLASSES = {
    "IronCondorStrategy": IronCondorStrategy,
    "CreditSpreadStrategy": CreditSpreadStrategy,
    "DebitSpreadStrategy": DebitSpreadStrategy,
}


def load_strategy(config_path: Path) -> TradingStrategy:
    """Load a strategy from its YAML config file."""
    config = load_strategy_config(config_path)

    class_name = config.strategy.class_name
    if class_name not in STRATEGY_CLASSES:
        raise ValueError(f"Unknown strategy class: {class_name}")

    cls = STRATEGY_CLASSES[class_name]

    if cls is IronCondorStrategy:
        return IronCondorStrategy(
            name=config.strategy.name,
            symbol=config.market.symbol,
            short_call_delta=Decimal(str(config.entry.strike_selection.short_call_delta)),
            short_put_delta=Decimal(str(config.entry.strike_selection.short_put_delta)),
            wing_width=Decimal(str(config.entry.strike_selection.wing_width)),
            min_credit=Decimal(str(config.entry.min_credit)),
            entry_earliest=time.fromisoformat(config.entry.time_window.earliest),
            entry_latest=time.fromisoformat(config.entry.time_window.latest),
        )

    if cls is CreditSpreadStrategy:
        return CreditSpreadStrategy(
            name=config.strategy.name,
            symbol=config.market.symbol,
            direction=config.entry.direction,
            short_delta=Decimal(str(config.entry.strike_selection.short_delta)),
            wing_width=Decimal(str(config.entry.strike_selection.wing_width)),
            min_credit=Decimal(str(config.entry.min_credit)),
            entry_earliest=time.fromisoformat(config.entry.time_window.earliest),
            entry_latest=time.fromisoformat(config.entry.time_window.latest),
        )

    if cls is DebitSpreadStrategy:
        return DebitSpreadStrategy(
            name=config.strategy.name,
            symbol=config.market.symbol,
            direction=config.entry.direction,
            long_delta=Decimal(str(config.entry.strike_selection.long_delta)),
            short_delta=Decimal(str(config.entry.strike_selection.short_delta)),
            max_debit=Decimal(str(config.entry.max_debit)),
            entry_earliest=time.fromisoformat(config.entry.time_window.earliest),
            entry_latest=time.fromisoformat(config.entry.time_window.latest),
        )

    raise ValueError(f"No loader for strategy class: {class_name}")
```

- [ ] **Step 4: Run all strategy tests**

Run: `uv run pytest tests/unit/test_registry_new_strategies.py tests/unit/test_credit_spread.py tests/unit/test_debit_spread.py tests/unit/test_strategies.py -v`
Expected: PASS — all tests

- [ ] **Step 5: Run full test suite**

Run: `uv run pytest -v`
Expected: All tests pass

- [ ] **Step 6: Commit**

```bash
git add src/tradebot/strategy/registry.py tests/unit/test_registry_new_strategies.py
git commit -m "feat: register credit and debit spread strategies in registry"
```

---

## Chunk 2: Alembic Database Migrations

### Task 5: Initialize Alembic

**Files:**
- Create: `alembic.ini` (at project root)
- Create: `alembic/env.py`
- Create: `alembic/script.py.mako`
- Create: `alembic/versions/` (empty directory)

- [ ] **Step 1: Initialize Alembic in the project**

Run: `uv run alembic init alembic`

This creates the `alembic/` directory and `alembic.ini`.

- [ ] **Step 2: Configure alembic/env.py to use our models and settings**

Modify `alembic/env.py` to import and use our ORM models. The key changes to the generated file:

At the top, after existing imports:
```python
import os
import sys

# Add src to path so we can import tradebot
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from tradebot.persistence.database import Base
from tradebot.persistence import models as _models  # noqa: F401 — registers ORM models

target_metadata = Base.metadata
```

In `run_migrations_online()`, replace the `connectable` setup with:
```python
from sqlalchemy import create_engine
url = os.getenv("DATABASE_URL", config.get_main_option("sqlalchemy.url"))
connectable = create_engine(url)
```

- [ ] **Step 3: Generate initial migration**

Run: `uv run alembic revision --autogenerate -m "initial schema"`

Verify the generated migration creates tables: `trades`, `trade_legs`, `daily_snapshots`, `day_trade_log`.

- [ ] **Step 4: Verify migration applies cleanly**

Run: `rm -f test_alembic.db && DATABASE_URL=sqlite:///test_alembic.db uv run alembic upgrade head && rm test_alembic.db`

Expected: Tables created successfully, no errors.

- [ ] **Step 5: Update main.py to note Alembic manages schema**

In `src/tradebot/main.py`, change:
```python
Base.metadata.create_all(engine)
```
to:
```python
# Schema managed by Alembic — run `alembic upgrade head` to apply migrations
# For development convenience, auto-create tables if they don't exist
Base.metadata.create_all(engine)
```

Keep `create_all` for now so the bot works without running migrations manually during development. The comment documents that Alembic is the canonical migration tool.

- [ ] **Step 6: Commit**

```bash
git add alembic/ alembic.ini src/tradebot/main.py
git commit -m "feat: initialize Alembic migrations with initial schema"
```

---

## Chunk 3: NAV History API & Chart

### Task 6: Repository Methods for NAV History

**Files:**
- Modify: `src/tradebot/persistence/repository.py`
- Modify: `tests/unit/test_persistence.py`

- [ ] **Step 1: Write failing tests for NAV history methods**

Add to `tests/unit/test_persistence.py`:
```python
from tradebot.persistence.models import DailySnapshotRecord


def test_record_daily_snapshot(repo):
    repo.record_daily_snapshot(
        snapshot_date=date(2026, 3, 18),
        nav=Decimal("2550.00"),
        realized_pnl=Decimal("50.00"),
        unrealized_pnl=Decimal("0.00"),
        drawdown=Decimal("0.0"),
        day_trade_count=1,
    )
    history = repo.get_nav_history(days=30)
    assert len(history) == 1
    assert history[0]["date"] == "2026-03-18"
    assert history[0]["nav"] == "2550.00"


def test_get_nav_history_ordered_by_date(repo):
    for i, d in enumerate([date(2026, 3, 16), date(2026, 3, 18), date(2026, 3, 17)]):
        repo.record_daily_snapshot(
            snapshot_date=d,
            nav=Decimal(str(2500 + i * 25)),
            realized_pnl=Decimal("0"),
            unrealized_pnl=Decimal("0"),
            drawdown=Decimal("0"),
            day_trade_count=0,
        )
    history = repo.get_nav_history(days=30)
    dates = [h["date"] for h in history]
    assert dates == ["2026-03-16", "2026-03-17", "2026-03-18"]


def test_get_nav_history_respects_days_limit(repo):
    repo.record_daily_snapshot(
        snapshot_date=date(2025, 1, 1),
        nav=Decimal("2500"),
        realized_pnl=Decimal("0"),
        unrealized_pnl=Decimal("0"),
        drawdown=Decimal("0"),
        day_trade_count=0,
    )
    repo.record_daily_snapshot(
        snapshot_date=date(2026, 3, 18),
        nav=Decimal("2600"),
        realized_pnl=Decimal("0"),
        unrealized_pnl=Decimal("0"),
        drawdown=Decimal("0"),
        day_trade_count=0,
    )
    history = repo.get_nav_history(days=30)
    assert len(history) == 1
    assert history[0]["date"] == "2026-03-18"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_persistence.py -v -k "nav"`
Expected: FAIL — `record_daily_snapshot` and `get_nav_history` don't exist on `Repository`

- [ ] **Step 3: Implement repository methods**

Read `src/tradebot/persistence/repository.py` and add:

```python
def record_daily_snapshot(
    self,
    snapshot_date: date,
    nav: Decimal,
    realized_pnl: Decimal,
    unrealized_pnl: Decimal,
    drawdown: Decimal,
    day_trade_count: int,
) -> None:
    """Record end-of-day portfolio snapshot."""
    snapshot = DailySnapshotRecord(
        snapshot_date=snapshot_date,
        nav=nav,
        realized_pnl=realized_pnl,
        unrealized_pnl=unrealized_pnl,
        drawdown=drawdown,
        day_trade_count=day_trade_count,
    )
    self._session.add(snapshot)
    self._session.flush()

def get_nav_history(self, days: int = 30) -> list[dict]:
    """Get NAV history for the last N days, ordered by date ascending."""
    from datetime import timedelta
    start_date = date.today() - timedelta(days=days)
    stmt = (
        select(DailySnapshotRecord)
        .where(DailySnapshotRecord.snapshot_date >= start_date)
        .order_by(DailySnapshotRecord.snapshot_date.asc())
    )
    snapshots = self._session.execute(stmt).scalars().all()
    return [
        {
            "date": s.snapshot_date.isoformat(),
            "nav": str(s.nav),
            "realized_pnl": str(s.realized_pnl),
            "unrealized_pnl": str(s.unrealized_pnl),
            "drawdown": str(s.drawdown),
            "day_trades": s.day_trade_count,
        }
        for s in snapshots
    ]

def commit(self) -> None:
    """Commit the current session."""
    self._session.commit()
```

Add necessary imports at top: `from datetime import date` and ensure `DailySnapshotRecord` is imported from `tradebot.persistence.models`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_persistence.py -v`
Expected: PASS — all persistence tests including new nav history ones

- [ ] **Step 5: Commit**

```bash
git add src/tradebot/persistence/repository.py tests/unit/test_persistence.py
git commit -m "feat: add NAV history repository methods"
```

---

### Task 7: NAV History API Endpoint

**Files:**
- Modify: `src/tradebot/api/routes/portfolio.py`
- Modify: `tests/unit/test_api.py`

- [ ] **Step 1: Write failing tests for nav-history endpoint**

Add to `tests/unit/test_api.py`:
```python
def test_nav_history_endpoint(client_with_repo):
    response = client_with_repo.get("/api/portfolio/nav-history")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_nav_history_with_days_param(client_with_repo):
    response = client_with_repo.get("/api/portfolio/nav-history?days=7")
    assert response.status_code == 200


def test_nav_history_without_repo(client):
    response = client.get("/api/portfolio/nav-history")
    assert response.status_code == 200
    assert response.json() == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_api.py -v -k "nav_history"`
Expected: FAIL — 404 or similar, endpoint doesn't exist

- [ ] **Step 3: Add the endpoint**

Read `src/tradebot/api/routes/portfolio.py` and add:

```python
@router.get("/portfolio/nav-history")
async def get_nav_history(request: Request, days: int = 30):
    """Get NAV history for chart display."""
    state: AppState = request.app.state.app_state
    if state.repository is None:
        return []
    return state.repository.get_nav_history(days=days)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_api.py -v`
Expected: PASS — all API tests

- [ ] **Step 5: Commit**

```bash
git add src/tradebot/api/routes/portfolio.py tests/unit/test_api.py
git commit -m "feat: add NAV history API endpoint"
```

---

### Task 8: NAV History Chart Component

**Files:**
- Create: `frontend/src/components/NAVChart.tsx`
- Modify: `frontend/src/pages/Dashboard.tsx`

- [ ] **Step 1: Create NAVChart component**

`frontend/src/components/NAVChart.tsx`:
```tsx
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { useApi } from "../hooks/useApi";

interface NavSnapshot {
  date: string;
  nav: string;
  realized_pnl: string;
  unrealized_pnl: string;
  drawdown: string;
  day_trades: number;
}

interface ChartPoint {
  date: string;
  nav: number;
  drawdown: number;
}

export function NAVChart() {
  const { data: history } = useApi<NavSnapshot[]>(
    "/api/portfolio/nav-history?days=30",
    60000
  );

  if (!history || history.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-500">
        No NAV history yet. Data will appear after the first trading day.
      </div>
    );
  }

  const chartData: ChartPoint[] = history.map((item) => ({
    date: new Date(item.date).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
    }),
    nav: parseFloat(item.nav),
    drawdown: parseFloat(item.drawdown),
  }));

  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
        <XAxis dataKey="date" stroke="#9ca3af" fontSize={12} />
        <YAxis
          yAxisId="nav"
          stroke="#4ade80"
          fontSize={12}
          tickFormatter={(v: number) => `$${v.toFixed(0)}`}
        />
        <YAxis
          yAxisId="dd"
          orientation="right"
          stroke="#f87171"
          fontSize={12}
          tickFormatter={(v: number) => `${v.toFixed(1)}%`}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: "#1f2937",
            border: "1px solid #374151",
            borderRadius: "0.5rem",
            color: "#f3f4f6",
          }}
          formatter={(value: number, name: string) => {
            if (name === "NAV") return [`$${value.toFixed(2)}`, name];
            return [`${value.toFixed(2)}%`, name];
          }}
        />
        <Line
          yAxisId="nav"
          type="monotone"
          dataKey="nav"
          stroke="#4ade80"
          strokeWidth={2}
          dot={false}
          name="NAV"
        />
        <Line
          yAxisId="dd"
          type="monotone"
          dataKey="drawdown"
          stroke="#f87171"
          strokeWidth={1}
          dot={false}
          name="Drawdown"
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
```

- [ ] **Step 2: Add NAVChart to Dashboard page**

Read `frontend/src/pages/Dashboard.tsx` and add the chart after the stat cards, before the open positions section:

```tsx
// Add import at top:
import { NAVChart } from "../components/NAVChart";

// Add in the JSX, after stat cards section:
<div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
  <h2 className="text-lg font-semibold text-gray-100 mb-4">
    NAV History (30 Days)
  </h2>
  <NAVChart />
</div>
```

- [ ] **Step 3: Verify frontend builds**

Run: `cd frontend && npm run build`
Expected: Build succeeds with no errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/NAVChart.tsx frontend/src/pages/Dashboard.tsx
git commit -m "feat: add NAV history chart to dashboard"
```

---

### Task 9: Daily Snapshot Recording in Bot Loop

**Files:**
- Modify: `src/tradebot/main.py`

- [ ] **Step 1: Read main.py to understand the current bot loop**

Read `src/tradebot/main.py` and identify where to add end-of-day snapshot logic inside `bot_loop()`.

- [ ] **Step 2: Add daily snapshot recording**

Add logic to `bot_loop()` that records a daily snapshot near end of day. Add a `snapshot_taken_today` flag before the while loop to prevent duplicates.

Inside the while loop, after processing events and before the sleep:

```python
from datetime import datetime, time as dt_time

# Before the while loop:
snapshot_taken_today = False

# Inside the while loop, after event processing:
now = datetime.now().time()
if now >= dt_time(15, 50) and not snapshot_taken_today and state.repository:
    try:
        state.repository.record_daily_snapshot(
            snapshot_date=date.today(),
            nav=state.portfolio.nav,
            realized_pnl=state.portfolio.daily_pnl,
            unrealized_pnl=Decimal("0"),
            drawdown=state.portfolio.drawdown_pct,
            day_trade_count=state.pdt_day_trades_used,
        )
        state.repository.commit()
        snapshot_taken_today = True
        logger.info("daily_snapshot_recorded", nav=str(state.portfolio.nav))
    except Exception as e:
        logger.error("daily_snapshot_error", error=str(e))
```

Note: Use `state.repository.commit()` (the public method added in Task 6), NOT `state.repository._session.commit()`.

- [ ] **Step 3: Run full test suite**

Run: `uv run pytest -v`
Expected: All tests pass

- [ ] **Step 4: Commit**

```bash
git add src/tradebot/main.py
git commit -m "feat: record daily NAV snapshot at end of trading day"
```

---

### Task 10: Final Integration Verification

- [ ] **Step 1: Run full backend test suite**

Run: `uv run pytest -v --tb=short`
Expected: All tests pass

- [ ] **Step 2: Run ruff linter**

Run: `uv run ruff check src/ tests/`
Expected: No errors (or fix any that appear)

- [ ] **Step 3: Verify frontend builds**

Run: `cd frontend && npm run build`
Expected: Build succeeds

- [ ] **Step 4: Verify Docker build**

Run: `docker compose build`
Expected: Both backend and frontend containers build successfully

- [ ] **Step 5: Commit any remaining fixes**

```bash
git add -A
git commit -m "chore: lint fixes and integration verification"
```
