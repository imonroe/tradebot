"""Price history API route with interval aggregation."""
from datetime import datetime, timedelta

from fastapi import APIRouter, Query, Request

router = APIRouter(tags=["price-history"])

VALID_INTERVALS = {"1m": 1, "5m": 5, "15m": 15, "1h": 60}


def aggregate_bars(bars: list, interval_minutes: int) -> list[dict]:
    """Aggregate 1-minute bars into larger candles.

    Groups bars by flooring timestamp to the interval boundary,
    then computes OHLCV for each bucket.
    """
    # Ensure bars are sorted by timestamp for correct open/close
    bars = sorted(bars, key=lambda b: b.timestamp)
    if not bars or interval_minutes <= 1:
        return [
            {
                "timestamp": b.timestamp.isoformat(),
                "open": str(b.open),
                "high": str(b.high),
                "low": str(b.low),
                "close": str(b.close),
                "volume": b.volume,
            }
            for b in bars
        ]

    buckets: dict[datetime, list] = {}
    for b in bars:
        # Floor to interval boundary
        ts = b.timestamp
        minutes_since_midnight = ts.hour * 60 + ts.minute
        floored_minute = (minutes_since_midnight // interval_minutes) * interval_minutes
        bucket_ts = ts.replace(
            hour=floored_minute // 60,
            minute=floored_minute % 60,
            second=0, microsecond=0,
        )
        buckets.setdefault(bucket_ts, []).append(b)

    result = []
    for bucket_ts in sorted(buckets.keys()):
        group = buckets[bucket_ts]
        result.append({
            "timestamp": bucket_ts.isoformat(),
            "open": str(group[0].open),
            "high": str(max(b.high for b in group)),
            "low": str(min(b.low for b in group)),
            "close": str(group[-1].close),
            "volume": sum(b.volume for b in group),
        })
    return result


@router.get("/price-history")
async def get_price_history(
    request: Request,
    symbol: str | None = None,
    interval: str = Query(default="5m", pattern="^(1m|5m|15m|1h)$"),
    hours: int = Query(default=8, ge=1, le=168),
):
    """Get aggregated OHLC price bars for charting."""
    state = request.app.state.app_state
    if state.repository is None:
        return []

    # Default symbol from first strategy, fallback to XSP
    if symbol is None:
        symbol = state.strategies[0].symbol if state.strategies else "XSP"

    end = datetime.now()
    start = end - timedelta(hours=hours)
    bars = state.repository.get_price_bars(symbol=symbol, start=start, end=end)

    interval_minutes = VALID_INTERVALS.get(interval, 5)
    return aggregate_bars(bars, interval_minutes)
