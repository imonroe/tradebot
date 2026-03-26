"""Backtest API routes."""
import tempfile
from datetime import date
from decimal import Decimal
from pathlib import Path

import yaml
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, field_validator

router = APIRouter(prefix="/backtest", tags=["backtest"])

STRATEGIES_DIR = Path(__file__).resolve().parents[4] / "config" / "strategies"


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


@router.get("/runs")
async def list_backtest_runs(request: Request):
    """List saved backtest runs."""
    state = request.app.state.app_state
    if not state.repository:
        return []
    runs = state.repository.get_backtest_runs()
    return [
        {
            "id": r.id,
            "strategy_name": r.strategy_name,
            "start_date": r.start_date.isoformat(),
            "end_date": r.end_date.isoformat(),
            "starting_capital": str(r.starting_capital),
            "total_return_pct": str(r.total_return_pct),
            "total_trades": r.total_trades,
            "win_rate": str(r.win_rate),
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in runs
    ]
