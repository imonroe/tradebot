# Backtest GUI Design Spec

## Overview

Add a browser-based interface for running backtests, viewing results, and comparing past runs. The feature integrates into the existing Strategies page as a new tab and communicates with new API endpoints that wrap the existing CLI backtest engine.

## Approach

Thin API layer (Approach A): New FastAPI router endpoints run backtests synchronously in-process. The existing async `run_backtest()` engine is called directly. A 30-day date range cap keeps run times reasonable. No background workers or task queues.

## API Endpoints

New router: `src/tradebot/api/routes/backtest.py`

### POST /api/backtest/run

Run a backtest synchronously and return full results.

**Request body:**

```json
{
  "strategy": "xsp_iron_condor",
  "start_date": "2026-03-01",
  "end_date": "2026-03-20",
  "starting_capital": 2500,
  "slippage_pct": 0,
  "interval_minutes": 15,
  "save": true,
  "overrides": {
    "entry.strike_selection.short_call_delta": 0.10,
    "entry.min_credit": 0.25
  }
}
```

**Validation:**

- Date range: max 30 calendar days, start < end
- Starting capital: min $100
- Slippage: 0–5%
- Override keys must exist in the strategy YAML; unknown paths return 422

**Response:** Full BacktestResult — config, performance metrics, daily snapshots array, trades array. On validation failure, 422 with error details.

### GET /api/backtest/runs

List saved backtest runs ordered by created_at descending.

**Query params:** `limit` (default 20)

**Response:** Array of run summaries (id, strategy_name, start_date, end_date, starting_capital, total_return_pct, max_drawdown_pct, win_rate, profit_factor, total_trades, created_at).

### GET /api/backtest/runs/{id}

Get a single saved run with full details including daily snapshots and trades.

### DELETE /api/backtest/runs/{id}

Delete a saved backtest run.

### GET /api/backtest/strategies

List available strategy configs from `config/strategies/`. Returns the full YAML structure for each strategy so the frontend can render override fields.

**Response:**

```json
[
  {
    "name": "xsp_iron_condor",
    "filename": "xsp_iron_condor.yaml",
    "config": {
      "strategy": { "name": "xsp_0dte_iron_condor", ... },
      "entry": { ... },
      "exit": { ... },
      "position_sizing": { ... },
      "risk": { ... }
    }
  }
]
```

## Strategy Override Mechanism

1. API endpoint loads the strategy YAML into a dict
2. Applies dot-notation overrides (e.g., `entry.strike_selection.short_call_delta` → `yaml["entry"]["strike_selection"]["short_call_delta"]`)
3. Writes patched config to a temp file and passes that path to `run_backtest()`
4. Unknown override paths return 422

This avoids modifying the backtest engine — it still reads a config file path.

## Database Changes

### Modified table: backtest_runs

Add two JSON columns to the existing `backtest_runs` table:

- `daily_snapshots: JSON` — Array of daily snapshot dicts (date, nav, pnl, drawdown)
- `trades: JSON` — Array of trade detail dicts (entry/exit prices, P&L, timestamps)

These are read-only, always fetched together with the run, and don't need relational queries — JSON columns are the right fit.

New Alembic migration to add these columns.

### Updated repository methods

- `save_backtest_run()` — Include daily_snapshots and trades JSON
- `get_backtest_runs()` — Return summary fields only (exclude large JSON columns)
- `get_backtest_run(id)` — New method, returns full record including JSON data
- `delete_backtest_run(id)` — New method

## Frontend Structure

### Navigation

The Strategies page gains tabs: **Overview** (existing strategy card grid) and **Backtest** (new).

### Backtest Tab — Run View

**Left panel: Configuration form**

- Strategy dropdown (populated from GET /api/backtest/strategies)
- Date range pickers (start, end)
- Starting capital input (default from strategy config)
- Slippage % input (default 0)
- Interval minutes input (default 15)
- Expandable "Strategy Overrides" section — renders input fields based on the selected strategy's YAML structure (delta targets, wing widths, min credit, profit target, stop loss, etc.)
- "Run Backtest" button

**Right panel: Results display (after run completes)**

- Metrics cards: Total Return, Max Drawdown, Win Rate, Profit Factor, Total Trades
- Equity curve chart (Recharts LineChart — NAV over time from daily snapshots, same style as existing NAVChart)
- Trade log table: entry/exit timestamps, type, P&L (color-coded), strategy details

Loading spinner overlay during backtest execution.

### Backtest Tab — History View

- Toggle between "Run" and "History" sub-views
- Table of past runs: strategy name, date range, return %, max drawdown, win rate, profit factor, created date
- Checkbox column for selecting runs to compare
- "Compare Selected" button (enabled when 2+ runs selected)
- Click a row to expand and view full results (metrics + chart + trades)
- Delete button per row

### Comparison View

- Side-by-side metric cards for each selected run
- Overlaid equity curves on the same chart (different colors per run)
- Comparison table with metrics in columns, one column per selected run

### New Frontend Files

- `frontend/src/pages/Strategies.tsx` — Modified to add tab navigation
- `frontend/src/components/backtest/BacktestRunner.tsx` — Config form + results display
- `frontend/src/components/backtest/BacktestHistory.tsx` — History table + comparison
- `frontend/src/components/backtest/BacktestResults.tsx` — Reusable metrics + chart + trade log
- `frontend/src/components/backtest/BacktestComparison.tsx` — Side-by-side comparison view
- `frontend/src/components/backtest/StrategyOverrides.tsx` — Dynamic override form fields

## Tech Stack (No Changes)

- Backend: FastAPI, existing backtest engine, SQLAlchemy, Alembic
- Frontend: React 18, TypeScript, Tailwind CSS (dark theme), Recharts
- Existing hooks: useApi for REST polling
- Existing patterns: all new code follows established conventions

## Constraints

- Max date range: 30 calendar days (422 if exceeded)
- Synchronous execution: API blocks until backtest completes
- Synthetic data only: uses PaperDataSource with random-walk prices (no historical market data integration in this phase)
