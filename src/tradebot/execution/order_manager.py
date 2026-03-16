"""Order lifecycle management."""
import structlog

from tradebot.core.events import FillEvent, OrderEvent
from tradebot.execution.brokers.base import Broker

logger = structlog.get_logger()


class OrderManager:
    """Converts OrderEvents into broker orders and tracks lifecycle."""

    def __init__(self, broker: Broker) -> None:
        self._broker = broker

    async def on_order(self, event: OrderEvent) -> list:
        """Submit order to broker and return fill/rejection events."""
        signal = event.signal
        logger.info(
            "submitting_order",
            strategy=signal.strategy_name,
            symbol=signal.symbol,
            spread_type=signal.spread_type.value,
            legs=len(signal.legs),
            target_price=str(signal.target_price),
        )

        result = await self._broker.submit_multileg_order(
            legs=signal.legs,
            price=signal.target_price,
        )

        logger.info(
            "order_result",
            broker_order_id=result.broker_order_id,
            status=result.status.value,
        )

        return [
            FillEvent(
                broker_order_id=result.broker_order_id,
                signal=signal,
                fill_price=signal.target_price,
                status=result.status,
            )
        ]
