"""Portfolio state tracking: positions, P&L, drawdown."""
from decimal import Decimal

import structlog

from tradebot.core.events import FillEvent

logger = structlog.get_logger()


class PortfolioTracker:
    """Tracks open positions, realized P&L, NAV, and drawdown."""

    def __init__(self, starting_capital: Decimal) -> None:
        self._starting_capital = starting_capital
        self._nav = starting_capital
        self._peak_nav = starting_capital
        self._daily_pnl = Decimal("0")
        self._total_pnl = Decimal("0")
        self._open_positions: list[dict] = []

    @property
    def nav(self) -> Decimal:
        return self._nav

    @property
    def daily_pnl(self) -> Decimal:
        return self._daily_pnl

    @property
    def open_positions(self) -> list[dict]:
        return list(self._open_positions)

    @property
    def drawdown_pct(self) -> Decimal:
        if self._peak_nav == 0:
            return Decimal("0")
        return (self._peak_nav - self._nav) / self._peak_nav * 100

    def record_fill(self, fill: FillEvent) -> None:
        """Record a new filled position."""
        position = {
            "broker_order_id": fill.broker_order_id,
            "strategy": fill.signal.strategy_name,
            "symbol": fill.signal.symbol,
            "spread_type": fill.signal.spread_type.value,
            "legs": fill.signal.legs,
            "fill_price": fill.fill_price,
            "timestamp": fill.timestamp,
        }
        self._open_positions.append(position)
        logger.info(
            "position_opened",
            symbol=fill.signal.symbol,
            strategy=fill.signal.strategy_name,
            fill_price=str(fill.fill_price),
        )

    def close_position(self, broker_order_id: str, pnl: Decimal) -> None:
        """Close a position and record realized P&L."""
        self._open_positions = [
            p for p in self._open_positions if p["broker_order_id"] != broker_order_id
        ]
        self.record_realized_pnl(pnl)

    def record_realized_pnl(self, pnl: Decimal) -> None:
        """Record realized P&L and update NAV."""
        self._daily_pnl += pnl
        self._total_pnl += pnl
        self._nav += pnl
        if self._nav > self._peak_nav:
            self._peak_nav = self._nav

    def reset_daily(self) -> None:
        """Reset daily P&L counter (called at start of each trading day)."""
        self._daily_pnl = Decimal("0")

    async def on_fill(self, fill: FillEvent) -> list:
        """Event handler for FillEvents."""
        self.record_fill(fill)
        return []
