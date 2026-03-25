"""Shared application state between bot loop and API."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from tradebot.persistence.repository import Repository
from tradebot.portfolio.tracker import PortfolioTracker
from tradebot.strategy.base import TradingStrategy

if TYPE_CHECKING:
    from tradebot.api.websocket import ConnectionManager


@dataclass
class AppState:
    """Shared state accessible by both the bot loop and API routes."""

    portfolio: PortfolioTracker
    strategies: list[TradingStrategy] = field(default_factory=list)
    mode: str = "paper"
    bot_running: bool = False
    pdt_day_trades_used: int = 0
    kill_switch_active: bool = False
    kill_switch_reason: str | None = None
    repository: Repository | None = None
    ws_manager: "ConnectionManager | None" = None
