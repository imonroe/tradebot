"""Tests for core domain models."""
from decimal import Decimal
from datetime import datetime, date

from tradebot.core.enums import (
    OptionType, OrderSide, SpreadType,
)
from tradebot.core.models import (
    OptionContract, OrderLeg, Bar, Greeks,
)


def test_option_type_enum():
    assert OptionType.CALL.value == "call"
    assert OptionType.PUT.value == "put"


def test_order_side_enum():
    assert OrderSide.BUY_TO_OPEN.value == "buy_to_open"
    assert OrderSide.SELL_TO_CLOSE.value == "sell_to_close"


def test_spread_type_enum():
    assert SpreadType.IRON_CONDOR.value == "iron_condor"
    assert SpreadType.CREDIT_SPREAD.value == "credit_spread"
    assert SpreadType.DEBIT_SPREAD.value == "debit_spread"


def test_option_contract_creation():
    contract = OptionContract(
        symbol="XSP250316C00575000", underlying="XSP",
        option_type=OptionType.CALL, strike=Decimal("575.00"),
        expiration=date(2026, 3, 16), bid=Decimal("1.20"),
        ask=Decimal("1.35"), last=Decimal("1.25"),
        volume=150, open_interest=500,
        greeks=Greeks(delta=Decimal("0.30"), gamma=Decimal("0.05"),
            theta=Decimal("-0.15"), vega=Decimal("0.08"),
            implied_volatility=Decimal("0.22")),
    )
    assert contract.underlying == "XSP"
    assert contract.strike == Decimal("575.00")
    assert contract.greeks.delta == Decimal("0.30")


def test_option_contract_mid_price():
    contract = OptionContract(
        symbol="XSP250316C00575000", underlying="XSP",
        option_type=OptionType.CALL, strike=Decimal("575.00"),
        expiration=date(2026, 3, 16), bid=Decimal("1.20"),
        ask=Decimal("1.40"), last=Decimal("1.30"),
        volume=100, open_interest=200,
        greeks=Greeks(delta=Decimal("0.30"), gamma=Decimal("0.05"),
            theta=Decimal("-0.15"), vega=Decimal("0.08"),
            implied_volatility=Decimal("0.22")),
    )
    assert contract.mid_price == Decimal("1.30")


def test_order_leg_creation():
    leg = OrderLeg(option_symbol="XSP250316C00575000", side=OrderSide.SELL_TO_OPEN, quantity=1)
    assert leg.side == OrderSide.SELL_TO_OPEN
    assert leg.quantity == 1


def test_bar_creation():
    bar = Bar(symbol="XSP", timestamp=datetime(2026, 3, 16, 10, 0, 0),
        open=Decimal("570.00"), high=Decimal("572.50"),
        low=Decimal("569.00"), close=Decimal("571.25"), volume=10000)
    assert bar.symbol == "XSP"
    assert bar.close == Decimal("571.25")
