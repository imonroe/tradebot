"""Event types for the trading pipeline."""
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from tradebot.core.enums import OrderStatus, SpreadType
from tradebot.core.models import Bar, OptionsChain, OrderLeg

@dataclass(frozen=True)
class MarketEvent:
    bar: Bar
    options_chain: OptionsChain | None = None
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass(frozen=True)
class SignalEvent:
    strategy_name: str
    spread_type: SpreadType
    symbol: str
    legs: list[OrderLeg]
    target_price: Decimal
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass(frozen=True)
class OrderEvent:
    signal: SignalEvent
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass(frozen=True)
class FillEvent:
    broker_order_id: str
    signal: SignalEvent
    fill_price: Decimal
    status: OrderStatus
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass(frozen=True)
class RiskEvent:
    check_name: str
    passed: bool
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
