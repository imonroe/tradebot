"""Market data handler that orchestrates data sources and emits events."""
from datetime import date

import structlog

from tradebot.core.events import MarketEvent
from tradebot.data.sources.tradier import TradierDataSource

logger = structlog.get_logger()


class MarketDataHandler:
    """Fetches market data and produces MarketEvents."""

    def __init__(self, data_source: TradierDataSource) -> None:
        self._data_source = data_source

    async def fetch_market_data(self, symbol: str, expiration: date) -> MarketEvent:
        """Fetch current quote and options chain, return as MarketEvent."""
        logger.info("fetching_market_data", symbol=symbol, expiration=str(expiration))

        bar = await self._data_source.get_quote(symbol)
        chain = await self._data_source.get_options_chain(symbol, expiration)

        return MarketEvent(bar=bar, options_chain=chain)
