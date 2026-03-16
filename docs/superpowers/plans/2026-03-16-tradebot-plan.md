# Tradebot Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python trading bot for 0DTE options on XSP/SPX with Tradier as broker, event-driven architecture, risk management, and a React dashboard.

**Architecture:** Event-driven pipeline using asyncio.Queue with type-based dispatch. Components: Market Data → Strategy → Risk Manager → Order Manager → Broker. Tradier sandbox for paper trading. SQLite for persistence.

**Tech Stack:** Python 3.12+, httpx, FastAPI, SQLAlchemy 2.0, Pydantic v2, structlog, pandas-ta, pytest, React/Vite/TypeScript

**Spec:** `docs/superpowers/specs/2026-03-16-tradebot-design.md`

---

## Chunk 1: Foundation

### Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `src/tradebot/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `config/settings.toml`
- Create: `config/settings.paper.toml`
- Create: `.env.example`
- Modify: `.gitignore`

- [ ] **Step 1: Create pyproject.toml with all dependencies**

```toml
[project]
name = "tradebot"
version = "0.1.0"
description = "0DTE options trading bot"
requires-python = ">=3.12"
dependencies = [
    "httpx>=0.27",
    "fastapi>=0.115",
    "uvicorn[standard]>=0.32",
    "sqlalchemy>=2.0",
    "alembic>=1.14",
    "pydantic>=2.10",
    "pydantic-settings>=2.7",
    "structlog>=24.4",
    "pandas>=2.2",
    "pandas-ta>=0.3",
    "numpy>=2.0",
    "pyyaml>=6.0",
    "exchange-calendars>=4.5",
    "websockets>=13.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3",
    "pytest-asyncio>=0.24",
    "pytest-cov>=6.0",
    "ruff>=0.8",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/tradebot"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
pythonpath = ["src"]

[tool.ruff]
target-version = "py312"
line-length = 100
```

- [ ] **Step 2: Create package init, test conftest, config files**

`src/tradebot/__init__.py`:
```python
"""Tradebot: 0DTE options trading bot."""
```

`tests/__init__.py`: empty file

`tests/conftest.py`:
```python
"""Shared test fixtures."""
```

`config/settings.toml`:
```toml
[general]
mode = "paper"  # "paper" or "live"
log_level = "INFO"

[database]
url = "sqlite:///tradebot.db"

[trading]
starting_capital = 2500.00
max_daily_loss_pct = 3.0
max_drawdown_pct = 10.0
pdt_limit = 3
```

`config/settings.paper.toml`:
```toml
[broker]
name = "tradier"
base_url = "https://sandbox.tradier.com"

[broker.credentials]
env_file = ".env.paper"
```

`.env.example`:
```
TRADIER_API_TOKEN=your_sandbox_token_here
```

- [ ] **Step 3: Update .gitignore**

Append to `.gitignore`:
```
__pycache__/
*.pyc
*.egg-info/
dist/
build/
.eggs/
*.db
.env
.env.paper
.env.live
.venv/
.pytest_cache/
.ruff_cache/
node_modules/
frontend/dist/
```

- [ ] **Step 4: Install dependencies and verify**

Run: `cd /home/coder/code/tradebot && uv venv && uv pip install -e ".[dev]"`
Expected: successful install

- [ ] **Step 5: Verify pytest runs (no tests yet)**

Run: `cd /home/coder/code/tradebot && uv run pytest --co`
Expected: "no tests ran" or similar (no errors)

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml src/ tests/ config/ .env.example .gitignore
git commit -m "feat: project scaffolding with dependencies and config"
```

---

### Task 2: Core Enums and Domain Models

**Files:**
- Create: `src/tradebot/core/__init__.py`
- Create: `src/tradebot/core/enums.py`
- Create: `src/tradebot/core/models.py`
- Create: `tests/unit/__init__.py`
- Create: `tests/unit/test_models.py`

- [ ] **Step 1: Write tests for enums and models**

`tests/unit/__init__.py`: empty file

`tests/unit/test_models.py`:
```python
"""Tests for core domain models."""
from decimal import Decimal
from datetime import datetime, date

from tradebot.core.enums import (
    OptionType,
    OrderSide,
    OrderType,
    OrderStatus,
    SpreadType,
    TradeStatus,
)
from tradebot.core.models import (
    OptionContract,
    OptionsChain,
    OrderLeg,
    Bar,
    Greeks,
)


def test_option_type_enum():
    assert OptionType.CALL.value == "call"
    assert OptionType.PUT.value == "put"


def test_order_side_enum():
    assert OrderSide.BUY_TO_OPEN.value == "buy_to_open"
    assert OrderSide.SELL_TO_CLOSE.value == "sell_to_close"


def test_spread_type_enum():
    assert SpreadType.IRON_CONDOR.value == "iron_condor"
    assert SpreadType.CREDIT_SPREAD.value == "credit_spread"
    assert SpreadType.DEBIT_SPREAD.value == "debit_spread"


def test_option_contract_creation():
    contract = OptionContract(
        symbol="XSP250316C00575000",
        underlying="XSP",
        option_type=OptionType.CALL,
        strike=Decimal("575.00"),
        expiration=date(2026, 3, 16),
        bid=Decimal("1.20"),
        ask=Decimal("1.35"),
        last=Decimal("1.25"),
        volume=150,
        open_interest=500,
        greeks=Greeks(
            delta=Decimal("0.30"),
            gamma=Decimal("0.05"),
            theta=Decimal("-0.15"),
            vega=Decimal("0.08"),
            implied_volatility=Decimal("0.22"),
        ),
    )
    assert contract.underlying == "XSP"
    assert contract.strike == Decimal("575.00")
    assert contract.greeks.delta == Decimal("0.30")


def test_option_contract_mid_price():
    contract = OptionContract(
        symbol="XSP250316C00575000",
        underlying="XSP",
        option_type=OptionType.CALL,
        strike=Decimal("575.00"),
        expiration=date(2026, 3, 16),
        bid=Decimal("1.20"),
        ask=Decimal("1.40"),
        last=Decimal("1.30"),
        volume=100,
        open_interest=200,
        greeks=Greeks(
            delta=Decimal("0.30"),
            gamma=Decimal("0.05"),
            theta=Decimal("-0.15"),
            vega=Decimal("0.08"),
            implied_volatility=Decimal("0.22"),
        ),
    )
    assert contract.mid_price == Decimal("1.30")


def test_order_leg_creation():
    leg = OrderLeg(
        option_symbol="XSP250316C00575000",
        side=OrderSide.SELL_TO_OPEN,
        quantity=1,
    )
    assert leg.side == OrderSide.SELL_TO_OPEN
    assert leg.quantity == 1


def test_bar_creation():
    bar = Bar(
        symbol="XSP",
        timestamp=datetime(2026, 3, 16, 10, 0, 0),
        open=Decimal("570.00"),
        high=Decimal("572.50"),
        low=Decimal("569.00"),
        close=Decimal("571.25"),
        volume=10000,
    )
    assert bar.symbol == "XSP"
    assert bar.close == Decimal("571.25")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_models.py -v`
Expected: FAIL (modules not found)

- [ ] **Step 3: Implement enums**

`src/tradebot/core/__init__.py`: empty file

`src/tradebot/core/enums.py`:
```python
"""Core enumerations for the trading system."""
from enum import Enum


class OptionType(str, Enum):
    CALL = "call"
    PUT = "put"


class OrderSide(str, Enum):
    BUY_TO_OPEN = "buy_to_open"
    BUY_TO_CLOSE = "buy_to_close"
    SELL_TO_OPEN = "sell_to_open"
    SELL_TO_CLOSE = "sell_to_close"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    DEBIT = "debit"
    CREDIT = "credit"
    EVEN = "even"


class OrderStatus(str, Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class SpreadType(str, Enum):
    IRON_CONDOR = "iron_condor"
    CREDIT_SPREAD = "credit_spread"
    DEBIT_SPREAD = "debit_spread"


class TradeStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    EXPIRED = "expired"
```

- [ ] **Step 4: Implement domain models**

`src/tradebot/core/models.py`:
```python
"""Core domain models used across the trading system."""
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal

from tradebot.core.enums import OptionType, OrderSide, OrderStatus, SpreadType, TradeStatus


@dataclass(frozen=True)
class Greeks:
    """Option Greeks snapshot."""
    delta: Decimal
    gamma: Decimal
    theta: Decimal
    vega: Decimal
    implied_volatility: Decimal


@dataclass(frozen=True)
class Bar:
    """OHLCV price bar."""
    symbol: str
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int


@dataclass(frozen=True)
class OptionContract:
    """A single option contract with quote and Greeks."""
    symbol: str
    underlying: str
    option_type: OptionType
    strike: Decimal
    expiration: date
    bid: Decimal
    ask: Decimal
    last: Decimal
    volume: int
    open_interest: int
    greeks: Greeks

    @property
    def mid_price(self) -> Decimal:
        return (self.bid + self.ask) / 2


@dataclass(frozen=True)
class OptionsChain:
    """Full options chain for a symbol and expiration."""
    underlying: str
    expiration: date
    underlying_price: Decimal
    calls: list[OptionContract] = field(default_factory=list)
    puts: list[OptionContract] = field(default_factory=list)


@dataclass(frozen=True)
class OrderLeg:
    """A single leg of an options order."""
    option_symbol: str
    side: OrderSide
    quantity: int


@dataclass(frozen=True)
class OrderResult:
    """Result of submitting an order to the broker."""
    broker_order_id: str
    status: OrderStatus


@dataclass
class Account:
    """Broker account info."""
    balance: Decimal
    buying_power: Decimal
    day_trade_count: int
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_models.py -v`
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add src/tradebot/core/ tests/unit/
git commit -m "feat: core enums and domain models"
```

---

### Task 3: Event System

**Files:**
- Create: `src/tradebot/core/events.py`
- Create: `src/tradebot/core/event_bus.py`
- Create: `tests/unit/test_event_bus.py`

- [ ] **Step 1: Write tests for events and event bus**

`tests/unit/test_event_bus.py`:
```python
"""Tests for the event system."""
import asyncio
from datetime import datetime, date
from decimal import Decimal

import pytest

from tradebot.core.enums import OptionType, OrderSide, SpreadType
from tradebot.core.events import MarketEvent, SignalEvent, OrderEvent, FillEvent, RiskEvent
from tradebot.core.event_bus import EventBus
from tradebot.core.models import Bar, OrderLeg, OptionsChain


def test_market_event_creation():
    bar = Bar(
        symbol="XSP",
        timestamp=datetime(2026, 3, 16, 10, 0),
        open=Decimal("570"), high=Decimal("572"),
        low=Decimal("569"), close=Decimal("571"), volume=1000,
    )
    event = MarketEvent(bar=bar)
    assert event.bar.symbol == "XSP"


def test_signal_event_creation():
    legs = [
        OrderLeg(option_symbol="XSP250316C00580000", side=OrderSide.SELL_TO_OPEN, quantity=1),
        OrderLeg(option_symbol="XSP250316C00585000", side=OrderSide.BUY_TO_OPEN, quantity=1),
    ]
    event = SignalEvent(
        strategy_name="xsp_credit_spread",
        spread_type=SpreadType.CREDIT_SPREAD,
        symbol="XSP",
        legs=legs,
        target_price=Decimal("0.50"),
    )
    assert event.strategy_name == "xsp_credit_spread"
    assert len(event.legs) == 2


def test_risk_event_creation():
    event = RiskEvent(
        check_name="PDTCheck",
        passed=False,
        message="PDT limit reached: 3/3 day trades used",
    )
    assert not event.passed


@pytest.mark.asyncio
async def test_event_bus_dispatch():
    """Events are dispatched to the correct handler."""
    bus = EventBus()
    received = []

    async def on_market(event: MarketEvent) -> list:
        received.append(("market", event))
        return []

    bus.register_handler(MarketEvent, on_market)

    bar = Bar(
        symbol="XSP", timestamp=datetime(2026, 3, 16, 10, 0),
        open=Decimal("570"), high=Decimal("572"),
        low=Decimal("569"), close=Decimal("571"), volume=1000,
    )
    await bus.publish(MarketEvent(bar=bar))
    await bus.process_one()

    assert len(received) == 1
    assert received[0][0] == "market"


@pytest.mark.asyncio
async def test_event_bus_observers():
    """Observers see all events before handlers."""
    bus = EventBus()
    observed = []

    async def observer(event):
        observed.append(type(event).__name__)

    async def handler(event) -> list:
        return []

    bus.add_observer(observer)
    bus.register_handler(MarketEvent, handler)

    bar = Bar(
        symbol="XSP", timestamp=datetime(2026, 3, 16, 10, 0),
        open=Decimal("570"), high=Decimal("572"),
        low=Decimal("569"), close=Decimal("571"), volume=1000,
    )
    await bus.publish(MarketEvent(bar=bar))
    await bus.process_one()

    assert observed == ["MarketEvent"]


@pytest.mark.asyncio
async def test_event_bus_handler_produces_new_events():
    """Handler return values are re-queued."""
    bus = EventBus()
    results = []

    async def on_market(event: MarketEvent) -> list:
        return [RiskEvent(check_name="test", passed=True, message="ok")]

    async def on_risk(event: RiskEvent) -> list:
        results.append(event.message)
        return []

    bus.register_handler(MarketEvent, on_market)
    bus.register_handler(RiskEvent, on_risk)

    bar = Bar(
        symbol="XSP", timestamp=datetime(2026, 3, 16, 10, 0),
        open=Decimal("570"), high=Decimal("572"),
        low=Decimal("569"), close=Decimal("571"), volume=1000,
    )
    await bus.publish(MarketEvent(bar=bar))
    await bus.process_one()  # processes MarketEvent, queues RiskEvent
    await bus.process_one()  # processes RiskEvent

    assert results == ["ok"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_event_bus.py -v`
Expected: FAIL

- [ ] **Step 3: Implement event types**

`src/tradebot/core/events.py`:
```python
"""Event types for the trading pipeline."""
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from tradebot.core.enums import OrderStatus, SpreadType
from tradebot.core.models import Bar, OptionsChain, OrderLeg


@dataclass(frozen=True)
class MarketEvent:
    """New market data available."""
    bar: Bar
    options_chain: OptionsChain | None = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass(frozen=True)
class SignalEvent:
    """Strategy wants to open or close a position."""
    strategy_name: str
    spread_type: SpreadType
    symbol: str
    legs: list[OrderLeg]
    target_price: Decimal
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass(frozen=True)
class OrderEvent:
    """Signal approved by risk manager, ready for execution."""
    signal: SignalEvent
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass(frozen=True)
class FillEvent:
    """Order has been filled by the broker."""
    broker_order_id: str
    signal: SignalEvent
    fill_price: Decimal
    status: OrderStatus
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass(frozen=True)
class RiskEvent:
    """Risk check result (for logging/dashboard)."""
    check_name: str
    passed: bool
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
```

- [ ] **Step 4: Implement event bus**

`src/tradebot/core/event_bus.py`:
```python
"""Central event bus with type-based dispatch and observer pattern."""
import asyncio
from collections.abc import Callable, Coroutine
from typing import Any


class EventBus:
    """Single-queue event bus with type-based dispatch and passive observers."""

    def __init__(self) -> None:
        self._queue: asyncio.Queue = asyncio.Queue()
        self._handlers: dict[type, Callable[..., Coroutine[Any, Any, list]]] = {}
        self._observers: list[Callable[..., Coroutine[Any, Any, None]]] = []

    def register_handler(self, event_type: type, handler: Callable) -> None:
        """Register a handler for a specific event type."""
        self._handlers[event_type] = handler

    def add_observer(self, observer: Callable) -> None:
        """Add a passive observer that sees all events."""
        self._observers.append(observer)

    async def publish(self, event: Any) -> None:
        """Put an event on the queue."""
        await self._queue.put(event)

    async def process_one(self) -> bool:
        """Process a single event from the queue. Returns False if queue is empty."""
        try:
            event = self._queue.get_nowait()
        except asyncio.QueueEmpty:
            return False

        # Notify observers first
        for observer in self._observers:
            await observer(event)

        # Dispatch to handler
        handler = self._handlers.get(type(event))
        if handler:
            new_events = await handler(event)
            for e in new_events or []:
                await self._queue.put(e)

        return True

    async def run(self, shutdown_event: asyncio.Event | None = None) -> None:
        """Run the event loop until shutdown."""
        while True:
            if shutdown_event and shutdown_event.is_set():
                break
            try:
                event = await asyncio.wait_for(self._queue.get(), timeout=0.1)
            except asyncio.TimeoutError:
                continue

            for observer in self._observers:
                await observer(event)

            handler = self._handlers.get(type(event))
            if handler:
                new_events = await handler(event)
                for e in new_events or []:
                    await self._queue.put(e)

    @property
    def pending(self) -> int:
        return self._queue.qsize()
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_event_bus.py -v`
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add src/tradebot/core/events.py src/tradebot/core/event_bus.py tests/unit/test_event_bus.py
git commit -m "feat: event types and event bus with type-based dispatch"
```

---

### Task 4: Configuration System

**Files:**
- Create: `src/tradebot/utils/__init__.py`
- Create: `src/tradebot/utils/config.py`
- Create: `tests/unit/test_config.py`

- [ ] **Step 1: Write tests for config loading**

`tests/unit/test_config.py`:
```python
"""Tests for configuration loading."""
from decimal import Decimal
from pathlib import Path

import pytest

from tradebot.utils.config import Settings, StrategyConfig, load_strategy_config


def test_default_settings():
    settings = Settings()
    assert settings.mode == "paper"
    assert settings.log_level == "INFO"
    assert settings.database_url == "sqlite:///tradebot.db"
    assert settings.max_daily_loss_pct == Decimal("3.0")
    assert settings.pdt_limit == 3


def test_settings_paper_mode():
    settings = Settings(mode="paper")
    assert settings.mode == "paper"


def test_settings_rejects_invalid_mode():
    with pytest.raises(ValueError):
        Settings(mode="invalid")


def test_load_strategy_config(tmp_path: Path):
    yaml_content = """
strategy:
  name: "test_strategy"
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
  min_credit: 0.30

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
"""
    config_file = tmp_path / "test_strategy.yaml"
    config_file.write_text(yaml_content)

    config = load_strategy_config(config_file)
    assert config.strategy.name == "test_strategy"
    assert config.market.symbol == "XSP"
    assert config.entry.strike_selection.short_call_delta == 0.15
    assert config.exit.prefer_expire is True
    assert config.position_sizing.max_risk_per_trade == 250
    assert config.risk.pdt_aware is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_config.py -v`
Expected: FAIL

- [ ] **Step 3: Implement config models**

`src/tradebot/utils/__init__.py`: empty file

`src/tradebot/utils/config.py`:
```python
"""Configuration loading for infrastructure and strategy settings."""
from decimal import Decimal
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Infrastructure settings loaded from env/TOML."""

    mode: Literal["paper", "live"] = "paper"
    log_level: str = "INFO"
    database_url: str = "sqlite:///tradebot.db"
    starting_capital: Decimal = Decimal("2500.00")
    max_daily_loss_pct: Decimal = Decimal("3.0")
    max_drawdown_pct: Decimal = Decimal("10.0")
    pdt_limit: int = 3

    # Broker
    broker_name: str = "tradier"
    broker_base_url: str = "https://sandbox.tradier.com"
    tradier_api_token: str = ""

    model_config = {"env_prefix": "TRADEBOT_"}

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        if v not in ("paper", "live"):
            raise ValueError(f"mode must be 'paper' or 'live', got '{v}'")
        return v


# --- Strategy config models (loaded from YAML) ---


class StrategyInfo(BaseModel):
    name: str
    class_name: str | None = None
    enabled: bool = True

    model_config = {"populate_by_name": True}

    def __init__(self, **data):
        # Map 'class' key to 'class_name' since 'class' is a Python keyword
        if "class" in data:
            data["class_name"] = data.pop("class")
        super().__init__(**data)


class MarketConfig(BaseModel):
    symbol: str
    expiration: str = "0dte"


class TimeWindow(BaseModel):
    earliest: str = "09:30"
    latest: str = "16:00"


class StrikeSelection(BaseModel):
    method: str = "delta"
    short_call_delta: float = 0.15
    short_put_delta: float = -0.15
    wing_width: int = 5


class IVFilter(BaseModel):
    min_iv_rank: float = 0.0


class EntryConfig(BaseModel):
    time_window: TimeWindow = TimeWindow()
    strike_selection: StrikeSelection = StrikeSelection()
    iv_filter: IVFilter = IVFilter()
    min_credit: float = 0.0


class ExitConfig(BaseModel):
    profit_target_pct: float = 50.0
    stop_loss_pct: float = 200.0
    time_exit: str = "15:45"
    prefer_expire: bool = True


class PositionSizingConfig(BaseModel):
    method: str = "fixed_risk"
    max_risk_per_trade: int = 250
    max_contracts: int = 2


class RiskConfig(BaseModel):
    max_daily_trades: int = 1
    pdt_aware: bool = True


class StrategyConfig(BaseModel):
    """Full strategy configuration parsed from YAML."""

    strategy: StrategyInfo
    market: MarketConfig
    entry: EntryConfig = EntryConfig()
    exit: ExitConfig = ExitConfig()
    position_sizing: PositionSizingConfig = PositionSizingConfig()
    risk: RiskConfig = RiskConfig()


def load_strategy_config(path: Path) -> StrategyConfig:
    """Load and validate a strategy config from a YAML file."""
    with open(path) as f:
        raw = yaml.safe_load(f)
    return StrategyConfig(**raw)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_config.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add src/tradebot/utils/ tests/unit/test_config.py
git commit -m "feat: config system with Settings and strategy YAML loading"
```

---

### Task 5: Logging Setup

**Files:**
- Create: `src/tradebot/utils/logging.py`

- [ ] **Step 1: Implement structured logging setup**

`src/tradebot/utils/logging.py`:
```python
"""Structured logging configuration using structlog."""
import logging
import sys

import structlog


def setup_logging(log_level: str = "INFO") -> None:
    """Configure structlog for JSON-formatted structured logging."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        cache_logger_on_first_use=True,
    )
```

- [ ] **Step 2: Commit**

```bash
git add src/tradebot/utils/logging.py
git commit -m "feat: structlog-based structured logging setup"
```

---

## Chunk 2: Persistence & Broker

### Task 6: Database Models and Repository

**Files:**
- Create: `src/tradebot/persistence/__init__.py`
- Create: `src/tradebot/persistence/database.py`
- Create: `src/tradebot/persistence/models.py`
- Create: `src/tradebot/persistence/repository.py`
- Create: `tests/unit/test_persistence.py`

- [ ] **Step 1: Write tests for persistence layer**

`tests/unit/test_persistence.py`:
```python
"""Tests for database models and repository."""
import asyncio
from datetime import date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from tradebot.persistence.database import Base
from tradebot.persistence.models import TradeRecord, TradeLegRecord, DayTradeLogRecord, DailySnapshotRecord
from tradebot.persistence.repository import Repository


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture
def repo(db_session):
    return Repository(db_session)


def test_create_trade(repo):
    trade = repo.create_trade(
        strategy="xsp_iron_condor",
        symbol="XSP",
        spread_type="iron_condor",
        entry_price=Decimal("0.50"),
    )
    assert trade.id is not None
    assert trade.strategy == "xsp_iron_condor"
    assert trade.status == "open"


def test_add_trade_leg(repo):
    trade = repo.create_trade(
        strategy="xsp_credit_spread",
        symbol="XSP",
        spread_type="credit_spread",
        entry_price=Decimal("0.35"),
    )
    leg = repo.add_trade_leg(
        trade_id=trade.id,
        option_symbol="XSP250316P00565000",
        side="sell_to_open",
        quantity=1,
        strike=Decimal("565.00"),
        option_type="put",
        fill_price=Decimal("0.85"),
    )
    assert leg.trade_id == trade.id
    assert leg.strike == Decimal("565.00")


def test_log_day_trade(repo):
    repo.log_day_trade(trade_date=date(2026, 3, 16), order_id="ord_123", trade_id=1)
    count = repo.get_day_trade_count(
        start_date=date(2026, 3, 12),
        end_date=date(2026, 3, 16),
    )
    assert count == 1


def test_day_trade_count_rolling_window(repo):
    repo.log_day_trade(trade_date=date(2026, 3, 10), order_id="ord_1", trade_id=1)
    repo.log_day_trade(trade_date=date(2026, 3, 12), order_id="ord_2", trade_id=2)
    repo.log_day_trade(trade_date=date(2026, 3, 16), order_id="ord_3", trade_id=3)

    # Window: 3/12 - 3/16 (5 business days)
    count = repo.get_day_trade_count(
        start_date=date(2026, 3, 12),
        end_date=date(2026, 3, 16),
    )
    assert count == 2  # excludes 3/10


def test_close_trade(repo):
    trade = repo.create_trade(
        strategy="test", symbol="XSP",
        spread_type="credit_spread", entry_price=Decimal("0.50"),
    )
    repo.close_trade(trade.id, exit_price=Decimal("0.20"), pnl=Decimal("30.00"))
    updated = repo.get_trade(trade.id)
    assert updated.status == "closed"
    assert updated.pnl == Decimal("30.00")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_persistence.py -v`
Expected: FAIL

- [ ] **Step 3: Implement database base and ORM models**

`src/tradebot/persistence/__init__.py`: empty file

`src/tradebot/persistence/database.py`:
```python
"""Database engine and session setup."""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session


class Base(DeclarativeBase):
    pass


def create_db_engine(url: str = "sqlite:///tradebot.db"):
    return create_engine(url, echo=False)


def create_session(engine) -> Session:
    return Session(engine)
```

`src/tradebot/persistence/models.py`:
```python
"""SQLAlchemy ORM models for trade persistence."""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Integer, Numeric, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from tradebot.persistence.database import Base


class TradeRecord(Base):
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    strategy: Mapped[str] = mapped_column(String(100))
    symbol: Mapped[str] = mapped_column(String(20))
    spread_type: Mapped[str] = mapped_column(String(50))
    entry_price: Mapped[Decimal] = mapped_column(Numeric(10, 4))
    exit_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    pnl: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="open")
    entry_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    exit_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    legs: Mapped[list["TradeLegRecord"]] = relationship(back_populates="trade")


class TradeLegRecord(Base):
    __tablename__ = "trade_legs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trade_id: Mapped[int] = mapped_column(ForeignKey("trades.id"))
    option_symbol: Mapped[str] = mapped_column(String(50))
    side: Mapped[str] = mapped_column(String(20))
    quantity: Mapped[int] = mapped_column(Integer)
    strike: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    option_type: Mapped[str] = mapped_column(String(10))
    fill_price: Mapped[Decimal] = mapped_column(Numeric(10, 4))

    trade: Mapped["TradeRecord"] = relationship(back_populates="legs")


class DayTradeLogRecord(Base):
    __tablename__ = "day_trade_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trade_date: Mapped[date] = mapped_column(Date)
    order_id: Mapped[str] = mapped_column(String(50))
    trade_id: Mapped[int] = mapped_column(Integer)


class DailySnapshotRecord(Base):
    __tablename__ = "daily_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    snapshot_date: Mapped[date] = mapped_column(Date, unique=True)
    nav: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    realized_pnl: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    unrealized_pnl: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    drawdown: Mapped[Decimal] = mapped_column(Numeric(6, 4))
    day_trade_count: Mapped[int] = mapped_column(Integer)
```

- [ ] **Step 4: Implement repository**

`src/tradebot/persistence/repository.py`:
```python
"""Data access layer for trade persistence."""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from tradebot.persistence.models import (
    TradeRecord,
    TradeLegRecord,
    DayTradeLogRecord,
    DailySnapshotRecord,
)


class Repository:
    """Data access layer wrapping SQLAlchemy session."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create_trade(
        self,
        strategy: str,
        symbol: str,
        spread_type: str,
        entry_price: Decimal,
    ) -> TradeRecord:
        trade = TradeRecord(
            strategy=strategy,
            symbol=symbol,
            spread_type=spread_type,
            entry_price=entry_price,
            status="open",
        )
        self._session.add(trade)
        self._session.flush()
        return trade

    def get_trade(self, trade_id: int) -> TradeRecord | None:
        return self._session.get(TradeRecord, trade_id)

    def close_trade(
        self,
        trade_id: int,
        exit_price: Decimal,
        pnl: Decimal,
        status: str = "closed",
    ) -> None:
        trade = self.get_trade(trade_id)
        if trade:
            trade.exit_price = exit_price
            trade.pnl = pnl
            trade.status = status
            trade.exit_time = datetime.now()
            self._session.flush()

    def add_trade_leg(
        self,
        trade_id: int,
        option_symbol: str,
        side: str,
        quantity: int,
        strike: Decimal,
        option_type: str,
        fill_price: Decimal,
    ) -> TradeLegRecord:
        leg = TradeLegRecord(
            trade_id=trade_id,
            option_symbol=option_symbol,
            side=side,
            quantity=quantity,
            strike=strike,
            option_type=option_type,
            fill_price=fill_price,
        )
        self._session.add(leg)
        self._session.flush()
        return leg

    def log_day_trade(self, trade_date: date, order_id: str, trade_id: int) -> None:
        record = DayTradeLogRecord(
            trade_date=trade_date,
            order_id=order_id,
            trade_id=trade_id,
        )
        self._session.add(record)
        self._session.flush()

    def get_day_trade_count(self, start_date: date, end_date: date) -> int:
        stmt = (
            select(func.count())
            .select_from(DayTradeLogRecord)
            .where(
                DayTradeLogRecord.trade_date >= start_date,
                DayTradeLogRecord.trade_date <= end_date,
            )
        )
        return self._session.execute(stmt).scalar() or 0

    def get_open_trades(self) -> list[TradeRecord]:
        stmt = select(TradeRecord).where(TradeRecord.status == "open")
        return list(self._session.execute(stmt).scalars().all())
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_persistence.py -v`
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add src/tradebot/persistence/ tests/unit/test_persistence.py
git commit -m "feat: database models and repository for trade persistence"
```

---

### Task 7: Broker Abstraction and Tradier Client

**Files:**
- Create: `src/tradebot/execution/__init__.py`
- Create: `src/tradebot/execution/brokers/__init__.py`
- Create: `src/tradebot/execution/brokers/base.py`
- Create: `src/tradebot/execution/brokers/tradier.py`
- Create: `tests/unit/test_tradier_broker.py`

- [ ] **Step 1: Write tests for broker protocol and Tradier client**

`tests/unit/test_tradier_broker.py`:
```python
"""Tests for Tradier broker client."""
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from tradebot.core.enums import OptionType, OrderSide, OrderStatus
from tradebot.core.models import Account, OrderLeg, OrderResult
from tradebot.execution.brokers.tradier import TradierBroker


@pytest.fixture
def broker():
    return TradierBroker(
        base_url="https://sandbox.tradier.com",
        api_token="test_token",
    )


@pytest.mark.asyncio
async def test_get_account(broker):
    mock_response = {
        "profile": {
            "account": {
                "account_number": "TEST123",
                "value": 2500.00,
                "stock_buying_power": 2500.00,
                "day_trade_count": 0,
            }
        }
    }
    with patch.object(broker, "_request", new_callable=AsyncMock, return_value=mock_response):
        account = await broker.get_account()
        assert account.balance == Decimal("2500.00")
        assert account.buying_power == Decimal("2500.00")


@pytest.mark.asyncio
async def test_get_options_chain(broker):
    mock_response = {
        "options": {
            "option": [
                {
                    "symbol": "XSP250316C00575000",
                    "option_type": "call",
                    "strike": 575.00,
                    "expiration_date": "2026-03-16",
                    "bid": 1.20,
                    "ask": 1.35,
                    "last": 1.25,
                    "volume": 150,
                    "open_interest": 500,
                    "greeks": {
                        "delta": 0.30,
                        "gamma": 0.05,
                        "theta": -0.15,
                        "vega": 0.08,
                        "mid_iv": 0.22,
                    },
                }
            ]
        }
    }
    with patch.object(broker, "_request", new_callable=AsyncMock, return_value=mock_response):
        chain = await broker.get_options_chain("XSP", date(2026, 3, 16))
        assert len(chain.calls) == 1
        assert chain.calls[0].strike == Decimal("575.00")
        assert chain.calls[0].greeks.delta == Decimal("0.30")


@pytest.mark.asyncio
async def test_submit_multileg_order(broker):
    mock_response = {
        "order": {
            "id": 12345,
            "status": "pending",
        }
    }
    legs = [
        OrderLeg(option_symbol="XSP250316P00565000", side=OrderSide.SELL_TO_OPEN, quantity=1),
        OrderLeg(option_symbol="XSP250316P00560000", side=OrderSide.BUY_TO_OPEN, quantity=1),
    ]
    with patch.object(broker, "_request", new_callable=AsyncMock, return_value=mock_response):
        result = await broker.submit_multileg_order(legs=legs, price=Decimal("0.50"))
        assert result.broker_order_id == "12345"
        assert result.status == OrderStatus.PENDING
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_tradier_broker.py -v`
Expected: FAIL

- [ ] **Step 3: Implement broker base protocol**

`src/tradebot/execution/__init__.py`: empty file
`src/tradebot/execution/brokers/__init__.py`: empty file

`src/tradebot/execution/brokers/base.py`:
```python
"""Abstract broker interface."""
from datetime import date
from decimal import Decimal
from typing import Protocol

from tradebot.core.models import Account, OptionsChain, OrderLeg, OrderResult


class Broker(Protocol):
    """Protocol defining the broker interface."""

    async def get_account(self) -> Account: ...
    async def get_positions(self) -> list[dict]: ...
    async def get_options_chain(self, symbol: str, expiration: date) -> OptionsChain: ...
    async def submit_order(self, leg: OrderLeg, price: Decimal) -> OrderResult: ...
    async def submit_multileg_order(self, legs: list[OrderLeg], price: Decimal) -> OrderResult: ...
    async def cancel_order(self, order_id: str) -> None: ...
    async def get_order_status(self, order_id: str) -> str: ...
```

- [ ] **Step 4: Implement Tradier broker client**

`src/tradebot/execution/brokers/tradier.py`:
```python
"""Tradier broker implementation."""
from datetime import date
from decimal import Decimal

import httpx
import structlog

from tradebot.core.enums import OptionType, OrderStatus
from tradebot.core.models import (
    Account,
    Greeks,
    OptionContract,
    OptionsChain,
    OrderLeg,
    OrderResult,
)

logger = structlog.get_logger()

# Map OrderSide enum values to Tradier's expected side strings
SIDE_MAP = {
    "buy_to_open": "buy_to_open",
    "buy_to_close": "buy_to_close",
    "sell_to_open": "sell_to_open",
    "sell_to_close": "sell_to_close",
}


class TradierBroker:
    """Tradier API client for options trading.

    Works with both sandbox (paper) and production (live) environments —
    the only difference is base_url and api_token.
    """

    def __init__(self, base_url: str, api_token: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {api_token}",
            "Accept": "application/json",
        }
        self._account_id: str | None = None

    async def _request(
        self, method: str = "GET", path: str = "", params: dict | None = None, data: dict | None = None
    ) -> dict:
        """Make an authenticated request to the Tradier API."""
        url = f"{self._base_url}{path}"
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method, url, headers=self._headers, params=params, data=data
            )
            response.raise_for_status()
            return response.json()

    async def _ensure_account_id(self) -> str:
        if self._account_id is None:
            result = await self._request("GET", "/v1/user/profile")
            account = result["profile"]["account"]
            if isinstance(account, list):
                self._account_id = account[0]["account_number"]
            else:
                self._account_id = account["account_number"]
        return self._account_id

    async def get_account(self) -> Account:
        result = await self._request("GET", "/v1/user/profile")
        account = result["profile"]["account"]
        if isinstance(account, list):
            account = account[0]
        return Account(
            balance=Decimal(str(account.get("value", 0))),
            buying_power=Decimal(str(account.get("stock_buying_power", 0))),
            day_trade_count=account.get("day_trade_count", 0),
        )

    async def get_options_chain(self, symbol: str, expiration: date) -> OptionsChain:
        result = await self._request(
            "GET",
            "/v1/markets/options/chains",
            params={
                "symbol": symbol,
                "expiration": expiration.isoformat(),
                "greeks": "true",
            },
        )
        calls: list[OptionContract] = []
        puts: list[OptionContract] = []

        options = result.get("options", {}).get("option", [])
        if not isinstance(options, list):
            options = [options]

        for opt in options:
            greeks_data = opt.get("greeks", {}) or {}
            contract = OptionContract(
                symbol=opt["symbol"],
                underlying=symbol,
                option_type=OptionType(opt["option_type"]),
                strike=Decimal(str(opt["strike"])),
                expiration=date.fromisoformat(opt["expiration_date"]),
                bid=Decimal(str(opt.get("bid", 0))),
                ask=Decimal(str(opt.get("ask", 0))),
                last=Decimal(str(opt.get("last", 0))),
                volume=opt.get("volume", 0),
                open_interest=opt.get("open_interest", 0),
                greeks=Greeks(
                    delta=Decimal(str(greeks_data.get("delta", 0))),
                    gamma=Decimal(str(greeks_data.get("gamma", 0))),
                    theta=Decimal(str(greeks_data.get("theta", 0))),
                    vega=Decimal(str(greeks_data.get("vega", 0))),
                    implied_volatility=Decimal(str(greeks_data.get("mid_iv", 0))),
                ),
            )
            if contract.option_type == OptionType.CALL:
                calls.append(contract)
            else:
                puts.append(contract)

        # Get underlying price
        quote_result = await self._request(
            "GET", "/v1/markets/quotes", params={"symbols": symbol}
        )
        quote = quote_result.get("quotes", {}).get("quote", {})
        underlying_price = Decimal(str(quote.get("last", 0)))

        return OptionsChain(
            underlying=symbol,
            expiration=expiration,
            underlying_price=underlying_price,
            calls=sorted(calls, key=lambda c: c.strike),
            puts=sorted(puts, key=lambda p: p.strike),
        )

    async def submit_multileg_order(
        self, legs: list[OrderLeg], price: Decimal
    ) -> OrderResult:
        account_id = await self._ensure_account_id()

        data = {
            "class": "multileg",
            "symbol": self._extract_underlying(legs[0].option_symbol),
            "type": "credit" if price > 0 else "debit",
            "duration": "day",
            "price": str(abs(price)),
        }

        for i, leg in enumerate(legs):
            data[f"option_symbol[{i}]"] = leg.option_symbol
            data[f"side[{i}]"] = SIDE_MAP[leg.side.value]
            data[f"quantity[{i}]"] = str(leg.quantity)

        result = await self._request(
            "POST", f"/v1/accounts/{account_id}/orders", data=data
        )
        order = result.get("order", {})
        return OrderResult(
            broker_order_id=str(order.get("id", "")),
            status=OrderStatus.PENDING,
        )

    @staticmethod
    def _extract_underlying(option_symbol: str) -> str:
        """Extract underlying symbol from OCC option symbol (e.g., XSP250316C00575000 -> XSP)."""
        import re
        match = re.match(r'^([A-Z]+)\d', option_symbol)
        return match.group(1) if match else option_symbol

    async def get_positions(self) -> list[dict]:
        """Get current positions from the broker."""
        account_id = await self._ensure_account_id()
        result = await self._request("GET", f"/v1/accounts/{account_id}/positions")
        positions = result.get("positions", {})
        if positions == "null" or not positions:
            return []
        position_list = positions.get("position", [])
        if not isinstance(position_list, list):
            position_list = [position_list]
        return position_list

    async def submit_order(self, leg: OrderLeg, price: Decimal) -> OrderResult:
        return await self.submit_multileg_order([leg], price)

    async def cancel_order(self, order_id: str) -> None:
        account_id = await self._ensure_account_id()
        await self._request("DELETE", f"/v1/accounts/{account_id}/orders/{order_id}")

    async def get_order_status(self, order_id: str) -> str:
        account_id = await self._ensure_account_id()
        result = await self._request(
            "GET", f"/v1/accounts/{account_id}/orders/{order_id}"
        )
        return result.get("order", {}).get("status", "unknown")
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_tradier_broker.py -v`
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add src/tradebot/execution/ tests/unit/test_tradier_broker.py
git commit -m "feat: broker protocol and Tradier client implementation"
```

---

## Chunk 3: Trading Logic

### Task 8: Risk Manager

**Files:**
- Create: `src/tradebot/risk/__init__.py`
- Create: `src/tradebot/risk/checks.py`
- Create: `src/tradebot/risk/manager.py`
- Create: `tests/unit/test_risk_checks.py`

- [ ] **Step 1: Write tests for risk checks**

`tests/unit/test_risk_checks.py`:
```python
"""Tests for risk management checks."""
from datetime import date, time
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from tradebot.core.enums import OrderSide, SpreadType
from tradebot.core.events import SignalEvent
from tradebot.core.models import OrderLeg
from tradebot.risk.checks import (
    PDTCheck,
    MaxDailyLossCheck,
    MaxDrawdownCheck,
    PositionSizeCheck,
    SpreadWidthCheck,
    TimeWindowCheck,
    DuplicateCheck,
)


def _make_signal(spread_type=SpreadType.CREDIT_SPREAD, symbol="XSP") -> SignalEvent:
    return SignalEvent(
        strategy_name="test",
        spread_type=spread_type,
        symbol=symbol,
        legs=[
            OrderLeg(option_symbol="XSP250316P00565000", side=OrderSide.SELL_TO_OPEN, quantity=1),
            OrderLeg(option_symbol="XSP250316P00560000", side=OrderSide.BUY_TO_OPEN, quantity=1),
        ],
        target_price=Decimal("0.50"),
    )


class TestPDTCheck:
    def test_passes_when_under_limit(self):
        repo = MagicMock()
        repo.get_day_trade_count.return_value = 2
        check = PDTCheck(repo=repo, pdt_limit=3)
        result = check.check(_make_signal())
        assert result.passed

    def test_fails_when_at_limit(self):
        repo = MagicMock()
        repo.get_day_trade_count.return_value = 3
        check = PDTCheck(repo=repo, pdt_limit=3)
        result = check.check(_make_signal())
        assert not result.passed
        assert "3/3" in result.message


class TestMaxDailyLossCheck:
    def test_passes_when_under_threshold(self):
        check = MaxDailyLossCheck(
            max_daily_loss_pct=Decimal("3.0"),
            current_daily_pnl=Decimal("-50.00"),
            account_value=Decimal("2500.00"),
        )
        result = check.check(_make_signal())
        assert result.passed

    def test_fails_when_over_threshold(self):
        check = MaxDailyLossCheck(
            max_daily_loss_pct=Decimal("3.0"),
            current_daily_pnl=Decimal("-80.00"),
            account_value=Decimal("2500.00"),
        )
        result = check.check(_make_signal())
        assert not result.passed


class TestMaxDrawdownCheck:
    def test_passes_under_threshold(self):
        check = MaxDrawdownCheck(
            max_drawdown_pct=Decimal("10.0"),
            current_drawdown_pct=Decimal("5.0"),
        )
        result = check.check(_make_signal())
        assert result.passed

    def test_fails_over_threshold(self):
        check = MaxDrawdownCheck(
            max_drawdown_pct=Decimal("10.0"),
            current_drawdown_pct=Decimal("12.0"),
        )
        result = check.check(_make_signal())
        assert not result.passed


class TestPositionSizeCheck:
    def test_passes_within_limits(self):
        check = PositionSizeCheck(
            max_risk_per_trade=Decimal("250.00"),
            account_value=Decimal("2500.00"),
        )
        signal = _make_signal()  # 2 legs, $5 wide = $500 max risk for 1 contract
        # But we pass max_risk_per_trade which the check uses
        result = check.check(signal, trade_max_loss=Decimal("200.00"))
        assert result.passed

    def test_fails_over_limit(self):
        check = PositionSizeCheck(
            max_risk_per_trade=Decimal("250.00"),
            account_value=Decimal("2500.00"),
        )
        result = check.check(_make_signal(), trade_max_loss=Decimal("500.00"))
        assert not result.passed


class TestTimeWindowCheck:
    def test_passes_within_window(self):
        check = TimeWindowCheck(earliest=time(9, 45), latest=time(14, 0))
        result = check.check(_make_signal(), current_time=time(10, 30))
        assert result.passed

    def test_fails_before_window(self):
        check = TimeWindowCheck(earliest=time(9, 45), latest=time(14, 0))
        result = check.check(_make_signal(), current_time=time(9, 30))
        assert not result.passed

    def test_fails_after_window(self):
        check = TimeWindowCheck(earliest=time(9, 45), latest=time(14, 0))
        result = check.check(_make_signal(), current_time=time(14, 30))
        assert not result.passed


class TestDuplicateCheck:
    def test_passes_no_existing_position(self):
        check = DuplicateCheck(open_symbols=set())
        result = check.check(_make_signal())
        assert result.passed

    def test_fails_with_existing_position(self):
        check = DuplicateCheck(open_symbols={"XSP"})
        result = check.check(_make_signal())
        assert not result.passed
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_risk_checks.py -v`
Expected: FAIL

- [ ] **Step 3: Implement risk checks**

`src/tradebot/risk/__init__.py`: empty file

`src/tradebot/risk/checks.py`:
```python
"""Individual risk check implementations."""
from dataclasses import dataclass
from datetime import date, time, timedelta
from decimal import Decimal

from tradebot.core.events import RiskEvent, SignalEvent


@dataclass
class PDTCheck:
    """Tracks day trades in rolling 5-business-day window."""
    repo: object  # Repository
    pdt_limit: int = 3

    def check(self, signal: SignalEvent) -> RiskEvent:
        import exchange_calendars as xcals
        today = date.today()
        nyse = xcals.get_calendar("XNYS")
        sessions = nyse.sessions_in_range(today - timedelta(days=10), today)
        # Get the last 5 trading sessions (rolling 5 business days)
        recent_sessions = sessions[-5:] if len(sessions) >= 5 else sessions
        start = recent_sessions[0].date() if len(recent_sessions) > 0 else today
        count = self.repo.get_day_trade_count(start_date=start, end_date=today)
        passed = count < self.pdt_limit
        return RiskEvent(
            check_name="PDTCheck",
            passed=passed,
            message=(
                f"PDT OK: {count}/{self.pdt_limit} day trades used"
                if passed
                else f"PDT limit reached: {count}/{self.pdt_limit} day trades used"
            ),
        )


@dataclass
class MaxDailyLossCheck:
    """Halts trading when daily loss exceeds threshold."""
    max_daily_loss_pct: Decimal
    current_daily_pnl: Decimal
    account_value: Decimal

    def check(self, signal: SignalEvent) -> RiskEvent:
        loss_pct = abs(self.current_daily_pnl) / self.account_value * 100
        passed = self.current_daily_pnl >= 0 or loss_pct < self.max_daily_loss_pct
        return RiskEvent(
            check_name="MaxDailyLossCheck",
            passed=passed,
            message=(
                f"Daily P&L: ${self.current_daily_pnl} ({loss_pct:.1f}%)"
                if passed
                else f"Daily loss limit hit: ${self.current_daily_pnl} ({loss_pct:.1f}% >= {self.max_daily_loss_pct}%)"
            ),
        )


@dataclass
class PositionSizeCheck:
    """Validates trade risk against account size."""
    max_risk_per_trade: Decimal
    account_value: Decimal

    def check(self, signal: SignalEvent, trade_max_loss: Decimal = Decimal("0")) -> RiskEvent:
        passed = trade_max_loss <= self.max_risk_per_trade
        return RiskEvent(
            check_name="PositionSizeCheck",
            passed=passed,
            message=(
                f"Position size OK: max loss ${trade_max_loss} <= ${self.max_risk_per_trade}"
                if passed
                else f"Position too large: max loss ${trade_max_loss} > ${self.max_risk_per_trade}"
            ),
        )


@dataclass
class SpreadWidthCheck:
    """Validates spread width is appropriate for account size."""
    max_spread_width: Decimal = Decimal("10.0")

    def check(self, signal: SignalEvent, spread_width: Decimal = Decimal("0")) -> RiskEvent:
        passed = spread_width <= self.max_spread_width
        return RiskEvent(
            check_name="SpreadWidthCheck",
            passed=passed,
            message=(
                f"Spread width OK: ${spread_width}"
                if passed
                else f"Spread too wide: ${spread_width} > ${self.max_spread_width}"
            ),
        )


@dataclass
class TimeWindowCheck:
    """Only allows entries during configured time window."""
    earliest: time
    latest: time

    def check(self, signal: SignalEvent, current_time: time | None = None) -> RiskEvent:
        from datetime import datetime as dt
        now = current_time or dt.now().time()
        passed = self.earliest <= now <= self.latest
        return RiskEvent(
            check_name="TimeWindowCheck",
            passed=passed,
            message=(
                f"Time OK: {now} within {self.earliest}-{self.latest}"
                if passed
                else f"Outside trading window: {now} not in {self.earliest}-{self.latest}"
            ),
        )


@dataclass
class MaxDrawdownCheck:
    """Halts bot when drawdown from peak exceeds threshold."""
    max_drawdown_pct: Decimal
    current_drawdown_pct: Decimal

    def check(self, signal: SignalEvent) -> RiskEvent:
        passed = self.current_drawdown_pct < self.max_drawdown_pct
        return RiskEvent(
            check_name="MaxDrawdownCheck",
            passed=passed,
            message=(
                f"Drawdown OK: {self.current_drawdown_pct:.1f}%"
                if passed
                else f"Max drawdown hit: {self.current_drawdown_pct:.1f}% >= {self.max_drawdown_pct}%"
            ),
        )


@dataclass
class DuplicateCheck:
    """Prevents duplicate positions on the same underlying."""
    open_symbols: set[str]

    def check(self, signal: SignalEvent) -> RiskEvent:
        passed = signal.symbol not in self.open_symbols
        return RiskEvent(
            check_name="DuplicateCheck",
            passed=passed,
            message=(
                f"No duplicate: {signal.symbol} not in open positions"
                if passed
                else f"Duplicate position: {signal.symbol} already open"
            ),
        )
```

- [ ] **Step 4: Implement risk manager**

`src/tradebot/risk/manager.py`:
```python
"""Risk manager that chains checks and gates signals."""
import structlog

from tradebot.core.events import OrderEvent, RiskEvent, SignalEvent

logger = structlog.get_logger()


class RiskManager:
    """Evaluates signals against a chain of risk checks.

    If all checks pass, produces an OrderEvent.
    All check results are emitted as RiskEvents for logging/dashboard.
    """

    def __init__(self) -> None:
        self._checks: list = []

    def add_check(self, check: object) -> None:
        self._checks.append(check)

    async def on_signal(self, signal: SignalEvent) -> list:
        """Process a signal through all risk checks."""
        events: list = []
        all_passed = True

        for check in self._checks:
            result: RiskEvent = check.check(signal)
            events.append(result)

            if not result.passed:
                all_passed = False
                logger.warning(
                    "risk_check_failed",
                    check=result.check_name,
                    message=result.message,
                    strategy=signal.strategy_name,
                )
                break  # Stop on first failure

            logger.info(
                "risk_check_passed",
                check=result.check_name,
                message=result.message,
            )

        if all_passed:
            events.append(OrderEvent(signal=signal))
            logger.info(
                "signal_approved",
                strategy=signal.strategy_name,
                symbol=signal.symbol,
            )

        return events
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_risk_checks.py -v`
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add src/tradebot/risk/ tests/unit/test_risk_checks.py
git commit -m "feat: risk manager with PDT, daily loss, position size, and time window checks"
```

---

### Task 9: Portfolio Tracker

**Files:**
- Create: `src/tradebot/portfolio/__init__.py`
- Create: `src/tradebot/portfolio/tracker.py`
- Create: `tests/unit/test_portfolio.py`

- [ ] **Step 1: Write tests for portfolio tracker**

`tests/unit/test_portfolio.py`:
```python
"""Tests for portfolio tracking."""
from decimal import Decimal

import pytest

from tradebot.core.enums import OrderSide, OrderStatus, SpreadType
from tradebot.core.events import FillEvent, SignalEvent
from tradebot.core.models import OrderLeg
from tradebot.portfolio.tracker import PortfolioTracker


@pytest.fixture
def tracker():
    return PortfolioTracker(starting_capital=Decimal("2500.00"))


def _make_fill(
    price: Decimal = Decimal("0.50"),
    strategy: str = "test",
    spread_type: SpreadType = SpreadType.CREDIT_SPREAD,
) -> FillEvent:
    signal = SignalEvent(
        strategy_name=strategy,
        spread_type=spread_type,
        symbol="XSP",
        legs=[
            OrderLeg(option_symbol="XSP250316P00565000", side=OrderSide.SELL_TO_OPEN, quantity=1),
            OrderLeg(option_symbol="XSP250316P00560000", side=OrderSide.BUY_TO_OPEN, quantity=1),
        ],
        target_price=price,
    )
    return FillEvent(
        broker_order_id="ord_123",
        signal=signal,
        fill_price=price,
        status=OrderStatus.FILLED,
    )


def test_initial_state(tracker):
    assert tracker.nav == Decimal("2500.00")
    assert tracker.daily_pnl == Decimal("0")
    assert len(tracker.open_positions) == 0


def test_record_fill_opens_position(tracker):
    fill = _make_fill(Decimal("0.50"))
    tracker.record_fill(fill)
    assert len(tracker.open_positions) == 1
    assert tracker.open_positions[0]["fill_price"] == Decimal("0.50")


def test_daily_pnl_tracking(tracker):
    tracker.record_realized_pnl(Decimal("30.00"))
    assert tracker.daily_pnl == Decimal("30.00")
    tracker.record_realized_pnl(Decimal("-10.00"))
    assert tracker.daily_pnl == Decimal("20.00")


def test_nav_updates_with_pnl(tracker):
    tracker.record_realized_pnl(Decimal("50.00"))
    assert tracker.nav == Decimal("2550.00")


def test_drawdown_calculation(tracker):
    assert tracker.drawdown_pct == Decimal("0")
    tracker.record_realized_pnl(Decimal("100.00"))  # NAV = 2600, peak = 2600
    tracker.record_realized_pnl(Decimal("-150.00"))  # NAV = 2450, peak = 2600
    expected = (Decimal("2600") - Decimal("2450")) / Decimal("2600") * 100
    assert tracker.drawdown_pct == expected


def test_reset_daily(tracker):
    tracker.record_realized_pnl(Decimal("50.00"))
    tracker.reset_daily()
    assert tracker.daily_pnl == Decimal("0")
    assert tracker.nav == Decimal("2550.00")  # NAV persists
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_portfolio.py -v`
Expected: FAIL

- [ ] **Step 3: Implement portfolio tracker**

`src/tradebot/portfolio/__init__.py`: empty file

`src/tradebot/portfolio/tracker.py`:
```python
"""Portfolio state tracking: positions, P&L, drawdown."""
from decimal import Decimal

import structlog

from tradebot.core.events import FillEvent

logger = structlog.get_logger()


class PortfolioTracker:
    """Tracks open positions, realized P&L, NAV, and drawdown."""

    def __init__(self, starting_capital: Decimal) -> None:
        self._starting_capital = starting_capital
        self._nav = starting_capital
        self._peak_nav = starting_capital
        self._daily_pnl = Decimal("0")
        self._total_pnl = Decimal("0")
        self._open_positions: list[dict] = []

    @property
    def nav(self) -> Decimal:
        return self._nav

    @property
    def daily_pnl(self) -> Decimal:
        return self._daily_pnl

    @property
    def open_positions(self) -> list[dict]:
        return list(self._open_positions)

    @property
    def drawdown_pct(self) -> Decimal:
        if self._peak_nav == 0:
            return Decimal("0")
        return (self._peak_nav - self._nav) / self._peak_nav * 100

    def record_fill(self, fill: FillEvent) -> None:
        """Record a new filled position."""
        position = {
            "broker_order_id": fill.broker_order_id,
            "strategy": fill.signal.strategy_name,
            "symbol": fill.signal.symbol,
            "spread_type": fill.signal.spread_type.value,
            "legs": fill.signal.legs,
            "fill_price": fill.fill_price,
            "timestamp": fill.timestamp,
        }
        self._open_positions.append(position)
        logger.info(
            "position_opened",
            symbol=fill.signal.symbol,
            strategy=fill.signal.strategy_name,
            fill_price=str(fill.fill_price),
        )

    def close_position(self, broker_order_id: str, pnl: Decimal) -> None:
        """Close a position and record realized P&L."""
        self._open_positions = [
            p for p in self._open_positions if p["broker_order_id"] != broker_order_id
        ]
        self.record_realized_pnl(pnl)

    def record_realized_pnl(self, pnl: Decimal) -> None:
        """Record realized P&L and update NAV."""
        self._daily_pnl += pnl
        self._total_pnl += pnl
        self._nav += pnl
        if self._nav > self._peak_nav:
            self._peak_nav = self._nav

    def reset_daily(self) -> None:
        """Reset daily P&L counter (called at start of each trading day)."""
        self._daily_pnl = Decimal("0")

    async def on_fill(self, fill: FillEvent) -> list:
        """Event handler for FillEvents."""
        self.record_fill(fill)
        return []
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_portfolio.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add src/tradebot/portfolio/ tests/unit/test_portfolio.py
git commit -m "feat: portfolio tracker with P&L, NAV, and drawdown tracking"
```

---

### Task 10: Order Manager

**Files:**
- Create: `src/tradebot/execution/order_manager.py`
- Create: `tests/unit/test_order_manager.py`

- [ ] **Step 1: Write tests for order manager**

`tests/unit/test_order_manager.py`:
```python
"""Tests for order management."""
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from tradebot.core.enums import OrderSide, OrderStatus, SpreadType
from tradebot.core.events import FillEvent, OrderEvent, SignalEvent
from tradebot.core.models import OrderLeg, OrderResult
from tradebot.execution.order_manager import OrderManager


def _make_order_event() -> OrderEvent:
    signal = SignalEvent(
        strategy_name="test",
        spread_type=SpreadType.CREDIT_SPREAD,
        symbol="XSP",
        legs=[
            OrderLeg(option_symbol="XSP250316P00565000", side=OrderSide.SELL_TO_OPEN, quantity=1),
            OrderLeg(option_symbol="XSP250316P00560000", side=OrderSide.BUY_TO_OPEN, quantity=1),
        ],
        target_price=Decimal("0.50"),
    )
    return OrderEvent(signal=signal)


@pytest.mark.asyncio
async def test_on_order_submits_to_broker():
    broker = AsyncMock()
    broker.submit_multileg_order.return_value = OrderResult(
        broker_order_id="ord_456",
        status=OrderStatus.FILLED,
    )
    manager = OrderManager(broker=broker)
    events = await manager.on_order(_make_order_event())

    broker.submit_multileg_order.assert_called_once()
    assert len(events) == 1
    assert isinstance(events[0], FillEvent)
    assert events[0].broker_order_id == "ord_456"
    assert events[0].fill_price == Decimal("0.50")


@pytest.mark.asyncio
async def test_on_order_handles_rejection():
    broker = AsyncMock()
    broker.submit_multileg_order.return_value = OrderResult(
        broker_order_id="ord_789",
        status=OrderStatus.REJECTED,
    )
    manager = OrderManager(broker=broker)
    events = await manager.on_order(_make_order_event())

    # Rejected orders still produce a FillEvent with rejected status
    assert len(events) == 1
    assert events[0].status == OrderStatus.REJECTED
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_order_manager.py -v`
Expected: FAIL

- [ ] **Step 3: Implement order manager**

`src/tradebot/execution/order_manager.py`:
```python
"""Order lifecycle management."""
import structlog

from tradebot.core.events import FillEvent, OrderEvent
from tradebot.execution.brokers.base import Broker

logger = structlog.get_logger()


class OrderManager:
    """Converts OrderEvents into broker orders and tracks lifecycle."""

    def __init__(self, broker: Broker) -> None:
        self._broker = broker

    async def on_order(self, event: OrderEvent) -> list:
        """Submit order to broker and return fill/rejection events."""
        signal = event.signal
        logger.info(
            "submitting_order",
            strategy=signal.strategy_name,
            symbol=signal.symbol,
            spread_type=signal.spread_type.value,
            legs=len(signal.legs),
            target_price=str(signal.target_price),
        )

        result = await self._broker.submit_multileg_order(
            legs=signal.legs,
            price=signal.target_price,
        )

        logger.info(
            "order_result",
            broker_order_id=result.broker_order_id,
            status=result.status.value,
        )

        return [
            FillEvent(
                broker_order_id=result.broker_order_id,
                signal=signal,
                fill_price=signal.target_price,
                status=result.status,
            )
        ]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_order_manager.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add src/tradebot/execution/order_manager.py tests/unit/test_order_manager.py
git commit -m "feat: order manager for broker submission and fill tracking"
```

---

### Task 11: Strategy Base Class and Iron Condor Strategy

**Files:**
- Create: `src/tradebot/strategy/__init__.py`
- Create: `src/tradebot/strategy/base.py`
- Create: `src/tradebot/strategy/strategies/__init__.py`
- Create: `src/tradebot/strategy/strategies/iron_condor.py`
- Create: `src/tradebot/strategy/registry.py`
- Create: `tests/unit/test_strategies.py`
- Create: `config/strategies/xsp_iron_condor.yaml`

- [ ] **Step 1: Write tests for strategy base and iron condor**

`tests/unit/test_strategies.py`:
```python
"""Tests for trading strategies."""
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path

import pytest

from tradebot.core.enums import OptionType, OrderSide, SpreadType
from tradebot.core.events import MarketEvent, SignalEvent
from tradebot.core.models import Bar, Greeks, OptionContract, OptionsChain
from tradebot.strategy.strategies.iron_condor import IronCondorStrategy
from tradebot.utils.config import load_strategy_config


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
        expiration=date(2026, 3, 16),
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


def _make_chain(underlying_price: Decimal = Decimal("570.00")) -> OptionsChain:
    calls = [
        _make_option("XSP_C575", OptionType.CALL, Decimal("575"), Decimal("0.30"), Decimal("2.00"), Decimal("2.20")),
        _make_option("XSP_C580", OptionType.CALL, Decimal("580"), Decimal("0.15"), Decimal("0.80"), Decimal("1.00")),
        _make_option("XSP_C585", OptionType.CALL, Decimal("585"), Decimal("0.08"), Decimal("0.30"), Decimal("0.45")),
    ]
    puts = [
        _make_option("XSP_P555", OptionType.PUT, Decimal("555"), Decimal("-0.08"), Decimal("0.25"), Decimal("0.40")),
        _make_option("XSP_P560", OptionType.PUT, Decimal("560"), Decimal("-0.15"), Decimal("0.70"), Decimal("0.90")),
        _make_option("XSP_P565", OptionType.PUT, Decimal("565"), Decimal("-0.30"), Decimal("1.80"), Decimal("2.10")),
    ]
    return OptionsChain(
        underlying="XSP",
        expiration=date(2026, 3, 16),
        underlying_price=underlying_price,
        calls=calls,
        puts=puts,
    )


def _make_market_event(chain: OptionsChain | None = None) -> MarketEvent:
    bar = Bar(
        symbol="XSP",
        timestamp=datetime(2026, 3, 16, 10, 30),
        open=Decimal("570"), high=Decimal("572"),
        low=Decimal("569"), close=Decimal("571"), volume=5000,
    )
    return MarketEvent(bar=bar, options_chain=chain or _make_chain())


def test_iron_condor_selects_strikes_by_delta():
    strategy = IronCondorStrategy(
        name="test_ic",
        symbol="XSP",
        short_call_delta=Decimal("0.15"),
        short_put_delta=Decimal("-0.15"),
        wing_width=Decimal("5"),
        min_credit=Decimal("0.30"),
        entry_earliest=time(9, 45),
        entry_latest=time(14, 0),
    )

    chain = _make_chain()
    legs = strategy.select_strikes(chain)

    assert legs is not None
    assert len(legs) == 4  # iron condor = 4 legs

    # Verify we have sell and buy sides
    sides = [leg.side for leg in legs]
    assert OrderSide.SELL_TO_OPEN in sides
    assert OrderSide.BUY_TO_OPEN in sides


def test_iron_condor_returns_none_when_no_valid_strikes():
    strategy = IronCondorStrategy(
        name="test_ic",
        symbol="XSP",
        short_call_delta=Decimal("0.15"),
        short_put_delta=Decimal("-0.15"),
        wing_width=Decimal("5"),
        min_credit=Decimal("5.00"),  # Unrealistically high
        entry_earliest=time(9, 45),
        entry_latest=time(14, 0),
    )

    chain = _make_chain()
    legs = strategy.select_strikes(chain)
    assert legs is None  # Can't achieve min credit


def test_iron_condor_on_market_event():
    strategy = IronCondorStrategy(
        name="test_ic",
        symbol="XSP",
        short_call_delta=Decimal("0.15"),
        short_put_delta=Decimal("-0.15"),
        wing_width=Decimal("5"),
        min_credit=Decimal("0.30"),
        entry_earliest=time(9, 45),
        entry_latest=time(14, 0),
    )

    event = _make_market_event()
    signals = strategy.evaluate(event)

    assert len(signals) <= 1  # 0 or 1 signal
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_strategies.py -v`
Expected: FAIL

- [ ] **Step 3: Implement strategy base class**

`src/tradebot/strategy/__init__.py`: empty file
`src/tradebot/strategy/strategies/__init__.py`: empty file

`src/tradebot/strategy/base.py`:
```python
"""Abstract base class for trading strategies."""
from abc import ABC, abstractmethod

from tradebot.core.events import MarketEvent, SignalEvent


class TradingStrategy(ABC):
    """Base class all strategies must implement."""

    def __init__(self, name: str, symbol: str) -> None:
        self.name = name
        self.symbol = symbol

    @abstractmethod
    def evaluate(self, event: MarketEvent) -> list[SignalEvent]:
        """Evaluate market data and return zero or more signals."""
        ...
```

- [ ] **Step 4: Implement iron condor strategy**

`src/tradebot/strategy/strategies/iron_condor.py`:
```python
"""0DTE Iron Condor strategy."""
from datetime import time
from decimal import Decimal

import structlog

from tradebot.core.enums import OrderSide, SpreadType
from tradebot.core.events import MarketEvent, SignalEvent
from tradebot.core.models import OptionContract, OptionsChain, OrderLeg
from tradebot.strategy.base import TradingStrategy

logger = structlog.get_logger()


class IronCondorStrategy(TradingStrategy):
    """Sells OTM call + put spreads on XSP, collects credit from time decay.

    Strike selection is delta-based: find options closest to target delta
    for the short strikes, then add wings at a fixed width.
    """

    def __init__(
        self,
        name: str,
        symbol: str,
        short_call_delta: Decimal,
        short_put_delta: Decimal,
        wing_width: Decimal,
        min_credit: Decimal,
        entry_earliest: time,
        entry_latest: time,
    ) -> None:
        super().__init__(name=name, symbol=symbol)
        self.short_call_delta = short_call_delta
        self.short_put_delta = short_put_delta
        self.wing_width = wing_width
        self.min_credit = min_credit
        self.entry_earliest = entry_earliest
        self.entry_latest = entry_latest
        self._has_position = False

    def evaluate(self, event: MarketEvent) -> list[SignalEvent]:
        """Evaluate market event and potentially emit a signal."""
        if self._has_position:
            return []

        if event.options_chain is None:
            return []

        if event.bar.symbol != self.symbol:
            return []

        current_time = event.bar.timestamp.time()
        if not (self.entry_earliest <= current_time <= self.entry_latest):
            return []

        legs = self.select_strikes(event.options_chain)
        if legs is None:
            return []

        # Estimate net credit: sum of short leg mids - sum of long leg mids
        # This is approximate; actual fill determines real credit
        credit = self._estimate_credit(event.options_chain, legs)
        if credit < self.min_credit:
            logger.info(
                "iron_condor_skip",
                reason="credit_too_low",
                estimated_credit=str(credit),
                min_credit=str(self.min_credit),
            )
            return []

        self._has_position = True
        return [
            SignalEvent(
                strategy_name=self.name,
                spread_type=SpreadType.IRON_CONDOR,
                symbol=self.symbol,
                legs=legs,
                target_price=credit,
            )
        ]

    def select_strikes(self, chain: OptionsChain) -> list[OrderLeg] | None:
        """Select 4 legs for the iron condor based on delta."""
        short_call = self._find_by_delta(chain.calls, self.short_call_delta)
        short_put = self._find_by_delta(chain.puts, self.short_put_delta)

        if short_call is None or short_put is None:
            return None

        # Find wings
        long_call_strike = short_call.strike + self.wing_width
        long_put_strike = short_put.strike - self.wing_width

        long_call = self._find_by_strike(chain.calls, long_call_strike)
        long_put = self._find_by_strike(chain.puts, long_put_strike)

        if long_call is None or long_put is None:
            return None

        return [
            OrderLeg(option_symbol=short_put.symbol, side=OrderSide.SELL_TO_OPEN, quantity=1),
            OrderLeg(option_symbol=long_put.symbol, side=OrderSide.BUY_TO_OPEN, quantity=1),
            OrderLeg(option_symbol=short_call.symbol, side=OrderSide.SELL_TO_OPEN, quantity=1),
            OrderLeg(option_symbol=long_call.symbol, side=OrderSide.BUY_TO_OPEN, quantity=1),
        ]

    def _find_by_delta(
        self, contracts: list[OptionContract], target_delta: Decimal
    ) -> OptionContract | None:
        """Find the contract with delta closest to target."""
        if not contracts:
            return None
        return min(contracts, key=lambda c: abs(c.greeks.delta - target_delta))

    def _find_by_strike(
        self, contracts: list[OptionContract], target_strike: Decimal
    ) -> OptionContract | None:
        """Find the contract at or closest to the target strike."""
        if not contracts:
            return None
        exact = [c for c in contracts if c.strike == target_strike]
        if exact:
            return exact[0]
        return min(contracts, key=lambda c: abs(c.strike - target_strike))

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

- [ ] **Step 5: Implement strategy registry**

`src/tradebot/strategy/registry.py`:
```python
"""Strategy factory that loads strategies from config."""
from datetime import time
from decimal import Decimal
from pathlib import Path

from tradebot.strategy.base import TradingStrategy
from tradebot.strategy.strategies.iron_condor import IronCondorStrategy
from tradebot.utils.config import StrategyConfig, load_strategy_config

STRATEGY_CLASSES = {
    "IronCondorStrategy": IronCondorStrategy,
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

    raise ValueError(f"No loader for strategy class: {class_name}")
```

- [ ] **Step 6: Create example strategy config**

`config/strategies/xsp_iron_condor.yaml`:
```yaml
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
  min_credit: 0.30

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

- [ ] **Step 7: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_strategies.py -v`
Expected: all PASS

- [ ] **Step 8: Commit**

```bash
git add src/tradebot/strategy/ tests/unit/test_strategies.py config/strategies/
git commit -m "feat: strategy base class, iron condor strategy, and registry"
```

---

## Chunk 4: Integration & Main Loop

### Task 12: Market Data Handler

**Files:**
- Create: `src/tradebot/data/__init__.py`
- Create: `src/tradebot/data/handler.py`
- Create: `src/tradebot/data/sources/__init__.py`
- Create: `src/tradebot/data/sources/tradier.py`

- [ ] **Step 1: Implement Tradier data source**

`src/tradebot/data/__init__.py`: empty file
`src/tradebot/data/sources/__init__.py`: empty file

`src/tradebot/data/sources/tradier.py`:
```python
"""Tradier market data source for options chains and quotes."""
from datetime import date
from decimal import Decimal

import structlog

from tradebot.core.models import Bar, OptionsChain
from tradebot.execution.brokers.tradier import TradierBroker

logger = structlog.get_logger()


class TradierDataSource:
    """Fetches market data from Tradier API.

    Reuses the TradierBroker client since Tradier serves both
    trading and market data from the same API.
    """

    def __init__(self, broker: TradierBroker) -> None:
        self._broker = broker

    async def get_options_chain(self, symbol: str, expiration: date) -> OptionsChain:
        return await self._broker.get_options_chain(symbol, expiration)

    async def get_quote(self, symbol: str) -> Bar:
        """Get current quote as a Bar."""
        from datetime import datetime

        result = await self._broker._request(
            "GET", "/v1/markets/quotes", params={"symbols": symbol}
        )
        quote = result.get("quotes", {}).get("quote", {})
        return Bar(
            symbol=symbol,
            timestamp=datetime.now(),
            open=Decimal(str(quote.get("open", 0))),
            high=Decimal(str(quote.get("high", 0))),
            low=Decimal(str(quote.get("low", 0))),
            close=Decimal(str(quote.get("last", 0))),
            volume=quote.get("volume", 0),
        )
```

- [ ] **Step 2: Implement market data handler**

`src/tradebot/data/handler.py`:
```python
"""Market data handler that orchestrates data sources and emits events."""
from datetime import date, datetime

import structlog

from tradebot.core.events import MarketEvent
from tradebot.data.sources.tradier import TradierDataSource

logger = structlog.get_logger()


class MarketDataHandler:
    """Fetches market data and produces MarketEvents."""

    def __init__(self, data_source: TradierDataSource) -> None:
        self._data_source = data_source

    async def fetch_market_data(self, symbol: str, expiration: date) -> MarketEvent:
        """Fetch current quote and options chain, return as MarketEvent."""
        logger.info("fetching_market_data", symbol=symbol, expiration=str(expiration))

        bar = await self._data_source.get_quote(symbol)
        chain = await self._data_source.get_options_chain(symbol, expiration)

        return MarketEvent(bar=bar, options_chain=chain)
```

- [ ] **Step 3: Commit**

```bash
git add src/tradebot/data/
git commit -m "feat: market data handler with Tradier data source"
```

---

### Task 13: Main Event Loop

**Files:**
- Create: `src/tradebot/main.py`
- Create: `tests/integration/__init__.py`
- Create: `tests/integration/test_event_flow.py`

- [ ] **Step 1: Write integration test for full event flow**

`tests/integration/__init__.py`: empty file

`tests/integration/test_event_flow.py`:
```python
"""Integration test: full event pipeline with mocked broker."""
from datetime import date, datetime, time
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from tradebot.core.enums import OptionType, OrderSide, OrderStatus, SpreadType
from tradebot.core.event_bus import EventBus
from tradebot.core.events import MarketEvent
from tradebot.core.models import (
    Bar, Greeks, OptionContract, OptionsChain, OrderLeg, OrderResult,
)
from tradebot.execution.order_manager import OrderManager
from tradebot.portfolio.tracker import PortfolioTracker
from tradebot.risk.checks import TimeWindowCheck, DuplicateCheck
from tradebot.risk.manager import RiskManager
from tradebot.strategy.strategies.iron_condor import IronCondorStrategy


def _make_chain() -> OptionsChain:
    def opt(sym, otype, strike, delta, bid, ask):
        return OptionContract(
            symbol=sym, underlying="XSP", option_type=otype,
            strike=Decimal(str(strike)), expiration=date(2026, 3, 16),
            bid=Decimal(str(bid)), ask=Decimal(str(ask)),
            last=Decimal(str((bid + ask) / 2)), volume=100, open_interest=500,
            greeks=Greeks(
                delta=Decimal(str(delta)), gamma=Decimal("0.05"),
                theta=Decimal("-0.10"), vega=Decimal("0.08"),
                implied_volatility=Decimal("0.20"),
            ),
        )

    return OptionsChain(
        underlying="XSP", expiration=date(2026, 3, 16),
        underlying_price=Decimal("570.00"),
        calls=[
            opt("XSP_C580", OptionType.CALL, 580, 0.15, 0.80, 1.00),
            opt("XSP_C585", OptionType.CALL, 585, 0.08, 0.30, 0.45),
        ],
        puts=[
            opt("XSP_P555", OptionType.PUT, 555, -0.08, 0.25, 0.40),
            opt("XSP_P560", OptionType.PUT, 560, -0.15, 0.70, 0.90),
        ],
    )


@pytest.mark.asyncio
async def test_full_pipeline_market_to_fill():
    """MarketEvent → Strategy → Risk → Order → Fill → Portfolio"""
    # Setup components
    strategy = IronCondorStrategy(
        name="test_ic", symbol="XSP",
        short_call_delta=Decimal("0.15"), short_put_delta=Decimal("-0.15"),
        wing_width=Decimal("5"), min_credit=Decimal("0.10"),
        entry_earliest=time(9, 0), entry_latest=time(15, 0),
    )

    risk_manager = RiskManager()
    risk_manager.add_check(TimeWindowCheck(earliest=time(9, 0), latest=time(15, 0)))
    risk_manager.add_check(DuplicateCheck(open_symbols=set()))

    broker = AsyncMock()
    broker.submit_multileg_order.return_value = OrderResult(
        broker_order_id="ord_integration_test",
        status=OrderStatus.FILLED,
    )
    order_manager = OrderManager(broker=broker)
    portfolio = PortfolioTracker(starting_capital=Decimal("2500.00"))

    # Wire up event bus
    bus = EventBus()

    async def on_market(event: MarketEvent) -> list:
        return strategy.evaluate(event)

    bus.register_handler(MarketEvent, on_market)

    # Manual pipeline test (not using bus dispatch for clarity)
    bar = Bar(
        symbol="XSP", timestamp=datetime(2026, 3, 16, 10, 30),
        open=Decimal("570"), high=Decimal("572"),
        low=Decimal("569"), close=Decimal("571"), volume=5000,
    )
    market_event = MarketEvent(bar=bar, options_chain=_make_chain())

    # Step 1: Strategy evaluates
    signals = strategy.evaluate(market_event)
    assert len(signals) == 1, "Strategy should produce one signal"
    assert signals[0].spread_type == SpreadType.IRON_CONDOR

    # Step 2: Risk manager checks
    risk_events = await risk_manager.on_signal(signals[0])
    order_events = [e for e in risk_events if hasattr(e, "signal")]
    assert len(order_events) == 1, "Risk manager should approve the signal"

    # Step 3: Order manager submits
    fill_events = await order_manager.on_order(order_events[0])
    assert len(fill_events) == 1
    assert fill_events[0].status == OrderStatus.FILLED

    # Step 4: Portfolio records
    await portfolio.on_fill(fill_events[0])
    assert len(portfolio.open_positions) == 1
```

- [ ] **Step 2: Run integration test**

Run: `uv run pytest tests/integration/test_event_flow.py -v`
Expected: PASS

- [ ] **Step 3: Implement main entry point**

`src/tradebot/main.py`:
```python
"""Main entry point for the trading bot."""
import asyncio
import sys
from datetime import date, time
from decimal import Decimal
from pathlib import Path

import structlog

from tradebot.core.event_bus import EventBus
from tradebot.core.events import FillEvent, MarketEvent, OrderEvent, SignalEvent
from tradebot.data.handler import MarketDataHandler
from tradebot.data.sources.tradier import TradierDataSource
from tradebot.execution.brokers.tradier import TradierBroker
from tradebot.execution.order_manager import OrderManager
from tradebot.portfolio.tracker import PortfolioTracker
from tradebot.risk.checks import (
    DuplicateCheck, MaxDailyLossCheck, MaxDrawdownCheck, PDTCheck, TimeWindowCheck,
)
from tradebot.risk.manager import RiskManager
from tradebot.strategy.registry import load_strategy
from tradebot.utils.config import Settings
from tradebot.utils.logging import setup_logging

logger = structlog.get_logger()


async def run_bot(settings: Settings) -> None:
    """Run the trading bot main loop."""
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

    # Initialize components
    data_source = TradierDataSource(broker)
    market_data = MarketDataHandler(data_source)
    order_manager = OrderManager(broker)
    portfolio = PortfolioTracker(starting_capital=settings.starting_capital)
    risk_manager = RiskManager()

    # Wire risk checks
    # Note: PDTCheck requires a repository instance (added in persistence task)
    # For now, use the checks that don't need DB state
    risk_manager.add_check(TimeWindowCheck(
        earliest=time(9, 45), latest=time(14, 0),
    ))
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

    # Load strategies from config/strategies/
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

    # Event observer for logging
    async def log_observer(event):
        logger.debug("event", type=type(event).__name__)

    bus.add_observer(log_observer)

    # Main polling loop
    logger.info("bot_started", strategies=len(strategies))
    shutdown = asyncio.Event()

    try:
        while not shutdown.is_set():
            for strategy in strategies:
                try:
                    today = date.today()
                    event = await market_data.fetch_market_data(strategy.symbol, today)
                    await bus.publish(event)
                except Exception as e:
                    logger.error("market_data_error", symbol=strategy.symbol, error=str(e))

            # Process all queued events
            while await bus.process_one():
                pass

            # Wait before next poll
            await asyncio.sleep(60)  # Poll every 60 seconds
    except KeyboardInterrupt:
        logger.info("bot_shutdown_requested")
    finally:
        logger.info("bot_stopped")


def main() -> None:
    """CLI entry point."""
    setup_logging()
    settings = Settings()
    asyncio.run(run_bot(settings))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Commit**

```bash
git add src/tradebot/main.py tests/integration/
git commit -m "feat: main event loop and integration test for full pipeline"
```

---

### Task 14: Run All Tests

- [ ] **Step 1: Run full test suite**

Run: `uv run pytest -v --tb=short`
Expected: all PASS

- [ ] **Step 2: Run linting**

Run: `uv run ruff check src/ tests/`
Expected: clean (or fix any issues)

- [ ] **Step 3: Commit any fixes**

```bash
git add -A
git commit -m "fix: address lint issues from full test run"
```

---

## Future Chunks (not in this plan)

The following are deferred to subsequent implementation plans:

- **Credit Spread and Debit Spread strategies** — Task 11 pattern repeated
- **FastAPI backend** — REST routes + WebSocket for dashboard
- **React frontend** — Vite + TypeScript SPA
- **Alembic migrations** — Schema versioning
- **Simulated broker** — For offline backtesting
- **Historical data feed** — For backtesting
- **Portfolio analytics** — Sharpe, win rate, etc.
