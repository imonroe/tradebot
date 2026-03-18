"""Portfolio API routes."""
from fastapi import APIRouter, Request

router = APIRouter(tags=["portfolio"])


@router.get("/portfolio")
async def get_portfolio(request: Request):
    """Get portfolio overview: NAV, P&L, drawdown."""
    state = request.app.state.app_state
    portfolio = state.portfolio
    return {
        "nav": str(portfolio.nav),
        "daily_pnl": str(portfolio.daily_pnl),
        "drawdown_pct": str(portfolio.drawdown_pct),
        "open_positions": [
            {
                "broker_order_id": p["broker_order_id"],
                "strategy": p["strategy"],
                "symbol": p["symbol"],
                "spread_type": p["spread_type"],
                "fill_price": str(p["fill_price"]),
                "timestamp": p["timestamp"].isoformat(),
            }
            for p in portfolio.open_positions
        ],
        "pdt_day_trades_used": state.pdt_day_trades_used,
        "mode": state.mode,
    }


@router.get("/portfolio/nav-history")
async def get_nav_history(request: Request, days: int = 30):
    """Get NAV history for chart display."""
    state = request.app.state.app_state
    if state.repository is None:
        return []
    return state.repository.get_nav_history(days=days)


@router.get("/portfolio/positions")
async def get_positions(request: Request):
    """Get open positions."""
    state = request.app.state.app_state
    return [
        {
            "broker_order_id": p["broker_order_id"],
            "strategy": p["strategy"],
            "symbol": p["symbol"],
            "spread_type": p["spread_type"],
            "fill_price": str(p["fill_price"]),
            "timestamp": p["timestamp"].isoformat(),
        }
        for p in state.portfolio.open_positions
    ]
