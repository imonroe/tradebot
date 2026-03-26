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


# --- Task 2: Portfolio routes ---

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


# --- Task 3: Trades and Strategies routes ---

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from tradebot.persistence.database import Base
from tradebot.persistence.repository import Repository


@pytest.fixture
def repo():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
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


# --- NAV History ---

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


# --- Backtest routes ---

def test_backtest_strategies_endpoint(client):
    """GET /api/backtest/strategies returns available strategy configs."""
    response = client.get("/api/backtest/strategies")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    strat = data[0]
    assert "name" in strat
    assert "filename" in strat
    assert "config" in strat
    assert "entry" in strat["config"]


def test_backtest_run_endpoint(client_with_repo):
    """POST /api/backtest/run executes a backtest and returns results."""
    response = client_with_repo.post("/api/backtest/run", json={
        "strategy": "xsp_iron_condor",
        "start_date": "2026-03-02",
        "end_date": "2026-03-03",
        "starting_capital": 2500,
        "slippage_pct": 0,
        "interval_minutes": 15,
        "save": False,
    })
    assert response.status_code == 200
    data = response.json()
    assert "strategy_name" in data
    assert "total_return_pct" in data
    assert "daily_snapshots" in data
    assert "trades" in data


def test_backtest_run_date_range_too_large(client_with_repo):
    """POST /api/backtest/run rejects date ranges over 30 days."""
    response = client_with_repo.post("/api/backtest/run", json={
        "strategy": "xsp_iron_condor",
        "start_date": "2026-01-01",
        "end_date": "2026-03-15",
        "starting_capital": 2500,
    })
    assert response.status_code == 422


def test_backtest_run_invalid_dates(client_with_repo):
    """POST /api/backtest/run rejects start >= end."""
    response = client_with_repo.post("/api/backtest/run", json={
        "strategy": "xsp_iron_condor",
        "start_date": "2026-03-10",
        "end_date": "2026-03-05",
        "starting_capital": 2500,
    })
    assert response.status_code == 422


def test_backtest_run_invalid_strategy(client_with_repo):
    """POST /api/backtest/run rejects nonexistent strategy."""
    response = client_with_repo.post("/api/backtest/run", json={
        "strategy": "nonexistent_strategy",
        "start_date": "2026-03-02",
        "end_date": "2026-03-03",
        "starting_capital": 2500,
    })
    assert response.status_code == 422


def test_backtest_run_with_save(client_with_repo):
    """POST /api/backtest/run with save=true persists the run."""
    response = client_with_repo.post("/api/backtest/run", json={
        "strategy": "xsp_iron_condor",
        "start_date": "2026-03-02",
        "end_date": "2026-03-03",
        "starting_capital": 2500,
        "save": True,
    })
    assert response.status_code == 200
    # Verify it was saved
    runs_response = client_with_repo.get("/api/backtest/runs")
    assert runs_response.status_code == 200
    assert len(runs_response.json()) == 1


def test_backtest_run_with_overrides(client_with_repo):
    """POST /api/backtest/run applies strategy overrides."""
    response = client_with_repo.post("/api/backtest/run", json={
        "strategy": "xsp_iron_condor",
        "start_date": "2026-03-02",
        "end_date": "2026-03-03",
        "starting_capital": 2500,
        "overrides": {
            "entry.strike_selection.short_call_delta": 0.10,
        },
    })
    assert response.status_code == 200


def test_backtest_run_invalid_override_key(client_with_repo):
    """POST /api/backtest/run rejects unknown override keys."""
    response = client_with_repo.post("/api/backtest/run", json={
        "strategy": "xsp_iron_condor",
        "start_date": "2026-03-02",
        "end_date": "2026-03-03",
        "starting_capital": 2500,
        "overrides": {
            "nonexistent.path.key": 42,
        },
    })
    assert response.status_code == 422


# --- Task 4: WebSocket ---

def test_websocket_connection(client):
    with client.websocket_connect("/api/ws") as ws:
        # Server should send initial state on connect
        data = ws.receive_json()
        assert "nav" in data
        assert "mode" in data
