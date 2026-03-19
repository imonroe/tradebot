"""Backtest-specific risk check overrides."""
from datetime import time

from tradebot.backtest.clock import SimulatedClock
from tradebot.core.events import RiskEvent, SignalEvent
from tradebot.risk.checks import TimeWindowCheck


class BacktestTimeWindowCheck(TimeWindowCheck):
    """TimeWindowCheck that uses simulated time instead of wall-clock time."""

    def __init__(self, earliest: time, latest: time, clock: SimulatedClock) -> None:
        super().__init__(earliest=earliest, latest=latest)
        self._clock = clock

    def check(self, signal: SignalEvent, current_time: time | None = None) -> RiskEvent:
        return super().check(signal, current_time=self._clock.now().time())
