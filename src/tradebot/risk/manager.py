"""Risk manager that chains checks and gates signals."""
import structlog

from tradebot.core.events import OrderEvent, RiskEvent, SignalEvent

logger = structlog.get_logger()


class RiskManager:
    """Evaluates signals against a chain of risk checks.

    If all checks pass, produces an OrderEvent.
    All check results are emitted as RiskEvents for logging/dashboard.
    """

    def __init__(self) -> None:
        self._checks: list = []

    def add_check(self, check: object) -> None:
        self._checks.append(check)

    async def on_signal(self, signal: SignalEvent) -> list:
        """Process a signal through all risk checks."""
        events: list = []
        all_passed = True

        for check in self._checks:
            result: RiskEvent = check.check(signal)
            events.append(result)

            if not result.passed:
                all_passed = False
                logger.warning(
                    "risk_check_failed",
                    check=result.check_name,
                    message=result.message,
                    strategy=signal.strategy_name,
                )
                break  # Stop on first failure

            logger.info(
                "risk_check_passed",
                check=result.check_name,
                message=result.message,
            )

        if all_passed:
            events.append(OrderEvent(signal=signal))
            logger.info(
                "signal_approved",
                strategy=signal.strategy_name,
                symbol=signal.symbol,
            )

        return events
