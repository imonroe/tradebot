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
