# Tradebot

An event-driven Python trading bot for 0DTE options strategies on cash-settled index options (XSP/SPX), with a React dashboard for monitoring.

Built for paper trading first, designed to graduate to live trading with only a config change.

## Features

- **Event-driven architecture** — asyncio-based pipeline: Market Data → Strategy → Risk Manager → Order Manager → Broker
- **0DTE Iron Condor strategy** — delta-based strike selection, credit filtering, time-window entry rules
- **PDT-aware risk management** — tracks day trades in a rolling 5-business-day window; expirations don't count as day trades
- **7 risk checks** — PDT limit, daily loss cap, max drawdown, position size, spread width, time window, duplicate prevention
- **Tradier integration** — full API client for options chains, multi-leg orders, and account management (sandbox and production)
- **Real-time dashboard** — React SPA with WebSocket updates for NAV, P&L, drawdown, and open positions
- **Docker support** — containerized backend + frontend via Docker Compose

## Architecture

```
Market Data → Strategy Engine → Risk Manager → Order Manager → Tradier API
                                                                    ↓
  Dashboard ← Portfolio Tracker ← ← ← ← ← ← ← ← ← ←  Fill Events
```

The bot loop and FastAPI server run as concurrent asyncio tasks in the same process, sharing state through a common `AppState` object.

## Quick Start

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- Node.js 20+ (for the dashboard)
- A [Tradier](https://tradier.com) sandbox account (free, no funding required)

### Setup

```bash
# Clone and install
git clone <repo-url> && cd tradebot
uv venv && uv pip install -e ".[dev]"

# Configure your Tradier sandbox token
cp .env.example .env.paper
# Edit .env.paper with your token:
# TRADIER_API_TOKEN=your_sandbox_token_here

# Install frontend dependencies
cd frontend && npm install && cd ..
```

### Run locally

```bash
# Terminal 1: Start the backend (API + bot loop)
uv run python -m tradebot.main

# Terminal 2: Start the dashboard dev server
cd frontend && npm run dev
```

- Dashboard: http://localhost:5173
- API: http://localhost:8000
- API docs: http://localhost:8000/docs

### Run with Docker

```bash
docker compose up --build
```

- Dashboard: http://localhost:3000
- API: http://localhost:8000

## Project Structure

```
tradebot/
├── src/tradebot/
│   ├── main.py              # Entry point — runs API + bot loop
│   ├── core/                # Events, models, enums, event bus
│   ├── data/                # Market data handler + Tradier data source
│   ├── strategy/            # Strategy base class, iron condor, registry
│   ├── risk/                # Risk manager + 7 check implementations
│   ├── execution/           # Order manager + broker abstraction (Tradier)
│   ├── portfolio/           # Portfolio tracker (NAV, P&L, drawdown)
│   ├── persistence/         # SQLAlchemy ORM models + repository
│   ├── api/                 # FastAPI app, REST routes, WebSocket
│   └── utils/               # Config loading, structured logging
├── frontend/                # React + Vite + TypeScript + Tailwind
│   └── src/
│       ├── pages/           # Dashboard, Trades, Strategies
│       └── hooks/           # useWebSocket, useApi
├── config/
│   ├── settings.toml        # Infrastructure config
│   └── strategies/          # YAML strategy configs
├── tests/                   # pytest (58 tests)
├── Dockerfile               # Backend container
├── docker-compose.yml       # Full stack orchestration
└── pyproject.toml
```

## Configuration

### Infrastructure (`config/settings.toml`)

```toml
[general]
mode = "paper"       # "paper" or "live"
log_level = "INFO"

[database]
url = "sqlite:///tradebot.db"

[trading]
starting_capital = 2500.00
max_daily_loss_pct = 3.0
max_drawdown_pct = 10.0
pdt_limit = 3
```

### Strategy (`config/strategies/xsp_iron_condor.yaml`)

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
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Bot status and mode |
| GET | `/api/portfolio` | NAV, P&L, drawdown, positions |
| GET | `/api/portfolio/positions` | Open positions |
| GET | `/api/trades` | Trade history (last 100) |
| GET | `/api/strategies` | Loaded strategies and status |
| GET | `/api/kill-switch` | Kill switch status |
| POST | `/api/kill-switch/activate` | Halt all new trades |
| POST | `/api/kill-switch/deactivate` | Resume trading |
| WS | `/api/ws` | Real-time portfolio updates |

## Safety

- **Paper trading only** by default — live mode requires `--confirm-live` CLI flag
- **Credential isolation** — paper and live API keys in separate `.env` files, both gitignored
- **PDT compliance** — tracks sell-to-close orders (not expirations) against the 3-trade rolling limit
- **Circuit breakers** — daily loss cap (3%), max drawdown (10%), position size limits
- **Mode banner** — logs `>>> PAPER MODE <<<` or `>>> LIVE MODE <<<` prominently at startup

## Testing

```bash
uv run pytest -v          # 58 tests
uv run ruff check src/    # Linting
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.12+ |
| Async | asyncio |
| Broker | Tradier API via httpx |
| Web framework | FastAPI + uvicorn |
| Frontend | React 18, Vite, TypeScript, Tailwind CSS |
| Database | SQLite (dev) / PostgreSQL (prod) via SQLAlchemy 2.0 |
| Config | TOML (infrastructure) + YAML (strategies) |
| Logging | structlog (structured JSON) |
| Testing | pytest + pytest-asyncio |
| Containers | Docker + Docker Compose |

## Roadmap

- [x] Credit spread and debit spread strategies
- [x] NAV history chart (Recharts)
- [x] Alembic database migrations
- [x] Backtesting with simulated broker + historical data
- [x] CI/CD pipeline (GitHub Actions — backend tests, linting, frontend build)
- [x] Kill switch API endpoint
- [ ] Portfolio analytics (Sharpe ratio, win rate)
- [ ] Slack/Telegram trade notifications
- [ ] Additional brokers (IBKR, Alpaca)

## License

Private — not yet licensed for distribution.
