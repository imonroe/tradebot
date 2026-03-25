"""Portfolio analytics and trade metrics computation."""
from decimal import Decimal
import math


def compute_trade_metrics(trades: list[dict]) -> dict:
    """Compute trade statistics from a list of trades with 'pnl' field.

    Each trade dict must have a 'pnl' key with a Decimal value.
    Returns a dict of computed metrics.
    """
    if not trades:
        return {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "win_rate": Decimal("0"),
            "avg_win": Decimal("0"),
            "avg_loss": Decimal("0"),
            "largest_win": Decimal("0"),
            "largest_loss": Decimal("0"),
            "profit_factor": Decimal("0"),
            "total_pnl": Decimal("0"),
            "avg_trade_pnl": Decimal("0"),
            "current_streak": 0,
            "streak_type": "none",
        }

    wins = [t for t in trades if t["pnl"] > 0]
    losses = [t for t in trades if t["pnl"] < 0]
    total = len(trades)
    n_wins = len(wins)
    n_losses = len(losses)

    win_rate = (Decimal(n_wins) / Decimal(total) * Decimal("100")).quantize(Decimal("0.1"))
    avg_win = sum(t["pnl"] for t in wins) / n_wins if n_wins else Decimal("0")
    avg_loss = sum(t["pnl"] for t in losses) / n_losses if n_losses else Decimal("0")

    largest_win = max((t["pnl"] for t in wins), default=Decimal("0"))
    largest_loss = min((t["pnl"] for t in losses), default=Decimal("0"))

    total_pnl = sum(t["pnl"] for t in trades)
    avg_trade_pnl = total_pnl / total

    gross_profit = sum(t["pnl"] for t in wins)
    gross_loss = abs(sum(t["pnl"] for t in losses))

    if gross_loss == 0:
        profit_factor = Decimal("Infinity") if gross_profit > 0 else Decimal("0")
    else:
        profit_factor = Decimal(str(round(gross_profit / gross_loss, 2)))

    # Current streak: count consecutive wins or losses from most recent trade
    streak = 0
    streak_type = "none"
    if trades:
        last_pnl = trades[-1]["pnl"]
        if last_pnl > 0:
            streak_type = "win"
            for t in reversed(trades):
                if t["pnl"] > 0:
                    streak += 1
                else:
                    break
        elif last_pnl < 0:
            streak_type = "loss"
            for t in reversed(trades):
                if t["pnl"] < 0:
                    streak += 1
                else:
                    break

    return {
        "total_trades": total,
        "winning_trades": n_wins,
        "losing_trades": n_losses,
        "win_rate": win_rate,
        "avg_win": avg_win.quantize(Decimal("0.01")),
        "avg_loss": avg_loss.quantize(Decimal("0.01")),
        "largest_win": largest_win.quantize(Decimal("0.01")),
        "largest_loss": largest_loss.quantize(Decimal("0.01")),
        "profit_factor": profit_factor,
        "total_pnl": total_pnl.quantize(Decimal("0.01")),
        "avg_trade_pnl": avg_trade_pnl.quantize(Decimal("0.01")),
        "current_streak": streak,
        "streak_type": streak_type,
    }


def compute_sharpe_ratio(daily_navs: list[Decimal], risk_free_rate: float = 0.0) -> Decimal:
    """Compute annualized Sharpe ratio from a series of daily NAV values.

    Uses daily simple returns (curr / prev - 1). Assumes 252 trading days per year.
    Returns Decimal("0") if fewer than 2 data points.
    """
    if len(daily_navs) < 2:
        return Decimal("0")

    # Compute daily returns
    returns = []
    for i in range(1, len(daily_navs)):
        prev = float(daily_navs[i - 1])
        curr = float(daily_navs[i])
        if prev > 0:
            returns.append(curr / prev - 1)

    if not returns:
        return Decimal("0")

    n = len(returns)
    daily_rf = risk_free_rate / 252

    mean_raw_return = sum(returns) / n
    mean_return = mean_raw_return - daily_rf
    variance = sum((r - mean_raw_return) ** 2 for r in returns) / (n - 1) if n > 1 else 0
    std_dev = math.sqrt(variance)

    if std_dev == 0:
        return Decimal("0")

    sharpe = (mean_return / std_dev) * math.sqrt(252)
    return Decimal(str(round(sharpe, 2)))
