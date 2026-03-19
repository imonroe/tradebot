"""0DTE Iron Condor strategy."""
from datetime import time
from decimal import Decimal

import structlog

from tradebot.core.enums import OrderSide, SpreadType
from tradebot.core.events import MarketEvent, SignalEvent
from tradebot.core.models import OptionContract, OptionsChain, OrderLeg
from tradebot.strategy.base import TradingStrategy

logger = structlog.get_logger()


class IronCondorStrategy(TradingStrategy):
    """Sells OTM call + put spreads on XSP, collects credit from time decay.

    Strike selection is delta-based: find options closest to target delta
    for the short strikes, then add wings at a fixed width.
    """

    def __init__(
        self,
        name: str,
        symbol: str,
        short_call_delta: Decimal,
        short_put_delta: Decimal,
        wing_width: Decimal,
        min_credit: Decimal,
        entry_earliest: time,
        entry_latest: time,
    ) -> None:
        super().__init__(name=name, symbol=symbol)
        self.short_call_delta = short_call_delta
        self.short_put_delta = short_put_delta
        self.wing_width = wing_width
        self.min_credit = min_credit
        self.entry_earliest = entry_earliest
        self.entry_latest = entry_latest
        self._has_position = False

    def evaluate(self, event: MarketEvent) -> list[SignalEvent]:
        """Evaluate market event and potentially emit a signal."""
        if self._has_position:
            return []

        if event.options_chain is None:
            return []

        if event.bar.symbol != self.symbol:
            return []

        current_time = event.bar.timestamp.time()
        if not (self.entry_earliest <= current_time <= self.entry_latest):
            return []

        legs = self.select_strikes(event.options_chain)
        if legs is None:
            logger.info(
                "iron_condor_skip",
                reason="no_valid_strikes_or_credit_too_low",
                min_credit=str(self.min_credit),
            )
            return []

        # Estimate net credit for the target price
        credit = self._estimate_credit(event.options_chain, legs)

        self._has_position = True
        return [
            SignalEvent(
                strategy_name=self.name,
                spread_type=SpreadType.IRON_CONDOR,
                symbol=self.symbol,
                legs=legs,
                target_price=credit,
            )
        ]

    def select_strikes(self, chain: OptionsChain) -> list[OrderLeg] | None:
        """Select 4 legs for the iron condor based on delta.

        Returns None if valid strikes can't be found or if the estimated
        credit doesn't meet the minimum credit threshold.
        """
        short_call = self._find_by_delta(chain.calls, self.short_call_delta)
        short_put = self._find_by_delta(chain.puts, self.short_put_delta)

        if short_call is None or short_put is None:
            return None

        # Find wings
        long_call_strike = short_call.strike + self.wing_width
        long_put_strike = short_put.strike - self.wing_width

        long_call = self._find_by_strike(chain.calls, long_call_strike)
        long_put = self._find_by_strike(chain.puts, long_put_strike)

        if long_call is None or long_put is None:
            return None

        legs = [
            OrderLeg(option_symbol=short_put.symbol, side=OrderSide.SELL_TO_OPEN, quantity=1),
            OrderLeg(option_symbol=long_put.symbol, side=OrderSide.BUY_TO_OPEN, quantity=1),
            OrderLeg(option_symbol=short_call.symbol, side=OrderSide.SELL_TO_OPEN, quantity=1),
            OrderLeg(option_symbol=long_call.symbol, side=OrderSide.BUY_TO_OPEN, quantity=1),
        ]

        # Validate minimum credit
        credit = self._estimate_credit(chain, legs)
        if credit < self.min_credit:
            return None

        return legs

    def _find_by_delta(
        self, contracts: list[OptionContract], target_delta: Decimal
    ) -> OptionContract | None:
        """Find the contract with delta closest to target."""
        if not contracts:
            return None
        return min(contracts, key=lambda c: abs(c.greeks.delta - target_delta))

    def _find_by_strike(
        self, contracts: list[OptionContract], target_strike: Decimal
    ) -> OptionContract | None:
        """Find the contract at or closest to the target strike."""
        if not contracts:
            return None
        exact = [c for c in contracts if c.strike == target_strike]
        if exact:
            return exact[0]
        return min(contracts, key=lambda c: abs(c.strike - target_strike))

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
