"""Tests for Tradier broker client."""
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, patch
import pytest
from tradebot.core.enums import OrderSide, OrderStatus
from tradebot.core.models import OrderLeg
from tradebot.execution.brokers.tradier import TradierBroker

@pytest.fixture
def broker():
    return TradierBroker(base_url="https://sandbox.tradier.com", api_token="test_token")

@pytest.mark.asyncio
async def test_get_account(broker):
    mock_response = {
        "profile": {"account": {"account_number": "TEST123", "value": 2500.00,
            "stock_buying_power": 2500.00, "day_trade_count": 0}}
    }
    with patch.object(broker, "_request", new_callable=AsyncMock, return_value=mock_response):
        account = await broker.get_account()
        assert account.balance == Decimal("2500.00")
        assert account.buying_power == Decimal("2500.00")

@pytest.mark.asyncio
async def test_get_options_chain(broker):
    chain_response = {
        "options": {"option": [{
            "symbol": "XSP250316C00575000", "option_type": "call", "strike": 575.00,
            "expiration_date": "2026-03-16", "bid": 1.20, "ask": 1.35, "last": 1.25,
            "volume": 150, "open_interest": 500,
            "greeks": {"delta": 0.30, "gamma": 0.05, "theta": -0.15, "vega": 0.08, "mid_iv": 0.22},
        }]}
    }
    quote_response = {"quotes": {"quote": {"last": 570.50}}}
    with patch.object(broker, "_request", new_callable=AsyncMock, side_effect=[chain_response, quote_response]):
        chain = await broker.get_options_chain("XSP", date(2026, 3, 16))
        assert len(chain.calls) == 1
        assert chain.calls[0].strike == Decimal("575.00")
        assert chain.calls[0].greeks.delta == Decimal("0.30")
        assert chain.underlying_price == Decimal("570.50")

@pytest.mark.asyncio
async def test_submit_multileg_order(broker):
    profile_response = {"profile": {"account": {"account_number": "TEST123"}}}
    order_response = {"order": {"id": 12345, "status": "pending"}}
    legs = [
        OrderLeg(option_symbol="XSP250316P00565000", side=OrderSide.SELL_TO_OPEN, quantity=1),
        OrderLeg(option_symbol="XSP250316P00560000", side=OrderSide.BUY_TO_OPEN, quantity=1),
    ]
    with patch.object(broker, "_request", new_callable=AsyncMock, side_effect=[profile_response, order_response]):
        result = await broker.submit_multileg_order(legs=legs, price=Decimal("0.50"))
        assert result.broker_order_id == "12345"
        assert result.status == OrderStatus.PENDING
