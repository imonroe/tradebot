"""Core domain models used across the trading system."""
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from tradebot.core.enums import OptionType, OrderSide, OrderStatus

@dataclass(frozen=True)
class Greeks:
    """Option Greeks snapshot."""
    delta: Decimal
    gamma: Decimal
    theta: Decimal
    vega: Decimal
    implied_volatility: Decimal

@dataclass(frozen=True)
class Bar:
    """OHLCV price bar."""
    symbol: str
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int

@dataclass(frozen=True)
class OptionContract:
    """A single option contract with quote and Greeks."""
    symbol: str
    underlying: str
    option_type: OptionType
    strike: Decimal
    expiration: date
    bid: Decimal
    ask: Decimal
    last: Decimal
    volume: int
    open_interest: int
    greeks: Greeks

    @property
    def mid_price(self) -> Decimal:
        return (self.bid + self.ask) / 2

@dataclass(frozen=True)
class OptionsChain:
    """Full options chain for a symbol and expiration."""
    underlying: str
    expiration: date
    underlying_price: Decimal
    calls: list[OptionContract] = field(default_factory=list)
    puts: list[OptionContract] = field(default_factory=list)

@dataclass(frozen=True)
class OrderLeg:
    """A single leg of an options order."""
    option_symbol: str
    side: OrderSide
    quantity: int

@dataclass(frozen=True)
class OrderResult:
    """Result of submitting an order to the broker."""
    broker_order_id: str
    status: OrderStatus

@dataclass
class Account:
    """Broker account info."""
    balance: Decimal
    buying_power: Decimal
    day_trade_count: int
