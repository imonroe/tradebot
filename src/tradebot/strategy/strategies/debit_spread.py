"""Debit spread strategy — buys a vertical spread for directional exposure."""
from datetime import time
from decimal import Decimal

import structlog

from tradebot.core.enums import OrderSide, SpreadType
from tradebot.core.events import MarketEvent, SignalEvent
from tradebot.core.models import OptionContract, OptionsChain, OrderLeg
from tradebot.strategy.base import TradingStrategy

logger = structlog.get_logger()


class DebitSpreadStrategy(TradingStrategy):
    """Buy a vertical spread for directional exposure with defined risk.

    - direction="call": bull call spread (buy lower call, sell higher call)
    - direction="put": bear put spread (buy higher put, sell lower put)
    """

    def __init__(
        self,
        name: str,
        symbol: str,
        direction: str,
        long_delta: Decimal,
        short_delta: Decimal,
        max_debit: Decimal,
        entry_earliest: time,
        entry_latest: time,
    ) -> None:
        super().__init__(name=name, symbol=symbol)
        if direction not in ("call", "put"):
            raise ValueError(f"direction must be 'call' or 'put', got '{direction}'")
        self.direction = direction
        self.long_delta = long_delta
        self.short_delta = short_delta
        self.max_debit = max_debit
        self.entry_earliest = entry_earliest
        self.entry_latest = entry_latest
        self._has_position = False

    def evaluate(self, event: MarketEvent) -> list[SignalEvent]:
        if self._has_position:
            return []
        if event.options_chain is None:
            return []
        if event.bar.symbol != self.symbol:
            return []

        current_time = event.bar.timestamp.time()
        if not (self.entry_earliest <= current_time <= self.entry_latest):
            return []

        legs = self._select_strikes(event.options_chain)
        if legs is None:
            logger.info("debit_spread_skip", reason="no_valid_strikes_or_debit_too_high")
            return []

        debit = self._estimate_debit(event.options_chain, legs)

        self._has_position = True
        return [
            SignalEvent(
                strategy_name=self.name,
                spread_type=SpreadType.DEBIT_SPREAD,
                symbol=self.symbol,
                legs=legs,
                target_price=debit,
            )
        ]

    def _select_strikes(self, chain: OptionsChain) -> list[OrderLeg] | None:
        if self.direction == "call":
            return self._select_call_spread(chain)
        return self._select_put_spread(chain)

    def _find_closest_by_delta(
        self, contracts: list[OptionContract], target_delta: Decimal
    ) -> OptionContract | None:
        if not contracts:
            return None
        return min(contracts, key=lambda c: abs(c.greeks.delta - target_delta))

    def _select_call_spread(self, chain: OptionsChain) -> list[OrderLeg] | None:
        long_call = self._find_closest_by_delta(chain.calls, self.long_delta)
        short_call = self._find_closest_by_delta(chain.calls, self.short_delta)
        if long_call is None or short_call is None:
            return None
        if long_call.strike >= short_call.strike:
            return None

        debit = long_call.ask - short_call.bid
        if debit > self.max_debit:
            return None

        return [
            OrderLeg(option_symbol=long_call.symbol, side=OrderSide.BUY_TO_OPEN, quantity=1),
            OrderLeg(option_symbol=short_call.symbol, side=OrderSide.SELL_TO_OPEN, quantity=1),
        ]

    def _select_put_spread(self, chain: OptionsChain) -> list[OrderLeg] | None:
        long_put = self._find_closest_by_delta(chain.puts, -self.long_delta)
        short_put = self._find_closest_by_delta(chain.puts, -self.short_delta)
        if long_put is None or short_put is None:
            return None
        if long_put.strike <= short_put.strike:
            return None

        debit = long_put.ask - short_put.bid
        if debit > self.max_debit:
            return None

        return [
            OrderLeg(option_symbol=long_put.symbol, side=OrderSide.BUY_TO_OPEN, quantity=1),
            OrderLeg(option_symbol=short_put.symbol, side=OrderSide.SELL_TO_OPEN, quantity=1),
        ]

    def reset(self) -> None:
        """Reset position state for a new trading day."""
        self._has_position = False

    def _estimate_debit(self, chain: OptionsChain, legs: list[OrderLeg]) -> Decimal:
        """Estimate net debit from mid prices."""
        debit = Decimal("0")
        all_contracts = {c.symbol: c for c in chain.calls + chain.puts}
        for leg in legs:
            contract = all_contracts.get(leg.option_symbol)
            if contract is None:
                continue
            if leg.side in (OrderSide.BUY_TO_OPEN, OrderSide.BUY_TO_CLOSE):
                debit += contract.mid_price
            else:
                debit -= contract.mid_price
        return debit
