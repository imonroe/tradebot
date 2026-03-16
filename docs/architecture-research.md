# Python Trading Bot Architecture Research

> Research compiled for the `tradebot` project. Covers architecture patterns,
> strategy configuration, key components, project structure, safety practices,
> and notable open-source references.

---

## Table of Contents

1. [Architecture Patterns](#1-architecture-patterns)
2. [Strategy Configuration](#2-strategy-configuration)
3. [Key Components of a Trading Bot](#3-key-components-of-a-trading-bot)
4. [Python Project Structure](#4-python-project-structure)
5. [Safety: Paper to Live Trading](#5-safety-paper-to-live-trading)
6. [Notable Open Source Trading Bots](#6-notable-open-source-trading-bots)

---

## 1. Architecture Patterns

### 1.1 Event-Driven Architecture (EDA)

Event-driven architecture is the dominant pattern for trading bots. The system
reacts to discrete events (new tick, bar close, order fill, risk breach) rather
than polling in a loop.

**Core concepts:**

- **Event Queue** -- a central FIFO queue (or async channel) through which all
  components communicate. Common event types:
  - `MarketEvent` -- new OHLCV bar or tick arrives
  - `SignalEvent` -- strategy emits a buy/sell signal
  - `OrderEvent` -- order management creates an order
  - `FillEvent` -- broker confirms execution
  - `RiskEvent` -- risk module triggers a circuit breaker or adjustment
- **Event Loop** -- pulls events from the queue and dispatches them to the
  appropriate handler. In Python this maps naturally to `asyncio`.
- **Loose Coupling** -- components only know about the event types they
  consume/produce, not about each other.

```
MarketData --> [MarketEvent] --> Strategy --> [SignalEvent] --> RiskManager
    --> [OrderEvent] --> OrderManager --> Broker --> [FillEvent] --> Portfolio
```

**Why EDA?**

| Benefit | Explanation |
|---|---|
| Testability | Replay recorded events for deterministic backtests |
| Extensibility | Add a new strategy or data source without touching other modules |
| Real-time ready | `asyncio` event loop handles WebSocket streams naturally |
| Backtesting parity | Same event flow for backtest and live -- reduces "backtest vs live" bugs |

**Implementation options in Python:**

- `asyncio.Queue` for async event passing
- `collections.deque` for synchronous backtesting
- Third-party: `pyee` (EventEmitter), or a lightweight pub/sub built on `asyncio`

### 1.2 Strategy Pattern (Gang of Four)

The Strategy pattern lets you define a family of algorithms (trading strategies),
encapsulate each one, and make them interchangeable at runtime.

```python
from abc import ABC, abstractmethod

class TradingStrategy(ABC):
    """Base class all strategies must implement."""

    @abstractmethod
    def configure(self, config: dict) -> None:
        """Load parameters from config."""
        ...

    @abstractmethod
    def on_bar(self, bar: BarData) -> list[Signal]:
        """Process a new bar and return zero or more signals."""
        ...

    @abstractmethod
    def on_tick(self, tick: TickData) -> list[Signal]:
        """Process a new tick (optional, can be a no-op)."""
        ...
```

- Strategies are loaded by name from config, instantiated via a factory or
  registry, and plugged into the event loop.
- This makes it trivial to run multiple strategies in parallel or A/B test them.

### 1.3 Separation of Concerns

A well-structured trading bot separates into these layers:

| Layer | Responsibility | Talks to |
|---|---|---|
| **Data Ingestion** | Connects to exchanges/brokers, normalizes raw data into internal bar/tick format | Event queue (produces `MarketEvent`) |
| **Signal Generation** | Runs strategy logic on market data, produces buy/sell/hold signals | Event queue (consumes `MarketEvent`, produces `SignalEvent`) |
| **Risk Management** | Validates signals against portfolio exposure, drawdown limits, correlation limits | Event queue (consumes `SignalEvent`, produces `OrderEvent` or `RiskEvent`) |
| **Order Management** | Converts validated signals into exchange-specific orders, tracks order lifecycle | Broker API, event queue |
| **Portfolio Tracking** | Maintains positions, P&L, NAV, trade history | Database, event queue (consumes `FillEvent`) |
| **Monitoring / Dashboard** | Exposes state via API, logs, alerts | All layers (read-only) |

The key rule: **data flows in one direction through the pipeline.** A strategy
never places an order directly -- it emits a signal, which the risk manager
gates, and the order manager executes.

---

## 2. Strategy Configuration

### 2.1 How Popular Frameworks Handle Configuration

| Framework | Config Format | Approach |
|---|---|---|
| **Freqtrade** | JSON (+ Python class) | Global config in `config.json`; strategy params as Python class attributes with `@property` or `IntParameter`/`DecimalParameter` for hyperopt |
| **Jesse** | YAML + Python | Routes defined in `routes.py`; strategy params in YAML or as class attributes |
| **Lean/QuantConnect** | JSON + C#/Python class | Algorithm parameters in JSON config, universe selection in code |
| **Backtrader** | Pure Python | Parameters defined as `params = (('period', 20), ...)` tuple on the strategy class |
| **Zipline** | Pure Python | Parameters passed via `initialize()` function |

**Common pattern:** A two-tier config system:
1. **Infrastructure config** (file-based): exchange credentials, database URLs,
   logging levels, paper/live mode toggle
2. **Strategy config** (file-based or in-code): indicator parameters, entry/exit
   rules, position sizing, risk limits

### 2.2 YAML vs TOML vs JSON for Strategy Config

| Format | Pros | Cons | Best For |
|---|---|---|---|
| **YAML** | Human-readable, supports comments, complex nesting | Whitespace-sensitive, security footguns (`yaml.safe_load` required), implicit type coercion | Strategy configs with many nested parameters |
| **TOML** | Comments, explicit types, no indent ambiguity, Python-native (`tomllib` in 3.11+) | Deeply nested structures get verbose | Infrastructure config, simpler strategy configs |
| **JSON** | Universal, strict schema validation via JSON Schema, fast parsing | No comments, verbose | API-facing configs, Freqtrade-style |

**Recommendation:** Use **TOML** for infrastructure/global config (it is now in
the Python stdlib) and **YAML** for strategy configs where you need richer
nesting. Alternatively, use TOML for everything and keep strategy params flat.

### 2.3 Typical Strategy Configuration Parameters

```yaml
# Example strategy config (YAML)
strategy:
  name: "dual_ma_crossover"
  version: "1.2.0"

symbols:
  - "BTC/USDT"
  - "ETH/USDT"

timeframes:
  primary: "1h"
  confirmation: "4h"

indicators:
  fast_ma:
    type: "EMA"
    period: 12
    source: "close"
  slow_ma:
    type: "SMA"
    period: 26
    source: "close"
  atr:
    period: 14

entry_rules:
  long:
    condition: "fast_ma crosses above slow_ma"
    confirmation: "close > slow_ma on 4h"
  short:
    condition: "fast_ma crosses below slow_ma"
    confirmation: "close < slow_ma on 4h"
    enabled: false  # disable short selling

exit_rules:
  take_profit:
    type: "atr_multiple"
    multiplier: 3.0
  stop_loss:
    type: "atr_multiple"
    multiplier: 1.5
  trailing_stop:
    enabled: true
    activation_profit_pct: 2.0
    trail_pct: 1.0
  time_exit:
    max_bars: 48  # force exit after 48 bars

position_sizing:
  method: "risk_pct"          # risk a % of equity per trade
  risk_per_trade_pct: 1.0     # 1% of equity
  max_position_pct: 10.0      # never more than 10% in one position

risk_limits:
  max_open_positions: 5
  max_daily_loss_pct: 3.0
  max_drawdown_pct: 10.0
  max_correlation: 0.7        # avoid highly correlated positions
```

---

## 3. Key Components of a Trading Bot

### 3.1 Market Data Handler

**Responsibilities:**
- Connect to exchange WebSocket for real-time ticks/order book
- Connect to REST API for historical OHLCV data
- Normalize data into internal `Bar` / `Tick` dataclasses
- Handle reconnection, rate limiting, gap detection

**Design notes:**
- Use `asyncio` + `aiohttp` or `websockets` library for non-blocking I/O
- **CCXT** (`ccxt.async_support`) is the de facto standard for multi-exchange
  support (covers 100+ exchanges)
- Cache historical data in a local database to avoid repeated API calls
- Emit `MarketEvent` into the event queue on each new bar/tick

```python
class MarketDataHandler:
    async def subscribe(self, symbols: list[str], timeframe: str) -> None: ...
    async def get_historical(self, symbol: str, timeframe: str,
                              since: datetime, limit: int) -> list[Bar]: ...
    async def _on_message(self, msg: dict) -> None:
        bar = self._normalize(msg)
        await self.event_queue.put(MarketEvent(bar))
```

### 3.2 Strategy Engine (Signal Generation)

**Responsibilities:**
- Maintain indicator state per symbol/timeframe
- Evaluate entry/exit rules on each new bar
- Emit `SignalEvent` (direction, strength, metadata)

**Design notes:**
- Use **pandas-ta** or **TA-Lib** for indicator calculations
- Keep strategies stateless where possible (easier to test)
- Support "warm-up" period: strategies need N bars of history before generating
  valid signals

### 3.3 Order Management System (OMS)

**Responsibilities:**
- Convert signals into concrete orders (market, limit, stop)
- Submit orders to broker/exchange API
- Track order states: pending, partial, filled, cancelled, rejected
- Handle retries and partial fills

**Design notes:**
- Maintain an in-memory order book synced with the exchange
- Use idempotency keys to prevent duplicate orders on network retries
- Log every order state transition for audit

### 3.4 Risk Management Module

**Responsibilities:**
- Pre-trade checks: position size limits, max open positions, sector exposure
- In-flight checks: drawdown limits, daily loss limits, correlation limits
- Circuit breakers: halt trading on extreme conditions

**Design notes:**
- Risk manager sits **between** the strategy and the OMS -- it can reject,
  modify, or approve signals before they become orders
- Implement as a chain of `RiskCheck` objects (Chain of Responsibility pattern):

```python
class RiskCheck(ABC):
    @abstractmethod
    def check(self, signal: Signal, portfolio: Portfolio) -> Signal | None:
        """Return modified signal or None to reject."""
        ...

class MaxPositionCheck(RiskCheck): ...
class DailyLossCheck(RiskCheck): ...
class DrawdownCheck(RiskCheck): ...
class CorrelationCheck(RiskCheck): ...

class RiskManager:
    def __init__(self, checks: list[RiskCheck]):
        self.checks = checks

    def evaluate(self, signal: Signal, portfolio: Portfolio) -> Signal | None:
        for check in self.checks:
            signal = check.check(signal, portfolio)
            if signal is None:
                return None  # rejected
        return signal
```

### 3.5 Portfolio Tracker

**Responsibilities:**
- Track open positions (entry price, size, unrealized P&L)
- Record closed trades (realized P&L, fees, slippage)
- Compute portfolio-level metrics: NAV, drawdown, Sharpe, win rate
- Persist to database

**Design notes:**
- Update on every `FillEvent`
- Snapshot portfolio state periodically for dashboard/reporting
- Use double-entry bookkeeping for accuracy (debit cash, credit position)

### 3.6 Logging and Monitoring

**Responsibilities:**
- Structured logging of all events (trades, errors, risk breaches)
- Performance metrics (latency, fill rates)
- Alerting on anomalies (strategy stopped, exchange disconnected, drawdown threshold)

**Design notes:**
- Use Python `logging` with structured JSON output (via `structlog` or `python-json-logger`)
- Key log levels:
  - `INFO` -- trade signals, order fills, daily P&L summary
  - `WARNING` -- risk limit approaching, reconnection events
  - `ERROR` -- order rejection, API errors
  - `CRITICAL` -- circuit breaker triggered, unhandled exception
- Send alerts via Slack webhook, Telegram bot, or email for critical events
- Consider Prometheus + Grafana for metrics if running in production

### 3.7 Web Dashboard Considerations

**Purpose:** Monitor bot state, review trades, adjust config, start/stop strategies.

**Architecture options:**

| Approach | Stack | Pros | Cons |
|---|---|---|---|
| **API + SPA** | FastAPI backend + React/Vue frontend | Rich interactivity, real-time via WebSocket | More complexity, two codebases |
| **Server-rendered** | Flask/FastAPI + Jinja2 + HTMX | Simple, one codebase, fast to build | Less interactive |
| **Existing solution** | Freqtrade has FreqUI (Vue-based) | Battle-tested | Tied to Freqtrade |

**Key dashboard pages:**
- **Overview**: NAV curve, daily P&L, open positions
- **Trades**: History table with filters, individual trade details
- **Strategy**: Current signals, indicator values, config editor
- **Risk**: Drawdown chart, exposure heatmap, circuit breaker status
- **Logs**: Filterable log viewer

**Recommended approach for a new project:** Start with **FastAPI** + WebSocket
for real-time updates. Use a simple frontend (HTMX or a minimal React app).
Don't build the dashboard until the core trading engine is solid.

---

## 4. Python Project Structure

### 4.1 Recommended Layout

```
tradebot/
├── config/
│   ├── settings.toml          # Infrastructure config (exchange keys, DB, logging)
│   ├── settings.dev.toml      # Dev overrides
│   ├── settings.prod.toml     # Prod overrides
│   └── strategies/
│       ├── dual_ma.yaml       # Strategy-specific config
│       └── mean_reversion.yaml
├── src/
│   └── tradebot/
│       ├── __init__.py
│       ├── main.py            # Entry point, event loop setup
│       ├── core/
│       │   ├── __init__.py
│       │   ├── events.py      # Event dataclasses (MarketEvent, SignalEvent, etc.)
│       │   ├── models.py      # Domain models (Bar, Tick, Order, Position, Trade)
│       │   └── enums.py       # OrderSide, OrderType, OrderStatus, etc.
│       ├── data/
│       │   ├── __init__.py
│       │   ├── handler.py     # MarketDataHandler
│       │   ├── feed.py        # Historical data feed (for backtesting)
│       │   └── sources/       # Exchange-specific adapters
│       │       ├── __init__.py
│       │       ├── binance.py
│       │       └── alpaca.py
│       ├── strategy/
│       │   ├── __init__.py
│       │   ├── base.py        # Abstract TradingStrategy
│       │   ├── registry.py    # Strategy factory/registry
│       │   └── strategies/
│       │       ├── __init__.py
│       │       ├── dual_ma.py
│       │       └── mean_reversion.py
│       ├── risk/
│       │   ├── __init__.py
│       │   ├── manager.py     # RiskManager (chain of checks)
│       │   └── checks.py      # Individual risk check implementations
│       ├── execution/
│       │   ├── __init__.py
│       │   ├── order_manager.py
│       │   └── brokers/       # Broker-specific adapters
│       │       ├── __init__.py
│       │       ├── base.py    # Abstract broker interface
│       │       ├── paper.py   # Paper trading broker (simulated fills)
│       │       └── live.py    # Live broker (wraps CCXT or native API)
│       ├── portfolio/
│       │   ├── __init__.py
│       │   ├── tracker.py     # Portfolio state management
│       │   └── analytics.py   # Performance metrics (Sharpe, drawdown, etc.)
│       ├── persistence/
│       │   ├── __init__.py
│       │   ├── database.py    # SQLAlchemy engine/session setup
│       │   ├── models.py      # ORM models (Trade, Order, PortfolioSnapshot)
│       │   └── repository.py  # Data access layer
│       ├── api/
│       │   ├── __init__.py
│       │   ├── app.py         # FastAPI app
│       │   ├── routes/
│       │   │   ├── __init__.py
│       │   │   ├── portfolio.py
│       │   │   ├── trades.py
│       │   │   └── strategies.py
│       │   └── websocket.py   # Real-time updates
│       └── utils/
│           ├── __init__.py
│           ├── config.py      # Config loading (TOML/YAML parsing)
│           └── logging.py     # Logging setup
├── tests/
│   ├── conftest.py
│   ├── unit/
│   │   ├── test_strategies.py
│   │   ├── test_risk.py
│   │   └── test_portfolio.py
│   ├── integration/
│   │   └── test_event_flow.py
│   └── backtest/
│       └── test_historical.py
├── scripts/
│   ├── backtest.py            # CLI for running backtests
│   └── download_data.py       # CLI for fetching historical data
├── alembic/                   # Database migrations
│   ├── alembic.ini
│   └── versions/
├── pyproject.toml
├── Dockerfile
└── docker-compose.yml
```

### 4.2 Key Libraries

| Category | Library | Purpose |
|---|---|---|
| **Async runtime** | `asyncio` (stdlib) | Event loop, coroutines, WebSocket handling |
| **Exchange connectivity** | `ccxt` / `ccxt.async_support` | Unified API for 100+ crypto exchanges |
| **Traditional brokers** | `alpaca-trade-api`, `ibapi` | Stocks/futures via Alpaca, Interactive Brokers |
| **HTTP client** | `aiohttp` or `httpx` | Async HTTP requests |
| **WebSocket** | `websockets` | Low-level WebSocket client |
| **Technical analysis** | `pandas-ta`, `ta-lib` | Indicator calculations |
| **Data handling** | `pandas`, `numpy` | DataFrames, numerical operations |
| **Web framework** | `FastAPI` | REST API + WebSocket for dashboard |
| **ORM** | `SQLAlchemy 2.0` | Database models and queries |
| **Migrations** | `Alembic` | Schema migrations |
| **Config** | `tomllib` (stdlib 3.11+), `pyyaml` | Config file parsing |
| **Structured logging** | `structlog` | JSON-formatted structured logs |
| **Testing** | `pytest`, `pytest-asyncio` | Test framework with async support |
| **Task scheduling** | `APScheduler` | Periodic tasks (daily reports, data cleanup) |
| **Serialization** | `pydantic` | Data validation and settings management |

### 4.3 Database Choices

| Stage | Database | Rationale |
|---|---|---|
| **Development** | SQLite | Zero setup, file-based, great for backtesting |
| **Production** | PostgreSQL | Concurrent access, robust, TimescaleDB extension for time-series |
| **Time-series data** | TimescaleDB (Postgres extension) or InfluxDB | Optimized for OHLCV storage and time-range queries |
| **Caching** | Redis | Order state caching, pub/sub for inter-process communication |

Use SQLAlchemy with Alembic so the same ORM code works against both SQLite
(dev) and PostgreSQL (prod) with zero code changes -- just swap the connection
string.

### 4.4 Configuration Management

Use **Pydantic Settings** (`pydantic-settings`) for type-safe config:

```python
from pydantic_settings import BaseSettings
from pydantic import SecretStr

class Settings(BaseSettings):
    # Infrastructure
    mode: str = "paper"  # "paper" or "live"
    db_url: str = "sqlite:///tradebot.db"
    log_level: str = "INFO"

    # Exchange
    exchange_name: str = "binance"
    exchange_api_key: SecretStr = SecretStr("")
    exchange_api_secret: SecretStr = SecretStr("")

    # Risk
    max_daily_loss_pct: float = 3.0
    max_drawdown_pct: float = 10.0

    model_config = {"env_prefix": "TRADEBOT_", "env_file": ".env"}
```

This gives you: TOML/env file loading, environment variable overrides, type
validation, and secret masking in logs -- all out of the box.

---

## 5. Safety: Paper to Live Trading

### 5.1 Circuit Breakers

Circuit breakers automatically halt trading when anomalous conditions are
detected. Implement them as risk checks that can **disable the entire bot**,
not just reject individual signals.

**Must-have circuit breakers:**

| Circuit Breaker | Trigger | Action |
|---|---|---|
| **Max daily loss** | Daily realized + unrealized loss exceeds threshold (e.g., 3%) | Flatten all positions, halt trading for the day |
| **Max drawdown** | Portfolio drawdown from peak exceeds threshold (e.g., 10%) | Halt trading, require manual restart |
| **Rapid loss** | N consecutive losing trades or loss within M minutes | Pause trading for cooldown period |
| **Exchange anomaly** | Extreme spread, missing data, or API errors | Pause until conditions normalize |
| **Fat finger** | Single order exceeds unusual size or price deviation | Reject order, alert operator |

### 5.2 Position Size Limits

```python
# Enforce at multiple levels:
MAX_POSITION_PCT = 10.0      # No single position > 10% of portfolio
MAX_TOTAL_EXPOSURE_PCT = 80.0 # Total exposure never > 80% of portfolio
MIN_ORDER_SIZE_USD = 10.0     # Minimum order to avoid dust
MAX_ORDER_SIZE_USD = 50000.0  # Hard ceiling per order
```

- Enforce these in the risk manager AND in the order manager (defense in depth)
- Log every time a position size is clamped or rejected

### 5.3 Max Daily Loss Limits

- Track realized P&L + unrealized P&L in real time
- When daily loss crosses a warning threshold (e.g., 2%), send an alert
- When daily loss crosses a hard threshold (e.g., 3%), trigger circuit breaker
- Reset the counter at a fixed time each day (e.g., 00:00 UTC)
- Persist the counter so a bot restart mid-day does not reset it

### 5.4 Order Validation

Every order must pass validation before submission:

```python
class OrderValidator:
    def validate(self, order: Order, portfolio: Portfolio) -> Order:
        self._check_symbol_tradeable(order)
        self._check_sufficient_balance(order, portfolio)
        self._check_price_sanity(order)       # within N% of current market
        self._check_size_limits(order)         # min/max position size
        self._check_duplicate(order)           # no duplicate orders within N seconds
        self._check_rate_limit(order)          # max orders per minute
        return order
```

- **Price sanity check**: Reject limit orders more than X% away from the
  current mid price (catches typos and bad data)
- **Duplicate detection**: Prevent the same signal from generating multiple
  orders due to event replay or race conditions
- **Rate limiting**: Cap the number of orders per minute to avoid exchange
  rate limits and runaway behavior

### 5.5 Separation of Paper vs Live Credentials

**Architecture for safe paper-to-live transition:**

```
config/
├── settings.toml          # Shared settings (symbols, timeframes, strategies)
├── settings.paper.toml    # Paper trading: sandbox API keys, paper broker
└── settings.live.toml     # Live trading: real API keys, live broker
```

**Key practices:**

1. **Broker abstraction**: Use the same `Broker` interface for paper and live.
   The paper broker simulates fills locally; the live broker hits the real API.
   Strategy code is identical in both modes.

2. **Environment-based mode selection**: Set `TRADEBOT_MODE=paper` or
   `TRADEBOT_MODE=live` as an environment variable. The bot loads the
   corresponding config overlay.

3. **Credential isolation**:
   - Paper API keys go in `.env.paper`
   - Live API keys go in `.env.live`
   - Never store both in the same file
   - Use a secrets manager (AWS Secrets Manager, Vault, or even OS keychain)
     for live credentials in production

4. **Visual differentiation**: Log the mode prominently at startup:
   ```
   ============================================
   TRADEBOT STARTING IN >>> LIVE <<< MODE
   ============================================
   ```

5. **Graduated rollout**:
   - **Phase 1**: Backtest on historical data -- validate strategy logic
   - **Phase 2**: Paper trade for 2-4 weeks -- validate execution, slippage,
     and real-time behavior
   - **Phase 3**: Live trade with minimal size (e.g., 10% of target) -- validate
     real fills and costs
   - **Phase 4**: Scale to full size

6. **Kill switch**: Implement a manual kill switch (API endpoint, CLI command,
   or even a file-based flag like `touch /tmp/tradebot_halt`) that immediately
   flattens all positions and halts the bot.

---

## 6. Notable Open Source Trading Bots (Python)

### 6.1 Freqtrade

- **URL**: https://github.com/freqtrade/freqtrade
- **Focus**: Crypto trading
- **Language**: Python
- **Key features**:
  - Strategies written as Python classes with `populate_indicators()`,
    `populate_entry_trend()`, `populate_exit_trend()` methods
  - Built-in hyperparameter optimization (Hyperopt) for strategy tuning
  - Backtesting engine with detailed reporting
  - FreqUI -- a Vue.js web dashboard
  - Telegram bot integration for alerts and control
  - Dry-run (paper) mode built in
  - Edge positioning for dynamic position sizing
- **Config format**: JSON
- **Strengths**: Mature, large community, excellent documentation, very
  active development
- **Weaknesses**: Crypto-only, opinionated structure makes custom architectures
  harder

### 6.2 Jesse

- **URL**: https://github.com/jesse-ai/jesse
- **Focus**: Crypto trading (research-oriented)
- **Language**: Python
- **Key features**:
  - Clean strategy API: `should_long()`, `should_short()`, `go_long()`, etc.
  - Built-in support for multiple timeframes and symbols per strategy
  - Genetic algorithm for optimization
  - Candle generation from trade data for custom timeframes
  - Docker-based deployment
- **Config format**: YAML + Python
- **Strengths**: Clean API, good for research and backtesting
- **Weaknesses**: Smaller community than Freqtrade, live trading support less
  mature

### 6.3 Lean (QuantConnect)

- **URL**: https://github.com/QuantConnect/Lean
- **Focus**: Multi-asset (stocks, futures, options, crypto, forex)
- **Language**: C# core, Python and C# algorithm support
- **Key features**:
  - Institutional-grade backtesting engine
  - Universe selection (dynamic asset filtering)
  - Alpha streams for strategy marketplace
  - Cloud execution via QuantConnect platform
  - Extensive data library
- **Strengths**: Multi-asset, enormous data library, professional-grade
- **Weaknesses**: Complex setup for self-hosting, C# core means Python is a
  second-class citizen in some areas

### 6.4 Other Notable Projects

| Project | Focus | Notes |
|---|---|---|
| **Zipline** (`zipline-reloaded`) | Stocks backtesting | Originally by Quantopian, now community-maintained. Great backtesting, limited live trading. |
| **Backtrader** | Multi-asset backtesting | Feature-rich backtesting framework. Less active development but very stable. |
| **Hummingbot** | Crypto market making | Specialized for market making and arbitrage strategies. |
| **VN.PY** | Multi-asset (Asia-focused) | Popular in Chinese quant community, supports many Asian exchanges/brokers. |
| **Nautilus Trader** | Multi-asset, high performance | Written in Cython/Rust for speed. Event-driven, institutional-grade. Newer but very promising. |
| **CCXT** | Exchange connectivity | Not a bot framework, but the standard library for crypto exchange APIs. Almost every Python crypto bot uses it. |

### 6.5 Framework Comparison Summary

| Feature | Freqtrade | Jesse | Lean | Nautilus |
|---|---|---|---|---|
| Language | Python | Python | C#/Python | Python/Cython/Rust |
| Asset classes | Crypto | Crypto | All | All |
| Live trading | Yes | Yes | Yes | Yes |
| Backtesting | Yes | Yes | Yes | Yes |
| Web UI | Yes (FreqUI) | Yes | Cloud | No (API only) |
| Community size | Large | Medium | Large | Growing |
| Ease of setup | Easy | Easy | Complex | Moderate |
| Performance | Good | Good | Excellent | Excellent |

---

## Key Takeaways for This Project

1. **Start with event-driven architecture** -- it gives backtesting/live parity
   and clean separation of concerns.
2. **Use the Strategy pattern** for swappable strategies with a common interface.
3. **TOML for infra config, YAML for strategy config** -- both support comments
   and are human-friendly.
4. **Risk management is not optional** -- implement it as a first-class component
   that gates every signal before it becomes an order.
5. **Paper trade extensively** before going live. Use the same code path for
   both, differing only in the broker adapter.
6. **Study Freqtrade's architecture** for inspiration -- it is the most mature
   Python trading bot and solves many of the same problems.
7. **Don't build the dashboard first** -- get the core event loop, strategy
   engine, and risk manager working before adding a web UI.
