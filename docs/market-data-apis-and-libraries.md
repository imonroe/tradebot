# Market Data APIs & Technical Analysis Libraries for Trading Bots

> **Note:** This report reflects the state of these services as of early 2025. Pricing, features,
> and availability may have changed. Always verify current details on each provider's website
> before making architectural decisions.

---

## Table of Contents

1. [Real-time & Historical Market Data APIs](#real-time--historical-market-data-apis)
   - [Polygon.io](#1-polygonio)
   - [Alpha Vantage](#2-alpha-vantage)
   - [Yahoo Finance (yfinance)](#3-yahoo-finance-yfinance)
   - [IEX Cloud](#4-iex-cloud)
   - [Finnhub](#5-finnhub)
   - [Tiingo](#6-tiingo)
   - [Other Notable Providers](#7-other-notable-providers)
2. [Comparison Matrix](#data-api-comparison-matrix)
3. [Technical Analysis Libraries (Python)](#technical-analysis-libraries-python)
4. [Backtesting Frameworks](#backtesting-frameworks)
5. [Recommendations](#recommendations)

---

## Real-time & Historical Market Data APIs

### 1. Polygon.io

**Overview:** One of the most comprehensive market data platforms, offering stocks, options, forex, and crypto data. Used widely in the algorithmic trading community.

| Attribute | Details |
|---|---|
| **Pricing** | Free (Basic) / Starter ($29/mo) / Developer ($79/mo) / Advanced ($199/mo) / Business (custom) |
| **Real-time vs Delayed** | Free tier: 15-min delayed. Starter+: real-time SIP data for US stocks. |
| **Historical Data** | Full historical tick-level data back to 2003+ for stocks. Aggregates (1min, 5min, daily, etc.) available on all tiers. |
| **Options Data** | Yes -- full options chain snapshots, historical options aggregates, and options trades. Available on Developer tier and above. |
| **WebSocket/Streaming** | Yes -- WebSocket streaming for stocks, options, forex, crypto. Real-time on paid tiers. |
| **Free Tier Limits** | 5 API calls/minute. Delayed data only. Limited to basic endpoints (aggregates, grouped daily). No WebSocket streaming. |
| **Rate Limits** | Free: 5/min. Starter: unlimited API calls. Developer+: unlimited with higher burst limits. |
| **Python Library** | Official `polygon-api-client` (pip install polygon-api-client). Well-maintained, supports REST + WebSocket. |

**Strengths:**
- Excellent data quality (SIP-level real-time data on paid plans)
- Very comprehensive options data
- Flat-rate pricing (not message/credit-based)
- Active development and good documentation
- Strong WebSocket implementation

**Weaknesses:**
- Free tier is quite limited (5 calls/min, delayed data)
- Options data requires mid-tier subscription
- Historical tick data can be large to process

---

### 2. Alpha Vantage

**Overview:** Long-standing free-tier-friendly API providing stocks, forex, crypto, and economic indicators. Popular for prototyping and hobby projects.

| Attribute | Details |
|---|---|
| **Pricing** | Free / Premium ($49.99/mo) / Enterprise (custom) |
| **Real-time vs Delayed** | Free: 15-min delayed quotes. Premium: real-time quotes. |
| **Historical Data** | Up to 20+ years of daily data. Intraday data (1min, 5min, 15min, 30min, 60min) available with varying depth (free: last 1-2 months intraday; premium: extended). |
| **Options Data** | Added historical options data endpoint (as of 2024). Coverage and depth are more limited than Polygon. |
| **WebSocket/Streaming** | No native WebSocket support. REST-only polling model. |
| **Free Tier Limits** | 25 API calls/day (reduced from the previous 500/day limit as of late 2023). This is extremely restrictive. |
| **Rate Limits** | Free: 25 calls/day. Premium: 75 calls/min, no daily limit. |
| **Python Library** | `alpha_vantage` (pip install alpha_vantage). Community-maintained; returns pandas DataFrames. |

**Strengths:**
- Wide variety of data: stocks, forex, crypto, economic indicators, commodities
- Simple REST API, easy to get started
- Fundamental data (earnings, balance sheets, income statements)
- Technical indicator endpoints built-in (SMA, EMA, RSI, etc.)

**Weaknesses:**
- Free tier severely limited at 25 calls/day (practically unusable for real trading)
- No WebSocket/streaming support
- Data quality can be inconsistent (known issues with adjusted close values)
- Intraday historical depth is limited on the free tier
- Slow response times compared to competitors

---

### 3. Yahoo Finance (yfinance)

**Overview:** The `yfinance` Python library scrapes data from Yahoo Finance. It is not an official API -- it reverse-engineers Yahoo's internal endpoints. Extremely popular due to being free and easy to use.

| Attribute | Details |
|---|---|
| **Pricing** | Free (unofficial/scraped) |
| **Real-time vs Delayed** | ~15-min delayed quotes (varies by exchange). Not suitable for real-time trading. |
| **Historical Data** | Daily data back to the 1960s for major tickers. 1-minute intraday going back ~30 days. 1-hour intraday going back ~2 years. |
| **Options Data** | Yes -- options chains (current expiration dates, strikes, greeks). No historical options data. |
| **WebSocket/Streaming** | No |
| **Free Tier Limits** | No official limits, but aggressive scraping will get your IP rate-limited or blocked. |
| **Rate Limits** | Unofficial; ~2,000 requests/hour is generally safe. Yahoo actively blocks automated scraping periodically. |
| **Python Library** | `yfinance` (pip install yfinance). Very popular, 12k+ GitHub stars. |

**Strengths:**
- Completely free with no API key needed
- Broad ticker coverage (global markets)
- Easy pandas DataFrame integration
- Good for prototyping, backtesting with daily data, and research
- Active community maintenance (ranaroussi/yfinance)
- Includes basic fundamentals (P/E, market cap, financials)

**Weaknesses:**
- **Reliability is the core issue.** Yahoo periodically changes their internal endpoints, breaking the library. Expect occasional downtime (hours to days) until maintainers patch it.
- Not suitable for production trading systems
- No guaranteed uptime or SLA
- Data quality issues (adjusted prices sometimes incorrect, missing data points)
- Can get IP-blocked with high-frequency requests
- Yahoo has increasingly added anti-scraping measures; some endpoints now require cookies/consent
- No WebSocket or real-time data

**Viability assessment:** Still widely used as of early 2025 for research and backtesting. Should NOT be relied upon for live trading. The library has survived multiple "death scares" and the community consistently patches breakages, but expect periodic disruptions.

---

### 4. IEX Cloud

**Overview:** Originally built on IEX Exchange data, IEX Cloud pivoted significantly in 2023-2024. The service underwent major changes.

| Attribute | Details |
|---|---|
| **Pricing** | IEX Cloud underwent a major restructuring. The legacy free tier was discontinued. Current plans start at ~$19/mo (Launch) up to enterprise tiers. They introduced a credit-based pricing model. |
| **Real-time vs Delayed** | IEX Exchange real-time data (which covers ~2-3% of US equity volume). SIP real-time data on higher tiers. 15-min delayed data on lower tiers. |
| **Historical Data** | 5+ years daily, 90 days intraday on standard plans. Deeper history on premium. |
| **Options Data** | Limited. IEX Cloud was not strong on options data historically. |
| **WebSocket/Streaming** | SSE (Server-Sent Events) streaming available on paid plans. |
| **Free Tier Limits** | Legacy free tier discontinued. There may be a trial/limited free tier, but it is no longer a selling point. |
| **Rate Limits** | Credit-based system. Each API call costs a certain number of credits depending on the endpoint. |
| **Python Library** | `pyex` or `iexfinance` (community libraries). Less actively maintained since the restructuring. |

**Current Status Assessment:** IEX Cloud has lost significant community mindshare after discontinuing its generous free tier and pivoting to a credit-based model. The credit system makes costs harder to predict. Many developers who used the free tier have migrated to alternatives (Polygon, Finnhub, Tiingo). Still functional, but no longer the go-to recommendation it once was.

**Strengths:**
- Clean, well-documented API
- Good fundamental/reference data
- IEX Exchange data is truly real-time (not delayed)

**Weaknesses:**
- Credit-based pricing is confusing and can get expensive
- Free tier effectively gone
- Weaker options data coverage
- Community libraries less actively maintained
- IEX Exchange data only covers a fraction of total market volume

---

### 5. Finnhub

**Overview:** A comprehensive financial data API with a generous free tier. Covers stocks, forex, crypto, and alternative data. Strong on fundamental data and news.

| Attribute | Details |
|---|---|
| **Pricing** | Free / All-in-One ($149/mo) / Enterprise (custom) |
| **Real-time vs Delayed** | Free: real-time data for US stocks (trades, not full NBBO quotes). Paid: fuller real-time coverage. |
| **Historical Data** | Free: limited intraday (last 1 month of 1-min candles). Daily candles going back ~20 years. Paid: deeper intraday history. |
| **Options Data** | No options chain data. This is a significant gap. |
| **WebSocket/Streaming** | Yes -- WebSocket for real-time trades and news. Available on free tier (limited symbols). |
| **Free Tier Limits** | 60 API calls/minute. WebSocket available with limits on concurrent subscriptions. |
| **Rate Limits** | Free: 60 calls/min. Paid: 300+ calls/min. |
| **Python Library** | `finnhub-python` (pip install finnhub-python). Official, well-maintained. |

**Strengths:**
- Generous free tier (60 calls/min with WebSocket access)
- Real-time US stock trades on the free tier
- Excellent alternative data: congressional trading, insider transactions, ESG scores, earnings estimates
- News/sentiment endpoints
- International stock coverage
- Good fundamental data (financials, SEC filings)

**Weaknesses:**
- No options data
- Intraday historical data limited on free tier
- Data granularity not as fine as Polygon (no tick-level data)
- Real-time data on free tier is trade-level, not full quote-level
- Price jump to $149/mo for the first paid tier is steep

---

### 6. Tiingo

**Overview:** A smaller but respected data provider focused on quality and affordability. Strong in the algo trading community.

| Attribute | Details |
|---|---|
| **Pricing** | Free (Starter) / Power ($10/mo) / Commercial ($75/mo+) |
| **Real-time vs Delayed** | Free: end-of-day only. Power: IEX real-time quotes. Commercial: full SIP real-time. |
| **Historical Data** | Daily data back to 1960s (broad coverage). Intraday data (1-min, 5-min) back 5+ years on paid plans. |
| **Options Data** | No options chain data. |
| **WebSocket/Streaming** | Yes -- WebSocket for IEX real-time quotes and crypto. Available on Power tier+. |
| **Free Tier Limits** | 1,000 requests/day. End-of-day data only. 500 unique symbols/month. |
| **Rate Limits** | Free: ~20 requests/hr for some endpoints, 1,000/day overall. Power: 5,000/hr. Commercial: 20,000/hr. |
| **Python Library** | No official library, but REST API works easily with `requests`. Community packages exist but are less maintained. |

**Strengths:**
- Excellent price-to-value ratio ($10/mo for real-time IEX + deep historical)
- Very clean, well-structured data
- Good dividend-adjusted historical data
- Crypto and forex coverage
- News API included
- Founder is responsive to community feedback

**Weaknesses:**
- No options data
- Smaller company, less extensive documentation than Polygon
- No official Python SDK (though API is simple enough this is minor)
- IEX real-time on Power tier only covers ~2-3% of market volume
- Less feature-rich than Polygon or Finnhub for alternative data

---

### 7. Other Notable Providers

#### Alpaca Markets API
- **Free real-time data** for users with an Alpaca brokerage account (even paper trading)
- WebSocket streaming for trades and quotes
- Good historical data (bars, trades, quotes)
- No options data (Alpaca added options trading in 2024, data availability improving)
- Python SDK: `alpaca-py`
- Best if you also plan to use Alpaca as your broker -- data + execution in one platform

#### Databento
- Professional-grade market data (tick-level, L2/L3 order book)
- Pay-per-use pricing model (by data volume consumed)
- Extremely high-quality normalized data across multiple exchanges
- Supports options, futures, equities
- Python SDK: `databento`
- Best for serious quantitative work; overkill for most hobby projects

#### Unusual Whales
- Focused on options flow data, dark pool data, congressional trading
- Options chain and historical options flow data
- Subscription-based ($57/mo+)
- Python API available
- Niche but valuable for options-focused strategies

#### CBOE LiveVol / Options Data
- Institutional-grade historical options data
- Expensive (hundreds to thousands per month)
- Best for serious options research and backtesting

#### Interactive Brokers TWS API
- Real-time and historical data included with IB brokerage account
- Comprehensive options data
- Python SDK: `ib_insync` (community) or official `ibapi`
- Rate limits exist but are reasonable for personal use
- Best if you already use IB as your broker

---

## Data API Comparison Matrix

| Feature | Polygon.io | Alpha Vantage | yfinance | IEX Cloud | Finnhub | Tiingo |
|---|---|---|---|---|---|---|
| **Free Tier** | Yes (limited) | Yes (25/day) | Free (unofficial) | Trial only | Yes (generous) | Yes (EOD only) |
| **Real-time Data** | Paid only | Paid only | No (~15min delay) | Paid only | Free (trades) | Paid only |
| **WebSocket** | Yes (paid) | No | No | SSE (paid) | Yes (free) | Yes (paid) |
| **Options Data** | Yes (strong) | Limited | Current chains | Limited | No | No |
| **Historical Depth** | Excellent | Good | Good (daily) | Moderate | Good | Excellent |
| **Intraday History** | Excellent | Limited | ~30 days (1min) | 90 days | Limited (free) | Good (paid) |
| **Python SDK** | Official | Community | Community | Community | Official | None (REST) |
| **Best Free Tier** | -- | -- | -- | -- | **Winner** | -- |
| **Best Options** | **Winner** | -- | -- | -- | -- | -- |
| **Best Value Paid** | -- | -- | -- | -- | -- | **Winner** |
| **Min Cost for RT** | $29/mo | $49.99/mo | N/A | ~$19/mo | Free | $10/mo |

---

## Technical Analysis Libraries (Python)

### 1. TA-Lib (ta-lib-python)

**Package:** `TA-Lib` (pip install TA-Lib -- requires C library installation)

**Overview:** The gold standard for technical analysis. A Python wrapper around the C-based TA-Lib library originally developed by Mario Fortier. Covers 200+ indicators.

**Indicators (200+):**
- Overlap: SMA, EMA, BBANDS, DEMA, HT_TRENDLINE, KAMA, MA, MAMA, MAVP, MIDPOINT, MIDPRICE, SAR, SAREXT, T3, TEMA, TRIMA, WMA
- Momentum: ADX, ADXR, APO, AROON, BOP, CCI, CMO, DX, MACD, MFI, MINUS_DI, MOM, PPO, ROC, RSI, STOCH, STOCHF, STOCHRSI, TRIX, ULTOSC, WILLR
- Volume: AD, ADOSC, OBV
- Volatility: ATR, NATR, TRANGE
- Pattern Recognition: 61 candlestick patterns (CDL_DOJI, CDL_ENGULFING, CDL_HAMMER, etc.)
- Statistical: BETA, CORREL, LINEARREG, STDDEV, TSF, VAR

**Pros:**
- Extremely fast (C-based computation)
- Battle-tested, industry standard
- Widest indicator coverage
- Numpy array interface
- Candlestick pattern recognition (unique to TA-Lib)

**Cons:**
- **Installation is notoriously painful.** Requires the C TA-Lib library to be installed first, which fails on many systems without manual compilation.
  - Linux: `sudo apt-get install ta-lib` or compile from source
  - macOS: `brew install ta-lib`
  - Windows: Pre-built wheels or conda install
- API is functional but not very Pythonic
- Does not natively work with pandas DataFrames (requires numpy arrays, though wrappers exist)
- The upstream C library is no longer actively maintained

**Installation tip:** Use `conda install -c conda-forge ta-lib` for the smoothest experience across platforms.

---

### 2. pandas-ta

**Package:** `pandas_ta` (pip install pandas_ta)

**Overview:** A pure-Python technical analysis library built as a pandas DataFrame extension. No C dependencies. Covers 130+ indicators.

**Indicators (130+):**
- Trend: ADX, Aroon, MACD, PSAR, Supertrend, Ichimoku, and more
- Momentum: RSI, Stochastic, CCI, Williams %R, ROC, and more
- Volatility: Bollinger Bands, ATR, Keltner Channels, Donchian Channels
- Volume: OBV, MFI, VWAP, AD, CMF
- Overlap: SMA, EMA, WMA, HMA, DEMA, TEMA, and more
- Statistics: zscore, entropy, variance

**Pros:**
- Pure Python -- `pip install pandas_ta` just works everywhere
- Native pandas integration (use as `df.ta.rsi()`)
- Clean, Pythonic API
- Strategy system for applying multiple indicators at once
- Active development and good documentation
- No compilation required

**Cons:**
- Slower than TA-Lib for large datasets (pure Python vs C)
- Fewer candlestick patterns than TA-Lib
- Some indicators may produce slightly different results than TA-Lib (edge cases in calculation methods)
- Development pace has slowed somewhat (check GitHub for recent activity)

---

### 3. tulipy

**Package:** `tulipy` (pip install tulipy)

**Overview:** Python bindings for the Tulip Indicators C library. A lighter-weight alternative to TA-Lib.

**Indicators (~100):**
- Standard set: SMA, EMA, RSI, MACD, BBANDS, ATR, ADX, Stochastic, etc.

**Pros:**
- Fast (C-based)
- Easier to install than TA-Lib (ships with the C source, compiles during pip install)
- Clean, simple API
- Lightweight

**Cons:**
- Fewer indicators than TA-Lib or pandas-ta
- No candlestick pattern recognition
- Smaller community
- Less documentation
- Numpy-only interface (no pandas integration)
- Less actively maintained

---

### 4. Other Notable Libraries

#### ta (Technical Analysis Library in Python)
- **Package:** `ta` (pip install ta)
- Pure Python, pandas-native
- ~80 indicators organized by type
- Simple and clean API: `ta.momentum.RSIIndicator(close, window=14)`
- Good for beginners
- Less comprehensive than pandas-ta

#### finta (Financial Technical Analysis)
- **Package:** `finta` (pip install finta)
- Pure Python, pandas-based
- ~80 indicators
- Simple DataFrame interface: `TA.RSI(df)`
- Lightweight and easy to use

#### stockstats
- **Package:** `stockstats` (pip install stockstats)
- Wraps pandas DataFrame, access indicators as columns
- Usage: `stock['rsi_14']` automatically computes RSI
- Convenient but limited indicator set

### TA Library Comparison

| Feature | TA-Lib | pandas-ta | tulipy | ta |
|---|---|---|---|---|
| **Indicators** | 200+ | 130+ | ~100 | ~80 |
| **Speed** | Fastest (C) | Moderate (Python) | Fast (C) | Moderate (Python) |
| **Install Ease** | Difficult | Easy (pip) | Moderate | Easy (pip) |
| **Pandas Native** | No | Yes | No | Yes |
| **Candlestick Patterns** | Yes (61) | Limited | No | No |
| **Active Maintenance** | Low (C lib frozen) | Moderate | Low | Moderate |
| **Best For** | Production speed | General use | Lightweight C alt | Beginners |

---

## Backtesting Frameworks

### 1. Backtrader

**Package:** `backtrader` (pip install backtrader)

**Overview:** One of the most popular Python backtesting frameworks. Event-driven architecture. Mature and feature-rich.

**Features:**
- Event-driven backtesting engine
- Multiple data feeds simultaneously
- Built-in indicators (100+)
- Broker simulation with commission models
- Order types: market, limit, stop, stop-limit, trailing stop
- Position sizing with sizers
- Analyzers: Sharpe ratio, drawdown, trade statistics, returns
- Plotting with matplotlib
- Live trading support (IB, OANDA, and more via plugins)
- Cerebro engine orchestrates everything

**Pros:**
- Mature, well-documented
- Large community with many examples
- Flexible strategy definition
- Can transition from backtest to live trading
- Support for multiple timeframes and data feeds
- Extensive built-in analyzers

**Cons:**
- **No longer actively maintained** (last commit 2021-ish). Works but no new features or bug fixes.
- Somewhat steep learning curve
- Single-threaded, can be slow for large backtests
- Plotting is basic
- Python 3.11+ compatibility can have issues
- Documentation, while extensive, can be disorganized

---

### 2. Zipline / zipline-reloaded

**Package:** `zipline-reloaded` (pip install zipline-reloaded)

**Overview:** Originally developed by Quantopian (now defunct). `zipline-reloaded` is a community-maintained fork that keeps it alive. Event-driven, designed for daily/minute-bar strategies.

**Features:**
- Event-driven backtesting
- Pipeline API for factor-based screening
- Integrated risk model
- Slippage and commission models
- Daily and minute-bar data support
- Calendar-aware (trading calendars for various exchanges)
- Integration with pyfolio for performance analysis

**Pros:**
- Solid algorithmic design
- Pipeline API is powerful for cross-sectional strategies
- Good integration with pyfolio/empyrical for analysis
- Handles corporate actions (splits, dividends) properly

**Cons:**
- Complex installation (many dependencies including bcolz, numpy version constraints)
- Steep learning curve
- Requires specific data bundle format (Quandl WIKI bundle is dead; need custom ingest)
- Community fork is maintained but development is slow
- Heavy for simple strategies
- Memory-hungry for large universes

---

### 3. VectorBT

**Package:** `vectorbt` (pip install vectorbt)

**Overview:** A blazingly fast backtesting library built on numpy and numba. Uses vectorized operations instead of event-driven loops. Designed for rapid prototyping and parameter optimization.

**Features:**
- Vectorized backtesting (orders of magnitude faster than event-driven)
- Portfolio simulation
- Built-in indicators
- Parameter optimization with grid search
- Interactive Plotly-based visualizations
- Statistical analysis and metrics
- Supports custom signals

**Pros:**
- **Extremely fast** -- can test thousands of parameter combinations in seconds
- Excellent for parameter optimization and exploration
- Beautiful interactive plots (Plotly)
- Good pandas/numpy integration
- Active development
- Great for research and prototyping

**Cons:**
- Vectorized model is less realistic than event-driven (harder to model complex order logic)
- Not designed for live trading
- Pro version (vectorbt-pro) gates some features behind a paid license
- Learning curve for the vectorized paradigm
- Less intuitive for complex multi-asset strategies
- Cannot easily model strategies that depend on real-time portfolio state

---

### 4. Other Notable Frameworks

#### Lean (QuantConnect)
- Open-source C#/Python backtesting engine
- Cloud-based IDE with free backtesting on QuantConnect.com
- Institutional-quality engine
- Live trading support for multiple brokers
- Huge indicator library
- Steep learning curve, but very powerful
- **Package:** Can run locally or use QuantConnect cloud

#### bt (Backtesting Toolkit)
- **Package:** `bt` (pip install bt)
- Tree-based strategy structure
- Good for portfolio rebalancing strategies
- Simple API
- Lightweight

#### Backtesting.py
- **Package:** `backtesting` (pip install backtesting)
- Very simple, beginner-friendly
- Single-file strategies
- Interactive Bokeh-based plots
- Limited features but great for learning
- Quick to set up and run

#### PyAlgoTrade
- Older framework, less actively maintained
- Event-driven
- Simple but limited

### Backtesting Framework Comparison

| Feature | Backtrader | Zipline-Reloaded | VectorBT | Lean/QC | Backtesting.py |
|---|---|---|---|---|---|
| **Architecture** | Event-driven | Event-driven | Vectorized | Event-driven | Event-driven |
| **Speed** | Moderate | Moderate | Very Fast | Fast | Moderate |
| **Learning Curve** | Medium | High | Medium | High | Low |
| **Live Trading** | Yes (plugins) | No | No | Yes | No |
| **Active Maint.** | No | Low | Yes | Yes | Moderate |
| **Visualization** | Matplotlib | Pyfolio | Plotly | Web UI | Bokeh |
| **Best For** | Full workflow | Factor models | Research/optim | Production | Beginners |

---

## Recommendations

### For a Trading Bot Project

#### Data Provider
- **If budget allows ($29/mo):** Polygon.io Starter tier. Best overall data quality, real-time data, WebSocket support, and options data on higher tiers.
- **If free is essential:** Finnhub free tier (60 calls/min, real-time trades, WebSocket) for live data + yfinance for historical data backfill.
- **Best value:** Tiingo Power ($10/mo) for real-time IEX data + deep historical. Pair with yfinance for options chains if needed.
- **If you need options data:** Polygon.io (Developer tier, $79/mo) or Interactive Brokers API (free with brokerage account).

#### Technical Analysis Library
- **Default choice:** `pandas-ta` -- easy install, pandas-native, comprehensive indicators.
- **If speed matters:** `TA-Lib` -- fastest computation, but plan for installation complexity.
- **Quick prototyping:** `ta` -- simplest API, good enough for most common indicators.

#### Backtesting Framework
- **For research and optimization:** VectorBT -- fastest iteration speed, great visualizations.
- **For realistic simulation:** Backtrader -- most complete event-driven framework despite being unmaintained.
- **For beginners:** Backtesting.py -- get something running in minutes.
- **For production-grade:** Lean/QuantConnect -- most robust, supports live trading.

### Suggested Architecture

```
Historical Data (Polygon/yfinance) --> Backtesting (VectorBT/Backtrader)
                                           |
                                      Strategy Development
                                           |
Live Data (Polygon WebSocket/Finnhub) --> Live Trading Engine
                                           |
                                      Technical Analysis (pandas-ta/TA-Lib)
                                           |
                                      Broker API (Alpaca/IB)
```

### Key Considerations

1. **Do not rely on a single free data source for production.** yfinance breaks periodically. Free tiers have rate limits that will bite you during market hours.

2. **Start with daily bars for backtesting, then move to intraday.** Daily data is widely available, free, and easier to work with. Optimize your strategy on daily data before paying for intraday.

3. **Separate your data layer from your strategy layer.** Use an abstraction so you can swap data providers without rewriting your strategy code.

4. **Options data is expensive.** If your strategy needs historical options data, budget accordingly. Polygon Developer ($79/mo) or Databento are the most accessible options.

5. **Consider Alpaca as a 2-in-1 solution.** Free real-time data + brokerage API for execution. Good for getting started without paying for a separate data provider.
