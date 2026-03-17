"""Tradier market data source for options chains and quotes."""
from datetime import date, datetime
from decimal import Decimal

import structlog

from tradebot.core.models import Bar, OptionsChain
from tradebot.execution.brokers.tradier import TradierBroker

logger = structlog.get_logger()


class TradierDataSource:
    """Fetches market data from Tradier API.

    Reuses the TradierBroker client since Tradier serves both
    trading and market data from the same API.
    """

    def __init__(self, broker: TradierBroker) -> None:
        self._broker = broker

    async def get_options_chain(self, symbol: str, expiration: date) -> OptionsChain:
        return await self._broker.get_options_chain(symbol, expiration)

    async def get_quote(self, symbol: str) -> Bar:
        """Get current quote as a Bar."""
        result = await self._broker._request(
            "GET", "/v1/markets/quotes", params={"symbols": symbol}
        )
        quote = result.get("quotes", {}).get("quote", {})
        return Bar(
            symbol=symbol,
            timestamp=datetime.now(),
            open=Decimal(str(quote.get("open", 0))),
            high=Decimal(str(quote.get("high", 0))),
            low=Decimal(str(quote.get("low", 0))),
            close=Decimal(str(quote.get("last", 0))),
            volume=quote.get("volume", 0),
        )
