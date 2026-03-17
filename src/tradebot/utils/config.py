"""Configuration loading for infrastructure and strategy settings."""
from decimal import Decimal
from pathlib import Path
from typing import Literal
import yaml
from pydantic import BaseModel, field_validator
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    mode: Literal["paper", "live"] = "paper"
    log_level: str = "INFO"
    database_url: str = "sqlite:///tradebot.db"
    starting_capital: Decimal = Decimal("2500.00")
    max_daily_loss_pct: Decimal = Decimal("3.0")
    max_drawdown_pct: Decimal = Decimal("10.0")
    pdt_limit: int = 3
    broker_name: str = "tradier"
    broker_base_url: str = "https://sandbox.tradier.com"
    tradier_api_token: str = ""
    paper_base_price: Decimal = Decimal("570.00")
    record_market_data: bool = False
    model_config = {"env_prefix": "TRADEBOT_"}

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        if v not in ("paper", "live"):
            raise ValueError(f"mode must be 'paper' or 'live', got '{v}'")
        return v

class StrategyInfo(BaseModel):
    name: str
    class_name: str | None = None
    enabled: bool = True
    model_config = {"populate_by_name": True}
    def __init__(self, **data):
        if "class" in data:
            data["class_name"] = data.pop("class")
        super().__init__(**data)

class MarketConfig(BaseModel):
    symbol: str
    expiration: str = "0dte"

class TimeWindow(BaseModel):
    earliest: str = "09:30"
    latest: str = "16:00"

class StrikeSelection(BaseModel):
    method: str = "delta"
    short_call_delta: float = 0.15
    short_put_delta: float = -0.15
    wing_width: int = 5

class IVFilter(BaseModel):
    min_iv_rank: float = 0.0

class EntryConfig(BaseModel):
    time_window: TimeWindow = TimeWindow()
    strike_selection: StrikeSelection = StrikeSelection()
    iv_filter: IVFilter = IVFilter()
    min_credit: float = 0.0

class ExitConfig(BaseModel):
    profit_target_pct: float = 50.0
    stop_loss_pct: float = 200.0
    time_exit: str = "15:45"
    prefer_expire: bool = True

class PositionSizingConfig(BaseModel):
    method: str = "fixed_risk"
    max_risk_per_trade: int = 250
    max_contracts: int = 2

class RiskConfig(BaseModel):
    max_daily_trades: int = 1
    pdt_aware: bool = True

class StrategyConfig(BaseModel):
    strategy: StrategyInfo
    market: MarketConfig
    entry: EntryConfig = EntryConfig()
    exit: ExitConfig = ExitConfig()
    position_sizing: PositionSizingConfig = PositionSizingConfig()
    risk: RiskConfig = RiskConfig()

def load_strategy_config(path: Path) -> StrategyConfig:
    with open(path) as f:
        raw = yaml.safe_load(f)
    return StrategyConfig(**raw)
