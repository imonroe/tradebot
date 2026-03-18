"""Tradier broker implementation."""
from datetime import date
from decimal import Decimal
import re
import httpx
import structlog
from tradebot.core.enums import OptionType, OrderStatus
from tradebot.core.models import Account, Greeks, OptionContract, OptionsChain, OrderLeg, OrderResult

logger = structlog.get_logger()

SIDE_MAP = {
    "buy_to_open": "buy_to_open", "buy_to_close": "buy_to_close",
    "sell_to_open": "sell_to_open", "sell_to_close": "sell_to_close",
}

class TradierBroker:
    def __init__(self, base_url: str, api_token: str, account_id: str = "") -> None:
        self._base_url = base_url.rstrip("/")
        self._headers = {"Authorization": f"Bearer {api_token}", "Accept": "application/json"}
        self._account_id: str | None = account_id or None

    async def _request(self, method: str = "GET", path: str = "", params: dict | None = None, data: dict | None = None) -> dict:
        url = f"{self._base_url}{path}"
        async with httpx.AsyncClient() as client:
            response = await client.request(method, url, headers=self._headers, params=params, data=data)
            response.raise_for_status()
            return response.json()

    async def _ensure_account_id(self) -> str:
        if self._account_id is None:
            result = await self._request("GET", "/v1/user/profile")
            account = result["profile"]["account"]
            if isinstance(account, list):
                self._account_id = account[0]["account_number"]
            else:
                self._account_id = account["account_number"]
        return self._account_id

    async def get_account(self) -> Account:
        result = await self._request("GET", "/v1/user/profile")
        account = result["profile"]["account"]
        if isinstance(account, list):
            account = account[0]
        return Account(
            balance=Decimal(str(account.get("value", 0))),
            buying_power=Decimal(str(account.get("stock_buying_power", 0))),
            day_trade_count=account.get("day_trade_count", 0),
        )

    async def get_options_chain(self, symbol: str, expiration: date) -> OptionsChain:
        result = await self._request("GET", "/v1/markets/options/chains",
            params={"symbol": symbol, "expiration": expiration.isoformat(), "greeks": "true"})
        calls, puts = [], []
        options = result.get("options", {}).get("option", [])
        if not isinstance(options, list):
            options = [options]
        for opt in options:
            greeks_data = opt.get("greeks", {}) or {}
            contract = OptionContract(
                symbol=opt["symbol"], underlying=symbol,
                option_type=OptionType(opt["option_type"]),
                strike=Decimal(str(opt["strike"])),
                expiration=date.fromisoformat(opt["expiration_date"]),
                bid=Decimal(str(opt.get("bid", 0))), ask=Decimal(str(opt.get("ask", 0))),
                last=Decimal(str(opt.get("last", 0))), volume=opt.get("volume", 0),
                open_interest=opt.get("open_interest", 0),
                greeks=Greeks(
                    delta=Decimal(str(greeks_data.get("delta", 0))),
                    gamma=Decimal(str(greeks_data.get("gamma", 0))),
                    theta=Decimal(str(greeks_data.get("theta", 0))),
                    vega=Decimal(str(greeks_data.get("vega", 0))),
                    implied_volatility=Decimal(str(greeks_data.get("mid_iv", 0))),
                ),
            )
            if contract.option_type == OptionType.CALL:
                calls.append(contract)
            else:
                puts.append(contract)

        quote_result = await self._request("GET", "/v1/markets/quotes", params={"symbols": symbol})
        quote = quote_result.get("quotes", {}).get("quote", {})
        underlying_price = Decimal(str(quote.get("last", 0)))

        return OptionsChain(underlying=symbol, expiration=expiration,
            underlying_price=underlying_price,
            calls=sorted(calls, key=lambda c: c.strike),
            puts=sorted(puts, key=lambda p: p.strike))

    async def submit_multileg_order(self, legs: list[OrderLeg], price: Decimal) -> OrderResult:
        account_id = await self._ensure_account_id()
        data = {"class": "multileg", "symbol": self._extract_underlying(legs[0].option_symbol),
            "type": "credit" if price > 0 else "debit", "duration": "day", "price": str(abs(price))}
        for i, leg in enumerate(legs):
            data[f"option_symbol[{i}]"] = leg.option_symbol
            data[f"side[{i}]"] = SIDE_MAP[leg.side.value]
            data[f"quantity[{i}]"] = str(leg.quantity)
        result = await self._request("POST", f"/v1/accounts/{account_id}/orders", data=data)
        order = result.get("order", {})
        return OrderResult(broker_order_id=str(order.get("id", "")), status=OrderStatus.PENDING)

    @staticmethod
    def _extract_underlying(option_symbol: str) -> str:
        match = re.match(r'^([A-Z]+)\d', option_symbol)
        return match.group(1) if match else option_symbol

    async def get_positions(self) -> list[dict]:
        account_id = await self._ensure_account_id()
        result = await self._request("GET", f"/v1/accounts/{account_id}/positions")
        positions = result.get("positions", {})
        if positions == "null" or not positions:
            return []
        position_list = positions.get("position", [])
        if not isinstance(position_list, list):
            position_list = [position_list]
        return position_list

    async def submit_order(self, leg: OrderLeg, price: Decimal) -> OrderResult:
        return await self.submit_multileg_order([leg], price)

    async def cancel_order(self, order_id: str) -> None:
        account_id = await self._ensure_account_id()
        await self._request("DELETE", f"/v1/accounts/{account_id}/orders/{order_id}")

    async def get_order_status(self, order_id: str) -> str:
        account_id = await self._ensure_account_id()
        result = await self._request("GET", f"/v1/accounts/{account_id}/orders/{order_id}")
        return result.get("order", {}).get("status", "unknown")
