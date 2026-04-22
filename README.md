# Passive Portfolio Lab

A Buy-and-Hold backtesting platform for everyday investors. It explores the historical performance of passive portfolios across four risk profiles, quantifies the pain of drawdowns, and estimates how long you'd need to hold to reach financial independence (FIRE).

The central question the dashboard tries to answer: **when a portfolio's backtested return looks attractive, what is the accompanying cost?**

---

## Features

The Streamlit dashboard is organized into four sections, each answering a different question for a passive investor.

### 1. Asset Screening

Ranks and filters candidate assets — Taiwan ETFs (scraped from MoneyDJ, plus manually-included 元大 S&P 500 `00646.TW` and 中信日本商社 `00955.TWO`), US ETFs (scraped from TradingView), defensive ETFs (TLT / IEF / BND / GLD / DBC), and a fixed top-5 of major cryptocurrencies (BTC / ETH / XRP / BNB / SOL, deliberately excluding stablecoins, wrapped variants, and exchange-native tokens). Each row is checkable; selected tickers are added to a session-local watchlist for downstream sections.

A **Correlation Check** sits directly below the watchlist. It computes a Pearson-correlation matrix of 3-year daily returns across all selected assets, reports the pair with the highest correlation, and — when that correlation exceeds 0.85 — advises keeping only one of the two to avoid redundant exposure. The full heatmap is rendered inside a collapsible expander so the summary stays glanceable by default.

### 2. Risk Allocation

Given a chosen risk level (Low / Medium / High / Extreme High), the dashboard composes a default portfolio and visualizes it as an interactive treemap. Tile size = weight; tile color = volatility tier (6-step blue gradient across the full asset universe).

Click any tile to reveal an in-iframe detail card showing Annual Return, Volatility, Max Drawdown, Sharpe Ratio, Worst Year Return, Worst Year, and Risk Level, alongside a Chart.js radar plot of five normalized scores (Return, Low Vol, DD Protection, Sharpe, Worst Year). The card adopts the tile's color with a luminance-aware light/dark theme, and includes quick links to Yahoo Finance and TradingView.

### 3. Backtest & Pain Index

Runs a historical backtest of the chosen portfolio using lump-sum or dollar-cost-averaging contributions. Outputs an equity curve, rolling drawdown, and a "Pain Index" designed to convey the *experience* of holding through downturns — not just the final return. TWD/USD FX conversion is applied for US-denominated assets via the Yahoo Finance chart API (`period1`/`period2` epoch ranges to avoid silent monthly downsampling, with an implausible-rate filter dropping ticks outside 20–50 TWD/USD).

Below the charts, a **Top 5 Drawdown Episodes** table (collapsible) lists the five worst independent peak-to-trough-to-recovery episodes, each tagged with a curated historical-event label — Global Financial Crisis, COVID-19, Crypto Winter, Terra/Luna + FTX, 2022 Bear, SVB, AI bubble scare, and others. The same episodes appear as semi-transparent shaded bands (labelled `#1`–`#5`) on both the equity curve and the drawdown chart, so the user can see at a glance *when* the pain happened and *what* macro event coincided with it. Episodes still underwater at the end of the series are reported as `Ongoing`.

### 4. FIRE Calculator

Rather than asking for a directly-entered retirement target, the calculator derives it from **Annual Expenses ÷ Withdrawal Rate** (Trinity Study / 4% rule framing — the Rule of 25 in shortcut form). The implied target is displayed read-only so adjusting either input updates it live. A sibling collapsible expander documents where the 4% figure comes from (Cooley, Hubbard & Walz, 1998) and gives guidance on picking 3.0–3.5% (conservative, 40+ year horizons), 4.0% (baseline 30-year retirement), or 4.5–5.0% (with supplementary income).

Combined with your current savings and monthly contribution, the calculator projects how long it would take to compound into the implied target at the portfolio's historical CAGR — weighted by your current allocation, with each constituent's CAGR pulled from the `asset_metrics` BigQuery table. Two horizons are reported: a nominal years-to-FIRE and a real years-to-FIRE that deflates the projected value by the annual inflation rate (auto-fetched from FRED US CPI YoY, overridable).

---

## Tech Stack

| Layer | Tools |
|---|---|
| Dashboard | Streamlit, `streamlit.components.v1` for embedded HTML |
| Visualization | Plotly (treemap, time series), Chart.js 4 (radar), custom inline SVG/CSS |
| Data processing | pandas, numpy |
| Data collection | Yahoo Finance v8 chart REST API (direct HTTP, `verify=False`), FRED API, BeautifulSoup (MoneyDJ + TradingView scrape) |
| Storage | Google BigQuery (`raw_prices`, `asset_metrics` tables) |
| Config | python-dotenv |

---

## Project Structure

```
passive-portfolio-lab/
├── dashboard/
│   └── Passive_Portfolio_Lab.py      # Streamlit app: 4 sections + Summary, ~1530 lines
├── src/
│   ├── data_collection/
│   │   ├── fetch_prices.py           # Yahoo v8 chart REST → BigQuery raw_prices
│   │   └── fetch_macro.py            # FRED CPI YoY
│   └── processing/
│       ├── screening.py              # TW/US/defensive/crypto candidate universe
│       ├── metrics.py                # CAGR, vol, DD, Sharpe, worst-year — per-asset metrics
│       ├── backtest.py               # Lump-sum / DCA backtest, TWD FX handling
│       ├── drawdown_events.py        # Top-N drawdown episodes + historical-event labels
│       └── fire_calculator.py        # FIRE projection using BigQuery CAGRs
├── requirements.txt
├── .env.example
└── README.md
```

---

## Data Sources

| Source | Use | Access |
|---|---|---|
| Yahoo Finance v8 chart API | Daily OHLCV + adjclose for all tickers (equities, ETFs, crypto, TWD=X FX) | Direct HTTP to `query1.finance.yahoo.com/v8/finance/chart/{ticker}` with `verify=False` — robust against corporate SSL interception / custom root CAs that break `yfinance` |
| FRED | CPI YoY (inflation context) | HTTPS API, `verify=False` for restrictive SSL environments |
| MoneyDJ | Taiwan ETF rankings by 1-year market cap | HTML scraping via BeautifulSoup |
| TradingView | US ETF rankings by AUM | HTML scraping via BeautifulSoup |

> Crypto tickers are hardcoded to a top-5 (`BTC-USD`, `ETH-USD`, `XRP-USD`, `BNB-USD`, `SOL-USD`) rather than scraped from CoinGecko — the ranking shifts daily, and stablecoins / wrapped variants / exchange-native tokens don't fit the passive-portfolio thesis. See `get_crypto_ranking()` in `screening.py` for the rationale. A `YAHOO_UNAVAILABLE_TICKERS` blacklist (currently TW bond ETFs and `LEO-USD`) filters out symbols the upstream rankings list but Yahoo can't price.

---

## Methodology Notes

**Metrics** (`src/processing/metrics.py`). For each ticker, we compute CAGR, annualized volatility (stdev of daily returns × √N, where N = 365 for cryptocurrencies since they trade 24/7 and N = 252 for equities/ETFs), max drawdown, recovery period, Sharpe ratio (risk-free rate = 2% in the Sharpe numerator), and the worst calendar-year return with its label.

**Portfolio-level risk focus.** Per-asset risk is communicated through the raw metrics themselves (volatility, max drawdown, worst-year return, Sharpe) rather than a single categorical label — the numbers are more informative than a "Low / Medium / High" bucket. The dashboard emphasizes *portfolio-level* risk instead: the Risk Allocation section displays the weighted portfolio CAGR, volatility, max drawdown, and Sharpe, so the user sees the combined behavior of their holdings rather than the sum of individual classifications. The four tiers (Low / Medium / High / Extreme High) that appear in Risk Allocation, Backtest, and FIRE Calculator refer to a user-selected *target volatility* for the allocation algorithm, not a per-asset classification or a fixed composition.

**Risk tiers and thresholds.** Both the achievable-risk-range indicator and the per-tier volatility targets use the same four annualized-volatility bands:

| Annualized Volatility | Risk Tier | Target Volatility |
|---|---|---|
| < 16% | Low | 12% |
| 16% – 27% | Medium | 20% |
| 27% – 50% | High | 35% |
| ≥ 50% | Extreme High | 65% |

The achievable range shown in Risk Allocation is computed by mapping each watchlist asset's volatility into one of these bands and reporting the span from the lowest-vol asset's tier to the highest-vol asset's tier. Because `compute_allocation()` combines assets via a weighted average of individual volatilities (no cross-asset covariance), the resulting portfolio volatility is always bounded between the minimum and maximum single-asset volatility in the watchlist — so the user cannot reach a tier below the lowest-vol asset or above the highest-vol asset. Rough intuition for the thresholds: ~16% separates bond-heavy / conservative blends from broad-market equity, ~27% separates broad equity from concentrated / tech-heavy portfolios, and ~50% separates traditional equity from crypto-like volatility.

**Allocation algorithm** (`compute_allocation()` in `dashboard/Passive_Portfolio_Lab.py`). Given the user's selected tickers and a target portfolio volatility (determined by the chosen risk tier), the dashboard computes weights in two steps: (1) inverse-volatility weighting as a starting point, then (2) up to 200 iterations that nudge the weights toward the target volatility — shifting mass away from high-volatility assets when the portfolio is too volatile, and toward them when it is too tame. Final weights are clipped at a 1% floor per asset and renormalized. This means the exact composition the user sees depends on which tickers they selected in Asset Screening, not on a fixed preset.

**Backtest** (`src/processing/backtest.py`) supports both lump-sum and monthly DCA contribution schedules, and runs against the weights produced by `compute_allocation()`. US-denominated assets are converted to TWD using the daily TWD=X rate from Yahoo's v8 chart API with explicit `period1`/`period2` epoch ranges (the `range=max` shorthand silently downsamples older data to monthly, which would poison any backtest that crosses those regions). An implausible-rate filter drops ticks outside 20–50 TWD/USD as a second line of defence, and missing FX days fall back to the most recent available rate.

**Drawdown episodes** (`src/processing/drawdown_events.py`) walks the backtest equity curve and carves it into independent underwater episodes: an episode opens the first day the portfolio trades below its running all-time high, reaches its trough at the deepest percentage decline, and closes on the first day the portfolio recovers to (or above) the prior peak. Episodes are filtered by a minimum-depth threshold (default 2%) to suppress noise, ranked by depth, and the top-5 are returned along with peak/trough/recovery dates and durations. Each episode is then matched against a curated `MARKET_EVENTS` lookup (GFC, COVID, 2022 Fed tightening, SVB, Terra/Luna + FTX, AI-bubble scare, and others) and tagged with any overlapping event labels — episodes still underwater at the end of the series are reported with `recovery_date=None` and handled correctly by matching up to the trough date.

**FIRE projection** (`src/processing/fire_calculator.py`) uses the user's current allocation (the same weights produced by `compute_allocation()`) to compute a blended historical CAGR — a weighted average of each constituent's CAGR from the `asset_metrics` table — and solves for the years needed for `current_savings + monthly_contribution × months` to compound into the FIRE target. The target itself is **not directly entered**: the dashboard takes the user's `Annual Expenses` and `Withdrawal Rate` and computes `target = expenses ÷ rate` (equivalent to the Rule of 25 at 4%). The dashboard reports two horizons: a nominal years-to-FIRE (no inflation applied), and a real years-to-FIRE that deflates the projected portfolio value by `(1 + inflation_rate) ^ year` before comparing against the target. The default inflation rate is auto-fetched from FRED (US CPI YoY) and can be overridden in the FIRE Calculator's Advanced Settings.

---

## Known Limitations

- Historical CAGRs are not predictions. Crypto's high CAGR reflects a specific period and will not persist; take FIRE estimates for the High/Extreme High tiers with a grain of salt.
- Volatility-based metrics (Sharpe ratio, annualized stdev) assume daily returns follow a normal distribution. In reality, markets — especially crypto — have "fat tails": extreme drops happen far more often than the model predicts, so Sharpe ratios can overstate risk-adjusted returns for volatile assets. Treat the numbers as a lower bound on tail risk, not a ceiling.
- The 4% withdrawal rate baseline comes from the Trinity Study, which was calibrated on 1926–1995 US equity + bond portfolios and a 30-year retirement horizon. Applying it to portfolios that include Taiwan equities, crypto, or cover horizons much longer than 30 years is an extrapolation; prefer a lower rate (3.0–3.5%) for multi-decade early-retirement scenarios.
- Scrapers depend on the page layout of MoneyDJ (Taiwan ETF rankings) and TradingView (US ETF rankings); if either changes their HTML, the corresponding function in `screening.py` will need to be updated.
- Price fetching uses `verify=False` on Yahoo and FRED calls by design, to work on networks that intercept SSL (corporate VPNs, custom root CAs). This trades certificate verification for reliability — in a production setting that isn't behind such a network, you'd want to remove `verify=False` and let the normal certificate chain validate.
- Historical-event labels on drawdown episodes are editorial (curated in `MARKET_EVENTS`) rather than detected automatically; a missing label just means no curated event overlapped the episode, not that the drawdown wasn't real.
