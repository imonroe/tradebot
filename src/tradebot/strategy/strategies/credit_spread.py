"""Credit spread strategy — sells OTM vertical spread for a credit."""
from datetime import time
from decimal import Decimal

import structlog

from tradebot.core.enums import OrderSide, SpreadType
from tradebot.core.events import MarketEvent, SignalEvent
from tradebot.core.models import OptionContract, OptionsChain, OrderLeg
from tradebot.strategy.base import TradingStrategy

logger = structlog.get_logger()


class CreditSpreadStrategy(TradingStrategy):
    """Sell an OTM call or put spread, collecting premium from time decay.

    - direction="put": bull put spread (sell higher put, buy lower put)
    - direction="call": bear call spread (sell lower call, buy higher call)
    """

    def __init__(
        self,
        name: str,
        symbol: str,
        direction: str,
        short_delta: Decimal,
        wing_width: Decimal,
        min_credit: Decimal,
        entry_earliest: time,
        entry_latest: time,
    ) -> None:
        super().__init__(name=name, symbol=symbol)
        if direction not in ("call", "put"):
            raise ValueError(f"direction must be 'call' or 'put', got '{direction}'")
        self.direction = direction
        self.short_delta = short_delta
        self.wing_width = wing_width
        self.min_credit = min_credit
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
            logger.info("credit_spread_skip", reason="no_valid_strikes_or_credit_too_low")
            return []

        credit = self._estimate_credit(event.options_chain, legs)

        self._has_position = True
        return [
            SignalEvent(
                strategy_name=self.name,
                spread_type=SpreadType.CREDIT_SPREAD,
                symbol=self.symbol,
                legs=legs,
                target_price=credit,
            )
        ]

    def _select_strikes(self, chain: OptionsChain) -> list[OrderLeg] | None:
        if self.direction == "put":
            return self._select_put_spread(chain)
        return self._select_call_spread(chain)

    def _find_closest_by_delta(
        self, contracts: list[OptionContract], target_delta: Decimal
    ) -> OptionContract | None:
        if not contracts:
            return None
        return min(contracts, key=lambda c: abs(c.greeks.delta - target_delta))

    def _find_by_strike(
        self, contracts: list[OptionContract], target_strike: Decimal
    ) -> OptionContract | None:
        if not contracts:
            return None
        exact = [c for c in contracts if c.strike == target_strike]
        if exact:
            return exact[0]
        return None

    def _select_put_spread(self, chain: OptionsChain) -> list[OrderLeg] | None:
        short_put = self._find_closest_by_delta(chain.puts, -self.short_delta)
        if short_put is None:
            return None

        long_strike = short_put.strike - self.wing_width
        long_put = self._find_by_strike(chain.puts, long_strike)
        if long_put is None:
            return None

        credit = short_put.bid - long_put.ask
        if credit < self.min_credit:
            return None

        return [
            OrderLeg(option_symbol=short_put.symbol, side=OrderSide.SELL_TO_OPEN, quantity=1),
            OrderLeg(option_symbol=long_put.symbol, side=OrderSide.BUY_TO_OPEN, quantity=1),
        ]

    def _select_call_spread(self, chain: OptionsChain) -> list[OrderLeg] | None:
        short_call = self._find_closest_by_delta(chain.calls, self.short_delta)
        if short_call is None:
            return None

        long_strike = short_call.strike + self.wing_width
        long_call = self._find_by_strike(chain.calls, long_strike)
        if long_call is None:
            return None

        credit = short_call.bid - long_call.ask
        if credit < self.min_credit:
            return None

        return [
            OrderLeg(option_symbol=short_call.symbol, side=OrderSide.SELL_TO_OPEN, quantity=1),
            OrderLeg(option_symbol=long_call.symbol, side=OrderSide.BUY_TO_OPEN, quantity=1),
        ]

    def reset(self) -> None:
        """Reset position state for a new trading day."""
        self._has_position = False

    def _estimate_credit(self, chain: OptionsChain, legs: list[OrderLeg]) -> Decimal:
        """Estimate net credit from mid prices."""
        credit = Decimal("0")
        all_contracts = {c.symbol: c for c in chain.calls + chain.puts}
        for leg in legs:
            contract = all_contracts.get(leg.option_symbol)
            if contract is None:
                continue
            if leg.side in (OrderSide.SELL_TO_OPEN, OrderSide.SELL_TO_CLOSE):
                credit += contract.mid_price
            else:
                credit -= contract.mid_price
        return credit
