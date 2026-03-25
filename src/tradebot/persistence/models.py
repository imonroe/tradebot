"""SQLAlchemy ORM models for trade persistence."""
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import Date, DateTime, Integer, Numeric, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from tradebot.persistence.database import Base

class TradeRecord(Base):
    __tablename__ = "trades"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    strategy: Mapped[str] = mapped_column(String(100))
    symbol: Mapped[str] = mapped_column(String(20))
    spread_type: Mapped[str] = mapped_column(String(50))
    entry_price: Mapped[Decimal] = mapped_column(Numeric(10, 4))
    exit_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    pnl: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="open")
    entry_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    exit_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    legs: Mapped[list["TradeLegRecord"]] = relationship(back_populates="trade")

class TradeLegRecord(Base):
    __tablename__ = "trade_legs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trade_id: Mapped[int] = mapped_column(ForeignKey("trades.id"))
    option_symbol: Mapped[str] = mapped_column(String(50))
    side: Mapped[str] = mapped_column(String(20))
    quantity: Mapped[int] = mapped_column(Integer)
    strike: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    option_type: Mapped[str] = mapped_column(String(10))
    fill_price: Mapped[Decimal] = mapped_column(Numeric(10, 4))
    trade: Mapped["TradeRecord"] = relationship(back_populates="legs")

class DayTradeLogRecord(Base):
    __tablename__ = "day_trade_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trade_date: Mapped[date] = mapped_column(Date)
    order_id: Mapped[str] = mapped_column(String(50))
    trade_id: Mapped[int] = mapped_column(Integer)

class DailySnapshotRecord(Base):
    __tablename__ = "daily_snapshots"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    snapshot_date: Mapped[date] = mapped_column(Date, unique=True)
    nav: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    realized_pnl: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    unrealized_pnl: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    drawdown: Mapped[Decimal] = mapped_column(Numeric(6, 4))
    day_trade_count: Mapped[int] = mapped_column(Integer)


class PriceBarRecord(Base):
    __tablename__ = "price_bars"
    __table_args__ = (UniqueConstraint("symbol", "timestamp", name="uq_price_bar_symbol_ts"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(20))
    timestamp: Mapped[datetime] = mapped_column(DateTime)
    open: Mapped[Decimal] = mapped_column(Numeric(10, 4))
    high: Mapped[Decimal] = mapped_column(Numeric(10, 4))
    low: Mapped[Decimal] = mapped_column(Numeric(10, 4))
    close: Mapped[Decimal] = mapped_column(Numeric(10, 4))
    volume: Mapped[int] = mapped_column(Integer)


class BacktestRunRecord(Base):
    __tablename__ = "backtest_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    strategy_name: Mapped[str] = mapped_column(String(100))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    starting_capital: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    interval_minutes: Mapped[int] = mapped_column(Integer)
    slippage_pct: Mapped[Decimal] = mapped_column(Numeric(6, 4), default=0)
    ending_nav: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    total_return_pct: Mapped[Decimal] = mapped_column(Numeric(8, 2))
    max_drawdown_pct: Mapped[Decimal] = mapped_column(Numeric(8, 2))
    total_trades: Mapped[int] = mapped_column(Integer)
    win_rate: Mapped[Decimal] = mapped_column(Numeric(6, 2))
    profit_factor: Mapped[Decimal] = mapped_column(Numeric(8, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
