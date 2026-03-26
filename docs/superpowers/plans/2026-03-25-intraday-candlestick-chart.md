# Plan: Intraday Candlestick Chart

**Date:** 2026-03-25
**Status:** Implementation

## Problem Statement

The dashboard shows NAV history but provides no visibility into underlying price movement. Traders need to see intraday OHLC candlestick charts for the underlying (XSP) to understand market context alongside their trading activity.

## Design

### Approach: Persist Polled Bars

The bot loop already fetches a `Bar` (OHLCV) every 60 seconds. We persist each bar to the database, then aggregate into user-selected intervals (1m, 5m, 15m, 1h) at query time. This avoids complex in-process aggregation and gives us raw data to re-aggregate however we want.

### Database

New `price_bars` table:
- `id`, `symbol`, `timestamp`, `open`, `high`, `low`, `close`, `volume`
- Unique constraint on `(symbol, timestamp)` to prevent duplicates on restart
- Index on `(symbol, timestamp)` for fast range queries

### API Endpoint

`GET /api/price-history?symbol=XSP&interval=5m&hours=8`

- `symbol`: underlying ticker (default: first strategy's symbol)
- `interval`: candle width — `1m`, `5m`, `15m`, `1h` (default: `5m`)
- `hours`: lookback window in hours (default: 8, i.e. one trading day)

Server-side aggregation: group raw 1m bars into the requested interval using SQL or Python, computing OHLC per bucket.

### Frontend

New `CandlestickChart.tsx` component using Recharts `ComposedChart`:
- Green/red bars for up/down candles
- Wicks (high/low) as thin error bars
- Time scale selector buttons: 1m | 5m | 15m | 1h
- Hours selector: 2h | 4h | 8h | 1D
- Auto-refresh every 60s

Placed on Dashboard between NAV chart and analytics section.

## Files Changed

| File | Change |
|------|--------|
| `src/tradebot/persistence/models.py` | Add `PriceBarRecord` |
| `alembic/versions/..._add_price_bars_table.py` | New migration |
| `src/tradebot/persistence/repository.py` | Add `save_price_bar()`, `get_price_bars()` |
| `src/tradebot/main.py` | Persist bar after each poll |
| `src/tradebot/api/routes/price_history.py` | New — price history endpoint with aggregation |
| `src/tradebot/api/app.py` | Register price history router |
| `frontend/src/components/CandlestickChart.tsx` | New — candlestick chart with interval selector |
| `frontend/src/pages/Dashboard.tsx` | Include CandlestickChart |
| `tests/unit/test_price_history.py` | New — tests for aggregation + API |
| `README.md`, `CLAUDE.md` | Update docs |

## Success Criteria

1. Bot persists 1m bars to `price_bars` table on each poll
2. `GET /api/price-history` returns aggregated OHLC candles
3. Dashboard displays candlestick chart with selectable intervals
4. All tests pass
