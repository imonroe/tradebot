"""Strategies API routes."""
from fastapi import APIRouter, Request

router = APIRouter(tags=["strategies"])


@router.get("/strategies")
async def get_strategies(request: Request):
    """Get loaded strategies and their status."""
    state = request.app.state.app_state
    return [
        {
            "name": s.name,
            "symbol": s.symbol,
            "type": type(s).__name__,
            "has_position": getattr(s, "_has_position", False),
        }
        for s in state.strategies
    ]
