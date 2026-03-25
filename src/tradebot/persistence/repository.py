"""Data access layer for trade persistence."""
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from tradebot.persistence.models import TradeRecord, TradeLegRecord, DayTradeLogRecord, DailySnapshotRecord, BacktestRunRecord, PriceBarRecord

class Repository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_trade(self, strategy: str, symbol: str, spread_type: str, entry_price: Decimal) -> TradeRecord:
        trade = TradeRecord(strategy=strategy, symbol=symbol, spread_type=spread_type,
            entry_price=entry_price, status="open")
        self._session.add(trade)
        self._session.flush()
        return trade

    def get_trade(self, trade_id: int) -> TradeRecord | None:
        return self._session.get(TradeRecord, trade_id)

    def close_trade(self, trade_id: int, exit_price: Decimal, pnl: Decimal, status: str = "closed") -> None:
        trade = self.get_trade(trade_id)
        if trade:
            trade.exit_price = exit_price
            trade.pnl = pnl
            trade.status = status
            trade.exit_time = datetime.now()
            self._session.flush()

    def add_trade_leg(self, trade_id: int, option_symbol: str, side: str, quantity: int,
            strike: Decimal, option_type: str, fill_price: Decimal) -> TradeLegRecord:
        leg = TradeLegRecord(trade_id=trade_id, option_symbol=option_symbol, side=side,
            quantity=quantity, strike=strike, option_type=option_type, fill_price=fill_price)
        self._session.add(leg)
        self._session.flush()
        return leg

    def log_day_trade(self, trade_date: date, order_id: str, trade_id: int) -> None:
        record = DayTradeLogRecord(trade_date=trade_date, order_id=order_id, trade_id=trade_id)
        self._session.add(record)
        self._session.flush()

    def get_day_trade_count(self, start_date: date, end_date: date) -> int:
        stmt = (select(func.count()).select_from(DayTradeLogRecord)
            .where(DayTradeLogRecord.trade_date >= start_date, DayTradeLogRecord.trade_date <= end_date))
        return self._session.execute(stmt).scalar() or 0

    def get_open_trades(self) -> list[TradeRecord]:
        stmt = select(TradeRecord).where(TradeRecord.status == "open")
        return list(self._session.execute(stmt).scalars().all())

    def get_closed_trades(self) -> list[TradeRecord]:
        """Get all closed trades, ordered by exit time ascending."""
        stmt = (
            select(TradeRecord)
            .where(TradeRecord.status == "closed")
            .order_by(TradeRecord.exit_time.asc())
        )
        return list(self._session.execute(stmt).scalars().all())

    def get_all_daily_snapshots(self) -> list[DailySnapshotRecord]:
        """Get all daily snapshots ordered by date ascending."""
        stmt = select(DailySnapshotRecord).order_by(DailySnapshotRecord.snapshot_date.asc())
        return list(self._session.execute(stmt).scalars().all())

    def get_recent_trades(self, limit: int = 100) -> list[TradeRecord]:
        stmt = select(TradeRecord).order_by(TradeRecord.entry_time.desc()).limit(limit)
        return list(self._session.execute(stmt).scalars().all())

    def record_daily_snapshot(
        self,
        snapshot_date: date,
        nav: Decimal,
        realized_pnl: Decimal,
        unrealized_pnl: Decimal,
        drawdown: Decimal,
        day_trade_count: int,
    ) -> None:
        """Record end-of-day portfolio snapshot."""
        snapshot = DailySnapshotRecord(
            snapshot_date=snapshot_date,
            nav=nav,
            realized_pnl=realized_pnl,
            unrealized_pnl=unrealized_pnl,
            drawdown=drawdown,
            day_trade_count=day_trade_count,
        )
        self._session.add(snapshot)
        self._session.flush()

    def get_nav_history(self, days: int = 30) -> list[dict]:
        """Get NAV history for the last N days, ordered by date ascending."""
        from datetime import timedelta
        start_date = date.today() - timedelta(days=days)
        stmt = (
            select(DailySnapshotRecord)
            .where(DailySnapshotRecord.snapshot_date >= start_date)
            .order_by(DailySnapshotRecord.snapshot_date.asc())
        )
        snapshots = self._session.execute(stmt).scalars().all()
        return [
            {
                "date": s.snapshot_date.isoformat(),
                "nav": str(s.nav),
                "realized_pnl": str(s.realized_pnl),
                "unrealized_pnl": str(s.unrealized_pnl),
                "drawdown": str(s.drawdown),
                "day_trades": s.day_trade_count,
            }
            for s in snapshots
        ]

    def save_backtest_run(self, result) -> BacktestRunRecord:
        """Save a backtest run summary."""
        record = BacktestRunRecord(
            strategy_name=result.strategy_name,
            start_date=result.start_date,
            end_date=result.end_date,
            starting_capital=result.starting_capital,
            interval_minutes=result.interval_minutes,
            ending_nav=result.ending_nav,
            total_return_pct=result.total_return_pct,
            max_drawdown_pct=result.max_drawdown_pct,
            total_trades=result.total_trades,
            win_rate=result.win_rate,
            profit_factor=result.profit_factor,
        )
        self._session.add(record)
        self._session.flush()
        return record

    def get_backtest_runs(self, limit: int = 20) -> list[BacktestRunRecord]:
        """Get recent backtest runs."""
        stmt = (
            select(BacktestRunRecord)
            .order_by(BacktestRunRecord.created_at.desc())
            .limit(limit)
        )
        return list(self._session.execute(stmt).scalars().all())

    def save_price_bar(
        self, symbol: str, timestamp: datetime, open_: Decimal,
        high: Decimal, low: Decimal, close: Decimal, volume: int,
    ) -> None:
        """Save a price bar, silently ignoring duplicates via IntegrityError."""
        bar = PriceBarRecord(
            symbol=symbol, timestamp=timestamp,
            open=open_, high=high, low=low, close=close, volume=volume,
        )
        self._session.add(bar)
        try:
            self._session.flush()
        except IntegrityError:
            self._session.rollback()

    def get_price_bars(
        self, symbol: str, start: datetime, end: datetime,
    ) -> list[PriceBarRecord]:
        """Get price bars for a symbol within a time range."""
        stmt = (
            select(PriceBarRecord)
            .where(
                PriceBarRecord.symbol == symbol,
                PriceBarRecord.timestamp >= start,
                PriceBarRecord.timestamp <= end,
            )
            .order_by(PriceBarRecord.timestamp.asc())
        )
        return list(self._session.execute(stmt).scalars().all())

    def commit(self) -> None:
        """Commit the current session."""
        self._session.commit()

    def rollback(self) -> None:
        """Rollback the current session."""
        self._session.rollback()
