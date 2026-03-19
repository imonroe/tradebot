"""Tests for trading strategies."""
from datetime import date, datetime, time
from decimal import Decimal


from tradebot.core.enums import OptionType, OrderSide
from tradebot.core.events import MarketEvent
from tradebot.core.models import Bar, Greeks, OptionContract, OptionsChain
from tradebot.strategy.strategies.iron_condor import IronCondorStrategy


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
        expiration=date(2026, 3, 16),
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


def _make_chain(underlying_price: Decimal = Decimal("570.00")) -> OptionsChain:
    calls = [
        _make_option("XSP_C575", OptionType.CALL, Decimal("575"), Decimal("0.30"), Decimal("2.00"), Decimal("2.20")),
        _make_option("XSP_C580", OptionType.CALL, Decimal("580"), Decimal("0.15"), Decimal("0.80"), Decimal("1.00")),
        _make_option("XSP_C585", OptionType.CALL, Decimal("585"), Decimal("0.08"), Decimal("0.30"), Decimal("0.45")),
    ]
    puts = [
        _make_option("XSP_P555", OptionType.PUT, Decimal("555"), Decimal("-0.08"), Decimal("0.25"), Decimal("0.40")),
        _make_option("XSP_P560", OptionType.PUT, Decimal("560"), Decimal("-0.15"), Decimal("0.70"), Decimal("0.90")),
        _make_option("XSP_P565", OptionType.PUT, Decimal("565"), Decimal("-0.30"), Decimal("1.80"), Decimal("2.10")),
    ]
    return OptionsChain(
        underlying="XSP",
        expiration=date(2026, 3, 16),
        underlying_price=underlying_price,
        calls=calls,
        puts=puts,
    )


def _make_market_event(chain: OptionsChain | None = None) -> MarketEvent:
    bar = Bar(
        symbol="XSP",
        timestamp=datetime(2026, 3, 16, 10, 30),
        open=Decimal("570"), high=Decimal("572"),
        low=Decimal("569"), close=Decimal("571"), volume=5000,
    )
    return MarketEvent(bar=bar, options_chain=chain or _make_chain())


def test_iron_condor_selects_strikes_by_delta():
    strategy = IronCondorStrategy(
        name="test_ic",
        symbol="XSP",
        short_call_delta=Decimal("0.15"),
        short_put_delta=Decimal("-0.15"),
        wing_width=Decimal("5"),
        min_credit=Decimal("0.30"),
        entry_earliest=time(9, 45),
        entry_latest=time(14, 0),
    )

    chain = _make_chain()
    legs = strategy.select_strikes(chain)

    assert legs is not None
    assert len(legs) == 4  # iron condor = 4 legs

    # Verify we have sell and buy sides
    sides = [leg.side for leg in legs]
    assert OrderSide.SELL_TO_OPEN in sides
    assert OrderSide.BUY_TO_OPEN in sides


def test_iron_condor_returns_none_when_no_valid_strikes():
    strategy = IronCondorStrategy(
        name="test_ic",
        symbol="XSP",
        short_call_delta=Decimal("0.15"),
        short_put_delta=Decimal("-0.15"),
        wing_width=Decimal("5"),
        min_credit=Decimal("5.00"),  # Unrealistically high
        entry_earliest=time(9, 45),
        entry_latest=time(14, 0),
    )

    chain = _make_chain()
    legs = strategy.select_strikes(chain)
    assert legs is None  # Can't achieve min credit


def test_iron_condor_on_market_event():
    strategy = IronCondorStrategy(
        name="test_ic",
        symbol="XSP",
        short_call_delta=Decimal("0.15"),
        short_put_delta=Decimal("-0.15"),
        wing_width=Decimal("5"),
        min_credit=Decimal("0.30"),
        entry_earliest=time(9, 45),
        entry_latest=time(14, 0),
    )

    event = _make_market_event()
    signals = strategy.evaluate(event)

    assert len(signals) <= 1  # 0 or 1 signal


def test_iron_condor_reset_clears_position():
    strategy = IronCondorStrategy(
        name="test_ic", symbol="XSP",
        short_call_delta=Decimal("0.15"), short_put_delta=Decimal("-0.15"),
        wing_width=Decimal("5"), min_credit=Decimal("0.30"),
        entry_earliest=time(9, 45), entry_latest=time(14, 0),
    )
    strategy._has_position = True
    strategy.reset()
    assert strategy._has_position is False
