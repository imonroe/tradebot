"""Tests for database models and repository."""
from datetime import date
from decimal import Decimal
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from tradebot.persistence.database import Base
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
    trade = repo.create_trade(strategy="xsp_iron_condor", symbol="XSP",
        spread_type="iron_condor", entry_price=Decimal("0.50"))
    assert trade.id is not None
    assert trade.strategy == "xsp_iron_condor"
    assert trade.status == "open"

def test_add_trade_leg(repo):
    trade = repo.create_trade(strategy="xsp_credit_spread", symbol="XSP",
        spread_type="credit_spread", entry_price=Decimal("0.35"))
    leg = repo.add_trade_leg(trade_id=trade.id, option_symbol="XSP250316P00565000",
        side="sell_to_open", quantity=1, strike=Decimal("565.00"),
        option_type="put", fill_price=Decimal("0.85"))
    assert leg.trade_id == trade.id
    assert leg.strike == Decimal("565.00")

def test_log_day_trade(repo):
    repo.log_day_trade(trade_date=date(2026, 3, 16), order_id="ord_123", trade_id=1)
    count = repo.get_day_trade_count(start_date=date(2026, 3, 12), end_date=date(2026, 3, 16))
    assert count == 1

def test_day_trade_count_rolling_window(repo):
    repo.log_day_trade(trade_date=date(2026, 3, 10), order_id="ord_1", trade_id=1)
    repo.log_day_trade(trade_date=date(2026, 3, 12), order_id="ord_2", trade_id=2)
    repo.log_day_trade(trade_date=date(2026, 3, 16), order_id="ord_3", trade_id=3)
    count = repo.get_day_trade_count(start_date=date(2026, 3, 12), end_date=date(2026, 3, 16))
    assert count == 2  # excludes 3/10

def test_close_trade(repo):
    trade = repo.create_trade(strategy="test", symbol="XSP",
        spread_type="credit_spread", entry_price=Decimal("0.50"))
    repo.close_trade(trade.id, exit_price=Decimal("0.20"), pnl=Decimal("30.00"))
    updated = repo.get_trade(trade.id)
    assert updated.status == "closed"
    assert updated.pnl == Decimal("30.00")


def test_record_daily_snapshot(repo):
    repo.record_daily_snapshot(
        snapshot_date=date(2026, 3, 18),
        nav=Decimal("2550.00"),
        realized_pnl=Decimal("50.00"),
        unrealized_pnl=Decimal("0.00"),
        drawdown=Decimal("0.0"),
        day_trade_count=1,
    )
    history = repo.get_nav_history(days=30)
    assert len(history) == 1
    assert history[0]["date"] == "2026-03-18"
    assert history[0]["nav"] == "2550.00"


def test_get_nav_history_ordered_by_date(repo):
    for i, d in enumerate([date(2026, 3, 16), date(2026, 3, 18), date(2026, 3, 17)]):
        repo.record_daily_snapshot(
            snapshot_date=d,
            nav=Decimal(str(2500 + i * 25)),
            realized_pnl=Decimal("0"),
            unrealized_pnl=Decimal("0"),
            drawdown=Decimal("0"),
            day_trade_count=0,
        )
    history = repo.get_nav_history(days=30)
    dates = [h["date"] for h in history]
    assert dates == ["2026-03-16", "2026-03-17", "2026-03-18"]


def test_get_nav_history_respects_days_limit(repo):
    repo.record_daily_snapshot(
        snapshot_date=date(2025, 1, 1),
        nav=Decimal("2500"),
        realized_pnl=Decimal("0"),
        unrealized_pnl=Decimal("0"),
        drawdown=Decimal("0"),
        day_trade_count=0,
    )
    repo.record_daily_snapshot(
        snapshot_date=date(2026, 3, 18),
        nav=Decimal("2600"),
        realized_pnl=Decimal("0"),
        unrealized_pnl=Decimal("0"),
        drawdown=Decimal("0"),
        day_trade_count=0,
    )
    history = repo.get_nav_history(days=30)
    assert len(history) == 1
    assert history[0]["date"] == "2026-03-18"


class _FakeResult:
    """Minimal object matching BacktestResult fields for save_backtest_run."""
    strategy_name = "test_ic"
    start_date = date(2026, 1, 2)
    end_date = date(2026, 3, 1)
    starting_capital = Decimal("2500")
    interval_minutes = 15
    ending_nav = Decimal("2715")
    total_return_pct = Decimal("8.60")
    max_drawdown_pct = Decimal("3.20")
    total_trades = 38
    win_rate = Decimal("68.4")
    profit_factor = Decimal("2.31")


def test_save_backtest_run(repo):
    record = repo.save_backtest_run(_FakeResult())
    assert record.id is not None
    assert record.strategy_name == "test_ic"
    assert record.total_trades == 38


def test_get_backtest_runs(repo):
    repo.save_backtest_run(_FakeResult())
    runs = repo.get_backtest_runs()
    assert len(runs) == 1
    assert runs[0].strategy_name == "test_ic"
