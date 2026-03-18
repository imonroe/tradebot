"""Tests for credit spread strategy."""
from datetime import date, datetime, time
from decimal import Decimal

import pytest

from tradebot.core.enums import OptionType, OrderSide, SpreadType
from tradebot.core.events import MarketEvent
from tradebot.core.models import Bar, Greeks, OptionContract, OptionsChain
from tradebot.strategy.strategies.credit_spread import CreditSpreadStrategy


def _make_option(
    symbol: str,
    option_type: OptionType,
    strike: Decimal,
    delta: Decimal,
    bid: Decimal = Decimal("1.00"),
    ask: Decimal = Decimal("1.20"),
) -> OptionContract:
    return OptionContract(
        symbol=symbol,
        underlying="XSP",
        option_type=option_type,
        strike=strike,
        expiration=date(2026, 3, 18),
        bid=bid,
        ask=ask,
        last=(bid + ask) / 2,
        volume=100,
        open_interest=500,
        greeks=Greeks(
            delta=delta,
            gamma=Decimal("0.05"),
            theta=Decimal("-0.10"),
            vega=Decimal("0.08"),
            implied_volatility=Decimal("0.20"),
        ),
    )


def _make_chain() -> OptionsChain:
    calls = [
        _make_option("XSP_C670", OptionType.CALL, Decimal("670"), Decimal("0.30"), Decimal("2.00"), Decimal("2.20")),
        _make_option("XSP_C675", OptionType.CALL, Decimal("675"), Decimal("0.15"), Decimal("0.80"), Decimal("1.00")),
        _make_option("XSP_C680", OptionType.CALL, Decimal("680"), Decimal("0.08"), Decimal("0.30"), Decimal("0.45")),
    ]
    puts = [
        _make_option("XSP_P650", OptionType.PUT, Decimal("650"), Decimal("-0.08"), Decimal("0.25"), Decimal("0.40")),
        _make_option("XSP_P655", OptionType.PUT, Decimal("655"), Decimal("-0.15"), Decimal("0.70"), Decimal("0.90")),
        _make_option("XSP_P660", OptionType.PUT, Decimal("660"), Decimal("-0.30"), Decimal("1.80"), Decimal("2.10")),
    ]
    return OptionsChain(
        underlying="XSP",
        expiration=date(2026, 3, 18),
        underlying_price=Decimal("665.00"),
        calls=calls,
        puts=puts,
    )


def _make_market_event(chain: OptionsChain | None = None) -> MarketEvent:
    bar = Bar(
        symbol="XSP",
        timestamp=datetime(2026, 3, 18, 10, 30),
        open=Decimal("665"), high=Decimal("666"),
        low=Decimal("664"), close=Decimal("665"), volume=5000,
    )
    return MarketEvent(bar=bar, options_chain=chain or _make_chain())


class TestCreditSpreadStrategy:
    def _make_strategy(self, direction: str = "put") -> CreditSpreadStrategy:
        return CreditSpreadStrategy(
            name="test_credit_spread",
            symbol="XSP",
            direction=direction,
            short_delta=Decimal("0.15"),
            wing_width=Decimal("5"),
            min_credit=Decimal("0.10"),
            entry_earliest=time(9, 45),
            entry_latest=time(14, 0),
        )

    def test_put_spread_generates_two_legs(self):
        strategy = self._make_strategy(direction="put")
        event = _make_market_event()
        signals = strategy.evaluate(event)
        assert len(signals) == 1
        signal = signals[0]
        assert signal.spread_type == SpreadType.CREDIT_SPREAD
        assert len(signal.legs) == 2
        assert signal.strategy_name == "test_credit_spread"
        assert signal.symbol == "XSP"

    def test_put_spread_has_sell_and_buy_legs(self):
        strategy = self._make_strategy(direction="put")
        event = _make_market_event()
        signals = strategy.evaluate(event)
        signal = signals[0]
        sides = {leg.side for leg in signal.legs}
        assert OrderSide.SELL_TO_OPEN in sides
        assert OrderSide.BUY_TO_OPEN in sides

    def test_call_spread_generates_signal(self):
        strategy = self._make_strategy(direction="call")
        event = _make_market_event()
        signals = strategy.evaluate(event)
        assert len(signals) == 1
        signal = signals[0]
        assert signal.spread_type == SpreadType.CREDIT_SPREAD
        assert len(signal.legs) == 2

    def test_no_signal_when_position_open(self):
        strategy = self._make_strategy()
        event = _make_market_event()
        strategy.evaluate(event)
        signals = strategy.evaluate(event)
        assert len(signals) == 0

    def test_no_signal_when_no_chain(self):
        strategy = self._make_strategy()
        bar = Bar(
            symbol="XSP",
            timestamp=datetime(2026, 3, 18, 10, 30),
            open=Decimal("665"), high=Decimal("666"),
            low=Decimal("664"), close=Decimal("665"), volume=10000,
        )
        event = MarketEvent(bar=bar, options_chain=None)
        signals = strategy.evaluate(event)
        assert len(signals) == 0

    def test_no_signal_outside_time_window(self):
        strategy = self._make_strategy()
        bar = Bar(
            symbol="XSP",
            timestamp=datetime(2026, 3, 18, 15, 30),
            open=Decimal("665"), high=Decimal("666"),
            low=Decimal("664"), close=Decimal("665"), volume=10000,
        )
        event = MarketEvent(bar=bar, options_chain=_make_chain())
        signals = strategy.evaluate(event)
        assert len(signals) == 0

    def test_no_signal_wrong_symbol(self):
        strategy = self._make_strategy()
        bar = Bar(
            symbol="SPY",
            timestamp=datetime(2026, 3, 18, 10, 30),
            open=Decimal("665"), high=Decimal("666"),
            low=Decimal("664"), close=Decimal("665"), volume=10000,
        )
        event = MarketEvent(bar=bar, options_chain=_make_chain())
        signals = strategy.evaluate(event)
        assert len(signals) == 0

    def test_direction_must_be_call_or_put(self):
        with pytest.raises(ValueError, match="direction"):
            CreditSpreadStrategy(
                name="bad",
                symbol="XSP",
                direction="diagonal",
                short_delta=Decimal("0.15"),
                wing_width=Decimal("5"),
                min_credit=Decimal("0.10"),
                entry_earliest=time(9, 45),
                entry_latest=time(14, 0),
            )
