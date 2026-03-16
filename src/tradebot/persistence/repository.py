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
