# Tradebot: 0DTE Options Trading Bot — Design Spec

> **Date:** 2026-03-16
> **Status:** Draft
> **Author:** Claude + Ian

---

## 1. Overview

A custom Python trading bot for 0DTE options strategies on cash-settled index
options (XSP/SPX). The bot uses an event-driven architecture with swappable
strategy configurations, PDT-aware risk management, and a React web dashboard.

**Starting conditions:**
- Paper trading only (Tradier sandbox)
- $2,500 simulated starting capital
- 0DTE strategies: iron condors, credit spreads, debit spreads on XSP
- Sub-$25K account → PDT rules apply

**End goal:** A system the owner can trust enough to graduate from paper trading
to live trading with real money, using the same codebase with only a config
change.

---

## 2. Architecture

### 2.1 Event-Driven Pipeline

Data flows in one direction through the system:

```
Market Data → Strategy Engine → Risk Manager → Order Manager → Broker API
                                                                    ↓
Dashboard ← Portfolio Tracker ← ← ← ← ← ← ← ← ← ← ← Fill Events
```

Components communicate via an async event queue (`asyncio.Queue`). Each
component consumes events it cares about and produces events for the next stage.
This same pipeline works for both backtesting (replay historical events) and
live trading (real-time events from WebSocket).

### 2.2 Event Types

| Event | Produced By | Consumed By |
|---|---|---|
| `MarketEvent` | Market Data Handler | Strategy Engine |
| `SignalEvent` | Strategy Engine | Risk Manager |
| `OrderEvent` | Risk Manager | Order Manager |
| `FillEvent` | Broker / Order Manager | Portfolio Tracker |
| `RiskEvent` | Risk Manager | Logging, Dashboard |

### 2.3 Core Components

| Component | Responsibility |
|---|---|
| **Market Data Handler** | Connects to data APIs, normalizes into internal bar/tick/options-chain format, emits `MarketEvent`s |
| **Strategy Engine** | Loads strategy configs (YAML), runs indicator calculations, emits `SignalEvent`s |
| **Risk Manager** | Chain of checks — PDT tracking, position size limits, daily loss cap, max drawdown. Can reject or modify signals. |
| **Order Manager** | Converts signals into broker-specific multi-leg orders, tracks order lifecycle |
| **Portfolio Tracker** | Tracks positions, P&L (realized + unrealized), Greeks exposure, persists to database |
| **Web Dashboard** | FastAPI + React SPA — portfolio view, trade history, strategy status |

### 2.4 Broker Abstraction

A common `Broker` interface with implementations for:

- **`TradierBroker`** — options via Tradier API (sandbox for paper, live later).
  This is the primary broker for the initial build since all three starter
  strategies are pure options plays on cash-settled indices.
- **`SimulatedBroker`** — local simulated fills for offline backtesting when
  no API connection is available.
- **`AlpacaBroker`** — equities via Alpaca API. Deferred to a future phase
  when equity strategies are added.

The `TradierBroker` handles both paper and live trading — the only difference
is the base URL (sandbox vs production) and API credentials, controlled by
config.

**Broker interface (key methods):**

```python
class Broker(Protocol):
    async def get_account(self) -> Account: ...
    async def get_positions(self) -> list[Position]: ...
    async def get_options_chain(self, symbol: str, expiration: date) -> OptionsChain: ...
    async def submit_order(self, order: Order) -> OrderResult: ...
    async def submit_multileg_order(self, legs: list[OrderLeg], price: Decimal) -> OrderResult: ...
    async def cancel_order(self, order_id: str) -> None: ...
    async def get_order_status(self, order_id: str) -> OrderStatus: ...
```

Multi-leg order submission is first-class because iron condors require atomic
4-leg submission. Tradier supports this natively via their `multileg` order
type.

**Financial precision:** All monetary values use `Decimal` throughout the
system to avoid floating-point rounding errors. This applies to prices,
P&L calculations, position sizing, and risk checks.

### 2.5 Event Bus Topology

A single `asyncio.Queue` with type-based dispatch. The event loop pulls events
from the queue and routes them to the appropriate handler based on event type:

```python
handlers = {
    MarketEvent: strategy_engine.on_market_event,
    SignalEvent: risk_manager.on_signal,
    OrderEvent: order_manager.on_order,
    FillEvent: portfolio_tracker.on_fill,
}

while running:
    event = await queue.get()
    handler = handlers[type(event)]
    new_events = await handler(event)
    for e in new_events:
        await queue.put(e)
```

The dashboard and logger subscribe as passive observers via a separate observer
list. Every event is passed to all observers *before* dispatch to the primary
handler. Observers receive all event types (including `RiskEvent`) but do not
produce events that feed back into the pipeline.

```python
for observer in observers:     # logger, dashboard, etc.
    await observer.on_event(event)
handler = handlers.get(type(event))
if handler:
    new_events = await handler(event)
```

### 2.6 Backtesting Architecture

Backtesting uses the same event pipeline as live trading, with two swaps:

1. **`HistoricalDataFeed`** replaces the live `MarketDataHandler` — replays
   saved market data as `MarketEvent`s at configurable speed
2. **`SimulatedBroker`** replaces `TradierBroker` — simulates order fills
   locally using historical data (no API calls)

This gives backtest/live parity: the strategy, risk manager, and portfolio
tracker run identical code in both modes. Historical options chain data is
the main constraint — see Section 10 for sourcing considerations.

### 2.7 Options-Specific Considerations

- Multi-leg order support from day one (iron condors = 4 legs)
- Options chain fetching and strike selection logic (by delta or fixed offset)
- Greeks tracking (delta, theta, gamma) for risk management — sourced from
  Tradier's option quotes (they provide Greeks on each option contract),
  not computed locally. This avoids model divergence issues, especially for
  0DTE where Greeks change rapidly.
- Expiration-aware position management (0DTE positions auto-close or expire at EOD)
- Cash-settled index options (XSP/SPX) — no assignment risk
- Market calendar awareness via `exchange_calendars` library — handles half-days,
  holidays, and market hours. The bot will not attempt to trade outside of
  regular market hours.

---

## 3. Tech Stack

### 3.1 Backend

| Category | Choice | Rationale |
|---|---|---|
| Language | Python 3.12+ | Target language, asyncio for event loop |
| Broker (options) | Tradier (REST via `httpx`) | Best options API, free sandbox, multi-leg support |
| Broker (equities) | Alpaca (`alpaca-py`) — future phase | Deferred until equity strategies are added |
| Market data | Tradier (options chains + underlying quotes) | Comes with broker account |
| Historical data | `yfinance` (prototyping), Polygon.io (later) | Free to start |
| Technical analysis | `pandas-ta` | Pure Python, easy install, pandas-native |
| Async HTTP | `httpx` | Modern, async-native |
| Web framework | FastAPI + WebSocket | Real-time dashboard updates |
| Database | SQLite (dev) → PostgreSQL (prod) | SQLAlchemy 2.0 + Alembic |
| Config | TOML (infrastructure) + YAML (strategies) | TOML in stdlib, YAML for richer nesting |
| Validation | Pydantic v2 | Settings, event models, API schemas |
| Logging | `structlog` | Structured JSON logs |
| Testing | `pytest` + `pytest-asyncio` | Async test support |
| Packaging | `pyproject.toml` + `uv` | Fast dependency management |
| Data handling | `pandas`, `numpy` | Standard |

### 3.2 Frontend

| Category | Choice | Rationale |
|---|---|---|
| Framework | React (Vite + TypeScript) | Owner is comfortable with modern JS frameworks |
| Styling | TBD (Tailwind or similar) | Decide during implementation |
| Real-time | WebSocket to FastAPI backend | Live position/P&L updates |

### 3.3 Key Dashboard Pages

- **Dashboard** — NAV chart, open positions, daily P&L, PDT counter
- **Trades** — trade history table with filters
- **Strategies** — strategy status, current signals, config viewer

---

## 4. Strategy Configuration

### 4.1 Config Format

Each strategy gets its own YAML file in `config/strategies/`. Infrastructure
config (API keys, DB, logging, mode) uses TOML.

### 4.2 Example Strategy Config

```yaml
# config/strategies/xsp_iron_condor.yaml
strategy:
  name: "xsp_0dte_iron_condor"
  class: "IronCondorStrategy"
  enabled: true

market:
  symbol: "XSP"
  expiration: "0dte"

entry:
  time_window:
    earliest: "09:45"
    latest: "14:00"
  strike_selection:
    method: "delta"
    short_call_delta: 0.15
    short_put_delta: -0.15
    wing_width: 5
  iv_filter:
    min_iv_rank: 25       # requires historical IV data — see Section 10
  min_credit: 0.30

exit:
  profit_target_pct: 50
  stop_loss_pct: 200
  time_exit: "15:45"
  prefer_expire: true    # prefer expiration over closing when PDT-constrained

position_sizing:
  method: "fixed_risk"
  max_risk_per_trade: 250
  max_contracts: 2

risk:
  max_daily_trades: 1
  pdt_aware: true
```

### 4.3 Starter Strategies

| Strategy | Description | Legs |
|---|---|---|
| **0DTE Iron Condor** | Sell OTM call + put spreads on XSP, collect credit, profit from time decay | 4 |
| **0DTE Credit Spread** | Single-side (bull put or bear call) spread based on directional bias | 2 |
| **0DTE Debit Spread** | Buy a directional spread when a breakout signal triggers | 2 |

Each strategy extends a `TradingStrategy` base class, reads its config from
YAML, and emits `SignalEvent`s. The strategy handles strike selection; the risk
manager and order manager handle validation and execution.

---

## 5. Safety & Guardrails

### 5.1 Risk Manager Checks

Executed in order on every signal:

| Check | Rule | Action on Failure |
|---|---|---|
| `PDTCheck` | Track explicit sell-to-close orders in rolling 5-business-day window. Expirations do NOT count as day trades. | Block trade, or activate `prefer_expire` exit mode |
| `MaxDailyLossCheck` | Track realized + unrealized P&L. Warn at 2%, halt at 3% of account. | Halt new entries for the day |
| `MaxDrawdownCheck` | Track drawdown from portfolio peak. Hard stop at 10%. | Halt bot, require manual restart |
| `PositionSizeCheck` | Max risk per trade (e.g., $250). Max total exposure. | Reject or reduce size |
| `SpreadWidthCheck` | Validate spread width vs account size. | Reject signal |
| `DuplicateCheck` | No second position on same underlying if one is already open. | Reject signal |
| `TimeWindowCheck` | Only allow entries during configured window. | Reject signal |

### 5.2 PDT Rules — Key Nuance

- **Day trade** = you *sell to close* a position opened the same day
- **Not a day trade** = position expires (worthless or ITM cash settlement)
- Sub-$25K margin account: max 3 day trades per rolling 5 business days
- The bot tracks this and factors it into exit decisions:
  - If PDT budget is exhausted, prefer letting 0DTE positions expire over closing early
  - Strategy exit logic knows the PDT budget and adjusts behavior accordingly
- **PDT state is persisted to the database** so it survives bot restarts.
  If the bot restarts on day 3 of a window, it remembers trades from days 1-2.

### 5.3 Paper → Live Graduation

```
Phase 1: Backtest         → Replay historical data through the engine
Phase 2: Paper (sandbox)  → Live market data, simulated fills via Tradier sandbox
Phase 3: Live (tiny)      → Real money, 1 contract max, all guardrails on
Phase 4: Live (scaled)    → Increase size gradually
```

### 5.4 Startup Safety

- Bot logs mode prominently: `>>> PAPER MODE <<<` or `>>> LIVE MODE <<<`
- Live mode requires explicit `--confirm-live` CLI flag
- Kill switch: `POST /api/kill` flattens all positions and halts the bot
  - Closes multi-leg positions as spreads (not individual legs) to maintain
    hedging during close
  - Uses market orders for guaranteed fill (accepts slippage for safety)
  - If triggered after market close, marks positions for close-at-open and
    halts any new activity

### 5.5 Failure Modes and Recovery

| Failure | Recovery |
|---|---|
| **API outage (Tradier down)** | Exponential backoff reconnection. No new orders while disconnected. Existing positions monitored via cached state. |
| **WebSocket disconnect** | Auto-reconnect with gap detection. Re-fetch current state from REST API on reconnect. |
| **Order submitted, no fill confirmation** | Poll order status on timeout. If still pending after configurable threshold, cancel and re-evaluate. |
| **Bot crash with open positions** | On startup: reconcile local state with broker positions via `get_positions()`. Detect orphaned positions and alert operator. |
| **Database unavailable** | Bot continues operating with in-memory state. Log warning. Persist backlog when DB returns. |

### 5.6 Credential Isolation

- `.env.paper` — sandbox API keys
- `.env.live` — real API keys (future)
- `.gitignore` excludes both
- Never stored in the same file

---

## 6. Project Structure

```
tradebot/
├── config/
│   ├── settings.toml
│   ├── settings.paper.toml
│   ├── settings.live.toml
│   └── strategies/
│       ├── xsp_iron_condor.yaml
│       ├── xsp_credit_spread.yaml
│       └── xsp_debit_spread.yaml
├── src/
│   └── tradebot/
│       ├── __init__.py
│       ├── main.py
│       ├── core/
│       │   ├── events.py
│       │   ├── models.py
│       │   └── enums.py
│       ├── data/
│       │   ├── handler.py
│       │   └── sources/
│       │       └── tradier.py     # Options chains + underlying quotes
│       ├── strategy/
│       │   ├── base.py
│       │   ├── registry.py
│       │   └── strategies/
│       │       ├── iron_condor.py
│       │       ├── credit_spread.py
│       │       └── debit_spread.py
│       ├── risk/
│       │   ├── manager.py
│       │   └── checks.py
│       ├── execution/
│       │   ├── order_manager.py
│       │   └── brokers/
│       │       ├── base.py        # Abstract Broker protocol
│       │       ├── tradier.py     # Tradier (sandbox + live)
│       │       └── simulated.py   # Local simulated fills (backtesting)
│       ├── portfolio/
│       │   ├── tracker.py
│       │   └── analytics.py
│       ├── persistence/
│       │   ├── database.py
│       │   ├── models.py
│       │   └── repository.py
│       ├── api/
│       │   ├── app.py
│       │   ├── routes/
│       │   │   ├── portfolio.py
│       │   │   ├── trades.py
│       │   │   └── strategies.py
│       │   └── websocket.py
│       └── utils/
│           ├── config.py
│           └── logging.py
├── frontend/
│   ├── package.json
│   └── src/
│       ├── App.tsx
│       ├── pages/
│       │   ├── Dashboard.tsx
│       │   ├── Trades.tsx
│       │   └── Strategies.tsx
│       └── components/
├── tests/
│   ├── conftest.py
│   ├── unit/
│   │   ├── test_strategies.py
│   │   ├── test_risk_checks.py
│   │   └── test_portfolio.py
│   └── integration/
│       └── test_event_flow.py
├── docs/
├── pyproject.toml
├── .env.example
└── .gitignore
```

---

## 7. Data Models

Key database entities (SQLAlchemy ORM models):

| Entity | Purpose | Key Fields |
|---|---|---|
| `Trade` | A complete trade lifecycle (open → close/expire) | id, strategy, symbol, spread_type, legs[], entry_time, exit_time, entry_price, exit_price, pnl, status |
| `TradeLeg` | Individual option leg within a trade | id, trade_id, option_symbol, side (buy/sell), quantity, strike, option_type (call/put), fill_price |
| `Position` | Currently open position | id, trade_id, legs[], unrealized_pnl, greeks, opened_at |
| `Order` | Order submitted to broker | id, broker_order_id, trade_id, order_type, status, submitted_at, filled_at, fill_price |
| `DayTradeLog` | PDT tracking — explicit sell-to-close events | id, date, order_id, trade_id |
| `DailySnapshot` | End-of-day portfolio snapshot | id, date, nav, realized_pnl, unrealized_pnl, drawdown, day_trade_count |
| `AccountState` | Account balance and buying power | id, timestamp, balance, buying_power, margin_used |

---

## 8. Data Flow Example: 0DTE Iron Condor

A complete lifecycle for a single trade:

1. **Market opens** → `MarketDataHandler` fetches XSP price + options chain
   from Tradier
2. **Strategy evaluates** → Checks current price, IV rank, time of day against
   entry rules
3. **Strike selection** → Strategy selects strikes by delta (e.g., short
   call/put at 0.15 delta, wings $5 wide)
4. **Signal emitted** → `SignalEvent`: "open iron condor, 4 legs, net credit
   target $X"
5. **Risk checks** → `RiskManager` validates: position size, daily loss budget,
   PDT count, existing exposure, spread width vs account
6. **Order submitted** → `OrderManager` constructs multi-leg order → sends to
   Tradier sandbox
7. **Fill received** → `FillEvent` → `PortfolioTracker` records position with
   Greeks
8. **Intraday monitoring** → Track P&L, time decay, check exit rules
   (profit target, stop loss, time exit)
9. **Exit decision** →
   - If profit target hit and PDT budget allows: close early (sell to close)
   - If PDT budget exhausted: let expire if profitable, only close if stop
     loss hit (use one of remaining day trades for loss prevention)
   - If near close (15:45) and still open: close or let expire based on P&L
     and PDT budget
10. **End of day** → Record final P&L, update analytics, log trade summary

---

## 9. Logging & Audit Trail

Every trading-relevant event is logged with timestamps via `structlog`:

- **INFO** — trade signals, order submissions, fills, daily P&L summary,
  strategy decisions (why a trade was entered or skipped)
- **WARNING** — risk limit approaching, reconnection events, PDT budget low
- **ERROR** — order rejections, API errors, data gaps
- **CRITICAL** — circuit breaker triggered, unhandled exceptions

All order state transitions are logged: submitted → acknowledged → partial →
filled / rejected / cancelled. This provides a full audit trail for debugging
and for reviewing trading behavior before going live.

---

## 10. Open Questions / Future Considerations

- **IV rank data source** — IV rank requires 52 weeks of historical IV data.
  Neither Tradier nor Alpaca provides IV rank directly. Options: (a) compute
  from historical options data we collect over time, (b) use a third-party
  source like Polygon or CBOE, (c) use a simpler IV filter (current IV vs
  recent average) as a starting proxy. Start with (c), graduate to (a) as
  we accumulate data.
- **Backtesting historical options data** — Options chain history is expensive.
  May use QuantConnect for backtesting ideas before implementing in the bot.
- **SPX vs XSP** — SPX has better liquidity but 10x the contract size. At
  $2,500 capital, XSP is the only realistic choice. Support both in config.
- **Cash account vs margin account** — Cash accounts avoid PDT but have
  settlement delays. Worth supporting both account types in the risk manager.
- **Alerts** — Slack/Telegram integration for trade notifications. Low priority
  but easy to add.
- **Alpaca for equities** — Add `AlpacaBroker` when equity strategies are
  introduced. Deferred from initial build.
- **Additional brokers** — IBKR as a production broker behind the same
  abstraction layer. Add when graduating to live trading.
- **Additional strategies** — Calendars, diagonals, butterflies. Architecture
  supports these via new strategy files + configs.
