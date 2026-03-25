# Plan: Portfolio Analytics

**Date:** 2026-03-25
**Status:** Implementation

## Problem Statement

The bot tracks trades and daily snapshots but provides no aggregate performance metrics. Operators need Sharpe ratio, win rate, profit factor, and other statistics to evaluate strategy performance — both in live trading and backtesting.

## Design

### Metrics Computed

**From closed trades (TradeRecord where status="closed"):**
- Total trades, winning trades, losing trades
- Win rate (%)
- Average win, average loss
- Profit factor (gross profit / gross loss)
- Largest win, largest loss
- Average trade P&L
- Total P&L

**From daily snapshots (DailySnapshotRecord):**
- Sharpe ratio (annualized, using daily NAV returns)
- Max drawdown (%)
- Current streak (consecutive wins or losses)

### Shared Module

Extract analytics logic into `src/tradebot/analytics/metrics.py` so both the API endpoint and `BacktestResult` can use it. The existing `backtest/results.py::compute_metrics()` will be replaced with an import from the shared module.

### API Endpoint

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/portfolio/analytics` | Full analytics from trade history + daily snapshots |

Response shape:
```json
{
  "total_trades": 42,
  "winning_trades": 28,
  "losing_trades": 14,
  "win_rate": "66.7",
  "avg_win": "1.25",
  "avg_loss": "-0.80",
  "largest_win": "3.50",
  "largest_loss": "-2.10",
  "profit_factor": "2.50",
  "total_pnl": "22.40",
  "sharpe_ratio": "1.85",
  "max_drawdown_pct": "4.20",
  "current_streak": 3,
  "streak_type": "win"
}
```

### Frontend

Add an "Analytics" stats row to the Dashboard below the existing stat cards, showing key metrics in a compact grid.

## Files Changed

| File | Change |
|------|--------|
| `src/tradebot/analytics/__init__.py` | New package |
| `src/tradebot/analytics/metrics.py` | New — shared metrics computation |
| `src/tradebot/backtest/results.py` | Import from analytics instead of inline compute |
| `src/tradebot/persistence/repository.py` | Add `get_closed_trades()` method |
| `src/tradebot/api/routes/portfolio.py` | Add `/portfolio/analytics` endpoint |
| `frontend/src/pages/Dashboard.tsx` | Add analytics display section |
| `tests/unit/test_analytics.py` | New — tests for metrics computation |
| `tests/unit/test_api.py` | Add test for analytics endpoint |
| `README.md` | Mark roadmap item complete, add endpoint |
| `CLAUDE.md` | Add analytics module description |

## Success Criteria

1. `GET /api/portfolio/analytics` returns correct metrics from trade history
2. Sharpe ratio computed correctly from daily snapshots
3. Backtest results reuse the shared metrics module
4. Dashboard displays analytics section
5. All tests pass
