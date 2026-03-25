# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Tradebot is an automated options trading bot focused on 0DTE (zero days to expiration) iron condor strategies on XSP. It has a Python/FastAPI backend with an event-driven architecture and a React/TypeScript frontend dashboard.

## Common Commands

### Backend
```bash
uv venv && uv pip install -e ".[dev]"   # Initial setup
uv run python -m tradebot.main          # Run the bot + API server
uv run pytest -v                        # Run all tests
uv run pytest tests/unit/ -v            # Unit tests only
uv run pytest tests/path/to/test.py -v  # Single test file
uv run pytest -k "test_name" -v         # Single test by name
uv run ruff check src/                  # Lint
```

### Frontend
```bash
cd frontend
npm install                              # Install dependencies
npm run dev                              # Vite dev server on :5173
npm run build                            # TypeScript check + production build
```

### Docker
```bash
docker compose up --build                # Run full stack (backend :8000, frontend :3000)
```

## Architecture

### Event-Driven Pipeline

The core backend follows an event-driven pipeline where each stage communicates via an async `EventBus` with type-based dispatch:

```
MarketEvent → Strategy.evaluate() → SignalEvent → RiskManager (7 checks) → OrderEvent → OrderManager → FillEvent → PortfolioTracker
```

All events are defined in `src/tradebot/core/events.py`. The bus is in `src/tradebot/core/event_bus.py`.

### Concurrency Model

`main.py` runs the bot loop and FastAPI/uvicorn server as concurrent asyncio tasks in the same process, sharing an `AppState` instance (`api/state.py`). The bot loop fetches market data every 60s, publishes events, and broadcasts WebSocket updates.

### Key Backend Modules

- **`core/`** — Domain models, enums, events, event bus
- **`data/sources/base.py`** — `DataSource` protocol (interface for market data providers)
- **`data/sources/tradier.py`** — Tradier market data fetcher (quotes + options chains)
- **`data/sources/paper.py`** — Synthetic market data with random-walk prices and approximate Greeks
- **`data/sources/recorder.py`** — Passthrough wrapper that saves data source responses to JSON files
- **`strategy/`** — Abstract base + iron condor implementation; strategies loaded from YAML configs in `config/strategies/`
- **`risk/manager.py`** — Chains risk checks that gate every signal; 8 checks available (kill switch, PDT, daily loss, drawdown, time window, position size, spread width, duplicate), 5 wired in `main.py` (kill switch, time window, daily loss, drawdown, duplicate)
- **`execution/brokers/tradier.py`** — Tradier API client implementing `Broker` protocol
- **`execution/brokers/paper.py`** — Simulated broker with instant fills and local state (no API needed)
- **`portfolio/tracker.py`** — NAV, P&L, drawdown, open position tracking
- **`persistence/`** — SQLAlchemy ORM models + repository pattern; SQLite dev / PostgreSQL prod

### Frontend

React 18 + Vite + TypeScript + Tailwind CSS (dark theme). Three pages: Dashboard (real-time via WebSocket), Trades history, Strategies overview. The `useWebSocket` hook connects to `/api/ws` with auto-reconnect. Vite proxies `/api` to `localhost:8000` in dev.

### API Endpoints

- `GET /api/health` — Status + mode
- `GET /api/portfolio` — NAV, P&L, positions, PDT count
- `GET /api/trades` — Last 100 trades
- `GET /api/strategies` — Loaded strategies
- `GET /api/kill-switch` — Kill switch status
- `POST /api/kill-switch/activate` — Halt all new trades
- `POST /api/kill-switch/deactivate` — Resume trading
- `WS /api/ws` — Real-time portfolio updates

## Configuration

- **Infrastructure**: `config/settings.toml` (mode, DB URL, capital, risk limits)
- **Broker**: `config/settings.paper.toml` (Tradier sandbox URL, credential env file)
- **Strategy**: `config/strategies/xsp_iron_condor.yaml` (entry/exit rules, position sizing, risk params)
- **Environment**: Settings use `TRADEBOT_` prefix (e.g., `TRADEBOT_MODE`, `TRADEBOT_DATABASE_URL`, `TRADEBOT_TRADIER_API_TOKEN`). Copy `.env.example` to `.env.paper`.
- **Broker selection**: `TRADEBOT_BROKER_NAME=paper` (default in `.env.paper`) uses `PaperBroker` + `PaperDataSource` with no API key required. Set to `tradier` with a valid token for real market data.

## Safety

The bot has a paper/live mode split. Live mode requires a `--confirm-live` CLI flag. Separate `.env.paper` and `.env.live` files keep credentials isolated.
