"""Individual risk check implementations."""
from dataclasses import dataclass
from datetime import date, time, timedelta
from decimal import Decimal

from tradebot.core.events import RiskEvent, SignalEvent


@dataclass
class PDTCheck:
    """Tracks day trades in rolling 5-business-day window."""
    repo: object  # Repository
    pdt_limit: int = 3

    def check(self, signal: SignalEvent) -> RiskEvent:
        import exchange_calendars as xcals
        today = date.today()
        nyse = xcals.get_calendar("XNYS")
        sessions = nyse.sessions_in_range(today - timedelta(days=10), today)
        # Get the last 5 trading sessions (rolling 5 business days)
        recent_sessions = sessions[-5:] if len(sessions) >= 5 else sessions
        start = recent_sessions[0].date() if len(recent_sessions) > 0 else today
        count = self.repo.get_day_trade_count(start_date=start, end_date=today)
        passed = count < self.pdt_limit
        return RiskEvent(
            check_name="PDTCheck",
            passed=passed,
            message=(
                f"PDT OK: {count}/{self.pdt_limit} day trades used"
                if passed
                else f"PDT limit reached: {count}/{self.pdt_limit} day trades used"
            ),
        )


@dataclass
class MaxDailyLossCheck:
    """Halts trading when daily loss exceeds threshold."""
    max_daily_loss_pct: Decimal
    current_daily_pnl: Decimal
    account_value: Decimal

    def check(self, signal: SignalEvent) -> RiskEvent:
        loss_pct = abs(self.current_daily_pnl) / self.account_value * 100
        passed = self.current_daily_pnl >= 0 or loss_pct < self.max_daily_loss_pct
        return RiskEvent(
            check_name="MaxDailyLossCheck",
            passed=passed,
            message=(
                f"Daily P&L: ${self.current_daily_pnl} ({loss_pct:.1f}%)"
                if passed
                else f"Daily loss limit hit: ${self.current_daily_pnl} ({loss_pct:.1f}% >= {self.max_daily_loss_pct}%)"
            ),
        )


@dataclass
class PositionSizeCheck:
    """Validates trade risk against account size."""
    max_risk_per_trade: Decimal
    account_value: Decimal

    def check(self, signal: SignalEvent, trade_max_loss: Decimal = Decimal("0")) -> RiskEvent:
        passed = trade_max_loss <= self.max_risk_per_trade
        return RiskEvent(
            check_name="PositionSizeCheck",
            passed=passed,
            message=(
                f"Position size OK: max loss ${trade_max_loss} <= ${self.max_risk_per_trade}"
                if passed
                else f"Position too large: max loss ${trade_max_loss} > ${self.max_risk_per_trade}"
            ),
        )


@dataclass
class SpreadWidthCheck:
    """Validates spread width is appropriate for account size."""
    max_spread_width: Decimal = Decimal("10.0")

    def check(self, signal: SignalEvent, spread_width: Decimal = Decimal("0")) -> RiskEvent:
        passed = spread_width <= self.max_spread_width
        return RiskEvent(
            check_name="SpreadWidthCheck",
            passed=passed,
            message=(
                f"Spread width OK: ${spread_width}"
                if passed
                else f"Spread too wide: ${spread_width} > ${self.max_spread_width}"
            ),
        )


@dataclass
class TimeWindowCheck:
    """Only allows entries during configured time window."""
    earliest: time
    latest: time

    def check(self, signal: SignalEvent, current_time: time | None = None) -> RiskEvent:
        from datetime import datetime as dt
        now = current_time or dt.now().time()
        passed = self.earliest <= now <= self.latest
        return RiskEvent(
            check_name="TimeWindowCheck",
            passed=passed,
            message=(
                f"Time OK: {now} within {self.earliest}-{self.latest}"
                if passed
                else f"Outside trading window: {now} not in {self.earliest}-{self.latest}"
            ),
        )


@dataclass
class MaxDrawdownCheck:
    """Halts bot when drawdown from peak exceeds threshold."""
    max_drawdown_pct: Decimal
    current_drawdown_pct: Decimal

    def check(self, signal: SignalEvent) -> RiskEvent:
        passed = self.current_drawdown_pct < self.max_drawdown_pct
        return RiskEvent(
            check_name="MaxDrawdownCheck",
            passed=passed,
            message=(
                f"Drawdown OK: {self.current_drawdown_pct:.1f}%"
                if passed
                else f"Max drawdown hit: {self.current_drawdown_pct:.1f}% >= {self.max_drawdown_pct}%"
            ),
        )


@dataclass
class DuplicateCheck:
    """Prevents duplicate positions on the same underlying."""
    open_symbols: set[str]

    def check(self, signal: SignalEvent) -> RiskEvent:
        passed = signal.symbol not in self.open_symbols
        return RiskEvent(
            check_name="DuplicateCheck",
            passed=passed,
            message=(
                f"No duplicate: {signal.symbol} not in open positions"
                if passed
                else f"Duplicate position: {signal.symbol} already open"
            ),
        )
