"""Historical data source for backtesting."""
from datetime import date

from tradebot.backtest.clock import SimulatedClock
from tradebot.core.events import MarketEvent
from tradebot.core.models import Bar
from tradebot.data.sources.base import DataSource


class HistoricalDataSource:
    """Wraps a DataSource and stamps data with simulated time."""

    def __init__(self, source: DataSource, clock: SimulatedClock) -> None:
        self._source = source
        self._clock = clock

    async def get_market_event(self, symbol: str, expiration: date) -> MarketEvent:
        """Fetch data and return a MarketEvent with simulated timestamp."""
        bar = await self._source.get_quote(symbol)
        chain = await self._source.get_options_chain(symbol, expiration)

        timed_bar = Bar(
            symbol=bar.symbol,
            timestamp=self._clock.now(),
            open=bar.open,
            high=bar.high,
            low=bar.low,
            close=bar.close,
            volume=bar.volume,
        )

        return MarketEvent(
            bar=timed_bar,
            options_chain=chain,
            timestamp=self._clock.now(),
        )
