"""Tests for BacktestEngine."""
from datetime import date
from decimal import Decimal
from pathlib import Path
from textwrap import dedent

import pytest

from tradebot.backtest.engine import run_backtest, _generate_timestamps


def test_generate_timestamps_skips_weekends():
    # Jan 3 2026 is Saturday, Jan 4 is Sunday
    timestamps = _generate_timestamps(
        start_date=date(2026, 1, 2),  # Friday
        end_date=date(2026, 1, 5),    # Monday
        interval_minutes=60,
    )
    days = {ts.date() for ts in timestamps}
    assert date(2026, 1, 2) in days   # Friday
    assert date(2026, 1, 3) not in days  # Saturday
    assert date(2026, 1, 4) not in days  # Sunday
    assert date(2026, 1, 5) in days   # Monday


def test_generate_timestamps_interval():
    timestamps = _generate_timestamps(
        start_date=date(2026, 1, 2),
        end_date=date(2026, 1, 2),
        interval_minutes=30,
    )
    # 9:30 to 16:00 at 30min intervals = 14 timestamps
    assert len(timestamps) == 14
    assert timestamps[0].hour == 9 and timestamps[0].minute == 30
    assert timestamps[-1].hour == 16 and timestamps[-1].minute == 0


@pytest.fixture
def backtest_config(tmp_path):
    """Credit spread config tuned for synthetic data.

    Uses ITM short delta (-0.60) where the PaperDataSource generates
    meaningful intrinsic value differences between short and long strikes,
    producing reliable trade fills.
    """
    config = dedent("""\
        strategy:
          name: "xsp_0dte_credit_spread_put"
          class: "CreditSpreadStrategy"
          enabled: true

        market:
          symbol: "XSP"
          expiration: "0dte"

        entry:
          direction: "put"
          time_window:
            earliest: "09:45"
            latest: "14:00"
          strike_selection:
            method: "delta"
            short_delta: 0.60
            wing_width: 2
          min_credit: 0.10

        exit:
          profit_target_pct: 50
          stop_loss_pct: 200
          time_exit: "15:45"
          prefer_expire: true

        position_sizing:
          method: "fixed_risk"
          max_risk_per_trade: 250
          max_contracts: 2

        risk:
          max_daily_trades: 1
          pdt_aware: true
    """)
    config_path = tmp_path / "xsp_credit_spread_put.yaml"
    config_path.write_text(config)
    return config_path


@pytest.mark.asyncio
async def test_backtest_runs_and_returns_result(backtest_config):
    result = await run_backtest(
        strategy_config_path=backtest_config,
        start_date=date(2026, 1, 2),
        end_date=date(2026, 1, 10),
        interval_minutes=30,
        starting_capital=Decimal("2500"),
    )

    assert result.strategy_name == "xsp_0dte_credit_spread_put"
    assert result.starting_capital == Decimal("2500")
    assert result.ending_nav > 0
    assert result.total_trades > 0
    assert len(result.daily_snapshots) > 0


@pytest.mark.asyncio
async def test_backtest_single_day(backtest_config):
    result = await run_backtest(
        strategy_config_path=backtest_config,
        start_date=date(2026, 1, 2),
        end_date=date(2026, 1, 2),
        interval_minutes=15,
        starting_capital=Decimal("2500"),
    )

    assert result.start_date == date(2026, 1, 2)
    assert result.end_date == date(2026, 1, 2)
    assert len(result.daily_snapshots) == 1
