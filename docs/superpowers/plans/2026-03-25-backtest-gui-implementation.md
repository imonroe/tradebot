# Backtest GUI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add browser-based backtest running, result viewing, and run comparison to the existing Strategies page.

**Architecture:** New FastAPI router wraps the existing `run_backtest()` engine. Two JSON columns added to `backtest_runs` table for snapshots/trades. Frontend adds a tabbed interface to the Strategies page with config form, results display, history table, and comparison view.

**Tech Stack:** Python/FastAPI, SQLAlchemy/Alembic, React 18, TypeScript, Tailwind CSS, Recharts

---

### Task 1: Database Migration — Add JSON Columns

**Files:**
- Modify: `src/tradebot/persistence/models.py:52-67`
- Create: `alembic/versions/xxxx_add_backtest_json_columns.py` (via alembic)
- Modify: `src/tradebot/persistence/repository.py:114-140`
- Test: `tests/unit/test_persistence.py`

- [ ] **Step 1: Write failing tests for new repository methods**

Add to `tests/unit/test_persistence.py`:

```python
from tradebot.backtest.results import BacktestResult
from datetime import date
from decimal import Decimal


def test_save_backtest_run_with_json(repo):
    """save_backtest_run persists daily_snapshots and trades as JSON."""
    result = BacktestResult(
        strategy_name="test_strategy",
        start_date=date(2026, 3, 1),
        end_date=date(2026, 3, 5),
        starting_capital=Decimal("2500"),
        interval_minutes=15,
        ending_nav=Decimal("2550"),
        total_return_pct=Decimal("2.00"),
        max_drawdown_pct=Decimal("1.50"),
        total_trades=3,
        winning_trades=2,
        losing_trades=1,
        win_rate=Decimal("66.67"),
        avg_win=Decimal("40.00"),
        avg_loss=Decimal("30.00"),
        profit_factor=Decimal("2.67"),
        daily_snapshots=[{"date": "2026-03-03", "nav": "2520", "daily_pnl": "20", "drawdown": "0"}],
        trades=[{"date": "2026-03-03", "pnl": 20.0, "strategy": "test"}],
    )
    record = repo.save_backtest_run(result)
    assert record.id is not None
    assert record.daily_snapshots == result.daily_snapshots
    assert record.trades == result.trades


def test_get_backtest_run_by_id(repo):
    """get_backtest_run returns full record including JSON columns."""
    result = BacktestResult(
        strategy_name="test_strategy",
        start_date=date(2026, 3, 1),
        end_date=date(2026, 3, 5),
        starting_capital=Decimal("2500"),
        interval_minutes=15,
        ending_nav=Decimal("2550"),
        total_return_pct=Decimal("2.00"),
        max_drawdown_pct=Decimal("1.50"),
        total_trades=3,
        winning_trades=2,
        losing_trades=1,
        win_rate=Decimal("66.67"),
        avg_win=Decimal("40.00"),
        avg_loss=Decimal("30.00"),
        profit_factor=Decimal("2.67"),
        daily_snapshots=[{"date": "2026-03-03", "nav": "2520"}],
        trades=[{"pnl": 20.0}],
    )
    saved = repo.save_backtest_run(result)
    fetched = repo.get_backtest_run(saved.id)
    assert fetched is not None
    assert fetched.daily_snapshots == [{"date": "2026-03-03", "nav": "2520"}]
    assert fetched.trades == [{"pnl": 20.0}]


def test_get_backtest_run_not_found(repo):
    """get_backtest_run returns None for nonexistent ID."""
    assert repo.get_backtest_run(999) is None


def test_delete_backtest_run(repo):
    """delete_backtest_run removes the record."""
    result = BacktestResult(
        strategy_name="test_strategy",
        start_date=date(2026, 3, 1),
        end_date=date(2026, 3, 5),
        starting_capital=Decimal("2500"),
        interval_minutes=15,
        ending_nav=Decimal("2550"),
        total_return_pct=Decimal("2.00"),
        max_drawdown_pct=Decimal("1.50"),
        total_trades=3,
        winning_trades=2,
        losing_trades=1,
        win_rate=Decimal("66.67"),
        avg_win=Decimal("40.00"),
        avg_loss=Decimal("30.00"),
        profit_factor=Decimal("2.67"),
        daily_snapshots=[],
        trades=[],
    )
    saved = repo.save_backtest_run(result)
    deleted = repo.delete_backtest_run(saved.id)
    assert deleted is True
    assert repo.get_backtest_run(saved.id) is None


def test_delete_backtest_run_not_found(repo):
    """delete_backtest_run returns False for nonexistent ID."""
    assert repo.delete_backtest_run(999) is False


def test_get_backtest_runs_excludes_json(repo):
    """get_backtest_runs returns summary records (JSON columns are populated but that's fine for now)."""
    result = BacktestResult(
        strategy_name="test_strategy",
        start_date=date(2026, 3, 1),
        end_date=date(2026, 3, 5),
        starting_capital=Decimal("2500"),
        interval_minutes=15,
        ending_nav=Decimal("2550"),
        total_return_pct=Decimal("2.00"),
        max_drawdown_pct=Decimal("1.50"),
        total_trades=3,
        winning_trades=2,
        losing_trades=1,
        win_rate=Decimal("66.67"),
        avg_win=Decimal("40.00"),
        avg_loss=Decimal("30.00"),
        profit_factor=Decimal("2.67"),
        daily_snapshots=[{"date": "2026-03-03"}],
        trades=[{"pnl": 20.0}],
    )
    repo.save_backtest_run(result)
    runs = repo.get_backtest_runs(limit=10)
    assert len(runs) == 1
    assert runs[0].strategy_name == "test_strategy"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_persistence.py -v -k "backtest"`
Expected: FAIL — `daily_snapshots` and `trades` columns don't exist on model, `get_backtest_run` and `delete_backtest_run` methods don't exist.

- [ ] **Step 3: Add JSON columns to BacktestRunRecord model**

In `src/tradebot/persistence/models.py`, add the `JSON` import and two new columns to `BacktestRunRecord`:

```python
from sqlalchemy import Date, DateTime, Integer, JSON, Numeric, String, ForeignKey
```

Add after the `created_at` column in `BacktestRunRecord`:

```python
    daily_snapshots: Mapped[list | None] = mapped_column(JSON, nullable=True)
    trades: Mapped[list | None] = mapped_column(JSON, nullable=True)
```

- [ ] **Step 4: Update repository methods**

In `src/tradebot/persistence/repository.py`, update `save_backtest_run` to include JSON fields, and add `get_backtest_run` and `delete_backtest_run`:

Update `save_backtest_run`:
```python
    def save_backtest_run(self, result) -> BacktestRunRecord:
        """Save a backtest run summary with daily snapshots and trades."""
        record = BacktestRunRecord(
            strategy_name=result.strategy_name,
            start_date=result.start_date,
            end_date=result.end_date,
            starting_capital=result.starting_capital,
            interval_minutes=result.interval_minutes,
            ending_nav=result.ending_nav,
            total_return_pct=result.total_return_pct,
            max_drawdown_pct=result.max_drawdown_pct,
            total_trades=result.total_trades,
            win_rate=result.win_rate,
            profit_factor=result.profit_factor,
            daily_snapshots=result.daily_snapshots,
            trades=result.trades,
        )
        self._session.add(record)
        self._session.flush()
        return record
```

Add new methods:
```python
    def get_backtest_run(self, run_id: int) -> BacktestRunRecord | None:
        """Get a single backtest run by ID."""
        return self._session.get(BacktestRunRecord, run_id)

    def delete_backtest_run(self, run_id: int) -> bool:
        """Delete a backtest run. Returns True if found and deleted."""
        record = self._session.get(BacktestRunRecord, run_id)
        if record is None:
            return False
        self._session.delete(record)
        self._session.flush()
        return True
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_persistence.py -v -k "backtest"`
Expected: All 6 new tests PASS.

- [ ] **Step 6: Create Alembic migration**

Run: `cd /home/ian/code/tradebot && uv run alembic revision --autogenerate -m "add json columns to backtest_runs"`

Verify the generated migration adds `daily_snapshots` and `trades` columns.

- [ ] **Step 7: Commit**

```bash
git add src/tradebot/persistence/models.py src/tradebot/persistence/repository.py tests/unit/test_persistence.py alembic/versions/
git commit -m "feat: add JSON columns to backtest_runs for snapshots and trades"
```

---

### Task 2: Backtest API Router — Strategy Listing and Run Endpoint

**Files:**
- Create: `src/tradebot/api/routes/backtest.py`
- Modify: `src/tradebot/api/app.py:31-37`
- Test: `tests/unit/test_api.py`

- [ ] **Step 1: Write failing tests for the strategies listing endpoint**

Add to `tests/unit/test_api.py`:

```python
def test_backtest_strategies_endpoint(client):
    """GET /api/backtest/strategies returns available strategy configs."""
    response = client.get("/api/backtest/strategies")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    strat = data[0]
    assert "name" in strat
    assert "filename" in strat
    assert "config" in strat
    assert "entry" in strat["config"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_api.py::test_backtest_strategies_endpoint -v`
Expected: FAIL — 404, route not registered.

- [ ] **Step 3: Create the backtest router with strategies endpoint**

Create `src/tradebot/api/routes/backtest.py`:

```python
"""Backtest API routes."""
import tempfile
from datetime import date
from decimal import Decimal
from pathlib import Path

import yaml
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, field_validator

router = APIRouter(prefix="/backtest", tags=["backtest"])

STRATEGIES_DIR = Path(__file__).resolve().parents[3] / "config" / "strategies"


@router.get("/strategies")
async def list_strategies():
    """List available strategy configs with their full YAML structure."""
    strategies = []
    for path in sorted(STRATEGIES_DIR.glob("*.yaml")):
        with open(path) as f:
            config = yaml.safe_load(f)
        strategies.append({
            "name": path.stem,
            "filename": path.name,
            "config": config,
        })
    return strategies
```

- [ ] **Step 4: Register the router in app.py**

In `src/tradebot/api/app.py`, add the import and include:

```python
    from tradebot.api.routes import portfolio, trades, strategies, kill_switch, backtest

    # ... existing includes ...
    app.include_router(backtest.router, prefix="/api")
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_api.py::test_backtest_strategies_endpoint -v`
Expected: PASS.

- [ ] **Step 6: Write failing tests for the run endpoint**

Add to `tests/unit/test_api.py`:

```python
def test_backtest_run_endpoint(client_with_repo):
    """POST /api/backtest/run executes a backtest and returns results."""
    response = client_with_repo.post("/api/backtest/run", json={
        "strategy": "xsp_iron_condor",
        "start_date": "2026-03-02",
        "end_date": "2026-03-03",
        "starting_capital": 2500,
        "slippage_pct": 0,
        "interval_minutes": 15,
        "save": False,
    })
    assert response.status_code == 200
    data = response.json()
    assert "strategy_name" in data
    assert "total_return_pct" in data
    assert "daily_snapshots" in data
    assert "trades" in data


def test_backtest_run_date_range_too_large(client_with_repo):
    """POST /api/backtest/run rejects date ranges over 30 days."""
    response = client_with_repo.post("/api/backtest/run", json={
        "strategy": "xsp_iron_condor",
        "start_date": "2026-01-01",
        "end_date": "2026-03-15",
        "starting_capital": 2500,
    })
    assert response.status_code == 422


def test_backtest_run_invalid_dates(client_with_repo):
    """POST /api/backtest/run rejects start >= end."""
    response = client_with_repo.post("/api/backtest/run", json={
        "strategy": "xsp_iron_condor",
        "start_date": "2026-03-10",
        "end_date": "2026-03-05",
        "starting_capital": 2500,
    })
    assert response.status_code == 422


def test_backtest_run_invalid_strategy(client_with_repo):
    """POST /api/backtest/run rejects nonexistent strategy."""
    response = client_with_repo.post("/api/backtest/run", json={
        "strategy": "nonexistent_strategy",
        "start_date": "2026-03-02",
        "end_date": "2026-03-03",
        "starting_capital": 2500,
    })
    assert response.status_code == 422


def test_backtest_run_with_save(client_with_repo):
    """POST /api/backtest/run with save=true persists the run."""
    response = client_with_repo.post("/api/backtest/run", json={
        "strategy": "xsp_iron_condor",
        "start_date": "2026-03-02",
        "end_date": "2026-03-03",
        "starting_capital": 2500,
        "save": True,
    })
    assert response.status_code == 200
    # Verify it was saved
    runs_response = client_with_repo.get("/api/backtest/runs")
    assert runs_response.status_code == 200
    assert len(runs_response.json()) == 1


def test_backtest_run_with_overrides(client_with_repo):
    """POST /api/backtest/run applies strategy overrides."""
    response = client_with_repo.post("/api/backtest/run", json={
        "strategy": "xsp_iron_condor",
        "start_date": "2026-03-02",
        "end_date": "2026-03-03",
        "starting_capital": 2500,
        "overrides": {
            "entry.strike_selection.short_call_delta": 0.10,
        },
    })
    assert response.status_code == 200


def test_backtest_run_invalid_override_key(client_with_repo):
    """POST /api/backtest/run rejects unknown override keys."""
    response = client_with_repo.post("/api/backtest/run", json={
        "strategy": "xsp_iron_condor",
        "start_date": "2026-03-02",
        "end_date": "2026-03-03",
        "starting_capital": 2500,
        "overrides": {
            "nonexistent.path.key": 42,
        },
    })
    assert response.status_code == 422
```

- [ ] **Step 7: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_api.py -v -k "backtest_run"`
Expected: FAIL — run endpoint not implemented.

- [ ] **Step 8: Implement the run endpoint with validation and override logic**

Add to `src/tradebot/api/routes/backtest.py`:

```python
class BacktestRequest(BaseModel):
    strategy: str
    start_date: date
    end_date: date
    starting_capital: float = 2500
    slippage_pct: float = 0
    interval_minutes: int = 15
    save: bool = False
    overrides: dict[str, float | int | str | bool] | None = None

    @field_validator("starting_capital")
    @classmethod
    def capital_min(cls, v: float) -> float:
        if v < 100:
            raise ValueError("Starting capital must be at least $100")
        return v

    @field_validator("slippage_pct")
    @classmethod
    def slippage_range(cls, v: float) -> float:
        if not 0 <= v <= 5:
            raise ValueError("Slippage must be between 0% and 5%")
        return v


def _apply_overrides(config: dict, overrides: dict[str, float | int | str | bool]) -> None:
    """Apply dot-notation overrides to a config dict. Raises ValueError for unknown paths."""
    for key, value in overrides.items():
        parts = key.split(".")
        target = config
        for part in parts[:-1]:
            if not isinstance(target, dict) or part not in target:
                raise ValueError(f"Unknown override path: {key}")
            target = target[part]
        if not isinstance(target, dict) or parts[-1] not in target:
            raise ValueError(f"Unknown override path: {key}")
        target[parts[-1]] = value


@router.post("/run")
async def run_backtest_endpoint(req: BacktestRequest, request: Request):
    """Run a backtest synchronously and return results."""
    from tradebot.backtest.engine import run_backtest

    # Validate dates
    if req.start_date >= req.end_date:
        raise HTTPException(status_code=422, detail="start_date must be before end_date")
    if (req.end_date - req.start_date).days > 30:
        raise HTTPException(status_code=422, detail="Date range cannot exceed 30 days")

    # Find strategy config
    config_path = STRATEGIES_DIR / f"{req.strategy}.yaml"
    if not config_path.exists():
        raise HTTPException(status_code=422, detail=f"Strategy not found: {req.strategy}")

    # Apply overrides if provided
    if req.overrides:
        with open(config_path) as f:
            config = yaml.safe_load(f)
        try:
            _apply_overrides(config, req.overrides)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))
        # Write patched config to temp file
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
        yaml.dump(config, tmp)
        tmp.close()
        config_path = Path(tmp.name)

    # Run the backtest
    result = await run_backtest(
        strategy_config_path=config_path,
        start_date=req.start_date,
        end_date=req.end_date,
        interval_minutes=req.interval_minutes,
        starting_capital=Decimal(str(req.starting_capital)),
        slippage_pct=Decimal(str(req.slippage_pct)),
    )

    # Save if requested
    state = request.app.state.app_state
    run_id = None
    if req.save and state.repository:
        record = state.repository.save_backtest_run(result)
        state.repository.commit()
        run_id = record.id

    return {
        "id": run_id,
        "strategy_name": result.strategy_name,
        "start_date": result.start_date.isoformat(),
        "end_date": result.end_date.isoformat(),
        "starting_capital": str(result.starting_capital),
        "interval_minutes": result.interval_minutes,
        "ending_nav": str(result.ending_nav),
        "total_return_pct": str(result.total_return_pct),
        "max_drawdown_pct": str(result.max_drawdown_pct),
        "total_trades": result.total_trades,
        "winning_trades": result.winning_trades,
        "losing_trades": result.losing_trades,
        "win_rate": str(result.win_rate),
        "avg_win": str(result.avg_win),
        "avg_loss": str(result.avg_loss),
        "profit_factor": str(result.profit_factor),
        "daily_snapshots": result.daily_snapshots,
        "trades": result.trades,
    }
```

- [ ] **Step 9: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_api.py -v -k "backtest"`
Expected: All backtest tests PASS.

- [ ] **Step 10: Commit**

```bash
git add src/tradebot/api/routes/backtest.py src/tradebot/api/app.py tests/unit/test_api.py
git commit -m "feat: add backtest API router with run and strategies endpoints"
```

---

### Task 3: Backtest API Router — History Endpoints

**Files:**
- Modify: `src/tradebot/api/routes/backtest.py`
- Test: `tests/unit/test_api.py`

- [ ] **Step 1: Write failing tests for history endpoints**

Add to `tests/unit/test_api.py`:

```python
def test_backtest_runs_endpoint(client_with_repo):
    """GET /api/backtest/runs returns saved runs."""
    # Run and save a backtest first
    client_with_repo.post("/api/backtest/run", json={
        "strategy": "xsp_iron_condor",
        "start_date": "2026-03-02",
        "end_date": "2026-03-03",
        "starting_capital": 2500,
        "save": True,
    })
    response = client_with_repo.get("/api/backtest/runs")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert "id" in data[0]
    assert "strategy_name" in data[0]
    assert "total_return_pct" in data[0]


def test_backtest_run_detail_endpoint(client_with_repo):
    """GET /api/backtest/runs/{id} returns full run with snapshots and trades."""
    run_response = client_with_repo.post("/api/backtest/run", json={
        "strategy": "xsp_iron_condor",
        "start_date": "2026-03-02",
        "end_date": "2026-03-03",
        "starting_capital": 2500,
        "save": True,
    })
    run_id = run_response.json()["id"]
    response = client_with_repo.get(f"/api/backtest/runs/{run_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == run_id
    assert "daily_snapshots" in data
    assert "trades" in data


def test_backtest_run_detail_not_found(client_with_repo):
    """GET /api/backtest/runs/{id} returns 404 for nonexistent run."""
    response = client_with_repo.get("/api/backtest/runs/999")
    assert response.status_code == 404


def test_backtest_run_delete_endpoint(client_with_repo):
    """DELETE /api/backtest/runs/{id} removes the run."""
    run_response = client_with_repo.post("/api/backtest/run", json={
        "strategy": "xsp_iron_condor",
        "start_date": "2026-03-02",
        "end_date": "2026-03-03",
        "starting_capital": 2500,
        "save": True,
    })
    run_id = run_response.json()["id"]
    delete_response = client_with_repo.delete(f"/api/backtest/runs/{run_id}")
    assert delete_response.status_code == 200
    # Verify it's gone
    get_response = client_with_repo.get(f"/api/backtest/runs/{run_id}")
    assert get_response.status_code == 404


def test_backtest_run_delete_not_found(client_with_repo):
    """DELETE /api/backtest/runs/{id} returns 404 for nonexistent run."""
    response = client_with_repo.delete("/api/backtest/runs/999")
    assert response.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_api.py -v -k "backtest_run_detail or backtest_runs_endpoint or backtest_run_delete"`
Expected: FAIL — endpoints not implemented.

- [ ] **Step 3: Implement history endpoints**

Add to `src/tradebot/api/routes/backtest.py`:

```python
@router.get("/runs")
async def list_runs(request: Request, limit: int = 20):
    """List saved backtest runs."""
    state = request.app.state.app_state
    if not state.repository:
        return []
    runs = state.repository.get_backtest_runs(limit=limit)
    return [
        {
            "id": r.id,
            "strategy_name": r.strategy_name,
            "start_date": r.start_date.isoformat(),
            "end_date": r.end_date.isoformat(),
            "starting_capital": str(r.starting_capital),
            "total_return_pct": str(r.total_return_pct),
            "max_drawdown_pct": str(r.max_drawdown_pct),
            "total_trades": r.total_trades,
            "win_rate": str(r.win_rate),
            "profit_factor": str(r.profit_factor),
            "created_at": r.created_at.isoformat(),
        }
        for r in runs
    ]


@router.get("/runs/{run_id}")
async def get_run(run_id: int, request: Request):
    """Get a single backtest run with full details."""
    state = request.app.state.app_state
    if not state.repository:
        raise HTTPException(status_code=404, detail="No repository configured")
    record = state.repository.get_backtest_run(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Backtest run not found")
    return {
        "id": record.id,
        "strategy_name": record.strategy_name,
        "start_date": record.start_date.isoformat(),
        "end_date": record.end_date.isoformat(),
        "starting_capital": str(record.starting_capital),
        "interval_minutes": record.interval_minutes,
        "ending_nav": str(record.ending_nav),
        "total_return_pct": str(record.total_return_pct),
        "max_drawdown_pct": str(record.max_drawdown_pct),
        "total_trades": record.total_trades,
        "win_rate": str(record.win_rate),
        "profit_factor": str(record.profit_factor),
        "daily_snapshots": record.daily_snapshots or [],
        "trades": record.trades or [],
        "created_at": record.created_at.isoformat(),
    }


@router.delete("/runs/{run_id}")
async def delete_run(run_id: int, request: Request):
    """Delete a backtest run."""
    state = request.app.state.app_state
    if not state.repository:
        raise HTTPException(status_code=404, detail="No repository configured")
    deleted = state.repository.delete_backtest_run(run_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Backtest run not found")
    state.repository.commit()
    return {"deleted": True}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_api.py -v -k "backtest"`
Expected: All backtest tests PASS.

- [ ] **Step 5: Run full test suite**

Run: `uv run pytest tests/unit/ -v`
Expected: All tests PASS (no regressions).

- [ ] **Step 6: Commit**

```bash
git add src/tradebot/api/routes/backtest.py tests/unit/test_api.py
git commit -m "feat: add backtest history API endpoints (list, detail, delete)"
```

---

### Task 4: Frontend — Strategies Page Tabs and Backtest Runner Form

**Files:**
- Modify: `frontend/src/pages/Strategies.tsx`
- Create: `frontend/src/components/backtest/BacktestRunner.tsx`
- Create: `frontend/src/components/backtest/StrategyOverrides.tsx`

- [ ] **Step 1: Create the StrategyOverrides component**

Create `frontend/src/components/backtest/StrategyOverrides.tsx`:

```tsx
import { useState } from "react";

interface StrategyOverridesProps {
  config: Record<string, unknown>;
  overrides: Record<string, number | string>;
  onChange: (overrides: Record<string, number | string>) => void;
}

/** Flattens a nested config object into dot-notation paths with leaf values. */
function flattenConfig(
  obj: Record<string, unknown>,
  prefix = ""
): { path: string; value: unknown }[] {
  const entries: { path: string; value: unknown }[] = [];
  for (const [key, value] of Object.entries(obj)) {
    const path = prefix ? `${prefix}.${key}` : key;
    if (
      value !== null &&
      typeof value === "object" &&
      !Array.isArray(value)
    ) {
      entries.push(
        ...flattenConfig(value as Record<string, unknown>, path)
      );
    } else {
      entries.push({ path, value });
    }
  }
  return entries;
}

/** Sections we allow overriding (skip strategy metadata and market). */
const OVERRIDE_SECTIONS = ["entry", "exit", "position_sizing", "risk"];

export default function StrategyOverrides({
  config,
  overrides,
  onChange,
}: StrategyOverridesProps) {
  const [expanded, setExpanded] = useState(false);

  const fields = flattenConfig(config).filter((f) =>
    OVERRIDE_SECTIONS.some((s) => f.path.startsWith(s))
  );

  const handleChange = (path: string, raw: string) => {
    const next = { ...overrides };
    if (raw === "") {
      delete next[path];
    } else {
      const num = Number(raw);
      next[path] = isNaN(num) ? raw : num;
    }
    onChange(next);
  };

  return (
    <div className="border border-gray-700 rounded-lg">
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-3 py-2 text-sm text-gray-300 hover:text-white"
      >
        <span>Strategy Overrides</span>
        <span>{expanded ? "▲" : "▼"}</span>
      </button>
      {expanded && (
        <div className="px-3 pb-3 space-y-2">
          {fields.map(({ path, value }) => (
            <div key={path} className="flex items-center gap-2">
              <label className="text-xs text-gray-400 w-56 truncate" title={path}>
                {path}
              </label>
              <input
                type="text"
                placeholder={String(value)}
                value={overrides[path] ?? ""}
                onChange={(e) => handleChange(path, e.target.value)}
                className="flex-1 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-sm text-white placeholder-gray-600"
              />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Create the BacktestRunner component**

Create `frontend/src/components/backtest/BacktestRunner.tsx`:

```tsx
import { useState, useEffect } from "react";
import { useApi } from "../../hooks/useApi";
import StrategyOverrides from "./StrategyOverrides";
import BacktestResults from "./BacktestResults";

interface StrategyConfig {
  name: string;
  filename: string;
  config: Record<string, unknown>;
}

interface BacktestResultData {
  id: number | null;
  strategy_name: string;
  start_date: string;
  end_date: string;
  starting_capital: string;
  interval_minutes: number;
  ending_nav: string;
  total_return_pct: string;
  max_drawdown_pct: string;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: string;
  avg_win: string;
  avg_loss: string;
  profit_factor: string;
  daily_snapshots: { date: string; nav: string; daily_pnl: string; drawdown: string }[];
  trades: { date: string; strategy: string; symbol: string; spread_type: string; entry_price: string; pnl: number }[];
}

export default function BacktestRunner() {
  const { data: strategies } = useApi<StrategyConfig[]>("/api/backtest/strategies");

  const [selectedStrategy, setSelectedStrategy] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [capital, setCapital] = useState("2500");
  const [slippage, setSlippage] = useState("0");
  const [interval, setInterval] = useState("15");
  const [save, setSave] = useState(true);
  const [overrides, setOverrides] = useState<Record<string, number | string>>({});

  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<BacktestResultData | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Select first strategy when loaded
  useEffect(() => {
    if (strategies && strategies.length > 0 && !selectedStrategy) {
      setSelectedStrategy(strategies[0].name);
    }
  }, [strategies, selectedStrategy]);

  const selectedConfig = strategies?.find((s) => s.name === selectedStrategy)?.config;

  const handleRun = async () => {
    setRunning(true);
    setError(null);
    setResult(null);

    const cleanOverrides: Record<string, number | string> = {};
    for (const [k, v] of Object.entries(overrides)) {
      if (v !== "") cleanOverrides[k] = v;
    }

    try {
      const response = await fetch("/api/backtest/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          strategy: selectedStrategy,
          start_date: startDate,
          end_date: endDate,
          starting_capital: parseFloat(capital),
          slippage_pct: parseFloat(slippage),
          interval_minutes: parseInt(interval),
          save,
          overrides: Object.keys(cleanOverrides).length > 0 ? cleanOverrides : undefined,
        }),
      });
      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || `Error ${response.status}`);
      }
      const data: BacktestResultData = await response.json();
      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setRunning(false);
    }
  };

  const canRun = selectedStrategy && startDate && endDate && !running;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Config Form */}
      <div className="space-y-4">
        <h3 className="font-semibold text-gray-200">Configuration</h3>

        <div>
          <label className="block text-sm text-gray-400 mb-1">Strategy</label>
          <select
            value={selectedStrategy}
            onChange={(e) => {
              setSelectedStrategy(e.target.value);
              setOverrides({});
            }}
            className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
          >
            {strategies?.map((s) => (
              <option key={s.name} value={s.name}>{s.name}</option>
            ))}
          </select>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-sm text-gray-400 mb-1">Start Date</label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">End Date</label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
            />
          </div>
        </div>

        <div className="grid grid-cols-3 gap-3">
          <div>
            <label className="block text-sm text-gray-400 mb-1">Capital ($)</label>
            <input
              type="number"
              value={capital}
              onChange={(e) => setCapital(e.target.value)}
              min="100"
              className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">Slippage %</label>
            <input
              type="number"
              value={slippage}
              onChange={(e) => setSlippage(e.target.value)}
              min="0"
              max="5"
              step="0.1"
              className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">Interval (min)</label>
            <input
              type="number"
              value={interval}
              onChange={(e) => setInterval(e.target.value)}
              min="1"
              className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
            />
          </div>
        </div>

        {selectedConfig && (
          <StrategyOverrides
            config={selectedConfig}
            overrides={overrides}
            onChange={setOverrides}
          />
        )}

        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-gray-400">
            <input
              type="checkbox"
              checked={save}
              onChange={(e) => setSave(e.target.checked)}
              className="rounded"
            />
            Save to history
          </label>
        </div>

        <button
          onClick={handleRun}
          disabled={!canRun}
          className={`w-full py-2 rounded font-medium ${
            canRun
              ? "bg-green-600 hover:bg-green-500 text-white"
              : "bg-gray-700 text-gray-500 cursor-not-allowed"
          }`}
        >
          {running ? "Running..." : "Run Backtest"}
        </button>

        {error && (
          <div className="bg-red-900/50 border border-red-700 rounded p-3 text-sm text-red-300">
            {error}
          </div>
        )}
      </div>

      {/* Results */}
      <div className="lg:col-span-2">
        {running && (
          <div className="flex items-center justify-center h-64 text-gray-400">
            <div className="text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-400 mx-auto mb-3"></div>
              <p>Running backtest...</p>
            </div>
          </div>
        )}
        {!running && result && <BacktestResults result={result} />}
        {!running && !result && !error && (
          <div className="flex items-center justify-center h-64 text-gray-500">
            Configure and run a backtest to see results here.
          </div>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Add tabs to the Strategies page**

Replace `frontend/src/pages/Strategies.tsx` with:

```tsx
import { useState } from "react";
import { useApi } from "../hooks/useApi";
import BacktestRunner from "../components/backtest/BacktestRunner";
import BacktestHistory from "../components/backtest/BacktestHistory";

interface Strategy {
  name: string;
  symbol: string;
  type: string;
  has_position: boolean;
}

type Tab = "overview" | "backtest";
type BacktestSubView = "run" | "history";

function StrategiesOverview() {
  const { data: strategies, loading } = useApi<Strategy[]>(
    "/api/strategies",
    10000
  );

  if (loading)
    return <div className="text-gray-400">Loading strategies...</div>;

  return (
    <div>
      {!strategies || strategies.length === 0 ? (
        <div className="text-gray-500 bg-gray-900 border border-gray-800 rounded-lg p-8 text-center">
          No strategies loaded
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {strategies.map((s) => (
            <div
              key={s.name}
              className="bg-gray-900 border border-gray-800 rounded-lg p-4"
            >
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-semibold">{s.name}</h3>
                <span
                  className={`px-2 py-0.5 rounded text-xs ${
                    s.has_position
                      ? "bg-blue-900 text-blue-300"
                      : "bg-gray-700 text-gray-300"
                  }`}
                >
                  {s.has_position ? "In Position" : "Watching"}
                </span>
              </div>
              <div className="text-sm text-gray-400 space-y-1">
                <div>
                  Symbol: <span className="text-gray-200 font-mono">{s.symbol}</span>
                </div>
                <div>
                  Type: <span className="text-gray-200">{s.type}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function Strategies() {
  const [tab, setTab] = useState<Tab>("overview");
  const [backtestView, setBacktestView] = useState<BacktestSubView>("run");

  return (
    <div>
      {/* Tab navigation */}
      <div className="flex items-center gap-6 mb-6 border-b border-gray-800">
        <button
          onClick={() => setTab("overview")}
          className={`pb-2 text-sm font-medium border-b-2 ${
            tab === "overview"
              ? "border-green-400 text-white"
              : "border-transparent text-gray-400 hover:text-gray-200"
          }`}
        >
          Overview
        </button>
        <button
          onClick={() => setTab("backtest")}
          className={`pb-2 text-sm font-medium border-b-2 ${
            tab === "backtest"
              ? "border-green-400 text-white"
              : "border-transparent text-gray-400 hover:text-gray-200"
          }`}
        >
          Backtest
        </button>
      </div>

      {tab === "overview" && <StrategiesOverview />}

      {tab === "backtest" && (
        <div>
          {/* Sub-view toggle */}
          <div className="flex items-center gap-4 mb-4">
            <button
              onClick={() => setBacktestView("run")}
              className={`px-3 py-1 rounded text-sm ${
                backtestView === "run"
                  ? "bg-gray-700 text-white"
                  : "text-gray-400 hover:text-white"
              }`}
            >
              Run
            </button>
            <button
              onClick={() => setBacktestView("history")}
              className={`px-3 py-1 rounded text-sm ${
                backtestView === "history"
                  ? "bg-gray-700 text-white"
                  : "text-gray-400 hover:text-white"
              }`}
            >
              History
            </button>
          </div>

          {backtestView === "run" && <BacktestRunner />}
          {backtestView === "history" && <BacktestHistory />}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Verify frontend compiles**

Run: `cd /home/ian/code/tradebot/frontend && npm run build`
Expected: Build succeeds (BacktestResults and BacktestHistory don't exist yet — create empty placeholders first if needed for the build to pass, or defer this check to after Task 5).

Note: If the build fails due to missing BacktestResults/BacktestHistory, create minimal placeholder components:

`frontend/src/components/backtest/BacktestResults.tsx`:
```tsx
export default function BacktestResults({ result }: { result: unknown }) {
  return <div className="text-gray-400">Results placeholder</div>;
}
```

`frontend/src/components/backtest/BacktestHistory.tsx`:
```tsx
export default function BacktestHistory() {
  return <div className="text-gray-400">History placeholder</div>;
}
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Strategies.tsx frontend/src/components/backtest/
git commit -m "feat: add backtest tab to strategies page with runner form"
```

---

### Task 5: Frontend — BacktestResults Component

**Files:**
- Create: `frontend/src/components/backtest/BacktestResults.tsx` (replace placeholder if created)

- [ ] **Step 1: Implement BacktestResults with metrics, chart, and trade log**

Create/replace `frontend/src/components/backtest/BacktestResults.tsx`:

```tsx
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

interface DailySnapshot {
  date: string;
  nav: string;
  daily_pnl: string;
  drawdown: string;
}

interface Trade {
  date: string;
  strategy: string;
  symbol: string;
  spread_type: string;
  entry_price: string;
  pnl: number;
}

interface BacktestResultData {
  strategy_name: string;
  start_date: string;
  end_date: string;
  starting_capital: string;
  ending_nav: string;
  total_return_pct: string;
  max_drawdown_pct: string;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: string;
  avg_win: string;
  avg_loss: string;
  profit_factor: string;
  daily_snapshots: DailySnapshot[];
  trades: Trade[];
}

function MetricCard({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg p-3">
      <div className="text-xs text-gray-400">{label}</div>
      <div className={`text-lg font-semibold ${color || "text-white"}`}>{value}</div>
    </div>
  );
}

export default function BacktestResults({ result }: { result: BacktestResultData }) {
  const returnPct = parseFloat(result.total_return_pct);
  const returnColor = returnPct >= 0 ? "text-green-400" : "text-red-400";

  const chartData = result.daily_snapshots.map((s) => ({
    date: new Date(s.date).toLocaleDateString("en-US", { month: "short", day: "numeric" }),
    nav: parseFloat(s.nav),
    drawdown: parseFloat(s.drawdown),
  }));

  return (
    <div className="space-y-6">
      {/* Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <MetricCard
          label="Total Return"
          value={`${returnPct >= 0 ? "+" : ""}${result.total_return_pct}%`}
          color={returnColor}
        />
        <MetricCard label="Max Drawdown" value={`-${result.max_drawdown_pct}%`} color="text-red-400" />
        <MetricCard label="Win Rate" value={`${result.win_rate}%`} />
        <MetricCard label="Profit Factor" value={result.profit_factor} />
        <MetricCard label="Total Trades" value={String(result.total_trades)} />
      </div>

      {/* Additional stats row */}
      <div className="grid grid-cols-4 gap-3">
        <MetricCard label="Starting Capital" value={`$${parseFloat(result.starting_capital).toFixed(2)}`} />
        <MetricCard label="Ending NAV" value={`$${parseFloat(result.ending_nav).toFixed(2)}`} />
        <MetricCard label="Avg Win" value={`$${result.avg_win}`} color="text-green-400" />
        <MetricCard label="Avg Loss" value={`$${result.avg_loss}`} color="text-red-400" />
      </div>

      {/* Equity Curve */}
      {chartData.length > 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
          <h4 className="text-sm font-medium text-gray-300 mb-3">Equity Curve</h4>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="date" stroke="#9ca3af" fontSize={12} />
              <YAxis
                yAxisId="nav"
                stroke="#4ade80"
                fontSize={12}
                tickFormatter={(v: number) => `$${v.toFixed(0)}`}
              />
              <YAxis
                yAxisId="dd"
                orientation="right"
                stroke="#f87171"
                fontSize={12}
                tickFormatter={(v: number) => `${v.toFixed(1)}%`}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#1f2937",
                  border: "1px solid #374151",
                  borderRadius: "0.5rem",
                  color: "#f3f4f6",
                }}
                formatter={(value: number, name: string) => {
                  if (name === "NAV") return [`$${value.toFixed(2)}`, name];
                  return [`${value.toFixed(2)}%`, name];
                }}
              />
              <Line yAxisId="nav" type="monotone" dataKey="nav" stroke="#4ade80" strokeWidth={2} dot={false} name="NAV" />
              <Line yAxisId="dd" type="monotone" dataKey="drawdown" stroke="#f87171" strokeWidth={1} dot={false} name="Drawdown" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Trade Log */}
      {result.trades.length > 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
          <h4 className="text-sm font-medium text-gray-300 mb-3">Trade Log</h4>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-gray-400 border-b border-gray-800">
                  <th className="text-left py-2 pr-4">Date</th>
                  <th className="text-left py-2 pr-4">Strategy</th>
                  <th className="text-left py-2 pr-4">Symbol</th>
                  <th className="text-left py-2 pr-4">Type</th>
                  <th className="text-right py-2 pr-4">Entry</th>
                  <th className="text-right py-2">P&L</th>
                </tr>
              </thead>
              <tbody>
                {result.trades.map((t, i) => (
                  <tr key={i} className="border-b border-gray-800/50">
                    <td className="py-2 pr-4 text-gray-300">{t.date}</td>
                    <td className="py-2 pr-4 text-gray-300">{t.strategy}</td>
                    <td className="py-2 pr-4 font-mono text-gray-300">{t.symbol}</td>
                    <td className="py-2 pr-4 text-gray-300">{t.spread_type}</td>
                    <td className="py-2 pr-4 text-right text-gray-300">${t.entry_price}</td>
                    <td className={`py-2 text-right font-medium ${t.pnl >= 0 ? "text-green-400" : "text-red-400"}`}>
                      {t.pnl >= 0 ? "+" : ""}${t.pnl.toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Verify frontend compiles**

Run: `cd /home/ian/code/tradebot/frontend && npm run build`
Expected: Build succeeds (BacktestHistory placeholder still in place).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/backtest/BacktestResults.tsx
git commit -m "feat: add BacktestResults component with metrics, chart, and trade log"
```

---

### Task 6: Frontend — BacktestHistory and Comparison

**Files:**
- Create: `frontend/src/components/backtest/BacktestHistory.tsx` (replace placeholder)
- Create: `frontend/src/components/backtest/BacktestComparison.tsx`

- [ ] **Step 1: Create the BacktestComparison component**

Create `frontend/src/components/backtest/BacktestComparison.tsx`:

```tsx
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

interface RunDetail {
  id: number;
  strategy_name: string;
  start_date: string;
  end_date: string;
  starting_capital: string;
  ending_nav: string;
  total_return_pct: string;
  max_drawdown_pct: string;
  total_trades: number;
  win_rate: string;
  profit_factor: string;
  daily_snapshots: { date: string; nav: string }[];
}

const COLORS = ["#4ade80", "#60a5fa", "#f59e0b", "#f87171", "#a78bfa"];

export default function BacktestComparison({
  runs,
  onClose,
}: {
  runs: RunDetail[];
  onClose: () => void;
}) {
  // Merge equity curves: union of all dates, one NAV series per run
  const dateSet = new Set<string>();
  for (const run of runs) {
    for (const s of run.daily_snapshots) {
      dateSet.add(s.date);
    }
  }
  const dates = Array.from(dateSet).sort();

  const chartData = dates.map((d) => {
    const point: Record<string, string | number> = { date: d };
    for (const run of runs) {
      const snap = run.daily_snapshots.find((s) => s.date === d);
      if (snap) point[`run_${run.id}`] = parseFloat(snap.nav);
    }
    return point;
  });

  const metrics = ["total_return_pct", "max_drawdown_pct", "win_rate", "profit_factor", "total_trades"] as const;
  const metricLabels: Record<string, string> = {
    total_return_pct: "Return %",
    max_drawdown_pct: "Max DD %",
    win_rate: "Win Rate %",
    profit_factor: "Profit Factor",
    total_trades: "Trades",
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-gray-200">
          Comparing {runs.length} Runs
        </h3>
        <button
          onClick={onClose}
          className="text-sm text-gray-400 hover:text-white"
        >
          Close Comparison
        </button>
      </div>

      {/* Metrics table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-800">
              <th className="text-left py-2 pr-4 text-gray-400">Metric</th>
              {runs.map((r, i) => (
                <th
                  key={r.id}
                  className="text-right py-2 px-3"
                  style={{ color: COLORS[i % COLORS.length] }}
                >
                  Run #{r.id}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr className="border-b border-gray-800/50">
              <td className="py-2 pr-4 text-gray-400">Strategy</td>
              {runs.map((r) => (
                <td key={r.id} className="py-2 px-3 text-right text-gray-300">
                  {r.strategy_name}
                </td>
              ))}
            </tr>
            <tr className="border-b border-gray-800/50">
              <td className="py-2 pr-4 text-gray-400">Period</td>
              {runs.map((r) => (
                <td key={r.id} className="py-2 px-3 text-right text-gray-300">
                  {r.start_date} — {r.end_date}
                </td>
              ))}
            </tr>
            {metrics.map((m) => (
              <tr key={m} className="border-b border-gray-800/50">
                <td className="py-2 pr-4 text-gray-400">{metricLabels[m]}</td>
                {runs.map((r) => (
                  <td key={r.id} className="py-2 px-3 text-right text-gray-300">
                    {String(r[m])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Overlaid equity curves */}
      {chartData.length > 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
          <h4 className="text-sm font-medium text-gray-300 mb-3">
            Equity Curves
          </h4>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="date" stroke="#9ca3af" fontSize={12} />
              <YAxis
                stroke="#9ca3af"
                fontSize={12}
                tickFormatter={(v: number) => `$${v.toFixed(0)}`}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#1f2937",
                  border: "1px solid #374151",
                  borderRadius: "0.5rem",
                  color: "#f3f4f6",
                }}
                formatter={(value: number) => [`$${value.toFixed(2)}`, ""]}
              />
              <Legend />
              {runs.map((r, i) => (
                <Line
                  key={r.id}
                  type="monotone"
                  dataKey={`run_${r.id}`}
                  stroke={COLORS[i % COLORS.length]}
                  strokeWidth={2}
                  dot={false}
                  name={`#${r.id} ${r.strategy_name}`}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Implement BacktestHistory with selection and comparison**

Create/replace `frontend/src/components/backtest/BacktestHistory.tsx`:

```tsx
import { useState } from "react";
import { useApi } from "../../hooks/useApi";
import BacktestResults from "./BacktestResults";
import BacktestComparison from "./BacktestComparison";

interface RunSummary {
  id: number;
  strategy_name: string;
  start_date: string;
  end_date: string;
  starting_capital: string;
  total_return_pct: string;
  max_drawdown_pct: string;
  total_trades: number;
  win_rate: string;
  profit_factor: string;
  created_at: string;
}

interface RunDetail extends RunSummary {
  ending_nav: string;
  interval_minutes: number;
  winning_trades: number;
  losing_trades: number;
  avg_win: string;
  avg_loss: string;
  daily_snapshots: { date: string; nav: string; daily_pnl: string; drawdown: string }[];
  trades: { date: string; strategy: string; symbol: string; spread_type: string; entry_price: string; pnl: number }[];
}

export default function BacktestHistory() {
  const { data: runs, loading } = useApi<RunSummary[]>("/api/backtest/runs", 10000);

  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [expandedData, setExpandedData] = useState<RunDetail | null>(null);
  const [comparing, setComparing] = useState(false);
  const [comparisonRuns, setComparisonRuns] = useState<RunDetail[]>([]);
  const [loadingDetail, setLoadingDetail] = useState(false);

  const toggleSelect = (id: number) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleExpand = async (id: number) => {
    if (expandedId === id) {
      setExpandedId(null);
      setExpandedData(null);
      return;
    }
    setExpandedId(id);
    setLoadingDetail(true);
    try {
      const res = await fetch(`/api/backtest/runs/${id}`);
      const data: RunDetail = await res.json();
      setExpandedData(data);
    } finally {
      setLoadingDetail(false);
    }
  };

  const handleDelete = async (id: number) => {
    await fetch(`/api/backtest/runs/${id}`, { method: "DELETE" });
    if (expandedId === id) {
      setExpandedId(null);
      setExpandedData(null);
    }
    selected.delete(id);
    setSelected(new Set(selected));
    // Data will refresh via useApi polling
  };

  const handleCompare = async () => {
    setLoadingDetail(true);
    try {
      const details = await Promise.all(
        Array.from(selected).map(async (id) => {
          const res = await fetch(`/api/backtest/runs/${id}`);
          return res.json() as Promise<RunDetail>;
        })
      );
      setComparisonRuns(details);
      setComparing(true);
    } finally {
      setLoadingDetail(false);
    }
  };

  if (comparing && comparisonRuns.length > 0) {
    return (
      <BacktestComparison
        runs={comparisonRuns}
        onClose={() => {
          setComparing(false);
          setComparisonRuns([]);
        }}
      />
    );
  }

  if (loading) return <div className="text-gray-400">Loading history...</div>;

  if (!runs || runs.length === 0) {
    return (
      <div className="text-gray-500 bg-gray-900 border border-gray-800 rounded-lg p-8 text-center">
        No saved backtest runs yet. Run a backtest with "Save to history" enabled.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Toolbar */}
      <div className="flex items-center justify-between">
        <span className="text-sm text-gray-400">
          {selected.size} selected
        </span>
        <button
          onClick={handleCompare}
          disabled={selected.size < 2 || loadingDetail}
          className={`px-3 py-1 rounded text-sm ${
            selected.size >= 2
              ? "bg-blue-600 hover:bg-blue-500 text-white"
              : "bg-gray-700 text-gray-500 cursor-not-allowed"
          }`}
        >
          Compare Selected
        </button>
      </div>

      {/* Runs table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-gray-400 border-b border-gray-800">
              <th className="py-2 pr-2 w-8"></th>
              <th className="text-left py-2 pr-4">Strategy</th>
              <th className="text-left py-2 pr-4">Period</th>
              <th className="text-right py-2 pr-4">Return</th>
              <th className="text-right py-2 pr-4">Max DD</th>
              <th className="text-right py-2 pr-4">Win Rate</th>
              <th className="text-right py-2 pr-4">PF</th>
              <th className="text-right py-2 pr-4">Trades</th>
              <th className="text-right py-2">Actions</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((r) => {
              const ret = parseFloat(r.total_return_pct);
              return (
                <tr
                  key={r.id}
                  className={`border-b border-gray-800/50 cursor-pointer hover:bg-gray-800/50 ${
                    expandedId === r.id ? "bg-gray-800/30" : ""
                  }`}
                >
                  <td className="py-2 pr-2" onClick={(e) => e.stopPropagation()}>
                    <input
                      type="checkbox"
                      checked={selected.has(r.id)}
                      onChange={() => toggleSelect(r.id)}
                      className="rounded"
                    />
                  </td>
                  <td className="py-2 pr-4 text-gray-300" onClick={() => handleExpand(r.id)}>
                    {r.strategy_name}
                  </td>
                  <td className="py-2 pr-4 text-gray-400" onClick={() => handleExpand(r.id)}>
                    {r.start_date} — {r.end_date}
                  </td>
                  <td
                    className={`py-2 pr-4 text-right ${ret >= 0 ? "text-green-400" : "text-red-400"}`}
                    onClick={() => handleExpand(r.id)}
                  >
                    {ret >= 0 ? "+" : ""}{r.total_return_pct}%
                  </td>
                  <td className="py-2 pr-4 text-right text-red-400" onClick={() => handleExpand(r.id)}>
                    -{r.max_drawdown_pct}%
                  </td>
                  <td className="py-2 pr-4 text-right text-gray-300" onClick={() => handleExpand(r.id)}>
                    {r.win_rate}%
                  </td>
                  <td className="py-2 pr-4 text-right text-gray-300" onClick={() => handleExpand(r.id)}>
                    {r.profit_factor}
                  </td>
                  <td className="py-2 pr-4 text-right text-gray-300" onClick={() => handleExpand(r.id)}>
                    {r.total_trades}
                  </td>
                  <td className="py-2 text-right" onClick={(e) => e.stopPropagation()}>
                    <button
                      onClick={() => handleDelete(r.id)}
                      className="text-gray-500 hover:text-red-400 text-xs"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Expanded detail */}
      {expandedId && expandedData && (
        <div className="border border-gray-700 rounded-lg p-4">
          <BacktestResults result={expandedData} />
        </div>
      )}
      {expandedId && loadingDetail && !expandedData && (
        <div className="text-gray-400 text-center py-4">Loading details...</div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Verify frontend compiles**

Run: `cd /home/ian/code/tradebot/frontend && npm run build`
Expected: Build succeeds with no TypeScript errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/backtest/
git commit -m "feat: add BacktestHistory and BacktestComparison components"
```

---

### Task 7: Integration Testing and Final Verification

**Files:**
- No new files

- [ ] **Step 1: Run full backend test suite**

Run: `uv run pytest tests/unit/ -v`
Expected: All tests PASS.

- [ ] **Step 2: Run frontend build**

Run: `cd /home/ian/code/tradebot/frontend && npm run build`
Expected: Build succeeds.

- [ ] **Step 3: Run linter**

Run: `uv run ruff check src/`
Expected: No lint errors.

- [ ] **Step 4: Verify docker compose builds**

Run: `docker compose build`
Expected: Build succeeds.

- [ ] **Step 5: Commit any fixes**

If any issues were found in steps 1-4, fix them and commit:

```bash
git add -A
git commit -m "fix: address integration issues from final verification"
```
