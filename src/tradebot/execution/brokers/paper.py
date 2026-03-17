"""Paper broker that simulates order execution locally."""
from datetime import date
from decimal import Decimal

import structlog

from tradebot.core.enums import OrderSide, OrderStatus
from tradebot.core.models import Account, OptionsChain, OrderLeg, OrderResult

logger = structlog.get_logger()


class PaperBroker:
    """Simulates a broker with instant fills and local state tracking."""

    def __init__(self, starting_balance: Decimal) -> None:
        self._balance = starting_balance
        self._positions: list[dict] = []
        self._orders: dict[str, dict] = {}
        self._next_order_id = 1

    async def get_account(self) -> Account:
        return Account(
            balance=self._balance,
            buying_power=self._balance,
            day_trade_count=0,
        )

    async def get_positions(self) -> list[dict]:
        return list(self._positions)

    async def get_options_chain(self, symbol: str, expiration: date) -> OptionsChain:
        raise NotImplementedError(
            "PaperBroker does not provide market data. Use PaperDataSource instead."
        )

    async def submit_multileg_order(
        self, legs: list[OrderLeg], price: Decimal
    ) -> OrderResult:
        order_id = f"PAPER-{self._next_order_id}"
        self._next_order_id += 1

        # Adjust balance: positive price = credit received, negative = debit paid
        quantity = legs[0].quantity if legs else 1
        self._balance += price * 100 * quantity

        # Track positions
        for leg in legs:
            self._positions.append({
                "symbol": leg.option_symbol,
                "quantity": leg.quantity if leg.side in (OrderSide.SELL_TO_OPEN, OrderSide.SELL_TO_CLOSE) else -leg.quantity,
                "cost_basis": float(price / len(legs)),
                "date_acquired": date.today().isoformat(),
            })

        self._orders[order_id] = {
            "status": OrderStatus.FILLED,
            "legs": legs,
            "price": price,
        }

        logger.info(
            "paper_order_filled",
            order_id=order_id,
            legs=len(legs),
            price=str(price),
            balance=str(self._balance),
        )

        return OrderResult(broker_order_id=order_id, status=OrderStatus.FILLED)

    async def submit_order(self, leg: OrderLeg, price: Decimal) -> OrderResult:
        return await self.submit_multileg_order([leg], price)

    async def cancel_order(self, order_id: str) -> None:
        if order_id in self._orders:
            self._orders[order_id]["status"] = OrderStatus.CANCELLED

    async def get_order_status(self, order_id: str) -> str:
        if order_id not in self._orders:
            return "unknown"
        return self._orders[order_id]["status"].value
