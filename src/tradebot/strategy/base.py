"""Abstract base class for trading strategies."""
from abc import ABC, abstractmethod

from tradebot.core.events import MarketEvent, SignalEvent


class TradingStrategy(ABC):
    """Base class all strategies must implement."""

    def __init__(self, name: str, symbol: str) -> None:
        self.name = name
        self.symbol = symbol

    @abstractmethod
    def evaluate(self, event: MarketEvent) -> list[SignalEvent]:
        """Evaluate market data and return zero or more signals."""
        ...

    def reset(self) -> None:
        """Reset state for a new trading day. Override if needed."""
        pass
