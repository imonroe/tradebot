# Paper Broker & Synthetic Market Data Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable the full trading pipeline to run end-to-end without a Tradier API key by providing a simulated broker and synthetic market data generator.

**Architecture:** Three new modules slot into the existing pipeline — `PaperBroker` replaces `TradierBroker`, `PaperDataSource` replaces `TradierDataSource`, and `DataRecorder` wraps any data source for future replay. Selection is based on `settings.broker_name` in `main.py`. No downstream changes to event bus, strategy, risk, or portfolio code.

**Tech Stack:** Python 3.12, asyncio, dataclasses, `math` stdlib for Greeks approximation, `random` for price walk, `json` for recording serialization. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-03-17-paper-broker-design.md`

---

### Task 1: DataSource Protocol

**Files:**
- Create: `src/tradebot/data/sources/base.py`
- Modify: `src/tradebot/data/handler.py`

- [ ] **Step 1: Create DataSource protocol**

```python
# src/tradebot/data/sources/base.py
"""Abstract data source interface."""
from datetime import date
from typing import Protocol

from tradebot.core.models import Bar, OptionsChain


class DataSource(Protocol):
    async def get_quote(self, symbol: str) -> Bar: ...
    async def get_options_chain(self, symbol: str, expiration: date) -> OptionsChain: ...
```

- [ ] **Step 2: Update MarketDataHandler type hint**

In `src/tradebot/data/handler.py`, change:
```python
from tradebot.data.sources.tradier import TradierDataSource
```
to:
```python
from tradebot.data.sources.base import DataSource
```

And change the `__init__` signature from:
```python
def __init__(self, data_source: TradierDataSource) -> None:
```
to:
```python
def __init__(self, data_source: DataSource) -> None:
```

- [ ] **Step 3: Run existing tests to confirm no regression**

Run: `uv run pytest tests/ -v`
Expected: All 64 tests pass (no behavior change, just a type hint relaxation)

- [ ] **Step 4: Commit**

```bash
git add src/tradebot/data/sources/base.py src/tradebot/data/handler.py
git commit -m "refactor: add DataSource protocol and relax MarketDataHandler type hint"
```

---

### Task 2: PaperBroker

**Files:**
- Create: `tests/unit/test_paper_broker.py`
- Create: `src/tradebot/execution/brokers/paper.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_paper_broker.py
"""Tests for paper broker."""
from datetime import date
from decimal import Decimal

import pytest

from tradebot.core.enums import OrderSide, OrderStatus
from tradebot.core.models import OrderLeg
from tradebot.execution.brokers.paper import PaperBroker


@pytest.fixture
def broker():
    return PaperBroker(starting_balance=Decimal("2500.00"))


async def test_get_account_returns_starting_balance(broker):
    account = await broker.get_account()
    assert account.balance == Decimal("2500.00")
    assert account.buying_power == Decimal("2500.00")
    assert account.day_trade_count == 0


async def test_get_positions_initially_empty(broker):
    positions = await broker.get_positions()
    assert positions == []


async def test_submit_multileg_order_fills_immediately(broker):
    legs = [
        OrderLeg(option_symbol="XSP260317P00560000", side=OrderSide.SELL_TO_OPEN, quantity=1),
        OrderLeg(option_symbol="XSP260317P00555000", side=OrderSide.BUY_TO_OPEN, quantity=1),
    ]
    result = await broker.submit_multileg_order(legs=legs, price=Decimal("0.50"))
    assert result.status == OrderStatus.FILLED
    assert result.broker_order_id.startswith("PAPER-")


async def test_submit_multileg_order_adjusts_balance(broker):
    legs = [
        OrderLeg(option_symbol="XSP260317P00560000", side=OrderSide.SELL_TO_OPEN, quantity=1),
        OrderLeg(option_symbol="XSP260317P00555000", side=OrderSide.BUY_TO_OPEN, quantity=1),
    ]
    await broker.submit_multileg_order(legs=legs, price=Decimal("0.50"))
    account = await broker.get_account()
    # Credit of $0.50 * 100 shares = $50
    assert account.balance == Decimal("2550.00")


async def test_submit_multileg_order_adds_positions(broker):
    legs = [
        OrderLeg(option_symbol="XSP260317P00560000", side=OrderSide.SELL_TO_OPEN, quantity=1),
        OrderLeg(option_symbol="XSP260317P00555000", side=OrderSide.BUY_TO_OPEN, quantity=1),
    ]
    await broker.submit_multileg_order(legs=legs, price=Decimal("0.50"))
    positions = await broker.get_positions()
    assert len(positions) == 2
    symbols = {p["symbol"] for p in positions}
    assert "XSP260317P00560000" in symbols
    assert "XSP260317P00555000" in symbols


async def test_submit_order_delegates_to_multileg(broker):
    leg = OrderLeg(option_symbol="XSP260317C00580000", side=OrderSide.BUY_TO_OPEN, quantity=1)
    result = await broker.submit_order(leg=leg, price=Decimal("1.20"))
    assert result.status == OrderStatus.FILLED
    positions = await broker.get_positions()
    assert len(positions) == 1


async def test_get_order_status(broker):
    legs = [
        OrderLeg(option_symbol="XSP260317P00560000", side=OrderSide.SELL_TO_OPEN, quantity=1),
    ]
    result = await broker.submit_multileg_order(legs=legs, price=Decimal("0.30"))
    status = await broker.get_order_status(result.broker_order_id)
    assert status == "filled"


async def test_cancel_order(broker):
    legs = [
        OrderLeg(option_symbol="XSP260317P00560000", side=OrderSide.SELL_TO_OPEN, quantity=1),
    ]
    result = await broker.submit_multileg_order(legs=legs, price=Decimal("0.30"))
    await broker.cancel_order(result.broker_order_id)
    status = await broker.get_order_status(result.broker_order_id)
    assert status == "cancelled"


async def test_get_options_chain_raises(broker):
    with pytest.raises(NotImplementedError):
        await broker.get_options_chain("XSP", date(2026, 3, 17))


async def test_order_ids_increment(broker):
    leg = OrderLeg(option_symbol="XSP260317C00580000", side=OrderSide.BUY_TO_OPEN, quantity=1)
    r1 = await broker.submit_multileg_order([leg], Decimal("1.00"))
    r2 = await broker.submit_multileg_order([leg], Decimal("1.00"))
    assert r1.broker_order_id != r2.broker_order_id
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_paper_broker.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tradebot.execution.brokers.paper'`

- [ ] **Step 3: Implement PaperBroker**

```python
# src/tradebot/execution/brokers/paper.py
"""Paper broker that simulates order execution locally."""
from datetime import date
from decimal import Decimal

import structlog

from tradebot.core.enums import OrderSide, OrderStatus
from tradebot.core.models import Account, OptionsChain, OrderLeg, OrderResult

logger = structlog.get_logger()


class PaperBroker:
    """Simulates a broker with instant fills and local state tracking."""

    def __init__(self, starting_balance: Decimal) -> None:
        self._balance = starting_balance
        self._positions: list[dict] = []
        self._orders: dict[str, dict] = {}
        self._next_order_id = 1

    async def get_account(self) -> Account:
        return Account(
            balance=self._balance,
            buying_power=self._balance,
            day_trade_count=0,
        )

    async def get_positions(self) -> list[dict]:
        return list(self._positions)

    async def get_options_chain(self, symbol: str, expiration: date) -> OptionsChain:
        raise NotImplementedError(
            "PaperBroker does not provide market data. Use PaperDataSource instead."
        )

    async def submit_multileg_order(
        self, legs: list[OrderLeg], price: Decimal
    ) -> OrderResult:
        order_id = f"PAPER-{self._next_order_id}"
        self._next_order_id += 1

        # Adjust balance: positive price = credit received, negative = debit paid
        quantity = legs[0].quantity if legs else 1
        self._balance += price * 100 * quantity

        # Track positions
        for leg in legs:
            self._positions.append({
                "symbol": leg.option_symbol,
                "quantity": leg.quantity if leg.side in (OrderSide.SELL_TO_OPEN, OrderSide.SELL_TO_CLOSE) else -leg.quantity,
                "cost_basis": float(price / len(legs)),
                "date_acquired": date.today().isoformat(),
            })

        self._orders[order_id] = {
            "status": OrderStatus.FILLED,
            "legs": legs,
            "price": price,
        }

        logger.info(
            "paper_order_filled",
            order_id=order_id,
            legs=len(legs),
            price=str(price),
            balance=str(self._balance),
        )

        return OrderResult(broker_order_id=order_id, status=OrderStatus.FILLED)

    async def submit_order(self, leg: OrderLeg, price: Decimal) -> OrderResult:
        return await self.submit_multileg_order([leg], price)

    async def cancel_order(self, order_id: str) -> None:
        if order_id in self._orders:
            self._orders[order_id]["status"] = OrderStatus.CANCELLED

    async def get_order_status(self, order_id: str) -> str:
        if order_id not in self._orders:
            return "unknown"
        return self._orders[order_id]["status"].value
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_paper_broker.py -v`
Expected: All 10 tests PASS

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_paper_broker.py src/tradebot/execution/brokers/paper.py
git commit -m "feat: add PaperBroker with instant fill simulation"
```

---

### Task 3: PaperDataSource

**Files:**
- Create: `tests/unit/test_paper_data_source.py`
- Create: `src/tradebot/data/sources/paper.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_paper_data_source.py
"""Tests for paper data source with synthetic market data."""
from datetime import date
from decimal import Decimal

from tradebot.core.enums import OptionType
from tradebot.data.sources.paper import PaperDataSource


def _make_source(seed: int = 42) -> PaperDataSource:
    return PaperDataSource(base_price=Decimal("570.00"), seed=seed)


async def test_get_quote_returns_bar():
    source = _make_source()
    bar = await source.get_quote("XSP")
    assert bar.symbol == "XSP"
    assert bar.volume > 0
    assert bar.close > 0


async def test_get_quote_price_changes_between_calls():
    source = _make_source()
    bar1 = await source.get_quote("XSP")
    bar2 = await source.get_quote("XSP")
    # With a random walk, prices should differ (seed 42 produces non-zero drift)
    assert bar1.close != bar2.close


async def test_get_quote_price_stays_within_bounds():
    source = _make_source(seed=1)
    for _ in range(100):
        bar = await source.get_quote("XSP")
    # Price should stay within 5% of base
    assert Decimal("541.50") <= bar.close <= Decimal("598.50")


async def test_get_options_chain_has_calls_and_puts():
    source = _make_source()
    chain = await source.get_options_chain("XSP", date(2026, 3, 17))
    assert len(chain.calls) > 0
    assert len(chain.puts) > 0
    assert chain.underlying == "XSP"
    assert chain.expiration == date(2026, 3, 17)


async def test_get_options_chain_strikes_bracket_underlying():
    source = _make_source()
    chain = await source.get_options_chain("XSP", date(2026, 3, 17))
    strikes = [c.strike for c in chain.calls]
    assert min(strikes) < chain.underlying_price
    assert max(strikes) > chain.underlying_price


async def test_get_options_chain_calls_sorted_by_strike():
    source = _make_source()
    chain = await source.get_options_chain("XSP", date(2026, 3, 17))
    strikes = [c.strike for c in chain.calls]
    assert strikes == sorted(strikes)


async def test_get_options_chain_call_deltas_decrease_with_strike():
    source = _make_source()
    chain = await source.get_options_chain("XSP", date(2026, 3, 17))
    deltas = [c.greeks.delta for c in chain.calls]
    # Deltas should generally decrease as strike increases (higher strike = more OTM)
    assert deltas[0] > deltas[-1]


async def test_get_options_chain_put_deltas_are_negative():
    source = _make_source()
    chain = await source.get_options_chain("XSP", date(2026, 3, 17))
    for put in chain.puts:
        assert put.greeks.delta < 0


async def test_get_options_chain_option_types_correct():
    source = _make_source()
    chain = await source.get_options_chain("XSP", date(2026, 3, 17))
    for call in chain.calls:
        assert call.option_type == OptionType.CALL
    for put in chain.puts:
        assert put.option_type == OptionType.PUT


async def test_get_options_chain_bid_less_than_ask():
    source = _make_source()
    chain = await source.get_options_chain("XSP", date(2026, 3, 17))
    for contract in chain.calls + chain.puts:
        assert contract.bid <= contract.ask


async def test_get_options_chain_occ_symbol_format():
    source = _make_source()
    chain = await source.get_options_chain("XSP", date(2026, 3, 17))
    # OCC format: XSP{YYMMDD}{C/P}{strike*1000:08d}
    call = chain.calls[0]
    assert call.symbol.startswith("XSP260317C")
    put = chain.puts[0]
    assert put.symbol.startswith("XSP260317P")


async def test_deterministic_with_same_seed():
    s1 = _make_source(seed=99)
    s2 = _make_source(seed=99)
    bar1 = await s1.get_quote("XSP")
    bar2 = await s2.get_quote("XSP")
    assert bar1.close == bar2.close
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_paper_data_source.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tradebot.data.sources.paper'`

- [ ] **Step 3: Implement PaperDataSource**

```python
# src/tradebot/data/sources/paper.py
"""Synthetic market data source for paper trading."""
import math
import random
from datetime import date, datetime
from decimal import Decimal

import structlog

from tradebot.core.enums import OptionType
from tradebot.core.models import Bar, Greeks, OptionContract, OptionsChain

logger = structlog.get_logger()


class PaperDataSource:
    """Generates synthetic options chain data with random-walk price movement."""

    def __init__(
        self,
        base_price: Decimal = Decimal("570.00"),
        seed: int | None = None,
    ) -> None:
        self._base_price = base_price
        self._current_price = base_price
        self._previous_price = base_price
        self._rng = random.Random(seed)

    async def get_quote(self, symbol: str) -> Bar:
        """Return a synthetic quote with random-walk price movement."""
        self._previous_price = self._current_price

        # Random walk
        drift = Decimal(str(round(self._rng.gauss(0, 0.3), 4)))
        self._current_price += drift

        # Clamp to ±5% of base
        lower = self._base_price * Decimal("0.95")
        upper = self._base_price * Decimal("1.05")
        self._current_price = max(lower, min(upper, self._current_price))

        open_price = self._previous_price
        close_price = self._current_price
        high = max(open_price, close_price) + Decimal(str(round(self._rng.uniform(0.05, 0.30), 2)))
        low = min(open_price, close_price) - Decimal(str(round(self._rng.uniform(0.05, 0.30), 2)))
        volume = self._rng.randint(500_000, 2_000_000)

        return Bar(
            symbol=symbol,
            timestamp=datetime.now(),
            open=open_price,
            high=high,
            low=low,
            close=close_price,
            volume=volume,
        )

    async def get_options_chain(self, symbol: str, expiration: date) -> OptionsChain:
        """Generate a synthetic options chain around the current price."""
        underlying_price = self._current_price
        calls: list[OptionContract] = []
        puts: list[OptionContract] = []

        # Generate strikes from -20 to +20 around current price (rounded to nearest $1)
        center = int(underlying_price)
        for strike_int in range(center - 20, center + 21):
            strike = Decimal(str(strike_int))
            moneyness = float((strike - underlying_price) / underlying_price)
            moneyness_sq = moneyness * moneyness

            # Greeks approximation
            call_delta = max(0.0, min(1.0, 0.5 - moneyness * 5))
            put_delta = call_delta - 1.0
            gamma = 0.05 * math.exp(-50 * moneyness_sq)
            theta = -0.05 * math.exp(-50 * moneyness_sq)
            vega = 0.10 * math.exp(-50 * moneyness_sq)
            iv = 0.20 + 0.10 * moneyness_sq

            # Pricing
            call_intrinsic = max(Decimal("0"), underlying_price - strike)
            put_intrinsic = max(Decimal("0"), strike - underlying_price)
            extrinsic = Decimal(str(round(0.50 * math.exp(-50 * moneyness_sq), 4)))

            for opt_type, intrinsic, delta in [
                (OptionType.CALL, call_intrinsic, call_delta),
                (OptionType.PUT, put_intrinsic, put_delta),
            ]:
                mid = intrinsic + extrinsic
                spread = Decimal(str(round(self._rng.uniform(0.01, 0.03), 2)))
                bid = max(Decimal("0.01"), mid - spread)
                ask = mid + spread

                # OCC symbol: XSP{YYMMDD}{C/P}{strike*1000:08d}
                type_char = "C" if opt_type == OptionType.CALL else "P"
                occ_symbol = (
                    f"{symbol}{expiration.strftime('%y%m%d')}"
                    f"{type_char}{int(strike * 1000):08d}"
                )

                contract = OptionContract(
                    symbol=occ_symbol,
                    underlying=symbol,
                    option_type=opt_type,
                    strike=strike,
                    expiration=expiration,
                    bid=bid,
                    ask=ask,
                    last=mid,
                    volume=self._rng.randint(0, 5000),
                    open_interest=self._rng.randint(100, 10000),
                    greeks=Greeks(
                        delta=Decimal(str(round(delta, 6))),
                        gamma=Decimal(str(round(gamma, 6))),
                        theta=Decimal(str(round(theta, 6))),
                        vega=Decimal(str(round(vega, 6))),
                        implied_volatility=Decimal(str(round(iv, 6))),
                    ),
                )

                if opt_type == OptionType.CALL:
                    calls.append(contract)
                else:
                    puts.append(contract)

        return OptionsChain(
            underlying=symbol,
            expiration=expiration,
            underlying_price=underlying_price,
            calls=sorted(calls, key=lambda c: c.strike),
            puts=sorted(puts, key=lambda p: p.strike),
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_paper_data_source.py -v`
Expected: All 12 tests PASS

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_paper_data_source.py src/tradebot/data/sources/paper.py
git commit -m "feat: add PaperDataSource with synthetic options chain generation"
```

---

### Task 4: DataRecorder

**Files:**
- Create: `tests/unit/test_data_recorder.py`
- Create: `src/tradebot/data/sources/recorder.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_data_recorder.py
"""Tests for data recorder wrapper."""
import json
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock

from tradebot.core.enums import OptionType
from tradebot.core.models import Bar, Greeks, OptionContract, OptionsChain
from tradebot.data.sources.recorder import DataRecorder


def _mock_source():
    source = AsyncMock()
    source.get_quote.return_value = Bar(
        symbol="XSP",
        timestamp=datetime(2026, 3, 17, 10, 30),
        open=Decimal("570.00"),
        high=Decimal("571.00"),
        low=Decimal("569.00"),
        close=Decimal("570.50"),
        volume=1000000,
    )
    source.get_options_chain.return_value = OptionsChain(
        underlying="XSP",
        expiration=date(2026, 3, 17),
        underlying_price=Decimal("570.00"),
        calls=[
            OptionContract(
                symbol="XSP260317C00570000",
                underlying="XSP",
                option_type=OptionType.CALL,
                strike=Decimal("570"),
                expiration=date(2026, 3, 17),
                bid=Decimal("1.00"),
                ask=Decimal("1.10"),
                last=Decimal("1.05"),
                volume=100,
                open_interest=500,
                greeks=Greeks(
                    delta=Decimal("0.5"),
                    gamma=Decimal("0.05"),
                    theta=Decimal("-0.05"),
                    vega=Decimal("0.10"),
                    implied_volatility=Decimal("0.20"),
                ),
            )
        ],
        puts=[],
    )
    return source


async def test_recorder_passes_through_quote(tmp_path):
    source = _mock_source()
    recorder = DataRecorder(source, output_dir=tmp_path)
    bar = await recorder.get_quote("XSP")
    assert bar.symbol == "XSP"
    assert bar.close == Decimal("570.50")
    source.get_quote.assert_awaited_once_with("XSP")


async def test_recorder_passes_through_chain(tmp_path):
    source = _mock_source()
    recorder = DataRecorder(source, output_dir=tmp_path)
    chain = await recorder.get_options_chain("XSP", date(2026, 3, 17))
    assert chain.underlying == "XSP"
    assert len(chain.calls) == 1
    source.get_options_chain.assert_awaited_once_with("XSP", date(2026, 3, 17))


async def test_recorder_writes_quote_file(tmp_path):
    source = _mock_source()
    recorder = DataRecorder(source, output_dir=tmp_path)
    await recorder.get_quote("XSP")
    files = list(tmp_path.glob("XSP_quote_*.json"))
    assert len(files) == 1
    data = json.loads(files[0].read_text())
    assert data["symbol"] == "XSP"


async def test_recorder_writes_chain_file(tmp_path):
    source = _mock_source()
    recorder = DataRecorder(source, output_dir=tmp_path)
    await recorder.get_options_chain("XSP", date(2026, 3, 17))
    files = list(tmp_path.glob("XSP_chain_*.json"))
    assert len(files) == 1
    data = json.loads(files[0].read_text())
    assert data["underlying"] == "XSP"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_data_recorder.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tradebot.data.sources.recorder'`

- [ ] **Step 3: Implement DataRecorder**

```python
# src/tradebot/data/sources/recorder.py
"""Data source wrapper that records responses to JSON files."""
import dataclasses
import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import structlog

from tradebot.core.models import Bar, OptionsChain
from tradebot.data.sources.base import DataSource

logger = structlog.get_logger()


class _TradebotEncoder(json.JSONEncoder):
    """JSON encoder that handles Decimal, datetime, date, and enums."""

    def default(self, o):
        if isinstance(o, Decimal):
            return str(o)
        if isinstance(o, datetime):
            return o.isoformat()
        if isinstance(o, date):
            return o.isoformat()
        if hasattr(o, "value"):  # Enum
            return o.value
        return super().default(o)


class DataRecorder:
    """Wraps a DataSource and saves each response to a JSON file."""

    def __init__(self, source: DataSource, output_dir: Path = Path("data/recordings")) -> None:
        self._source = source
        self._output_dir = output_dir
        self._output_dir.mkdir(parents=True, exist_ok=True)

    async def get_quote(self, symbol: str) -> Bar:
        bar = await self._source.get_quote(symbol)
        self._save("quote", symbol, dataclasses.asdict(bar))
        return bar

    async def get_options_chain(self, symbol: str, expiration: date) -> OptionsChain:
        chain = await self._source.get_options_chain(symbol, expiration)
        self._save("chain", symbol, dataclasses.asdict(chain))
        return chain

    def _save(self, data_type: str, symbol: str, data: dict) -> None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"{symbol}_{data_type}_{timestamp}.json"
        filepath = self._output_dir / filename
        filepath.write_text(json.dumps(data, cls=_TradebotEncoder, indent=2))
        logger.debug("data_recorded", file=str(filepath))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_data_recorder.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_data_recorder.py src/tradebot/data/sources/recorder.py
git commit -m "feat: add DataRecorder for capturing market data to JSON"
```

---

### Task 5: Config Changes

**Files:**
- Modify: `src/tradebot/utils/config.py`
- Modify: `.env.example`

- [ ] **Step 1: Add paper settings to config**

In `src/tradebot/utils/config.py`, add two fields to the `Settings` class after `tradier_api_token`:

```python
    paper_base_price: Decimal = Decimal("570.00")
    record_market_data: bool = False
```

- [ ] **Step 2: Update .env.example**

Append the following lines to `.env.example` (the file already has `TRADIER_API_TOKEN`):

```
TRADEBOT_BROKER_NAME=paper
TRADEBOT_PAPER_BASE_PRICE=570.00
TRADEBOT_RECORD_MARKET_DATA=false
```

- [ ] **Step 3: Run existing config tests to confirm no regression**

Run: `uv run pytest tests/unit/test_config.py -v`
Expected: All 4 tests PASS

- [ ] **Step 4: Commit**

```bash
git add src/tradebot/utils/config.py .env.example
git commit -m "feat: add paper trading config settings"
```

---

### Task 6: Wire Paper Mode in main.py

**Files:**
- Modify: `src/tradebot/main.py`
- Modify: `.env.paper`

- [ ] **Step 1: Update main.py broker/data source selection**

In `src/tradebot/main.py`, replace the hardcoded broker and data source initialization (lines ~92-106) with:

```python
    # Initialize broker and data source
    if settings.broker_name == "paper":
        from tradebot.execution.brokers.paper import PaperBroker
        from tradebot.data.sources.paper import PaperDataSource

        broker = PaperBroker(starting_balance=settings.starting_capital)
        data_source = PaperDataSource(base_price=settings.paper_base_price)
        logger.info("using_paper_broker", base_price=str(settings.paper_base_price))
    else:
        broker = TradierBroker(
            base_url=settings.broker_base_url,
            api_token=settings.tradier_api_token,
        )
        data_source = TradierDataSource(broker)
```

Also, if `settings.record_market_data` is true, wrap the data source:

```python
    # Optionally wrap data source with recorder
    if settings.record_market_data:
        from tradebot.data.sources.recorder import DataRecorder
        data_source = DataRecorder(data_source)
        logger.info("data_recording_enabled")
```

This block goes right after the broker/data source selection, before `market_data = MarketDataHandler(data_source)`.

- [ ] **Step 2: Update .env.paper to default to paper broker**

Replace the contents of `.env.paper`:

```
TRADIER_API_TOKEN=your_sandbox_token_here
TRADEBOT_BROKER_NAME=paper
```

- [ ] **Step 3: Run full test suite**

Run: `uv run pytest tests/ -v`
Expected: All tests PASS (existing + new)

- [ ] **Step 4: Commit**

```bash
git add src/tradebot/main.py .env.paper
git commit -m "feat: wire paper broker and data source selection in main.py"
```

---

### Task 7: Integration Test — Full Pipeline with Paper Components

**Files:**
- Create: `tests/integration/test_paper_pipeline.py`

- [ ] **Step 1: Write the integration test**

This test verifies the full pipeline: PaperDataSource → MarketEvent → IronCondorStrategy → RiskManager → OrderManager(PaperBroker) → FillEvent → PortfolioTracker.

```python
# tests/integration/test_paper_pipeline.py
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
    """Full pipeline: synthetic data → strategy → risk → paper broker → portfolio."""
    # Setup components
    data_source = PaperDataSource(base_price=Decimal("570.00"), seed=42)
    broker = PaperBroker(starting_balance=Decimal("2500.00"))
    market_data = MarketDataHandler(data_source)
    order_manager = OrderManager(broker)
    portfolio = PortfolioTracker(starting_capital=Decimal("2500.00"))

    # Use 0.30/-0.30 deltas (not the real strategy's 0.15/-0.15) because the
    # synthetic chain only spans ±20 strikes and the linear delta model can't
    # produce 0.15 delta within that range.
    strategy = IronCondorStrategy(
        name="test_paper_ic",
        symbol="XSP",
        short_call_delta=Decimal("0.30"),
        short_put_delta=Decimal("-0.30"),
        wing_width=Decimal("5"),
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
```

- [ ] **Step 2: Run the integration test**

Run: `uv run pytest tests/integration/test_paper_pipeline.py -v`
Expected: PASS

- [ ] **Step 3: Run full test suite to confirm no regressions**

Run: `uv run pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add tests/integration/test_paper_pipeline.py
git commit -m "test: add end-to-end integration test for paper trading pipeline"
```

---

### Task 8: Docker Smoke Test

**Files:** None (manual verification)

- [ ] **Step 1: Rebuild and start Docker stack**

```bash
docker compose down
docker compose up --build -d
```

- [ ] **Step 2: Wait for startup and check backend logs**

```bash
docker logs tradebot-backend-1 --tail 20
```

Expected: Should see `using_paper_broker`, `bot_loop_started`, and `fetching_market_data` log lines. No errors.

- [ ] **Step 3: Verify API health**

```bash
docker exec tradebot-backend-1 python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/api/health').read().decode())"
```

Expected: `{"status":"ok","mode":"paper","bot_running":true}`

- [ ] **Step 4: Verify portfolio endpoint shows data after a few cycles**

Wait ~60s for the bot loop to run, then:

```bash
docker exec tradebot-backend-1 python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/api/portfolio').read().decode())"
```

Expected: JSON with `nav`, `daily_pnl`, `positions` fields. If the strategy triggered, `positions` should be non-empty.

- [ ] **Step 5: Commit any final adjustments if needed**
