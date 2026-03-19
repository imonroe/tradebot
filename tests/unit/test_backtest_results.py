"""Tests for BacktestResult and metric calculations."""
from datetime import date
from decimal import Decimal

from tradebot.backtest.results import BacktestResult, compute_metrics


def test_compute_metrics_with_wins_and_losses():
    trades = [
        {"pnl": Decimal("50")},
        {"pnl": Decimal("30")},
        {"pnl": Decimal("-20")},
        {"pnl": Decimal("40")},
        {"pnl": Decimal("-10")},
    ]
    metrics = compute_metrics(trades)
    assert metrics["total_trades"] == 5
    assert metrics["winning_trades"] == 3
    assert metrics["losing_trades"] == 2
    assert metrics["win_rate"] == Decimal("60.0")
    assert metrics["avg_win"] == Decimal("40.00")
    assert metrics["avg_loss"] == Decimal("-15.00")
    assert metrics["profit_factor"] == Decimal("4.00")


def test_compute_metrics_all_wins():
    trades = [{"pnl": Decimal("50")}, {"pnl": Decimal("30")}]
    metrics = compute_metrics(trades)
    assert metrics["win_rate"] == Decimal("100.0")
    assert metrics["profit_factor"] == Decimal("Infinity")


def test_compute_metrics_no_trades():
    metrics = compute_metrics([])
    assert metrics["total_trades"] == 0
    assert metrics["win_rate"] == Decimal("0")
    assert metrics["profit_factor"] == Decimal("0")


def test_backtest_result_print_summary(capsys):
    result = BacktestResult(
        strategy_name="test_strategy",
        start_date=date(2026, 1, 2),
        end_date=date(2026, 3, 1),
        starting_capital=Decimal("2500"),
        interval_minutes=15,
        ending_nav=Decimal("2715"),
        total_return_pct=Decimal("8.60"),
        max_drawdown_pct=Decimal("3.20"),
        total_trades=38,
        winning_trades=26,
        losing_trades=12,
        win_rate=Decimal("68.4"),
        avg_win=Decimal("18.50"),
        avg_loss=Decimal("-12.30"),
        profit_factor=Decimal("2.31"),
    )
    result.print_summary()
    output = capsys.readouterr().out
    assert "test_strategy" in output
    assert "8.60%" in output
    assert "68.4%" in output
