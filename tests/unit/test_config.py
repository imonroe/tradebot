"""Tests for configuration loading."""
from decimal import Decimal
from pathlib import Path
import pytest
from tradebot.utils.config import Settings, load_strategy_config

def test_default_settings():
    settings = Settings()
    assert settings.mode == "paper"
    assert settings.log_level == "INFO"
    assert settings.database_url == "sqlite:///tradebot.db"
    assert settings.max_daily_loss_pct == Decimal("3.0")
    assert settings.pdt_limit == 3

def test_settings_paper_mode():
    settings = Settings(mode="paper")
    assert settings.mode == "paper"

def test_settings_rejects_invalid_mode():
    with pytest.raises(ValueError):
        Settings(mode="invalid")

def test_load_strategy_config(tmp_path: Path):
    yaml_content = """
strategy:
  name: "test_strategy"
  class: "IronCondorStrategy"
  enabled: true
market:
  symbol: "XSP"
  expiration: "0dte"
entry:
  time_window:
    earliest: "09:45"
    latest: "14:00"
  strike_selection:
    method: "delta"
    short_call_delta: 0.15
    short_put_delta: -0.15
    wing_width: 5
  min_credit: 0.30
exit:
  profit_target_pct: 50
  stop_loss_pct: 200
  time_exit: "15:45"
  prefer_expire: true
position_sizing:
  method: "fixed_risk"
  max_risk_per_trade: 250
  max_contracts: 2
risk:
  max_daily_trades: 1
  pdt_aware: true
"""
    config_file = tmp_path / "test_strategy.yaml"
    config_file.write_text(yaml_content)
    config = load_strategy_config(config_file)
    assert config.strategy.name == "test_strategy"
    assert config.market.symbol == "XSP"
    assert config.entry.strike_selection.short_call_delta == 0.15
    assert config.exit.prefer_expire is True
    assert config.position_sizing.max_risk_per_trade == 250
    assert config.risk.pdt_aware is True
