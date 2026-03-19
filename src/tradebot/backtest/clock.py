"""Time control for backtesting."""
from datetime import datetime


class Clock:
    """Returns current time. Uses real time by default."""

    def now(self) -> datetime:
        return datetime.now()


class SimulatedClock(Clock):
    """Manually advanced clock for backtesting."""

    def __init__(self, start: datetime) -> None:
        self._now = start

    def now(self) -> datetime:
        return self._now

    def advance_to(self, dt: datetime) -> None:
        self._now = dt
