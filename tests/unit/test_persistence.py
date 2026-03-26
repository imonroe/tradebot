"""Tests for database models and repository."""
from datetime import date
from decimal import Decimal
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from tradebot.persistence.database import Base
from tradebot.persistence.repository import Repository
from tradebot.backtest.results import BacktestResult

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
    daily_snapshots = None
    trades = None


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


# --- Backtest JSON column tests ---


def test_save_backtest_run_with_json(repo):
    """save_backtest_run persists daily_snapshots and trades as JSON."""
    result = BacktestResult(
        strategy_name="test_strategy",
        start_date=date(2026, 3, 1),
        end_date=date(2026, 3, 5),
        starting_capital=Decimal("2500"),
        interval_minutes=15,
        ending_nav=Decimal("2550"),
        total_return_pct=Decimal("2.00"),
        max_drawdown_pct=Decimal("1.50"),
        total_trades=3,
        winning_trades=2,
        losing_trades=1,
        win_rate=Decimal("66.67"),
        avg_win=Decimal("40.00"),
        avg_loss=Decimal("30.00"),
        profit_factor=Decimal("2.67"),
        daily_snapshots=[{"date": "2026-03-03", "nav": "2520", "daily_pnl": "20", "drawdown": "0"}],
        trades=[{"date": "2026-03-03", "pnl": 20.0, "strategy": "test"}],
    )
    record = repo.save_backtest_run(result)
    assert record.id is not None
    assert record.daily_snapshots == result.daily_snapshots
    assert record.trades == result.trades


def test_get_backtest_run_by_id(repo):
    """get_backtest_run returns full record including JSON columns."""
    result = BacktestResult(
        strategy_name="test_strategy",
        start_date=date(2026, 3, 1),
        end_date=date(2026, 3, 5),
        starting_capital=Decimal("2500"),
        interval_minutes=15,
        ending_nav=Decimal("2550"),
        total_return_pct=Decimal("2.00"),
        max_drawdown_pct=Decimal("1.50"),
        total_trades=3,
        winning_trades=2,
        losing_trades=1,
        win_rate=Decimal("66.67"),
        avg_win=Decimal("40.00"),
        avg_loss=Decimal("30.00"),
        profit_factor=Decimal("2.67"),
        daily_snapshots=[{"date": "2026-03-03", "nav": "2520"}],
        trades=[{"pnl": 20.0}],
    )
    saved = repo.save_backtest_run(result)
    fetched = repo.get_backtest_run(saved.id)
    assert fetched is not None
    assert fetched.daily_snapshots == [{"date": "2026-03-03", "nav": "2520"}]
    assert fetched.trades == [{"pnl": 20.0}]


def test_get_backtest_run_not_found(repo):
    """get_backtest_run returns None for nonexistent ID."""
    assert repo.get_backtest_run(999) is None


def test_delete_backtest_run(repo):
    """delete_backtest_run removes the record."""
    result = BacktestResult(
        strategy_name="test_strategy",
        start_date=date(2026, 3, 1),
        end_date=date(2026, 3, 5),
        starting_capital=Decimal("2500"),
        interval_minutes=15,
        ending_nav=Decimal("2550"),
        total_return_pct=Decimal("2.00"),
        max_drawdown_pct=Decimal("1.50"),
        total_trades=3,
        winning_trades=2,
        losing_trades=1,
        win_rate=Decimal("66.67"),
        avg_win=Decimal("40.00"),
        avg_loss=Decimal("30.00"),
        profit_factor=Decimal("2.67"),
        daily_snapshots=[],
        trades=[],
    )
    saved = repo.save_backtest_run(result)
    deleted = repo.delete_backtest_run(saved.id)
    assert deleted is True
    assert repo.get_backtest_run(saved.id) is None


def test_delete_backtest_run_not_found(repo):
    """delete_backtest_run returns False for nonexistent ID."""
    assert repo.delete_backtest_run(999) is False


def test_get_backtest_runs_returns_saved_records(repo):
    """get_backtest_runs returns saved records."""
    result = BacktestResult(
        strategy_name="test_strategy",
        start_date=date(2026, 3, 1),
        end_date=date(2026, 3, 5),
        starting_capital=Decimal("2500"),
        interval_minutes=15,
        ending_nav=Decimal("2550"),
        total_return_pct=Decimal("2.00"),
        max_drawdown_pct=Decimal("1.50"),
        total_trades=3,
        winning_trades=2,
        losing_trades=1,
        win_rate=Decimal("66.67"),
        avg_win=Decimal("40.00"),
        avg_loss=Decimal("30.00"),
        profit_factor=Decimal("2.67"),
        daily_snapshots=[{"date": "2026-03-03"}],
        trades=[{"pnl": 20.0}],
    )
    repo.save_backtest_run(result)
    runs = repo.get_backtest_runs(limit=10)
    assert len(runs) == 1
    assert runs[0].strategy_name == "test_strategy"
