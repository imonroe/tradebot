"""Backtest results and metrics."""
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal


def compute_metrics(trades: list[dict]) -> dict:
    """Compute trade statistics from a list of trades with 'pnl' field."""
    if not trades:
        return {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "win_rate": Decimal("0"),
            "avg_win": Decimal("0"),
            "avg_loss": Decimal("0"),
            "profit_factor": Decimal("0"),
        }

    wins = [t for t in trades if t["pnl"] > 0]
    losses = [t for t in trades if t["pnl"] < 0]
    total = len(trades)
    n_wins = len(wins)
    n_losses = len(losses)

    win_rate = Decimal(str(round(n_wins / total * 100, 1)))
    avg_win = (
        sum(t["pnl"] for t in wins) / n_wins if n_wins else Decimal("0")
    )
    avg_loss = (
        sum(t["pnl"] for t in losses) / n_losses if n_losses else Decimal("0")
    )

    gross_profit = sum(t["pnl"] for t in wins)
    gross_loss = abs(sum(t["pnl"] for t in losses))

    if gross_loss == 0:
        profit_factor = Decimal("Infinity") if gross_profit > 0 else Decimal("0")
    else:
        profit_factor = Decimal(str(round(gross_profit / gross_loss, 2)))

    return {
        "total_trades": total,
        "winning_trades": n_wins,
        "losing_trades": n_losses,
        "win_rate": win_rate,
        "avg_win": avg_win.quantize(Decimal("0.01")),
        "avg_loss": avg_loss.quantize(Decimal("0.01")),
        "profit_factor": profit_factor,
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
