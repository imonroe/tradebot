"""Tests for data recorder wrapper."""
import json
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock

from tradebot.core.enums import OptionType
from tradebot.core.models import Bar, Greeks, OptionContract, OptionsChain
from tradebot.data.sources.recorder import DataRecorder


def _mock_source():
    source = AsyncMock()
    source.get_quote.return_value = Bar(
        symbol="XSP",
        timestamp=datetime(2026, 3, 17, 10, 30),
        open=Decimal("570.00"),
        high=Decimal("571.00"),
        low=Decimal("569.00"),
        close=Decimal("570.50"),
        volume=1000000,
    )
    source.get_options_chain.return_value = OptionsChain(
        underlying="XSP",
        expiration=date(2026, 3, 17),
        underlying_price=Decimal("570.00"),
        calls=[
            OptionContract(
                symbol="XSP260317C00570000",
                underlying="XSP",
                option_type=OptionType.CALL,
                strike=Decimal("570"),
                expiration=date(2026, 3, 17),
                bid=Decimal("1.00"),
                ask=Decimal("1.10"),
                last=Decimal("1.05"),
                volume=100,
                open_interest=500,
                greeks=Greeks(
                    delta=Decimal("0.5"),
                    gamma=Decimal("0.05"),
                    theta=Decimal("-0.05"),
                    vega=Decimal("0.10"),
                    implied_volatility=Decimal("0.20"),
                ),
            )
        ],
        puts=[],
    )
    return source


async def test_recorder_passes_through_quote(tmp_path):
    source = _mock_source()
    recorder = DataRecorder(source, output_dir=tmp_path)
    bar = await recorder.get_quote("XSP")
    assert bar.symbol == "XSP"
    assert bar.close == Decimal("570.50")
    source.get_quote.assert_awaited_once_with("XSP")


async def test_recorder_passes_through_chain(tmp_path):
    source = _mock_source()
    recorder = DataRecorder(source, output_dir=tmp_path)
    chain = await recorder.get_options_chain("XSP", date(2026, 3, 17))
    assert chain.underlying == "XSP"
    assert len(chain.calls) == 1
    source.get_options_chain.assert_awaited_once_with("XSP", date(2026, 3, 17))


async def test_recorder_writes_quote_file(tmp_path):
    source = _mock_source()
    recorder = DataRecorder(source, output_dir=tmp_path)
    await recorder.get_quote("XSP")
    files = list(tmp_path.glob("XSP_quote_*.json"))
    assert len(files) == 1
    data = json.loads(files[0].read_text())
    assert data["symbol"] == "XSP"


async def test_recorder_writes_chain_file(tmp_path):
    source = _mock_source()
    recorder = DataRecorder(source, output_dir=tmp_path)
    await recorder.get_options_chain("XSP", date(2026, 3, 17))
    files = list(tmp_path.glob("XSP_chain_*.json"))
    assert len(files) == 1
    data = json.loads(files[0].read_text())
    assert data["underlying"] == "XSP"
