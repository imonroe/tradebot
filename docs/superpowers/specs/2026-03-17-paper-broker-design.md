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
- Margin/buying power simulation (PaperBroker does not enforce margin requirements)
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
- `get_positions() → list[dict]` — Returns `_positions` list. Each position dict uses Tradier-compatible keys: `{"symbol": str, "quantity": int, "cost_basis": float, "date_acquired": str}`
- `get_options_chain(symbol, expiration) → OptionsChain` — Raises `NotImplementedError`. In the paper wiring, market data comes from `PaperDataSource`, not the broker. This method exists only to satisfy the `Broker` protocol.
- `submit_multileg_order(legs, price) → OrderResult` — Instantly fills:
  - Generates order ID (`f"PAPER-{self._next_order_id}"`)
  - Adjusts `_balance` by credit/debit amount (price × 100 × quantity per contract)
  - Adds each leg to `_positions` (sell legs as positive quantity, buy legs as negative — matching Tradier convention)
  - Stores order in `_orders` with status FILLED, including the leg list for reference
  - Returns `OrderResult(broker_order_id=..., status=OrderStatus.FILLED)`
- `submit_order(leg, price) → OrderResult` — Delegates to `submit_multileg_order([leg], price)`
- `cancel_order(order_id) → None` — Sets order status to CANCELLED in `_orders`
- `get_order_status(order_id) → str` — Returns status string from `_orders`

**Position lifecycle:** PaperBroker only tracks positions for `get_positions()` API compatibility. The authoritative position/P&L tracking is done by `PortfolioTracker` via `FillEvent`s — same as with a real broker. Positions are added on fill; closing trades add offsetting entries. No automatic expiration/removal.

### 2. PaperDataSource

**File:** `src/tradebot/data/sources/paper.py`

**Interface:** Implements `DataSource` protocol (see below) — `async def get_quote(symbol) → Bar` and `async def get_options_chain(symbol, expiration) → OptionsChain`

**Price model:**

- Holds mutable `_current_price: Decimal`, initialized from `base_price` parameter (default 570.00)
- Tracks `_previous_price: Decimal` for OHLC derivation
- Each `get_quote()` call applies: `_current_price += Decimal(str(random.gauss(0, 0.3)))` clamped to `[base_price * 0.95, base_price * 1.05]`
- Returns a `Bar` with: open=previous price, close=current price, high=max(open,close)+small random, low=min(open,close)-small random, volume=random integer in `[500_000, 2_000_000]`

**Options chain generation:**

- Generates strikes from `current_price - 20` to `current_price + 20` in $1 increments
- For each strike, creates a call and a put `OptionContract`
- The `expiration` field on generated contracts matches the `expiration` parameter passed to `get_options_chain`
- **Greeks approximation:**
  - `moneyness = (strike - underlying_price) / underlying_price`
  - Call delta: `max(0, min(1, 0.5 - moneyness * 5))` (linear approximation around ATM)
  - Put delta: `call_delta - 1`
  - Gamma: `0.05 * exp(-50 * moneyness²)` (peaked at ATM)
  - Theta: `-0.05 * exp(-50 * moneyness²)` (largest at ATM, always negative)
  - Vega: `0.10 * exp(-50 * moneyness²)`
  - IV: `0.20 + 0.10 * moneyness²` (volatility smile)
- **Pricing formula:**
  - `intrinsic = max(0, underlying - strike)` for calls, `max(0, strike - underlying)` for puts
  - `extrinsic = 0.50 * exp(-50 * moneyness²)` (extrinsic value concentrated near ATM, decays at wings)
  - `mid = intrinsic + extrinsic`
  - Bid: `mid - random.uniform(0.01, 0.03)`, floored at `0.01`
  - Ask: `mid + random.uniform(0.01, 0.03)`
  - Last: `mid` (no trade simulation)
  - Open interest: random integer in `[100, 10000]`, volume: random integer in `[0, 5000]`
- **Option symbol format:** OCC format `XSP{YYMMDD}{C/P}{strike*1000:08d}` to match what the strategy/broker expects

**Deterministic seeding:** Accepts optional `seed` parameter for reproducible runs in tests.

### 3. DataSource Protocol

**File:** `src/tradebot/data/sources/base.py`

Analogous to the `Broker` protocol in `execution/brokers/base.py`:

```python
class DataSource(Protocol):
    async def get_quote(self, symbol: str) -> Bar: ...
    async def get_options_chain(self, symbol: str, expiration: date) -> OptionsChain: ...
```

Both `TradierDataSource` and `PaperDataSource` already satisfy this protocol. `MarketDataHandler` and `DataRecorder` will type-hint against it.

### 4. DataRecorder

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

Serializes to `{output_dir}/{symbol}_{type}_{timestamp}.json` using `dataclasses.asdict()` with a custom JSON encoder that handles `Decimal` (→ `str`), `datetime` (→ ISO format string), and `date` (→ ISO format string). Uses `json.dumps` with the custom encoder.

### 5. Wiring Changes

**`src/tradebot/main.py`:**

- Import `PaperBroker` and `PaperDataSource`
- Branch on `settings.broker_name == "paper"` to select implementations
- Optionally wrap data source with `DataRecorder` if a setting flag is set (default off)

**`src/tradebot/data/handler.py`:**

- Relax type hint from `TradierDataSource` to a protocol or use duck typing (the handler only calls `get_quote` and `get_options_chain`)

**`src/tradebot/utils/config.py`:**

- `broker_name` already exists with default `"tradier"` — no change needed, `main.py` branches on its value
- Add `paper_base_price: Decimal = Decimal("570.00")` to Settings
- Add `record_market_data: bool = False` to Settings

**No other files change.**

### 6. Docker / Config

The default `TRADEBOT_BROKER_NAME=paper` in `.env.paper` or `docker-compose.yml` environment means `docker compose up` works out of the box with zero API keys.

Update `.env.example` to document the new settings.

## Testing Strategy

- **PaperBroker unit tests:** Verify fill logic, balance tracking, position management, order status
- **PaperDataSource unit tests:** Verify chain generation produces valid OptionsChain with correct strike range, delta ordering (calls descending, puts ascending from ATM), price consistency
- **Integration test:** Full pipeline with PaperBroker + PaperDataSource → verify MarketEvent → SignalEvent → OrderEvent → FillEvent flow
- **DataRecorder unit test:** Verify files are written and source is passed through (uses `tmp_path` fixture to avoid polluting project tree)

## File Summary

| File | Action |
|------|--------|
| `src/tradebot/execution/brokers/paper.py` | **New** — PaperBroker |
| `src/tradebot/data/sources/base.py` | **New** — DataSource protocol |
| `src/tradebot/data/sources/paper.py` | **New** — PaperDataSource |
| `src/tradebot/data/sources/recorder.py` | **New** — DataRecorder |
| `src/tradebot/main.py` | **Modify** — broker/data source selection |
| `src/tradebot/data/handler.py` | **Modify** — type hint to DataSource protocol |
| `src/tradebot/utils/config.py` | **Modify** — add paper settings |
| `.env.example` | **Modify** — document new settings |
| `tests/unit/test_paper_broker.py` | **New** — PaperBroker tests |
| `tests/unit/test_paper_data_source.py` | **New** — PaperDataSource tests |
| `tests/unit/test_data_recorder.py` | **New** — DataRecorder tests |
