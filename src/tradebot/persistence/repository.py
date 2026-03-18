"""Data access layer for trade persistence."""
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from tradebot.persistence.models import TradeRecord, TradeLegRecord, DayTradeLogRecord, DailySnapshotRecord

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

    def commit(self) -> None:
        """Commit the current session."""
        self._session.commit()
