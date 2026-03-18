"""Data source wrapper that records responses to JSON files."""
import dataclasses
import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import structlog

from tradebot.core.models import Bar, OptionsChain
from tradebot.data.sources.base import DataSource

logger = structlog.get_logger()


class _TradebotEncoder(json.JSONEncoder):
    """JSON encoder that handles Decimal, datetime, date, and enums."""

    def default(self, o):
        if isinstance(o, Decimal):
            return str(o)
        if isinstance(o, datetime):
            return o.isoformat()
        if isinstance(o, date):
            return o.isoformat()
        if hasattr(o, "value"):  # Enum
            return o.value
        return super().default(o)


class DataRecorder:
    """Wraps a DataSource and saves each response to a JSON file."""

    def __init__(self, source: DataSource, output_dir: Path = Path("data/recordings")) -> None:
        self._source = source
        self._output_dir = output_dir
        self._output_dir.mkdir(parents=True, exist_ok=True)

    async def get_quote(self, symbol: str) -> Bar:
        bar = await self._source.get_quote(symbol)
        self._save("quote", symbol, dataclasses.asdict(bar))
        return bar

    async def get_options_chain(self, symbol: str, expiration: date) -> OptionsChain:
        chain = await self._source.get_options_chain(symbol, expiration)
        self._save("chain", symbol, dataclasses.asdict(chain))
        return chain

    def _save(self, data_type: str, symbol: str, data: dict) -> None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"{symbol}_{data_type}_{timestamp}.json"
        filepath = self._output_dir / filename
        filepath.write_text(json.dumps(data, cls=_TradebotEncoder, indent=2))
        logger.debug("data_recorded", file=str(filepath))
