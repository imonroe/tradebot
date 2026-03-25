"""Portfolio API routes."""
from decimal import Decimal

from fastapi import APIRouter, Request

from tradebot.analytics.metrics import compute_trade_metrics, compute_sharpe_ratio

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


@router.get("/portfolio/analytics")
async def get_analytics(request: Request):
    """Get portfolio performance analytics from trade history and daily snapshots."""
    state = request.app.state.app_state
    if state.repository is None:
        metrics = compute_trade_metrics([])
        sharpe = Decimal("0")
        max_drawdown = Decimal("0")
    else:
        # Compute trade metrics from closed trades
        closed_trades = state.repository.get_closed_trades()
        trade_dicts = [{"pnl": t.pnl} for t in closed_trades if t.pnl is not None]
        metrics = compute_trade_metrics(trade_dicts)

        # Compute Sharpe ratio from daily NAV snapshots
        snapshots = state.repository.get_all_daily_snapshots()
        daily_navs = [s.nav for s in snapshots]
        sharpe = compute_sharpe_ratio(daily_navs)

        # Max drawdown from snapshots
        max_drawdown = Decimal("0")
        for s in snapshots:
            if s.drawdown > max_drawdown:
                max_drawdown = s.drawdown

    # Serialize Decimals to strings — consistent shape regardless of repo presence
    result = {}
    for k, v in metrics.items():
        result[k] = str(v) if isinstance(v, Decimal) else v
    result["sharpe_ratio"] = str(sharpe)
    result["max_drawdown_pct"] = str(max_drawdown)
    return result


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
