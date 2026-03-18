"""Abstract data source interface."""
from datetime import date
from typing import Protocol

from tradebot.core.models import Bar, OptionsChain


class DataSource(Protocol):
    async def get_quote(self, symbol: str) -> Bar: ...
    async def get_options_chain(self, symbol: str, expiration: date) -> OptionsChain: ...
