"""Backtest broker with realistic fill simulation."""
from decimal import Decimal

from tradebot.core.enums import OrderSide
from tradebot.core.models import OptionsChain, OrderLeg, OrderResult
from tradebot.execution.brokers.paper import PaperBroker


class BacktestBroker(PaperBroker):
    """Paper broker that fills at actual bid/ask from current market data."""

    def __init__(
        self,
        starting_balance: Decimal,
        slippage_pct: Decimal = Decimal("0"),
    ) -> None:
        super().__init__(starting_balance=starting_balance)
        self._slippage_pct = slippage_pct
        self._current_chain: OptionsChain | None = None

    def update_market_data(self, chain: OptionsChain) -> None:
        """Set current market data for realistic fills."""
        self._current_chain = chain

    async def submit_multileg_order(
        self, legs: list[OrderLeg], price: Decimal
    ) -> OrderResult:
        if self._current_chain is None:
            return await super().submit_multileg_order(legs, price)

        fill_price = self._calculate_fill_price(legs)
        return await super().submit_multileg_order(legs, fill_price)

    def _calculate_fill_price(self, legs: list[OrderLeg]) -> Decimal:
        """Calculate net fill price from actual bid/ask in current chain."""
        all_contracts = {
            c.symbol: c
            for c in self._current_chain.calls + self._current_chain.puts
        }
        net_credit = Decimal("0")
        for leg in legs:
            contract = all_contracts.get(leg.option_symbol)
            if contract is None:
                continue
            if leg.side in (OrderSide.SELL_TO_OPEN, OrderSide.SELL_TO_CLOSE):
                fill = contract.bid
                if self._slippage_pct > 0:
                    fill = fill * (1 - self._slippage_pct / 100)
                net_credit += fill
            else:
                fill = contract.ask
                if self._slippage_pct > 0:
                    fill = fill * (1 + self._slippage_pct / 100)
                net_credit -= fill
        return net_credit
