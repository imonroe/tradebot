# Paper Broker & Synthetic Market Data Design

**Date:** 2026-03-17
**Status:** Draft

## Problem

The tradebot currently hardcodes Tradier for both brokerage and market data. Without a Tradier API key, the bot loop runs but can't fetch data or execute trades. This blocks all end-to-end development and dashboard testing.

## Goal

Enable the full trading pipeline to run without any external API by providing:

1. A `PaperBroker` that simulates order execution locally
2. A `PaperDataSource` that generates synthetic XSP options chain data with random-walk price movement
3. A `DataRecorder` wrapper for capturing real API responses for future replay

## Non-Goals

- Academically accurate option pricing (approximations are fine)
- Slippage/partial fill simulation (instant fill at requested price)
- Replay data source (future work, recorder captures data for it)
- Changes to existing event bus, strategy, risk, or portfolio code

## Architecture

```
PaperDataSource  →  MarketDataHandler  →  EventBus (unchanged)
PaperBroker      →  OrderManager (unchanged)
DataRecorder     →  wraps any DataSource (passthrough)
```

Selection happens in `main.py` based on `settings.broker_name`:

```python
if settings.broker_name == "paper":
    broker = PaperBroker(starting_balance=settings.starting_capital)
    data_source = PaperDataSource(base_price=Decimal("570.00"))
else:
    broker = TradierBroker(...)
    data_source = TradierDataSource(broker)
```

No changes to downstream interfaces. `MarketDataHandler` and `OrderManager` accept either implementation via protocol/duck typing.

## Component Details

### 1. PaperBroker

**File:** `src/tradebot/execution/brokers/paper.py`

**Implements:** `Broker` protocol from `base.py`

**Internal state:**

| Field | Type | Description |
|-------|------|-------------|
| `_balance` | `Decimal` | Current cash balance |
| `_positions` | `list[dict]` | Open positions (Tradier-compatible format) |
| `_orders` | `dict[str, dict]` | Order book keyed by order ID |
| `_next_order_id` | `int` | Auto-incrementing order ID counter |

**Methods:**

- `get_account() → Account` — Returns balance, buying power (= balance), and 0 day trade count
- `get_positions() → list[dict]` — Returns `_positions` list
- `submit_multileg_order(legs, price) → OrderResult` — Instantly fills:
  - Generates order ID (`f"PAPER-{self._next_order_id}"`)
  - Adjusts `_balance` by credit/debit amount (price × 100 × quantity per contract)
  - Adds each leg to `_positions`
  - Stores order in `_orders` with status FILLED
  - Returns `OrderResult(broker_order_id=..., status=OrderStatus.FILLED)`
- `submit_order(leg, price) → OrderResult` — Delegates to `submit_multileg_order([leg], price)`
- `cancel_order(order_id) → None` — Sets order status to CANCELLED in `_orders`
- `get_order_status(order_id) → str` — Returns status string from `_orders`

### 2. PaperDataSource

**File:** `src/tradebot/data/sources/paper.py`

**Interface:** Same as `TradierDataSource` — `get_quote(symbol) → Bar` and `get_options_chain(symbol, expiration) → OptionsChain`

**Price model:**

- Holds mutable `_current_price: Decimal`, initialized from `base_price` parameter (default 570.00)
- Each `get_quote()` call applies: `_current_price += Decimal(str(random.gauss(0, 0.3)))` clamped to `[base_price * 0.95, base_price * 1.05]`
- Returns a `Bar` with OHLCV derived from current price (open=previous, close=current, high/low bracketing)

**Options chain generation:**

- Generates strikes from `current_price - 20` to `current_price + 20` in $1 increments
- For each strike, creates a call and a put `OptionContract`
- **Greeks approximation:**
  - `moneyness = (strike - underlying_price) / underlying_price`
  - Call delta: `max(0, min(1, 0.5 - moneyness * 5))` (linear approximation around ATM)
  - Put delta: `call_delta - 1`
  - Gamma: `0.05 * exp(-50 * moneyness²)` (peaked at ATM)
  - Theta: `-0.05 * exp(-50 * moneyness²)` (largest at ATM, always negative)
  - Vega: `0.10 * exp(-50 * moneyness²)`
  - IV: `0.20 + 0.10 * moneyness²` (volatility smile)
- **Pricing:**
  - Intrinsic value + time value approximation based on IV and days-to-expiration
  - For 0DTE: mostly intrinsic + small extrinsic for near-ATM
  - Bid/ask: mid ± `random.uniform(0.01, 0.03)`
- **Option symbol format:** Follows OCC format `XSP{YYMMDD}{C/P}{strike*1000}` to match what the strategy/broker expects

**Deterministic seeding:** Accepts optional `seed` parameter for reproducible runs in tests.

### 3. DataRecorder

**File:** `src/tradebot/data/sources/recorder.py`

**Wraps:** Any object with `get_quote()` and `get_options_chain()` methods.

**Behavior:**

```python
class DataRecorder:
    def __init__(self, source, output_dir: Path = Path("data/recordings")):
        self._source = source
        self._output_dir = output_dir
        self._output_dir.mkdir(parents=True, exist_ok=True)

    async def get_quote(self, symbol: str) -> Bar:
        bar = await self._source.get_quote(symbol)
        self._save("quote", symbol, bar)
        return bar

    async def get_options_chain(self, symbol: str, expiration: date) -> OptionsChain:
        chain = await self._source.get_options_chain(symbol, expiration)
        self._save("chain", symbol, chain)
        return chain
```

Serializes to `{output_dir}/{symbol}_{type}_{timestamp}.json` using dataclass-to-dict conversion.

### 4. Wiring Changes

**`src/tradebot/main.py`:**

- Import `PaperBroker` and `PaperDataSource`
- Branch on `settings.broker_name == "paper"` to select implementations
- Optionally wrap data source with `DataRecorder` if a setting flag is set (default off)

**`src/tradebot/data/handler.py`:**

- Relax type hint from `TradierDataSource` to a protocol or use duck typing (the handler only calls `get_quote` and `get_options_chain`)

**`src/tradebot/utils/config.py`:**

- Add `paper_base_price: Decimal = Decimal("570.00")` to Settings
- Add `record_market_data: bool = False` to Settings

**No other files change.**

### 5. Docker / Config

The default `TRADEBOT_BROKER_NAME=paper` in `.env.paper` or `docker-compose.yml` environment means `docker compose up` works out of the box with zero API keys.

Update `.env.example` to document the new settings.

## Testing Strategy

- **PaperBroker unit tests:** Verify fill logic, balance tracking, position management, order status
- **PaperDataSource unit tests:** Verify chain generation produces valid OptionsChain with correct strike range, delta ordering (calls descending, puts ascending from ATM), price consistency
- **Integration test:** Full pipeline with PaperBroker + PaperDataSource → verify MarketEvent → SignalEvent → OrderEvent → FillEvent flow
- **DataRecorder unit test:** Verify files are written and source is passed through

## File Summary

| File | Action |
|------|--------|
| `src/tradebot/execution/brokers/paper.py` | **New** — PaperBroker |
| `src/tradebot/data/sources/paper.py` | **New** — PaperDataSource |
| `src/tradebot/data/sources/recorder.py` | **New** — DataRecorder |
| `src/tradebot/main.py` | **Modify** — broker/data source selection |
| `src/tradebot/data/handler.py` | **Modify** — relax type hint |
| `src/tradebot/utils/config.py` | **Modify** — add paper settings |
| `.env.example` | **Modify** — document new settings |
| `tests/unit/test_paper_broker.py` | **New** — PaperBroker tests |
| `tests/unit/test_paper_data_source.py` | **New** — PaperDataSource tests |
| `tests/unit/test_data_recorder.py` | **New** — DataRecorder tests |
