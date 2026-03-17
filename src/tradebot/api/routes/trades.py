"""Trades API routes."""
from fastapi import APIRouter, Request

router = APIRouter(tags=["trades"])


@router.get("/trades")
async def get_trades(request: Request):
    """Get trade history."""
    state = request.app.state.app_state
    if state.repository is None:
        return []

    all_trades = state.repository.get_recent_trades(limit=100)

    return [
        {
            "id": t.id,
            "strategy": t.strategy,
            "symbol": t.symbol,
            "spread_type": t.spread_type,
            "entry_price": str(t.entry_price),
            "exit_price": str(t.exit_price) if t.exit_price else None,
            "pnl": str(t.pnl) if t.pnl else None,
            "status": t.status,
            "entry_time": t.entry_time.isoformat() if t.entry_time else None,
            "exit_time": t.exit_time.isoformat() if t.exit_time else None,
        }
        for t in all_trades
    ]
