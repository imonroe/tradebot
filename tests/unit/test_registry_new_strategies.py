"""Tests for loading credit and debit spread strategies from YAML."""
from pathlib import Path

from tradebot.strategy.registry import load_strategy
from tradebot.strategy.strategies.credit_spread import CreditSpreadStrategy
from tradebot.strategy.strategies.debit_spread import DebitSpreadStrategy


def test_load_credit_spread(tmp_path: Path):
    config = tmp_path / "credit.yaml"
    config.write_text("""
strategy:
  name: "test_credit"
  class: "CreditSpreadStrategy"
  enabled: true
market:
  symbol: "XSP"
  expiration: "0dte"
entry:
  direction: "put"
  time_window:
    earliest: "09:45"
    latest: "14:00"
  strike_selection:
    method: "delta"
    short_delta: 0.15
    wing_width: 5
  min_credit: 0.15
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
""")
    strategy = load_strategy(config)
    assert isinstance(strategy, CreditSpreadStrategy)
    assert strategy.name == "test_credit"
    assert strategy.symbol == "XSP"
    assert strategy.direction == "put"


def test_load_debit_spread(tmp_path: Path):
    config = tmp_path / "debit.yaml"
    config.write_text("""
strategy:
  name: "test_debit"
  class: "DebitSpreadStrategy"
  enabled: true
market:
  symbol: "XSP"
  expiration: "0dte"
entry:
  direction: "call"
  time_window:
    earliest: "09:45"
    latest: "14:00"
  strike_selection:
    method: "delta"
    long_delta: 0.40
    short_delta: 0.20
  max_debit: 3.00
exit:
  profit_target_pct: 100
  stop_loss_pct: 75
  time_exit: "15:45"
  prefer_expire: true
position_sizing:
  method: "fixed_risk"
  max_risk_per_trade: 250
  max_contracts: 2
risk:
  max_daily_trades: 1
  pdt_aware: true
""")
    strategy = load_strategy(config)
    assert isinstance(strategy, DebitSpreadStrategy)
    assert strategy.name == "test_debit"
    assert strategy.symbol == "XSP"
    assert strategy.direction == "call"
