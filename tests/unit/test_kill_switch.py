"""Tests for kill switch endpoint and risk check."""
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from tradebot.api.app import create_app
from tradebot.api.state import AppState
from tradebot.core.enums import OrderSide, SpreadType
from tradebot.core.events import SignalEvent
from tradebot.core.models import OrderLeg
from tradebot.portfolio.tracker import PortfolioTracker
from tradebot.risk.checks import KillSwitchCheck


@pytest.fixture
def app_state():
    portfolio = PortfolioTracker(starting_capital=Decimal("2500.00"))
    return AppState(portfolio=portfolio, strategies=[], mode="paper")


@pytest.fixture
def client(app_state):
    app = create_app(app_state)
    return TestClient(app)


@pytest.fixture
def signal():
    return SignalEvent(
        strategy_name="test",
        symbol="XSP",
        spread_type=SpreadType.IRON_CONDOR,
        legs=[
            OrderLeg(
                option_symbol="XSP250325C00580000",
                side=OrderSide.SELL_TO_OPEN,
                quantity=1,
            )
        ],
        target_price=Decimal("0.50"),
    )


# --- API endpoint tests ---


def test_get_kill_switch_default(client):
    response = client.get("/api/kill-switch")
    assert response.status_code == 200
    data = response.json()
    assert data["active"] is False
    assert data["reason"] is None


def test_activate_kill_switch(client):
    response = client.post(
        "/api/kill-switch/activate",
        json={"reason": "emergency"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["active"] is True
    assert data["reason"] == "emergency"


def test_activate_without_reason(client):
    response = client.post("/api/kill-switch/activate")
    assert response.status_code == 200
    data = response.json()
    assert data["active"] is True
    assert data["reason"] is None


def test_deactivate_kill_switch(client):
    client.post("/api/kill-switch/activate", json={"reason": "test"})
    response = client.post("/api/kill-switch/deactivate")
    assert response.status_code == 200
    data = response.json()
    assert data["active"] is False
    assert data["reason"] is None


def test_kill_switch_roundtrip(client):
    # Start inactive
    assert client.get("/api/kill-switch").json()["active"] is False

    # Activate
    client.post("/api/kill-switch/activate", json={"reason": "halt"})
    assert client.get("/api/kill-switch").json()["active"] is True

    # Deactivate
    client.post("/api/kill-switch/deactivate")
    assert client.get("/api/kill-switch").json()["active"] is False


def test_health_includes_kill_switch(client):
    response = client.get("/api/health")
    data = response.json()
    assert "kill_switch_active" in data
    assert data["kill_switch_active"] is False


def test_websocket_includes_kill_switch(client):
    with client.websocket_connect("/api/ws") as ws:
        data = ws.receive_json()
        assert "kill_switch_active" in data
        assert data["kill_switch_active"] is False


# --- Risk check tests ---


def test_kill_switch_check_passes_when_inactive(app_state, signal):
    check = KillSwitchCheck(state=app_state)
    result = check.check(signal)
    assert result.passed is True
    assert result.check_name == "KillSwitchCheck"


def test_kill_switch_check_fails_when_active(app_state, signal):
    app_state.kill_switch_active = True
    app_state.kill_switch_reason = "testing"
    check = KillSwitchCheck(state=app_state)
    result = check.check(signal)
    assert result.passed is False
    assert "testing" in result.message


def test_kill_switch_check_default_reason(app_state, signal):
    app_state.kill_switch_active = True
    check = KillSwitchCheck(state=app_state)
    result = check.check(signal)
    assert result.passed is False
    assert "no reason given" in result.message
