"""Tests for paper data source with synthetic market data."""
from datetime import date
from decimal import Decimal

from tradebot.core.enums import OptionType
from tradebot.data.sources.paper import PaperDataSource


def _make_source(seed: int = 42) -> PaperDataSource:
    return PaperDataSource(base_price=Decimal("570.00"), seed=seed)


async def test_get_quote_returns_bar():
    source = _make_source()
    bar = await source.get_quote("XSP")
    assert bar.symbol == "XSP"
    assert bar.volume > 0
    assert bar.close > 0


async def test_get_quote_price_changes_between_calls():
    source = _make_source()
    bar1 = await source.get_quote("XSP")
    bar2 = await source.get_quote("XSP")
    # With a random walk, prices should differ (seed 42 produces non-zero drift)
    assert bar1.close != bar2.close


async def test_get_quote_price_stays_within_bounds():
    source = _make_source(seed=1)
    for _ in range(100):
        bar = await source.get_quote("XSP")
    # Price should stay within 5% of base
    assert Decimal("541.50") <= bar.close <= Decimal("598.50")


async def test_get_options_chain_has_calls_and_puts():
    source = _make_source()
    chain = await source.get_options_chain("XSP", date(2026, 3, 17))
    assert len(chain.calls) > 0
    assert len(chain.puts) > 0
    assert chain.underlying == "XSP"
    assert chain.expiration == date(2026, 3, 17)


async def test_get_options_chain_strikes_bracket_underlying():
    source = _make_source()
    chain = await source.get_options_chain("XSP", date(2026, 3, 17))
    strikes = [c.strike for c in chain.calls]
    assert min(strikes) < chain.underlying_price
    assert max(strikes) > chain.underlying_price


async def test_get_options_chain_calls_sorted_by_strike():
    source = _make_source()
    chain = await source.get_options_chain("XSP", date(2026, 3, 17))
    strikes = [c.strike for c in chain.calls]
    assert strikes == sorted(strikes)


async def test_get_options_chain_call_deltas_decrease_with_strike():
    source = _make_source()
    chain = await source.get_options_chain("XSP", date(2026, 3, 17))
    deltas = [c.greeks.delta for c in chain.calls]
    # Deltas should generally decrease as strike increases (higher strike = more OTM)
    assert deltas[0] > deltas[-1]


async def test_get_options_chain_put_deltas_are_negative():
    source = _make_source()
    chain = await source.get_options_chain("XSP", date(2026, 3, 17))
    for put in chain.puts:
        assert put.greeks.delta < 0


async def test_get_options_chain_option_types_correct():
    source = _make_source()
    chain = await source.get_options_chain("XSP", date(2026, 3, 17))
    for call in chain.calls:
        assert call.option_type == OptionType.CALL
    for put in chain.puts:
        assert put.option_type == OptionType.PUT


async def test_get_options_chain_bid_less_than_ask():
    source = _make_source()
    chain = await source.get_options_chain("XSP", date(2026, 3, 17))
    for contract in chain.calls + chain.puts:
        assert contract.bid <= contract.ask


async def test_get_options_chain_occ_symbol_format():
    source = _make_source()
    chain = await source.get_options_chain("XSP", date(2026, 3, 17))
    # OCC format: XSP{YYMMDD}{C/P}{strike*1000:08d}
    call = chain.calls[0]
    assert call.symbol.startswith("XSP260317C")
    put = chain.puts[0]
    assert put.symbol.startswith("XSP260317P")


async def test_deterministic_with_same_seed():
    s1 = _make_source(seed=99)
    s2 = _make_source(seed=99)
    bar1 = await s1.get_quote("XSP")
    bar2 = await s2.get_quote("XSP")
    assert bar1.close == bar2.close
