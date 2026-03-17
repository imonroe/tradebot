# Dashboard & Docker Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a FastAPI REST/WebSocket backend + React dashboard for monitoring the bot, and containerize the full application with Docker.

**Architecture:** The bot loop and FastAPI server run as concurrent asyncio tasks in the same process, sharing component state (portfolio tracker, strategies, risk manager) via a shared `AppState` object. The React frontend is a Vite+TypeScript SPA that communicates via REST for reads and WebSocket for real-time updates. Docker Compose runs both backend and frontend in separate containers.

**Tech Stack:** FastAPI, uvicorn, WebSocket, React 18, Vite, TypeScript, Tailwind CSS, Recharts, Docker, Docker Compose

**Spec:** `docs/superpowers/specs/2026-03-16-tradebot-design.md`

---

## Chunk 1: FastAPI Backend

### Task 1: Shared App State and FastAPI Scaffold

**Files:**
- Create: `src/tradebot/api/__init__.py`
- Create: `src/tradebot/api/state.py`
- Create: `src/tradebot/api/app.py`
- Create: `tests/unit/test_api.py`

- [ ] **Step 1: Write tests for app state and health endpoint**

`tests/unit/test_api.py`:
```python
"""Tests for FastAPI API."""
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from tradebot.api.app import create_app
from tradebot.api.state import AppState
from tradebot.portfolio.tracker import PortfolioTracker


@pytest.fixture
def app_state():
    portfolio = PortfolioTracker(starting_capital=Decimal("2500.00"))
    return AppState(
        portfolio=portfolio,
        strategies=[],
        mode="paper",
    )


@pytest.fixture
def client(app_state):
    app = create_app(app_state)
    return TestClient(app)


def test_health_endpoint(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["mode"] == "paper"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_api.py -v`
Expected: FAIL

- [ ] **Step 3: Implement AppState**

`src/tradebot/api/__init__.py`: empty file

`src/tradebot/api/state.py`:
```python
"""Shared application state between bot loop and API."""
from dataclasses import dataclass, field

from tradebot.portfolio.tracker import PortfolioTracker
from tradebot.strategy.base import TradingStrategy


@dataclass
class AppState:
    """Shared state accessible by both the bot loop and API routes."""

    portfolio: PortfolioTracker
    strategies: list[TradingStrategy] = field(default_factory=list)
    mode: str = "paper"
    bot_running: bool = False
    pdt_day_trades_used: int = 0
```

- [ ] **Step 4: Implement FastAPI app factory**

`src/tradebot/api/app.py`:
```python
"""FastAPI application factory."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from tradebot.api.state import AppState


def create_app(state: AppState) -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(title="Tradebot API", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.state.app_state = state

    @app.get("/api/health")
    async def health():
        return {
            "status": "ok",
            "mode": state.mode,
            "bot_running": state.bot_running,
        }

    # Import and include route modules
    from tradebot.api.routes import portfolio, trades, strategies

    app.include_router(portfolio.router, prefix="/api")
    app.include_router(trades.router, prefix="/api")
    app.include_router(strategies.router, prefix="/api")

    return app
```

- [ ] **Step 5: Create stub route files so imports work**

`src/tradebot/api/routes/__init__.py`: empty file

`src/tradebot/api/routes/portfolio.py`:
```python
"""Portfolio API routes."""
from fastapi import APIRouter

router = APIRouter(tags=["portfolio"])
```

`src/tradebot/api/routes/trades.py`:
```python
"""Trades API routes."""
from fastapi import APIRouter

router = APIRouter(tags=["trades"])
```

`src/tradebot/api/routes/strategies.py`:
```python
"""Strategies API routes."""
from fastapi import APIRouter

router = APIRouter(tags=["strategies"])
```

- [ ] **Step 6: Add `httpx` test dependency (needed for TestClient)**

Add to `pyproject.toml` dev dependencies:
```
"httpx>=0.27",
```
Note: `httpx` is already a runtime dependency, so TestClient will work.

- [ ] **Step 7: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_api.py -v`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add src/tradebot/api/ tests/unit/test_api.py
git commit -m "feat: FastAPI app scaffold with health endpoint and shared state"
```

---

### Task 2: Portfolio API Routes

**Files:**
- Modify: `src/tradebot/api/routes/portfolio.py`
- Modify: `tests/unit/test_api.py`

- [ ] **Step 1: Add portfolio endpoint tests**

Append to `tests/unit/test_api.py`:
```python
def test_portfolio_overview(client, app_state):
    response = client.get("/api/portfolio")
    assert response.status_code == 200
    data = response.json()
    assert data["nav"] == "2500.00"
    assert data["daily_pnl"] == "0"
    assert data["drawdown_pct"] == "0"
    assert data["open_positions"] == []


def test_portfolio_after_pnl(client, app_state):
    app_state.portfolio.record_realized_pnl(Decimal("50.00"))
    response = client.get("/api/portfolio")
    data = response.json()
    assert data["nav"] == "2550.00"
    assert data["daily_pnl"] == "50.00"


def test_positions_endpoint(client, app_state):
    response = client.get("/api/portfolio/positions")
    assert response.status_code == 200
    assert response.json() == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_api.py -v`
Expected: new tests FAIL (404)

- [ ] **Step 3: Implement portfolio routes**

`src/tradebot/api/routes/portfolio.py`:
```python
"""Portfolio API routes."""
from fastapi import APIRouter, Request

router = APIRouter(tags=["portfolio"])


@router.get("/portfolio")
async def get_portfolio(request: Request):
    """Get portfolio overview: NAV, P&L, drawdown."""
    state = request.app.state.app_state
    portfolio = state.portfolio
    return {
        "nav": str(portfolio.nav),
        "daily_pnl": str(portfolio.daily_pnl),
        "drawdown_pct": str(portfolio.drawdown_pct),
        "open_positions": [
            {
                "broker_order_id": p["broker_order_id"],
                "strategy": p["strategy"],
                "symbol": p["symbol"],
                "spread_type": p["spread_type"],
                "fill_price": str(p["fill_price"]),
                "timestamp": p["timestamp"].isoformat(),
            }
            for p in portfolio.open_positions
        ],
        "pdt_day_trades_used": state.pdt_day_trades_used,
        "mode": state.mode,
    }


@router.get("/portfolio/positions")
async def get_positions(request: Request):
    """Get open positions."""
    state = request.app.state.app_state
    return [
        {
            "broker_order_id": p["broker_order_id"],
            "strategy": p["strategy"],
            "symbol": p["symbol"],
            "spread_type": p["spread_type"],
            "fill_price": str(p["fill_price"]),
            "timestamp": p["timestamp"].isoformat(),
        }
        for p in state.portfolio.open_positions
    ]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_api.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add src/tradebot/api/routes/portfolio.py tests/unit/test_api.py
git commit -m "feat: portfolio API routes with NAV, P&L, and positions"
```

---

### Task 3: Trades and Strategies API Routes

**Files:**
- Modify: `src/tradebot/api/routes/trades.py`
- Modify: `src/tradebot/api/routes/strategies.py`
- Modify: `tests/unit/test_api.py`
- Modify: `src/tradebot/api/state.py`

- [ ] **Step 1: Add trades and strategies tests**

Append to `tests/unit/test_api.py`:
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from tradebot.persistence.database import Base
from tradebot.persistence.repository import Repository


@pytest.fixture
def repo():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    return Repository(session)


@pytest.fixture
def app_state_with_repo(repo):
    portfolio = PortfolioTracker(starting_capital=Decimal("2500.00"))
    return AppState(
        portfolio=portfolio,
        strategies=[],
        mode="paper",
        repository=repo,
    )


@pytest.fixture
def client_with_repo(app_state_with_repo):
    app = create_app(app_state_with_repo)
    return TestClient(app)


def test_trades_endpoint_empty(client_with_repo):
    response = client_with_repo.get("/api/trades")
    assert response.status_code == 200
    assert response.json() == []


def test_trades_endpoint_with_data(client_with_repo, app_state_with_repo):
    repo = app_state_with_repo.repository
    repo.create_trade(
        strategy="xsp_iron_condor", symbol="XSP",
        spread_type="iron_condor", entry_price=Decimal("0.50"),
    )
    response = client_with_repo.get("/api/trades")
    data = response.json()
    assert len(data) == 1
    assert data[0]["strategy"] == "xsp_iron_condor"
    assert data[0]["status"] == "open"


def test_strategies_endpoint(client):
    response = client.get("/api/strategies")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_api.py -v`
Expected: new tests FAIL

- [ ] **Step 3: Add repository to AppState**

Modify `src/tradebot/api/state.py`:
```python
"""Shared application state between bot loop and API."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from tradebot.persistence.repository import Repository
from tradebot.portfolio.tracker import PortfolioTracker
from tradebot.strategy.base import TradingStrategy

if TYPE_CHECKING:
    from tradebot.api.websocket import ConnectionManager


@dataclass
class AppState:
    """Shared state accessible by both the bot loop and API routes."""

    portfolio: PortfolioTracker
    strategies: list[TradingStrategy] = field(default_factory=list)
    mode: str = "paper"
    bot_running: bool = False
    pdt_day_trades_used: int = 0
    repository: Repository | None = None
    ws_manager: "ConnectionManager | None" = None
```

- [ ] **Step 3b: Add `get_recent_trades` to Repository**

Add to `src/tradebot/persistence/repository.py`:
```python
    def get_recent_trades(self, limit: int = 100) -> list[TradeRecord]:
        stmt = select(TradeRecord).order_by(TradeRecord.entry_time.desc()).limit(limit)
        return list(self._session.execute(stmt).scalars().all())
```

- [ ] **Step 4: Implement trades routes**

`src/tradebot/api/routes/trades.py`:
```python
"""Trades API routes."""
from fastapi import APIRouter, Request

router = APIRouter(tags=["trades"])


@router.get("/trades")
async def get_trades(request: Request):
    """Get trade history."""
    state = request.app.state.app_state
    if state.repository is None:
        return []

    all_trades = state.repository.get_recent_trades(limit=100)

    return [
        {
            "id": t.id,
            "strategy": t.strategy,
            "symbol": t.symbol,
            "spread_type": t.spread_type,
            "entry_price": str(t.entry_price),
            "exit_price": str(t.exit_price) if t.exit_price else None,
            "pnl": str(t.pnl) if t.pnl else None,
            "status": t.status,
            "entry_time": t.entry_time.isoformat() if t.entry_time else None,
            "exit_time": t.exit_time.isoformat() if t.exit_time else None,
        }
        for t in all_trades
    ]
```

- [ ] **Step 5: Implement strategies routes**

`src/tradebot/api/routes/strategies.py`:
```python
"""Strategies API routes."""
from fastapi import APIRouter, Request

router = APIRouter(tags=["strategies"])


@router.get("/strategies")
async def get_strategies(request: Request):
    """Get loaded strategies and their status."""
    state = request.app.state.app_state
    return [
        {
            "name": s.name,
            "symbol": s.symbol,
            "type": type(s).__name__,
            "has_position": getattr(s, "_has_position", False),
        }
        for s in state.strategies
    ]
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_api.py -v`
Expected: all PASS

- [ ] **Step 7: Commit**

```bash
git add src/tradebot/api/ tests/unit/test_api.py
git commit -m "feat: trades and strategies API routes"
```

---

### Task 4: WebSocket for Real-Time Updates

**Files:**
- Create: `src/tradebot/api/websocket.py`
- Modify: `src/tradebot/api/app.py`
- Modify: `tests/unit/test_api.py`

- [ ] **Step 1: Write WebSocket test**

Append to `tests/unit/test_api.py`:
```python
def test_websocket_connection(client):
    with client.websocket_connect("/api/ws") as ws:
        # Server should send initial state on connect
        data = ws.receive_json()
        assert "nav" in data
        assert "mode" in data
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_api.py::test_websocket_connection -v`
Expected: FAIL

- [ ] **Step 3: Implement WebSocket manager**

`src/tradebot/api/websocket.py`:
```python
"""WebSocket manager for real-time dashboard updates."""
import asyncio
import json
from decimal import Decimal

from fastapi import WebSocket
import structlog

logger = structlog.get_logger()


class DecimalEncoder(json.JSONEncoder):
    """JSON encoder that handles Decimal types."""

    def default(self, o):
        if isinstance(o, Decimal):
            return str(o)
        return super().default(o)


class ConnectionManager:
    """Manages WebSocket connections and broadcasts updates."""

    def __init__(self):
        self._connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.append(websocket)
        logger.info("websocket_connected", total=len(self._connections))

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.remove(websocket)
        logger.info("websocket_disconnected", total=len(self._connections))

    async def broadcast(self, data: dict) -> None:
        """Send data to all connected clients."""
        message = json.dumps(data, cls=DecimalEncoder)
        dead = []
        for ws in self._connections:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._connections.remove(ws)

    @property
    def connection_count(self) -> int:
        return len(self._connections)
```

- [ ] **Step 4: Wire WebSocket into app**

Modify `src/tradebot/api/app.py` — add after the route includes:
```python
    from tradebot.api.websocket import ConnectionManager

    ws_manager = ConnectionManager()
    app.state.ws_manager = ws_manager

    @app.websocket("/api/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await ws_manager.connect(websocket)
        try:
            # Send initial state
            portfolio = state.portfolio
            await websocket.send_json({
                "type": "snapshot",
                "nav": str(portfolio.nav),
                "daily_pnl": str(portfolio.daily_pnl),
                "drawdown_pct": str(portfolio.drawdown_pct),
                "positions": len(portfolio.open_positions),
                "mode": state.mode,
                "bot_running": state.bot_running,
                "pdt_day_trades_used": state.pdt_day_trades_used,
            })
            # Keep connection alive, wait for disconnect
            while True:
                await websocket.receive_text()
        except Exception:
            ws_manager.disconnect(websocket)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_api.py -v`
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add src/tradebot/api/
git commit -m "feat: WebSocket endpoint for real-time dashboard updates"
```

---

### Task 5: Integrate API into Main Loop

**Files:**
- Modify: `src/tradebot/main.py`

- [ ] **Step 1: Refactor main.py to run API server alongside bot loop**

Replace `src/tradebot/main.py`:
```python
"""Main entry point for the trading bot."""
import asyncio
import sys
from datetime import date, time
from pathlib import Path

import structlog
import uvicorn

from tradebot.api.app import create_app
from tradebot.api.state import AppState
from tradebot.core.event_bus import EventBus
from tradebot.core.events import FillEvent, MarketEvent, OrderEvent, SignalEvent
from tradebot.data.handler import MarketDataHandler
from tradebot.data.sources.tradier import TradierDataSource
from tradebot.execution.brokers.tradier import TradierBroker
from tradebot.execution.order_manager import OrderManager
from tradebot.persistence.database import Base, create_db_engine, create_session
from tradebot.persistence.repository import Repository
from tradebot.portfolio.tracker import PortfolioTracker
from tradebot.risk.checks import (
    DuplicateCheck,
    MaxDailyLossCheck,
    MaxDrawdownCheck,
    TimeWindowCheck,
)
from tradebot.risk.manager import RiskManager
from tradebot.strategy.registry import load_strategy
from tradebot.utils.config import Settings
from tradebot.utils.logging import setup_logging

logger = structlog.get_logger()


async def bot_loop(
    state: AppState,
    market_data: MarketDataHandler,
    bus: EventBus,
    shutdown: asyncio.Event,
) -> None:
    """Run the trading bot polling loop."""
    state.bot_running = True
    logger.info("bot_loop_started", strategies=len(state.strategies))

    try:
        while not shutdown.is_set():
            for strategy in state.strategies:
                try:
                    today = date.today()
                    event = await market_data.fetch_market_data(strategy.symbol, today)
                    await bus.publish(event)
                except Exception as e:
                    logger.error("market_data_error", symbol=strategy.symbol, error=str(e))

            while await bus.process_one():
                pass

            # Broadcast portfolio update to WebSocket clients
            try:
                ws_manager = state.ws_manager
                if ws_manager and ws_manager.connection_count > 0:
                    await ws_manager.broadcast({
                        "type": "update",
                        "nav": str(state.portfolio.nav),
                        "daily_pnl": str(state.portfolio.daily_pnl),
                        "drawdown_pct": str(state.portfolio.drawdown_pct),
                        "positions": len(state.portfolio.open_positions),
                        "bot_running": state.bot_running,
                        "pdt_day_trades_used": state.pdt_day_trades_used,
                    })
            except Exception:
                pass

            try:
                await asyncio.wait_for(shutdown.wait(), timeout=60)
            except asyncio.TimeoutError:
                pass
    finally:
        state.bot_running = False
        logger.info("bot_loop_stopped")


async def run_bot(settings: Settings) -> None:
    """Run the trading bot and API server."""
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

    # Initialize database
    engine = create_db_engine(settings.database_url)
    Base.metadata.create_all(engine)
    session = create_session(engine)
    repo = Repository(session)

    # Initialize components
    data_source = TradierDataSource(broker)
    market_data = MarketDataHandler(data_source)
    order_manager = OrderManager(broker)
    portfolio = PortfolioTracker(starting_capital=settings.starting_capital)
    risk_manager = RiskManager()

    # Wire risk checks
    risk_manager.add_check(TimeWindowCheck(earliest=time(9, 45), latest=time(14, 0)))
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

    # Load strategies
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

    # Create shared state
    state = AppState(
        portfolio=portfolio,
        strategies=strategies,
        mode=settings.mode,
        repository=repo,
    )

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

    async def log_observer(event):
        logger.debug("event", type=type(event).__name__)

    bus.add_observer(log_observer)

    # Create FastAPI app
    app = create_app(state)
    state.ws_manager = app.state.ws_manager

    # Run API server and bot loop concurrently
    shutdown = asyncio.Event()

    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config)

    try:
        await asyncio.gather(
            server.serve(),
            bot_loop(state, market_data, bus, shutdown),
        )
    except KeyboardInterrupt:
        shutdown.set()


def main() -> None:
    """CLI entry point."""
    setup_logging()
    settings = Settings()
    asyncio.run(run_bot(settings))


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run full test suite to verify no regressions**

Run: `uv run pytest -v --tb=short`
Expected: all PASS

- [ ] **Step 3: Commit**

```bash
git add src/tradebot/main.py
git commit -m "feat: run API server and bot loop concurrently"
```

---

## Chunk 2: React Dashboard

### Task 6: React App Scaffolding

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tsconfig.node.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/index.html`
- Create: `frontend/postcss.config.js`
- Create: `frontend/tailwind.config.js`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/index.css`

- [ ] **Step 1: Initialize frontend with package.json**

`frontend/package.json`:
```json
{
  "name": "tradebot-dashboard",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.28.0",
    "recharts": "^2.13.3"
  },
  "devDependencies": {
    "@types/react": "^18.3.12",
    "@types/react-dom": "^18.3.1",
    "@vitejs/plugin-react": "^4.3.4",
    "autoprefixer": "^10.4.20",
    "postcss": "^8.4.49",
    "tailwindcss": "^3.4.16",
    "typescript": "^5.7.2",
    "vite": "^6.0.3"
  }
}
```

- [ ] **Step 2: Create config files**

`frontend/tsconfig.json`:
```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "forceConsistentCasingInFileNames": true
  },
  "include": ["src"]
}
```

`frontend/tsconfig.node.json`:
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2023"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "strict": true
  },
  "include": ["vite.config.ts"]
}
```

`frontend/vite.config.ts`:
```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        ws: true,
      },
    },
  },
});
```

`frontend/postcss.config.js`:
```javascript
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
```

`frontend/tailwind.config.js`:
```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {},
  },
  plugins: [],
};
```

`frontend/index.html`:
```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Tradebot Dashboard</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 3: Create app entry point and base styles**

`frontend/src/index.css`:
```css
@tailwind base;
@tailwind components;
@tailwind utilities;

body {
  @apply bg-gray-950 text-gray-100;
}
```

`frontend/src/main.tsx`:
```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
);
```

`frontend/src/App.tsx`:
```tsx
import { Routes, Route, NavLink } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import Trades from "./pages/Trades";
import Strategies from "./pages/Strategies";

function App() {
  return (
    <div className="min-h-screen">
      <nav className="bg-gray-900 border-b border-gray-800 px-6 py-3">
        <div className="flex items-center gap-8">
          <h1 className="text-xl font-bold text-green-400">Tradebot</h1>
          <div className="flex gap-4">
            <NavLink
              to="/"
              className={({ isActive }) =>
                `px-3 py-1 rounded ${isActive ? "bg-gray-700 text-white" : "text-gray-400 hover:text-white"}`
              }
            >
              Dashboard
            </NavLink>
            <NavLink
              to="/trades"
              className={({ isActive }) =>
                `px-3 py-1 rounded ${isActive ? "bg-gray-700 text-white" : "text-gray-400 hover:text-white"}`
              }
            >
              Trades
            </NavLink>
            <NavLink
              to="/strategies"
              className={({ isActive }) =>
                `px-3 py-1 rounded ${isActive ? "bg-gray-700 text-white" : "text-gray-400 hover:text-white"}`
              }
            >
              Strategies
            </NavLink>
          </div>
        </div>
      </nav>
      <main className="p-6">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/trades" element={<Trades />} />
          <Route path="/strategies" element={<Strategies />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
```

- [ ] **Step 4: Create placeholder pages**

`frontend/src/pages/Dashboard.tsx`:
```tsx
export default function Dashboard() {
  return <div>Dashboard loading...</div>;
}
```

`frontend/src/pages/Trades.tsx`:
```tsx
export default function Trades() {
  return <div>Trades loading...</div>;
}
```

`frontend/src/pages/Strategies.tsx`:
```tsx
export default function Strategies() {
  return <div>Strategies loading...</div>;
}
```

- [ ] **Step 5: Install dependencies and verify build**

Run: `cd frontend && npm install && npm run build`
Expected: successful build

- [ ] **Step 6: Commit**

```bash
git add frontend/
git commit -m "feat: React dashboard scaffolding with Vite, Tailwind, and routing"
```

---

### Task 7: Dashboard Page with Real-Time Data

**Files:**
- Create: `frontend/src/hooks/useWebSocket.ts`
- Create: `frontend/src/hooks/useApi.ts`
- Modify: `frontend/src/pages/Dashboard.tsx`

- [ ] **Step 1: Create WebSocket hook**

`frontend/src/hooks/useWebSocket.ts`:
```tsx
import { useEffect, useRef, useState, useCallback } from "react";

interface PortfolioSnapshot {
  nav: string;
  daily_pnl: string;
  drawdown_pct: string;
  positions: number;
  mode: string;
  bot_running: boolean;
  pdt_day_trades_used: number;
}

export function useWebSocket() {
  const [data, setData] = useState<PortfolioSnapshot | null>(null);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  const connect = useCallback(() => {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const ws = new WebSocket(`${protocol}//${window.location.host}/api/ws`);

    ws.onopen = () => setConnected(true);
    ws.onclose = () => {
      setConnected(false);
      setTimeout(connect, 3000);
    };
    ws.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data);
        setData(parsed);
      } catch {
        // ignore malformed messages
      }
    };

    wsRef.current = ws;
  }, []);

  useEffect(() => {
    connect();
    return () => wsRef.current?.close();
  }, [connect]);

  return { data, connected };
}
```

- [ ] **Step 2: Create API fetch hook**

`frontend/src/hooks/useApi.ts`:
```tsx
import { useEffect, useState } from "react";

export function useApi<T>(url: string, interval?: number) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;

    async function fetchData() {
      try {
        const response = await fetch(url);
        if (!response.ok) throw new Error(`${response.status}`);
        const json = await response.json();
        if (mounted) {
          setData(json);
          setLoading(false);
        }
      } catch (e) {
        if (mounted) {
          setError(e instanceof Error ? e.message : "Unknown error");
          setLoading(false);
        }
      }
    }

    fetchData();

    if (interval) {
      const id = setInterval(fetchData, interval);
      return () => {
        mounted = false;
        clearInterval(id);
      };
    }

    return () => {
      mounted = false;
    };
  }, [url, interval]);

  return { data, loading, error };
}
```

- [ ] **Step 3: Build Dashboard page**

`frontend/src/pages/Dashboard.tsx`:
```tsx
import { useWebSocket } from "../hooks/useWebSocket";
import { useApi } from "../hooks/useApi";

interface Position {
  broker_order_id: string;
  strategy: string;
  symbol: string;
  spread_type: string;
  fill_price: string;
  timestamp: string;
}

interface PortfolioData {
  nav: string;
  daily_pnl: string;
  drawdown_pct: string;
  open_positions: Position[];
  pdt_day_trades_used: number;
  mode: string;
}

function StatCard({
  label,
  value,
  color = "text-white",
}: {
  label: string;
  value: string;
  color?: string;
}) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
      <div className="text-sm text-gray-400">{label}</div>
      <div className={`text-2xl font-bold mt-1 ${color}`}>{value}</div>
    </div>
  );
}

export default function Dashboard() {
  const { data: wsData, connected } = useWebSocket();
  const { data: portfolio, loading } = useApi<PortfolioData>(
    "/api/portfolio",
    10000
  );

  // Use WebSocket data if available, fall back to REST
  const nav = wsData?.nav ?? portfolio?.nav ?? "—";
  const dailyPnl = wsData?.daily_pnl ?? portfolio?.daily_pnl ?? "0";
  const drawdown = wsData?.drawdown_pct ?? portfolio?.drawdown_pct ?? "0";
  const pdtUsed =
    wsData?.pdt_day_trades_used ?? portfolio?.pdt_day_trades_used ?? 0;
  const mode = wsData?.mode ?? portfolio?.mode ?? "—";
  const positions = portfolio?.open_positions ?? [];

  const pnlNum = parseFloat(dailyPnl);
  const pnlColor =
    pnlNum > 0 ? "text-green-400" : pnlNum < 0 ? "text-red-400" : "text-white";
  const pnlDisplay = pnlNum >= 0 ? `+$${dailyPnl}` : `-$${Math.abs(pnlNum)}`;

  if (loading && !wsData) {
    return <div className="text-gray-400">Loading dashboard...</div>;
  }

  return (
    <div className="space-y-6">
      {/* Status bar */}
      <div className="flex items-center gap-4">
        <span
          className={`px-2 py-1 rounded text-xs font-bold ${
            mode === "paper"
              ? "bg-yellow-900 text-yellow-300"
              : "bg-red-900 text-red-300"
          }`}
        >
          {mode?.toUpperCase()} MODE
        </span>
        <span
          className={`flex items-center gap-1 text-xs ${
            connected ? "text-green-400" : "text-red-400"
          }`}
        >
          <span
            className={`w-2 h-2 rounded-full ${
              connected ? "bg-green-400" : "bg-red-400"
            }`}
          />
          {connected ? "Live" : "Disconnected"}
        </span>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label="NAV" value={`$${nav}`} />
        <StatCard label="Daily P&L" value={pnlDisplay} color={pnlColor} />
        <StatCard
          label="Drawdown"
          value={`${parseFloat(drawdown).toFixed(2)}%`}
          color={parseFloat(drawdown) > 5 ? "text-red-400" : "text-white"}
        />
        <StatCard label="PDT Used" value={`${pdtUsed}/3`} />
      </div>

      {/* Open Positions */}
      <div>
        <h2 className="text-lg font-semibold mb-3">Open Positions</h2>
        {positions.length === 0 ? (
          <div className="text-gray-500 bg-gray-900 border border-gray-800 rounded-lg p-8 text-center">
            No open positions
          </div>
        ) : (
          <div className="bg-gray-900 border border-gray-800 rounded-lg overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-800">
                <tr>
                  <th className="px-4 py-2 text-left text-gray-400">Symbol</th>
                  <th className="px-4 py-2 text-left text-gray-400">Strategy</th>
                  <th className="px-4 py-2 text-left text-gray-400">Type</th>
                  <th className="px-4 py-2 text-right text-gray-400">
                    Fill Price
                  </th>
                  <th className="px-4 py-2 text-right text-gray-400">Time</th>
                </tr>
              </thead>
              <tbody>
                {positions.map((p) => (
                  <tr key={p.broker_order_id} className="border-t border-gray-800">
                    <td className="px-4 py-2 font-mono">{p.symbol}</td>
                    <td className="px-4 py-2">{p.strategy}</td>
                    <td className="px-4 py-2">{p.spread_type}</td>
                    <td className="px-4 py-2 text-right">${p.fill_price}</td>
                    <td className="px-4 py-2 text-right text-gray-400">
                      {new Date(p.timestamp).toLocaleTimeString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Verify build**

Run: `cd frontend && npm run build`
Expected: successful build

- [ ] **Step 5: Commit**

```bash
git add frontend/
git commit -m "feat: dashboard page with real-time WebSocket updates"
```

---

### Task 8: Trades and Strategies Pages

**Files:**
- Modify: `frontend/src/pages/Trades.tsx`
- Modify: `frontend/src/pages/Strategies.tsx`

- [ ] **Step 1: Build Trades page**

`frontend/src/pages/Trades.tsx`:
```tsx
import { useApi } from "../hooks/useApi";

interface Trade {
  id: number;
  strategy: string;
  symbol: string;
  spread_type: string;
  entry_price: string;
  exit_price: string | null;
  pnl: string | null;
  status: string;
  entry_time: string | null;
  exit_time: string | null;
}

export default function Trades() {
  const { data: trades, loading } = useApi<Trade[]>("/api/trades", 15000);

  if (loading) return <div className="text-gray-400">Loading trades...</div>;

  return (
    <div>
      <h2 className="text-lg font-semibold mb-3">Trade History</h2>
      {!trades || trades.length === 0 ? (
        <div className="text-gray-500 bg-gray-900 border border-gray-800 rounded-lg p-8 text-center">
          No trades yet
        </div>
      ) : (
        <div className="bg-gray-900 border border-gray-800 rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-800">
              <tr>
                <th className="px-4 py-2 text-left text-gray-400">ID</th>
                <th className="px-4 py-2 text-left text-gray-400">Symbol</th>
                <th className="px-4 py-2 text-left text-gray-400">Strategy</th>
                <th className="px-4 py-2 text-left text-gray-400">Type</th>
                <th className="px-4 py-2 text-right text-gray-400">Entry</th>
                <th className="px-4 py-2 text-right text-gray-400">Exit</th>
                <th className="px-4 py-2 text-right text-gray-400">P&L</th>
                <th className="px-4 py-2 text-left text-gray-400">Status</th>
                <th className="px-4 py-2 text-right text-gray-400">Time</th>
              </tr>
            </thead>
            <tbody>
              {trades.map((t) => {
                const pnl = t.pnl ? parseFloat(t.pnl) : null;
                return (
                  <tr key={t.id} className="border-t border-gray-800">
                    <td className="px-4 py-2 text-gray-500">#{t.id}</td>
                    <td className="px-4 py-2 font-mono">{t.symbol}</td>
                    <td className="px-4 py-2">{t.strategy}</td>
                    <td className="px-4 py-2">{t.spread_type}</td>
                    <td className="px-4 py-2 text-right">${t.entry_price}</td>
                    <td className="px-4 py-2 text-right">
                      {t.exit_price ? `$${t.exit_price}` : "—"}
                    </td>
                    <td
                      className={`px-4 py-2 text-right ${
                        pnl !== null && pnl > 0
                          ? "text-green-400"
                          : pnl !== null && pnl < 0
                            ? "text-red-400"
                            : ""
                      }`}
                    >
                      {pnl !== null ? `$${t.pnl}` : "—"}
                    </td>
                    <td className="px-4 py-2">
                      <span
                        className={`px-2 py-0.5 rounded text-xs ${
                          t.status === "open"
                            ? "bg-blue-900 text-blue-300"
                            : t.status === "closed"
                              ? "bg-gray-700 text-gray-300"
                              : "bg-yellow-900 text-yellow-300"
                        }`}
                      >
                        {t.status}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-right text-gray-400 text-xs">
                      {t.entry_time
                        ? new Date(t.entry_time).toLocaleString()
                        : "—"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Build Strategies page**

`frontend/src/pages/Strategies.tsx`:
```tsx
import { useApi } from "../hooks/useApi";

interface Strategy {
  name: string;
  symbol: string;
  type: string;
  has_position: boolean;
}

export default function Strategies() {
  const { data: strategies, loading } = useApi<Strategy[]>(
    "/api/strategies",
    10000
  );

  if (loading)
    return <div className="text-gray-400">Loading strategies...</div>;

  return (
    <div>
      <h2 className="text-lg font-semibold mb-3">Loaded Strategies</h2>
      {!strategies || strategies.length === 0 ? (
        <div className="text-gray-500 bg-gray-900 border border-gray-800 rounded-lg p-8 text-center">
          No strategies loaded
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {strategies.map((s) => (
            <div
              key={s.name}
              className="bg-gray-900 border border-gray-800 rounded-lg p-4"
            >
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-semibold">{s.name}</h3>
                <span
                  className={`px-2 py-0.5 rounded text-xs ${
                    s.has_position
                      ? "bg-blue-900 text-blue-300"
                      : "bg-gray-700 text-gray-300"
                  }`}
                >
                  {s.has_position ? "In Position" : "Watching"}
                </span>
              </div>
              <div className="text-sm text-gray-400 space-y-1">
                <div>
                  Symbol: <span className="text-gray-200 font-mono">{s.symbol}</span>
                </div>
                <div>
                  Type: <span className="text-gray-200">{s.type}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Verify build**

Run: `cd frontend && npm run build`
Expected: successful build

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/
git commit -m "feat: trades history and strategies pages"
```

---

## Chunk 3: Docker

### Task 9: Dockerfile and Docker Compose

**Files:**
- Create: `Dockerfile`
- Create: `frontend/Dockerfile`
- Create: `frontend/nginx.conf`
- Create: `docker-compose.yml`
- Create: `.dockerignore`

- [ ] **Step 1: Create backend Dockerfile**

`Dockerfile`:
```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy project files
COPY pyproject.toml ./
COPY src/ src/
COPY config/ config/

# Install dependencies
RUN uv pip install --system .

# Create data directory for SQLite
RUN mkdir -p /app/data

ENV TRADEBOT_DATABASE_URL=sqlite:////app/data/tradebot.db

EXPOSE 8000

CMD ["python", "-m", "tradebot.main"]
```

- [ ] **Step 2: Create frontend Dockerfile with nginx**

`frontend/Dockerfile`:
```dockerfile
# Build stage
FROM node:20-slim AS build

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
```

`frontend/nginx.conf`:
```nginx
server {
    listen 80;
    server_name _;

    root /usr/share/nginx/html;
    index index.html;

    # SPA routing — serve index.html for all non-file routes
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Proxy API requests to backend
    location /api/ {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

- [ ] **Step 3: Create Docker Compose**

`docker-compose.yml`:
```yaml
services:
  backend:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - tradebot-data:/app/data
      - ./config:/app/config:ro
    env_file:
      - .env.paper
    environment:
      - TRADEBOT_MODE=paper
      - TRADEBOT_DATABASE_URL=sqlite:////app/data/tradebot.db
    restart: unless-stopped

  frontend:
    build: ./frontend
    ports:
      - "3000:80"
    depends_on:
      - backend
    restart: unless-stopped

volumes:
  tradebot-data:
```

- [ ] **Step 4: Create .dockerignore**

`.dockerignore`:
```
.git
.venv
__pycache__
*.pyc
*.db
.env
.env.*
.pytest_cache
.ruff_cache
node_modules
frontend/node_modules
frontend/dist
docs/
tests/
*.md
```

- [ ] **Step 5: Verify Docker build**

Run: `docker compose build`
Expected: both images build successfully

- [ ] **Step 6: Commit**

```bash
git add Dockerfile frontend/Dockerfile frontend/nginx.conf docker-compose.yml .dockerignore
git commit -m "feat: Docker containerization with compose for backend and frontend"
```

---

## Future Tasks (not in this plan)

- Credit Spread and Debit Spread strategies
- Alembic migrations for schema versioning
- Simulated broker for offline backtesting
- Historical data feed
- Portfolio analytics (Sharpe ratio, win rate charts)
- Kill switch API endpoint
- NAV history chart with Recharts
