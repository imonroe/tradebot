"""Synthetic market data source for paper trading."""
import math
import random
from datetime import date, datetime
from decimal import Decimal

import structlog

from tradebot.core.enums import OptionType
from tradebot.core.models import Bar, Greeks, OptionContract, OptionsChain

logger = structlog.get_logger()


class PaperDataSource:
    """Generates synthetic options chain data with random-walk price movement."""

    def __init__(
        self,
        base_price: Decimal = Decimal("570.00"),
        seed: int | None = None,
    ) -> None:
        self._base_price = base_price
        self._current_price = base_price
        self._previous_price = base_price
        self._rng = random.Random(seed)

    async def get_quote(self, symbol: str) -> Bar:
        """Return a synthetic quote with random-walk price movement."""
        self._previous_price = self._current_price

        # Random walk
        drift = Decimal(str(round(self._rng.gauss(0, 0.3), 4)))
        self._current_price += drift

        # Clamp to ±5% of base
        lower = self._base_price * Decimal("0.95")
        upper = self._base_price * Decimal("1.05")
        self._current_price = max(lower, min(upper, self._current_price))

        open_price = self._previous_price
        close_price = self._current_price
        high = max(open_price, close_price) + Decimal(str(round(self._rng.uniform(0.05, 0.30), 2)))
        low = min(open_price, close_price) - Decimal(str(round(self._rng.uniform(0.05, 0.30), 2)))
        volume = self._rng.randint(500_000, 2_000_000)

        return Bar(
            symbol=symbol,
            timestamp=datetime.now(),
            open=open_price,
            high=high,
            low=low,
            close=close_price,
            volume=volume,
        )

    async def get_options_chain(self, symbol: str, expiration: date) -> OptionsChain:
        """Generate a synthetic options chain around the current price."""
        underlying_price = self._current_price
        calls: list[OptionContract] = []
        puts: list[OptionContract] = []

        # Generate strikes from -20 to +20 around current price (rounded to nearest $1)
        center = int(underlying_price)
        for strike_int in range(center - 20, center + 21):
            strike = Decimal(str(strike_int))
            moneyness = float((strike - underlying_price) / underlying_price)
            moneyness_sq = moneyness * moneyness

            # Greeks approximation
            call_delta = max(0.0, min(1.0, 0.5 - moneyness * 5))
            put_delta = call_delta - 1.0
            gamma = 0.05 * math.exp(-50 * moneyness_sq)
            theta = -0.05 * math.exp(-50 * moneyness_sq)
            vega = 0.10 * math.exp(-50 * moneyness_sq)
            iv = 0.20 + 0.10 * moneyness_sq

            # Pricing
            call_intrinsic = max(Decimal("0"), underlying_price - strike)
            put_intrinsic = max(Decimal("0"), strike - underlying_price)
            extrinsic = Decimal(str(round(0.50 * math.exp(-50 * moneyness_sq), 4)))

            for opt_type, intrinsic, delta in [
                (OptionType.CALL, call_intrinsic, call_delta),
                (OptionType.PUT, put_intrinsic, put_delta),
            ]:
                mid = intrinsic + extrinsic
                spread = Decimal(str(round(self._rng.uniform(0.01, 0.03), 2)))
                bid = max(Decimal("0.01"), mid - spread)
                ask = mid + spread

                # OCC symbol: XSP{YYMMDD}{C/P}{strike*1000:08d}
                type_char = "C" if opt_type == OptionType.CALL else "P"
                occ_symbol = (
                    f"{symbol}{expiration.strftime('%y%m%d')}"
                    f"{type_char}{int(strike * 1000):08d}"
                )

                contract = OptionContract(
                    symbol=occ_symbol,
                    underlying=symbol,
                    option_type=opt_type,
                    strike=strike,
                    expiration=expiration,
                    bid=bid,
                    ask=ask,
                    last=mid,
                    volume=self._rng.randint(0, 5000),
                    open_interest=self._rng.randint(100, 10000),
                    greeks=Greeks(
                        delta=Decimal(str(round(delta, 6))),
                        gamma=Decimal(str(round(gamma, 6))),
                        theta=Decimal(str(round(theta, 6))),
                        vega=Decimal(str(round(vega, 6))),
                        implied_volatility=Decimal(str(round(iv, 6))),
                    ),
                )

                if opt_type == OptionType.CALL:
                    calls.append(contract)
                else:
                    puts.append(contract)

        return OptionsChain(
            underlying=symbol,
            expiration=expiration,
            underlying_price=underlying_price,
            calls=sorted(calls, key=lambda c: c.strike),
            puts=sorted(puts, key=lambda p: p.strike),
        )
