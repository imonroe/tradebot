# Trading Broker API Research

> **Last updated:** March 2026
>
> **Disclaimer:** This report is based on knowledge through mid-2025. Items marked with
> (**VERIFY**) should be confirmed against current documentation, as details may have
> changed. Always check the official developer portals before building integrations.

---

## Table of Contents

1. [Alpaca](#1-alpaca)
2. [Interactive Brokers (IBKR)](#2-interactive-brokers-ibkr)
3. [Tradier](#3-tradier)
4. [Charles Schwab (formerly TD Ameritrade)](#4-charles-schwab-formerly-td-ameritrade)
5. [E\*Trade (Morgan Stanley)](#5-etrade-morgan-stanley)
6. [Robinhood](#6-robinhood)
7. [Other Notable API-First Brokers](#7-other-notable-api-first-brokers)
8. [Comparison Matrix](#8-comparison-matrix)
9. [Recommendations](#9-recommendations)

---

## 1. Alpaca

**Website:** <https://alpaca.markets> | **Docs:** <https://docs.alpaca.markets>

Alpaca is the most bot-friendly broker on this list. It was designed from the ground up
for algorithmic trading.

| Attribute | Details |
|---|---|
| **Official API** | Yes. RESTful API + WebSocket streaming. Excellent documentation. |
| **Python SDK** | `alpaca-py` (official). Previously `alpaca-trade-api` (deprecated). Well-maintained. |
| **Paper Trading** | Yes, first-class support. Separate paper base URL; same API shape as live. No account funding needed to use paper trading. |
| **Options Trading** | Yes. Options API launched in 2024. Supports single-leg and multi-leg options orders. (**VERIFY** full feature parity with equities API.) |
| **Market Data** | Free tier: IEX real-time data (15-min delayed from SIP). Paid plans: Full SIP real-time data. Historical bars, quotes, trades available. Options data available on paid plans. |
| **Commissions** | $0 for equities. Options: $0.00 per contract on some plans (**VERIFY** current options pricing -- may be ~$0.015/contract). |
| **Rate Limits** | 200 requests/minute for paper, 200/minute for live trading API. Market data endpoints have separate limits. |
| **Authentication** | API key + secret key pair. OAuth 2.0 also supported for third-party apps (broker API). |
| **Community** | Large and active. Slack community, active GitHub repos, many tutorials and blog posts. One of the most popular choices for algo trading beginners. |

**Strengths:** Zero barrier to entry for paper trading, clean modern API, excellent docs,
free tier sufficient for hobby projects.

**Weaknesses:** Options API is newer and less battle-tested than equities. Limited to
US markets. No futures.

---

## 2. Interactive Brokers (IBKR)

**Website:** <https://www.interactivebrokers.com> | **Docs:** <https://ibkrguides.com>

IBKR offers the most comprehensive trading API in terms of asset class coverage and
global market access. However, it is also the most complex to set up.

| Attribute | Details |
|---|---|
| **Official API** | Multiple options: (1) **TWS API** -- native API connecting through Trader Workstation or IB Gateway; (2) **Client Portal API** -- REST API (requires gateway running locally); (3) **Web API** -- newer REST API (**VERIFY** current status, was in beta/early release). |
| **Python SDK** | `ib_insync` (community, very popular, wraps TWS API asyncio-style -- **VERIFY** maintenance status, original author archived it; forks like `ib_async` exist). Official `ibapi` package from IB (lower-level, callback-based). |
| **Paper Trading** | Yes, excellent. Separate paper trading account with simulated execution. Full feature parity with live. Requires TWS or IB Gateway running. |
| **Options Trading** | Full support. Single-leg, multi-leg, complex spreads. Options chains, Greeks, implied vol. The most comprehensive options API available. |
| **Market Data** | Free delayed data (15-min). Real-time requires paid subscriptions ($1.50-$10+/mo per exchange). Snapshot and streaming available. Excellent historical data. |
| **Commissions** | Tiered: ~$0.65/contract for options, ~$0.005/share for stocks (min $1). Fixed: $0.65/contract options, $1.00 min for stocks. Very competitive for active traders. |
| **Rate Limits** | TWS API: 50 messages/second. Market data: varies by subscription. Client Portal API: ~5 requests/second. |
| **Authentication** | TWS API: connects to locally running TWS/Gateway (no OAuth). Client Portal API: session-based auth. Web API: OAuth (**VERIFY**). |
| **Community** | Very large but fragmented. Active forums, many quant blogs. Steep learning curve discourages beginners. |

**Strengths:** Unmatched asset coverage (stocks, options, futures, forex, bonds, global
markets). Professional-grade execution. Paper trading is excellent.

**Weaknesses:** Complex setup (must run TWS/Gateway). API is callback-heavy and
can be finicky. Documentation is extensive but sometimes confusing. Connection drops
require handling.

---

## 3. Tradier

**Website:** <https://tradier.com> | **Docs:** <https://documentation.tradier.com>

Tradier is an API-first brokerage specifically designed for developers and platforms.

| Attribute | Details |
|---|---|
| **Official API** | Yes. Clean REST API. Good documentation. Purpose-built for developers. |
| **Python SDK** | No official SDK. Community libraries exist (e.g., `tradier-python`, `uvatradier`). Straightforward enough to use with `requests`. |
| **Paper Trading** | Yes, via **Sandbox** environment. Free sandbox API key available without opening a brokerage account. Separate base URL. |
| **Options Trading** | Full support. Single-leg and multi-leg orders. Options chains, expirations, Greeks. This is one of Tradier's core strengths. |
| **Market Data** | Real-time streaming included with brokerage account. Sandbox provides delayed/simulated data. Historical data available. Options chains with Greeks. |
| **Commissions** | $0 stock trades. Options: $0.35/contract (with subscription plan ~$10/mo) or $0/trade + $0.35/contract on free plan (**VERIFY** current pricing tiers). |
| **Rate Limits** | 120 requests/minute for most endpoints. Streaming endpoints are separate. |
| **Authentication** | OAuth 2.0 for brokerage access. Simple API token for sandbox. |
| **Community** | Smaller but dedicated. Popular among fintech startups building trading platforms. Less hobbyist content than Alpaca. |

**Strengths:** Clean API design. Sandbox requires no account funding. Excellent options
support. Built for embedding in third-party apps.

**Weaknesses:** Smaller community. No official Python SDK. Market data quality/coverage
can lag behind IBKR.

---

## 4. Charles Schwab (formerly TD Ameritrade)

**Website:** <https://developer.schwab.com>

This is the most important transition to understand. The beloved TD Ameritrade API was
shut down as part of the Schwab acquisition.

### The TDA-to-Schwab Migration Timeline

- **2020:** Schwab announced acquisition of TD Ameritrade.
- **2023:** Account migration began.
- **September 2023:** TDA accounts started migrating to Schwab.
- **Q1 2024:** Schwab launched its own developer portal at `developer.schwab.com`.
- **Mid-2024:** The legacy TDA API (`api.tdameritrade.com`) was fully sunset. (**VERIFY** exact shutdown date.)
- **2024-2025:** The Schwab API became the replacement.

### Schwab API (Current)

| Attribute | Details |
|---|---|
| **Official API** | Yes, at `developer.schwab.com`. REST API for trading, accounts, market data. (**VERIFY** current feature completeness.) |
| **Python SDK** | No official SDK. Community library `schwab-py` (maintained by Alex Golec, same author as `tda-api`) is the de facto standard. (**VERIFY** maintenance status.) |
| **Paper Trading** | **No official paper trading/sandbox** as of mid-2025. This is a significant regression from TDA, which had no sandbox either but at least had thinkorswim's paperMoney. You can use thinkorswim paperMoney for manual testing, but there is no API sandbox. (**VERIFY** if Schwab has added a sandbox since.) |
| **Options Trading** | Yes, the API supports options orders including single-leg and multi-leg. Options chains endpoint available. |
| **Market Data** | Real-time quotes available (with account). Delayed quotes for unauthenticated. Historical price data. Options chains. |
| **Commissions** | $0 stock trades. $0.65/contract for options. |
| **Rate Limits** | 120 requests/minute (**VERIFY**). Throttling details on developer portal. |
| **Authentication** | OAuth 2.0. Requires registering an app on the developer portal. The OAuth flow requires a redirect URI and manual initial authentication. Token refresh is supported. |
| **Community** | Moderate. The `schwab-py` community is active. Many former TDA API users migrated but some left for other brokers due to pain points in the transition. |

**Strengths:** Large brokerage with good execution. Free real-time data with account.
$0 equity commissions.

**Weaknesses:** No paper trading API. OAuth flow is cumbersome for personal bots
(requires browser-based initial auth). API is less mature than TDA's was. Documentation
quality is middling.

---

## 5. E\*Trade (Morgan Stanley)

**Website:** <https://developer.etrade.com>

E\*Trade has had an official API for many years, now under Morgan Stanley ownership.

| Attribute | Details |
|---|---|
| **Official API** | Yes. REST API for trading, accounts, market data. Documentation exists but is dated in presentation. |
| **Python SDK** | No official Python SDK. Community options are sparse. The API uses XML responses by default (JSON also available), which is unusual. |
| **Paper Trading** | **Yes, sandbox environment available.** E\*Trade provides a sandbox base URL for testing. This is a notable advantage over Schwab. |
| **Options Trading** | Yes. Supports options orders, options chains, multi-leg strategies. |
| **Market Data** | Real-time quotes with account. Delayed quotes available. Options chains. Historical data limited compared to other brokers. |
| **Commissions** | $0 stock trades. $0.65/contract for options ($0.50/contract for 30+ trades/quarter). |
| **Rate Limits** | 14,000 requests per hour for throttled endpoints; 7,000/hour for orders. Varies by endpoint (**VERIFY**). |
| **Authentication** | OAuth 1.0a. This is notably outdated -- most other brokers use OAuth 2.0. Makes integration more complex. |
| **Community** | Small. E\*Trade's API is one of the least popular for algo trading among retail developers. Limited tutorials and community resources. |

**Strengths:** Sandbox available. Established broker. Options support.

**Weaknesses:** OAuth 1.0a is painful. XML-default responses feel dated. Small developer
community. Documentation quality is poor. Morgan Stanley ownership creates uncertainty
about API's long-term future. (**VERIFY** if they've modernized auth or docs.)

---

## 6. Robinhood

**Website:** <https://robinhood.com>

### Official API Status

Robinhood launched an **official Trading API** in **2024**, initially in a limited beta
program. (**VERIFY** current availability -- it may still be invite-only or limited.)

| Attribute | Details |
|---|---|
| **Official API** | **Yes, but limited access.** Launched in 2024 as a beta/early-access program. REST API. Not yet widely available to all users as of mid-2025. (**VERIFY** current status.) |
| **Python SDK** | No official SDK yet. Unofficial: `robin_stocks` (community library, uses internal/undocumented API -- fragile, can break). The official API may have a Python SDK in development. |
| **Paper Trading** | **No.** Neither the official API nor unofficial libraries support paper trading. |
| **Options Trading** | The official API supports equities. Options support status is unclear (**VERIFY**). `robin_stocks` (unofficial) does support options via reverse-engineered endpoints. |
| **Market Data** | Limited market data via API. Robinhood has historically been weak on data APIs. |
| **Commissions** | $0 stock trades. $0 options (Robinhood pioneered commission-free options). |
| **Rate Limits** | Official API: not well-documented yet. Unofficial: aggressive rate limiting and account lockout risk. |
| **Authentication** | Official API: OAuth 2.0 (**VERIFY**). Unofficial (`robin_stocks`): username/password + MFA, fragile. |
| **Community** | `robin_stocks` has a large community but it's built on sand (unofficial endpoints). Official API community is nascent. |

**Strengths:** Commission-free everything. Massive user base. Official API is a welcome
development.

**Weaknesses:** Official API is immature and access-limited. No paper trading. Unofficial
libraries are fragile. Robinhood has historically been hostile to API users. Data offerings
are weak. Not recommended for serious algo trading.

---

## 7. Other Notable API-First Brokers

### Tastytrade (formerly Tastyworks)

- **API:** Official REST API available ("Open API"). Good options focus.
- **Paper Trading:** No dedicated API sandbox (**VERIFY**).
- **Options:** Excellent -- Tastytrade is options-focused by nature.
- **Python:** Community libraries exist (`tastytrade` package).
- **Auth:** Session-based token authentication.
- **Commissions:** $0 stock, $1.00/contract options (capped at $10/leg).
- **Strengths:** Great for options-heavy strategies. Clean API.
- **Website:** <https://developer.tastytrade.com>

### Webull

- **API:** No official public API. Unofficial libraries exist (`webull` package) using
  reverse-engineered endpoints. **Not recommended** for automated trading.
- **Paper Trading:** Available in the app, not via API.

### TradeStation

- **API:** Official REST API available. Supports equities, options, futures.
- **Paper Trading:** Simulated trading environment available.
- **Python:** No official SDK; community wrappers exist.
- **Auth:** OAuth 2.0.
- **Website:** <https://developer.tradestation.com>

### Firstrade

- No public API.

### Public.com (formerly Apex-based)

- No public trading API.

---

## 8. Comparison Matrix

| Feature | Alpaca | IBKR | Tradier | Schwab | E\*Trade | Robinhood | Tastytrade |
|---|---|---|---|---|---|---|---|
| **Official API** | Yes | Yes | Yes | Yes | Yes | Limited | Yes |
| **API Quality** | Excellent | Good (complex) | Good | Fair | Fair | Immature | Good |
| **Python SDK** | Official | Community | Community | Community | None | Unofficial | Community |
| **Paper Trading** | Yes | Yes | Yes (sandbox) | No | Yes (sandbox) | No | No |
| **Options API** | Yes | Yes | Yes | Yes | Yes | Unclear | Yes |
| **Multi-leg Options** | Yes | Yes | Yes | Yes | Yes | Unlikely | Yes |
| **Real-time Data** | Paid | Paid | With account | With account | With account | Limited | With account |
| **Free Delayed Data** | Yes (IEX) | Yes (15-min) | Limited | Yes | Yes | Yes | Yes |
| **Equity Commission** | $0 | ~$0.005/share | $0 | $0 | $0 | $0 | $0 |
| **Options Commission** | ~$0/contract | ~$0.65/contract | $0.35/contract | $0.65/contract | $0.65/contract | $0 | $1.00/contract |
| **Auth Method** | API Key / OAuth2 | TWS Session / OAuth2 | OAuth 2.0 | OAuth 2.0 | OAuth 1.0a | OAuth 2.0 | Session Token |
| **Rate Limits** | 200/min | 50 msg/sec | 120/min | ~120/min | 14,000/hr | Unknown | Unknown |
| **Futures** | No | Yes | No | No | No | No | Yes |
| **Global Markets** | No (US only) | Yes | No (US only) | No (US only) | No (US only) | No (US only) | No (US only) |
| **Community Size** | Large | Large | Small-Med | Medium | Small | Medium | Small-Med |

---

## 9. Recommendations

### For a New Algo Trading Project (Equities + Options with Paper Trading)

**Tier 1 -- Best choices:**

1. **Alpaca** -- Best overall developer experience. Paper trading works out of the box
   with zero setup cost. Options API is available. Start here if you want the fastest
   path to a working bot.

2. **Interactive Brokers** -- Best if you need comprehensive options support, global
   markets, or futures. Paper trading is excellent. Higher setup complexity but
   unmatched capability. The `ib_async`/`ib_insync` ecosystem makes Python integration
   manageable.

3. **Tradier** -- Best if options are your primary focus and you want a clean REST API.
   Sandbox is free and requires no account. Good middle ground between Alpaca's
   simplicity and IBKR's power.

**Tier 2 -- Viable but with caveats:**

4. **Schwab** -- Viable if you already have a Schwab account. No paper trading API
   is a significant limitation. The `schwab-py` library helps.

5. **Tastytrade** -- Good for options-heavy strategies. API is clean but ecosystem
   is small.

**Tier 3 -- Not recommended for algo trading:**

6. **E\*Trade** -- OAuth 1.0a and poor docs make this painful. Only use if you're
   already locked into E\*Trade.

7. **Robinhood** -- Official API is too immature. Unofficial libraries are fragile.
   No paper trading. Avoid for automated trading.

---

### Suggested Multi-Broker Architecture

For a robust trading bot, consider:

```
Development/Testing:  Alpaca Paper  or  Tradier Sandbox
                              |
                      Common abstraction layer
                              |
Production:           Alpaca Live  /  IBKR  /  Schwab
```

This lets you develop and backtest against a paper environment, then deploy to
whichever broker offers the best execution and pricing for your strategy.

---

## Key Links

| Broker | Developer Portal |
|---|---|
| Alpaca | <https://docs.alpaca.markets> |
| Interactive Brokers | <https://ibkrguides.com> |
| Tradier | <https://documentation.tradier.com> |
| Schwab | <https://developer.schwab.com> |
| E\*Trade | <https://developer.etrade.com> |
| Robinhood | <https://robinhood.com/us/en/support/articles/trading-api/> |
| Tastytrade | <https://developer.tastytrade.com> |
| TradeStation | <https://developer.tradestation.com> |

---

*Note: All information should be independently verified against current broker
documentation. API features, pricing, and availability change frequently. Items
marked (**VERIFY**) are areas where changes are most likely since this research
was compiled.*
