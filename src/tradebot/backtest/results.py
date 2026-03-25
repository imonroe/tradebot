"""Backtest results and metrics."""
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from tradebot.analytics.metrics import compute_trade_metrics


def compute_metrics(trades: list[dict]) -> dict:
    """Compute trade statistics from a list of trades with 'pnl' field.

    Thin wrapper around the shared analytics module for backwards compatibility.
    """
    result = compute_trade_metrics(trades)
    # Return only the fields the backtest engine expects
    return {
        "total_trades": result["total_trades"],
        "winning_trades": result["winning_trades"],
        "losing_trades": result["losing_trades"],
        "win_rate": result["win_rate"],
        "avg_win": result["avg_win"],
        "avg_loss": result["avg_loss"],
        "profit_factor": result["profit_factor"],
    }


@dataclass
class BacktestResult:
    """Complete results from a backtest run."""

    # Config
    strategy_name: str
    start_date: date
    end_date: date
    starting_capital: Decimal
    interval_minutes: int

    # Performance
    ending_nav: Decimal
    total_return_pct: Decimal
    max_drawdown_pct: Decimal

    # Trade stats
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: Decimal
    avg_win: Decimal
    avg_loss: Decimal
    profit_factor: Decimal

    # Daily data
    daily_snapshots: list[dict] = field(default_factory=list)
    trades: list[dict] = field(default_factory=list)

    def print_summary(self) -> None:
        """Print formatted summary to terminal."""
        ret_sign = "+" if self.total_return_pct >= 0 else ""
        w = self.winning_trades
        lo = self.losing_trades
        print()
        print("=" * 51)
        print(f"  Backtest: {self.strategy_name}")
        print(f"  Period:   {self.start_date} -> {self.end_date}")
        print(f"  Capital:  ${self.starting_capital:,.2f} -> ${self.ending_nav:,.2f}")
        print("=" * 51)
        print(f"  Total Return:    {ret_sign}{self.total_return_pct}%")
        print(f"  Max Drawdown:    -{self.max_drawdown_pct}%")
        print(f"  Total Trades:    {self.total_trades}")
        print(f"  Win Rate:        {self.win_rate}%  ({w}W / {lo}L)")
        print(f"  Avg Win:         ${self.avg_win}")
        print(f"  Avg Loss:        ${self.avg_loss}")
        print(f"  Profit Factor:   {self.profit_factor}")
        print("=" * 51)
