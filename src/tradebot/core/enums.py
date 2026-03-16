"""Core enumerations for the trading system."""
from enum import Enum

class OptionType(str, Enum):
    CALL = "call"
    PUT = "put"

class OrderSide(str, Enum):
    BUY_TO_OPEN = "buy_to_open"
    BUY_TO_CLOSE = "buy_to_close"
    SELL_TO_OPEN = "sell_to_open"
    SELL_TO_CLOSE = "sell_to_close"

class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    DEBIT = "debit"
    CREDIT = "credit"
    EVEN = "even"

class OrderStatus(str, Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"

class SpreadType(str, Enum):
    IRON_CONDOR = "iron_condor"
    CREDIT_SPREAD = "credit_spread"
    DEBIT_SPREAD = "debit_spread"

class TradeStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    EXPIRED = "expired"
