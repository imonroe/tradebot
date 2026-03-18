"""Strategy factory that loads strategies from config."""
from datetime import time
from decimal import Decimal
from pathlib import Path

from tradebot.strategy.base import TradingStrategy
from tradebot.strategy.strategies.credit_spread import CreditSpreadStrategy
from tradebot.strategy.strategies.debit_spread import DebitSpreadStrategy
from tradebot.strategy.strategies.iron_condor import IronCondorStrategy
from tradebot.utils.config import load_strategy_config

STRATEGY_CLASSES = {
    "IronCondorStrategy": IronCondorStrategy,
    "CreditSpreadStrategy": CreditSpreadStrategy,
    "DebitSpreadStrategy": DebitSpreadStrategy,
}


def load_strategy(config_path: Path) -> TradingStrategy:
    """Load a strategy from its YAML config file."""
    config = load_strategy_config(config_path)

    class_name = config.strategy.class_name
    if class_name not in STRATEGY_CLASSES:
        raise ValueError(f"Unknown strategy class: {class_name}")

    cls = STRATEGY_CLASSES[class_name]

    if cls is IronCondorStrategy:
        return IronCondorStrategy(
            name=config.strategy.name,
            symbol=config.market.symbol,
            short_call_delta=Decimal(str(config.entry.strike_selection.short_call_delta)),
            short_put_delta=Decimal(str(config.entry.strike_selection.short_put_delta)),
            wing_width=Decimal(str(config.entry.strike_selection.wing_width)),
            min_credit=Decimal(str(config.entry.min_credit)),
            entry_earliest=time.fromisoformat(config.entry.time_window.earliest),
            entry_latest=time.fromisoformat(config.entry.time_window.latest),
        )

    if cls is CreditSpreadStrategy:
        return CreditSpreadStrategy(
            name=config.strategy.name,
            symbol=config.market.symbol,
            direction=config.entry.direction,
            short_delta=Decimal(str(config.entry.strike_selection.short_delta)),
            wing_width=Decimal(str(config.entry.strike_selection.wing_width)),
            min_credit=Decimal(str(config.entry.min_credit)),
            entry_earliest=time.fromisoformat(config.entry.time_window.earliest),
            entry_latest=time.fromisoformat(config.entry.time_window.latest),
        )

    if cls is DebitSpreadStrategy:
        return DebitSpreadStrategy(
            name=config.strategy.name,
            symbol=config.market.symbol,
            direction=config.entry.direction,
            long_delta=Decimal(str(config.entry.strike_selection.long_delta)),
            short_delta=Decimal(str(config.entry.strike_selection.short_delta)),
            max_debit=Decimal(str(config.entry.max_debit)),
            entry_earliest=time.fromisoformat(config.entry.time_window.earliest),
            entry_latest=time.fromisoformat(config.entry.time_window.latest),
        )

    raise ValueError(f"No loader for strategy class: {class_name}")
