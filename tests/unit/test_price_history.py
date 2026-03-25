"""Tests for price bar persistence, aggregation, and API endpoint."""
from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from tradebot.api.routes.price_history import aggregate_bars
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


# --- Repository tests ---


class TestSavePriceBar:
    def test_save_and_retrieve(self, repo):
        ts = datetime(2026, 3, 25, 10, 0, 0)
        repo.save_price_bar(
            symbol="XSP", timestamp=ts,
            open_=Decimal("580.00"), high=Decimal("581.00"),
            low=Decimal("579.00"), close=Decimal("580.50"),
            volume=1000,
        )
        bars = repo.get_price_bars(
            symbol="XSP",
            start=datetime(2026, 3, 25, 0, 0),
            end=datetime(2026, 3, 25, 23, 59),
        )
        assert len(bars) == 1
        assert bars[0].symbol == "XSP"
        assert bars[0].close == Decimal("580.50")

    def test_duplicate_ignored(self, repo):
        ts = datetime(2026, 3, 25, 10, 0, 0)
        repo.save_price_bar(
            symbol="XSP", timestamp=ts,
            open_=Decimal("580.00"), high=Decimal("581.00"),
            low=Decimal("579.00"), close=Decimal("580.50"),
            volume=1000,
        )
        repo.commit()  # Commit first bar so rollback on duplicate doesn't lose it
        # Same symbol + timestamp should be silently ignored
        repo.save_price_bar(
            symbol="XSP", timestamp=ts,
            open_=Decimal("999.00"), high=Decimal("999.00"),
            low=Decimal("999.00"), close=Decimal("999.00"),
            volume=9999,
        )
        bars = repo.get_price_bars(
            symbol="XSP",
            start=datetime(2026, 3, 25, 0, 0),
            end=datetime(2026, 3, 25, 23, 59),
        )
        assert len(bars) == 1
        assert bars[0].close == Decimal("580.50")  # original value kept

    def test_range_filter(self, repo):
        for minute in range(5):
            repo.save_price_bar(
                symbol="XSP",
                timestamp=datetime(2026, 3, 25, 10, minute, 0),
                open_=Decimal("580"), high=Decimal("581"),
                low=Decimal("579"), close=Decimal("580"),
                volume=100,
            )
        bars = repo.get_price_bars(
            symbol="XSP",
            start=datetime(2026, 3, 25, 10, 1),
            end=datetime(2026, 3, 25, 10, 3),
        )
        assert len(bars) == 3  # minutes 1, 2, 3

    def test_symbol_filter(self, repo):
        ts = datetime(2026, 3, 25, 10, 0, 0)
        repo.save_price_bar("XSP", ts, Decimal("580"), Decimal("581"), Decimal("579"), Decimal("580"), 100)
        repo.save_price_bar("SPY", ts, Decimal("500"), Decimal("501"), Decimal("499"), Decimal("500"), 200)
        bars = repo.get_price_bars("XSP", datetime(2026, 3, 25, 0, 0), datetime(2026, 3, 25, 23, 59))
        assert len(bars) == 1
        assert bars[0].symbol == "XSP"


# --- Aggregation tests ---


def _make_bar(ts, open_, high, low, close, volume=100):
    """Create a mock bar object for aggregation testing."""
    bar = type("Bar", (), {})()
    bar.timestamp = ts
    bar.open = Decimal(str(open_))
    bar.high = Decimal(str(high))
    bar.low = Decimal(str(low))
    bar.close = Decimal(str(close))
    bar.volume = volume
    return bar


class TestAggregation:
    def test_1m_no_aggregation(self):
        bars = [
            _make_bar(datetime(2026, 3, 25, 10, 0), 580, 581, 579, 580.5),
            _make_bar(datetime(2026, 3, 25, 10, 1), 580.5, 582, 580, 581),
        ]
        result = aggregate_bars(bars, 1)
        assert len(result) == 2
        assert result[0]["open"] == "580"
        assert result[1]["close"] == "581"

    def test_5m_aggregation(self):
        bars = [
            _make_bar(datetime(2026, 3, 25, 10, 0), 580, 581, 579, 580.5, 100),
            _make_bar(datetime(2026, 3, 25, 10, 1), 580.5, 583, 580, 582, 200),
            _make_bar(datetime(2026, 3, 25, 10, 2), 582, 582, 578, 579, 150),
            _make_bar(datetime(2026, 3, 25, 10, 3), 579, 580, 577, 578, 100),
            _make_bar(datetime(2026, 3, 25, 10, 4), 578, 579, 577, 579, 50),
        ]
        result = aggregate_bars(bars, 5)
        assert len(result) == 1
        candle = result[0]
        assert candle["open"] == "580"  # first bar's open
        assert candle["high"] == "583"  # max high
        assert candle["low"] == "577"   # min low
        assert candle["close"] == "579" # last bar's close
        assert candle["volume"] == 600  # sum

    def test_5m_multiple_buckets(self):
        bars = [
            _make_bar(datetime(2026, 3, 25, 10, 0), 580, 581, 579, 580),
            _make_bar(datetime(2026, 3, 25, 10, 3), 580, 581, 579, 581),
            _make_bar(datetime(2026, 3, 25, 10, 5), 581, 582, 580, 582),
            _make_bar(datetime(2026, 3, 25, 10, 8), 582, 583, 581, 583),
        ]
        result = aggregate_bars(bars, 5)
        assert len(result) == 2  # 10:00-10:04 and 10:05-10:09

    def test_15m_aggregation(self):
        bars = [
            _make_bar(datetime(2026, 3, 25, 10, i), 580 + i * 0.1, 581, 579, 580)
            for i in range(15)
        ]
        result = aggregate_bars(bars, 15)
        assert len(result) == 1

    def test_1h_aggregation(self):
        bars = [
            _make_bar(datetime(2026, 3, 25, 10, i), 580, 581, 579, 580)
            for i in range(60)
        ]
        result = aggregate_bars(bars, 60)
        assert len(result) == 1

    def test_empty_bars(self):
        assert aggregate_bars([], 5) == []


# --- API endpoint tests ---


class TestPriceHistoryEndpoint:
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

    def test_empty_response(self, client):
        response = client.get("/api/price-history")
        assert response.status_code == 200
        assert response.json() == []

    def test_with_data(self, client, repo):
        from datetime import timedelta
        base = datetime.now().replace(second=0, microsecond=0) - timedelta(minutes=15)
        for i in range(10):
            repo.save_price_bar(
                symbol="XSP",
                timestamp=base + timedelta(minutes=i),
                open_=Decimal("580"), high=Decimal("581"),
                low=Decimal("579"), close=Decimal("580"),
                volume=100,
            )
        response = client.get("/api/price-history?symbol=XSP&interval=5m&hours=1")
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert "open" in data[0]
        assert "high" in data[0]
        assert "timestamp" in data[0]

    def test_invalid_interval_rejected(self, client):
        response = client.get("/api/price-history?interval=3m")
        assert response.status_code == 422

    def test_without_repo(self):
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
        response = client.get("/api/price-history")
        assert response.status_code == 200
        assert response.json() == []
