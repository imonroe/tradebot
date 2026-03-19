"""Tests for Clock and SimulatedClock."""
from datetime import datetime

from tradebot.backtest.clock import Clock, SimulatedClock


def test_clock_returns_current_time():
    clock = Clock()
    before = datetime.now()
    result = clock.now()
    after = datetime.now()
    assert before <= result <= after


def test_simulated_clock_returns_fixed_time():
    t = datetime(2026, 1, 15, 10, 30)
    clock = SimulatedClock(start=t)
    assert clock.now() == t


def test_simulated_clock_advance_to():
    t1 = datetime(2026, 1, 15, 10, 30)
    t2 = datetime(2026, 1, 15, 11, 0)
    clock = SimulatedClock(start=t1)
    clock.advance_to(t2)
    assert clock.now() == t2


def test_simulated_clock_is_subclass_of_clock():
    clock = SimulatedClock(start=datetime(2026, 1, 1))
    assert isinstance(clock, Clock)
