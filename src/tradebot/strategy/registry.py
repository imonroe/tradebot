"""Strategy factory that loads strategies from config."""
from datetime import time
from decimal import Decimal
from pathlib import Path

from tradebot.strategy.base import TradingStrategy
from tradebot.strategy.strategies.iron_condor import IronCondorStrategy
from tradebot.utils.config import StrategyConfig, load_strategy_config

STRATEGY_CLASSES = {
    "IronCondorStrategy": IronCondorStrategy,
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

    raise ValueError(f"No loader for strategy class: {class_name}")
