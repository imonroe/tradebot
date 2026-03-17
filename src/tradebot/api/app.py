"""FastAPI application factory."""
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from tradebot.api.state import AppState


def create_app(state: AppState) -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(title="Tradebot API", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.state.app_state = state

    @app.get("/api/health")
    async def health():
        return {
            "status": "ok",
            "mode": state.mode,
            "bot_running": state.bot_running,
        }

    # Import and include route modules
    from tradebot.api.routes import portfolio, trades, strategies

    app.include_router(portfolio.router, prefix="/api")
    app.include_router(trades.router, prefix="/api")
    app.include_router(strategies.router, prefix="/api")

    # WebSocket
    from tradebot.api.websocket import ConnectionManager

    ws_manager = ConnectionManager()
    app.state.ws_manager = ws_manager

    @app.websocket("/api/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await ws_manager.connect(websocket)
        try:
            # Send initial state
            portfolio = state.portfolio
            await websocket.send_json({
                "type": "snapshot",
                "nav": str(portfolio.nav),
                "daily_pnl": str(portfolio.daily_pnl),
                "drawdown_pct": str(portfolio.drawdown_pct),
                "positions": len(portfolio.open_positions),
                "mode": state.mode,
                "bot_running": state.bot_running,
                "pdt_day_trades_used": state.pdt_day_trades_used,
            })
            # Keep connection alive, wait for disconnect
            while True:
                await websocket.receive_text()
        except Exception:
            ws_manager.disconnect(websocket)

    return app
