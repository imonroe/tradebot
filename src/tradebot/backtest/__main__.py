"""CLI entry point for backtesting: python -m tradebot.backtest"""
import argparse
import asyncio
from datetime import date
from decimal import Decimal
from pathlib import Path

from tradebot.backtest.engine import run_backtest
from tradebot.utils.logging import setup_logging


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a backtest")
    parser.add_argument("--strategy", required=True, help="Path to strategy YAML config")
    parser.add_argument("--start", required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", required=True, help="End date (YYYY-MM-DD)")
    parser.add_argument("--interval", type=int, default=15, help="Minutes between data points (default: 15)")
    parser.add_argument("--capital", type=Decimal, default=Decimal("2500"), help="Starting capital (default: 2500)")
    parser.add_argument("--slippage", type=Decimal, default=Decimal("0"), help="Slippage percent (default: 0)")
    parser.add_argument("--save", action="store_true", help="Save results to database")

    args = parser.parse_args()

    setup_logging()

    result = asyncio.run(run_backtest(
        strategy_config_path=Path(args.strategy),
        start_date=date.fromisoformat(args.start),
        end_date=date.fromisoformat(args.end),
        interval_minutes=args.interval,
        starting_capital=args.capital,
        slippage_pct=args.slippage,
    ))

    result.print_summary()

    if args.save:
        from tradebot.persistence.database import Base, create_db_engine, create_session
        from tradebot.persistence.repository import Repository
        from tradebot.utils.config import Settings

        settings = Settings()
        engine = create_db_engine(settings.database_url)
        Base.metadata.create_all(engine)
        session = create_session(engine)
        repo = Repository(session)
        repo.save_backtest_run(result)
        repo.commit()
        print("  Results saved to database.")


if __name__ == "__main__":
    main()
