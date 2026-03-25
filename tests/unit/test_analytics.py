"""Tests for portfolio analytics metrics."""
from decimal import Decimal

import pytest

from tradebot.analytics.metrics import compute_trade_metrics, compute_sharpe_ratio


class TestComputeTradeMetrics:
    def test_empty_trades(self):
        result = compute_trade_metrics([])
        assert result["total_trades"] == 0
        assert result["win_rate"] == Decimal("0")
        assert result["streak_type"] == "none"

    def test_all_wins(self):
        trades = [
            {"pnl": Decimal("1.00")},
            {"pnl": Decimal("2.00")},
            {"pnl": Decimal("0.50")},
        ]
        result = compute_trade_metrics(trades)
        assert result["total_trades"] == 3
        assert result["winning_trades"] == 3
        assert result["losing_trades"] == 0
        assert result["win_rate"] == Decimal("100.0")
        assert result["profit_factor"] == Decimal("Infinity")
        assert result["total_pnl"] == Decimal("3.50")
        assert result["streak_type"] == "win"
        assert result["current_streak"] == 3

    def test_all_losses(self):
        trades = [
            {"pnl": Decimal("-1.00")},
            {"pnl": Decimal("-0.50")},
        ]
        result = compute_trade_metrics(trades)
        assert result["winning_trades"] == 0
        assert result["losing_trades"] == 2
        assert result["win_rate"] == Decimal("0.0")
        assert result["profit_factor"] == Decimal("0")
        assert result["streak_type"] == "loss"
        assert result["current_streak"] == 2

    def test_mixed_trades(self):
        trades = [
            {"pnl": Decimal("2.00")},
            {"pnl": Decimal("-1.00")},
            {"pnl": Decimal("3.00")},
            {"pnl": Decimal("-0.50")},
            {"pnl": Decimal("1.00")},
        ]
        result = compute_trade_metrics(trades)
        assert result["total_trades"] == 5
        assert result["winning_trades"] == 3
        assert result["losing_trades"] == 2
        assert result["win_rate"] == Decimal("60.0")
        assert result["largest_win"] == Decimal("3.00")
        assert result["largest_loss"] == Decimal("-1.00")
        assert result["total_pnl"] == Decimal("4.50")
        assert result["avg_trade_pnl"] == Decimal("0.90")
        # Profit factor: gross_profit=6.00, gross_loss=1.50 -> 4.0
        assert result["profit_factor"] == Decimal("4.0")
        # Last trade is a win, streak=1
        assert result["streak_type"] == "win"
        assert result["current_streak"] == 1

    def test_streak_multiple_wins_at_end(self):
        trades = [
            {"pnl": Decimal("-1.00")},
            {"pnl": Decimal("1.00")},
            {"pnl": Decimal("2.00")},
            {"pnl": Decimal("0.50")},
        ]
        result = compute_trade_metrics(trades)
        assert result["streak_type"] == "win"
        assert result["current_streak"] == 3

    def test_streak_multiple_losses_at_end(self):
        trades = [
            {"pnl": Decimal("1.00")},
            {"pnl": Decimal("-0.50")},
            {"pnl": Decimal("-0.25")},
        ]
        result = compute_trade_metrics(trades)
        assert result["streak_type"] == "loss"
        assert result["current_streak"] == 2

    def test_breakeven_trade_counts_as_neither(self):
        trades = [
            {"pnl": Decimal("1.00")},
            {"pnl": Decimal("0.00")},
        ]
        result = compute_trade_metrics(trades)
        assert result["winning_trades"] == 1
        assert result["losing_trades"] == 0
        assert result["total_trades"] == 2


class TestComputeSharpeRatio:
    def test_too_few_data_points(self):
        assert compute_sharpe_ratio([]) == Decimal("0")
        assert compute_sharpe_ratio([Decimal("1000")]) == Decimal("0")

    def test_constant_nav_returns_zero(self):
        navs = [Decimal("1000")] * 10
        assert compute_sharpe_ratio(navs) == Decimal("0")

    def test_positive_returns(self):
        # Steady 1% daily gain: high Sharpe
        navs = [Decimal(str(1000 * 1.01**i)) for i in range(30)]
        sharpe = compute_sharpe_ratio(navs)
        assert sharpe > Decimal("0")

    def test_volatile_returns_lower_sharpe(self):
        # Alternating +2%/-1% -> positive but volatile
        navs = [Decimal("1000")]
        for i in range(29):
            factor = Decimal("1.02") if i % 2 == 0 else Decimal("0.99")
            navs.append(navs[-1] * factor)

        # Steady 0.5% daily gain
        steady_navs = [Decimal(str(1000 * 1.005**i)) for i in range(30)]

        volatile_sharpe = compute_sharpe_ratio(navs)
        steady_sharpe = compute_sharpe_ratio(steady_navs)
        # Steady returns should have higher Sharpe than volatile
        assert steady_sharpe > volatile_sharpe


class TestAnalyticsEndpoint:
    """Test the analytics API endpoint via TestClient."""

    @pytest.fixture
    def repo(self):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session
        from sqlalchemy.pool import StaticPool
        from tradebot.persistence.database import Base
        from tradebot.persistence.repository import Repository

        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(engine)
        session = Session(engine)
        return Repository(session)

    @pytest.fixture
    def client(self, repo):
        from fastapi.testclient import TestClient
        from tradebot.api.app import create_app
        from tradebot.api.state import AppState
        from tradebot.portfolio.tracker import PortfolioTracker

        state = AppState(
            portfolio=PortfolioTracker(starting_capital=Decimal("2500.00")),
            strategies=[],
            mode="paper",
            repository=repo,
        )
        app = create_app(state)
        return TestClient(app)

    def test_analytics_empty(self, client):
        response = client.get("/api/portfolio/analytics")
        assert response.status_code == 200
        data = response.json()
        assert data["total_trades"] == 0
        assert data["sharpe_ratio"] == "0"

    def test_analytics_with_trades(self, client, repo):
        from datetime import date

        # Create and close some trades
        t1 = repo.create_trade(strategy="test", symbol="XSP", spread_type="iron_condor", entry_price=Decimal("0.50"))
        repo.close_trade(t1.id, exit_price=Decimal("0.10"), pnl=Decimal("0.40"))

        t2 = repo.create_trade(strategy="test", symbol="XSP", spread_type="iron_condor", entry_price=Decimal("0.50"))
        repo.close_trade(t2.id, exit_price=Decimal("0.80"), pnl=Decimal("-0.30"))

        t3 = repo.create_trade(strategy="test", symbol="XSP", spread_type="iron_condor", entry_price=Decimal("0.50"))
        repo.close_trade(t3.id, exit_price=Decimal("0.20"), pnl=Decimal("0.30"))

        # Add daily snapshots for Sharpe calc
        repo.record_daily_snapshot(date(2026, 3, 20), Decimal("2500"), Decimal("0"), Decimal("0"), Decimal("0"), 0)
        repo.record_daily_snapshot(date(2026, 3, 21), Decimal("2540"), Decimal("40"), Decimal("0"), Decimal("0"), 0)
        repo.record_daily_snapshot(date(2026, 3, 22), Decimal("2510"), Decimal("-30"), Decimal("0"), Decimal("1.18"), 0)
        repo.record_daily_snapshot(date(2026, 3, 23), Decimal("2540"), Decimal("30"), Decimal("0"), Decimal("0"), 0)

        response = client.get("/api/portfolio/analytics")
        assert response.status_code == 200
        data = response.json()
        assert data["total_trades"] == 3
        assert data["winning_trades"] == 2
        assert data["losing_trades"] == 1
        assert data["win_rate"] == "66.7"
        assert data["total_pnl"] == "0.40"
        assert data["streak_type"] == "win"
        assert data["current_streak"] == 1
        assert float(data["sharpe_ratio"]) != 0
        assert data["max_drawdown_pct"] == "1.1800"

    def test_analytics_without_repo(self):
        from fastapi.testclient import TestClient
        from tradebot.api.app import create_app
        from tradebot.api.state import AppState
        from tradebot.portfolio.tracker import PortfolioTracker

        state = AppState(
            portfolio=PortfolioTracker(starting_capital=Decimal("2500.00")),
            strategies=[],
            mode="paper",
        )
        app = create_app(state)
        client = TestClient(app)
        response = client.get("/api/portfolio/analytics")
        assert response.status_code == 200
        assert response.json()["total_trades"] == 0
