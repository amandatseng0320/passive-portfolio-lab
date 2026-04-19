# Passive Portfolio Lab

A Buy-and-Hold backtesting platform for everyday investors. It explores the historical performance of passive portfolios across four risk profiles, quantifies the pain of drawdowns, and estimates how long you'd need to hold to reach financial independence (FIRE).

The central question the dashboard tries to answer: **when a portfolio's backtested return looks attractive, what is the accompanying cost?**

---

## Features

The Streamlit dashboard is organized into four sections, each answering a different question for a passive investor.

### 1. Asset Screening

Ranks and filters candidate assets — Taiwan ETFs (scraped from MoneyDJ), US ETFs, defensive ETFs, and major cryptocurrencies — by risk level, CAGR, volatility, max drawdown, Sharpe ratio, and worst-year return. Each row is checkable; selected tickers are added to a session-local watchlist for downstream sections.

### 2. Risk Allocation

Given a chosen risk level (Low / Medium / High / Extreme High), the dashboard composes a default portfolio and visualizes it as an interactive treemap. Tile size = weight; tile color = volatility tier (6-step blue gradient across the full asset universe).

Click any tile to reveal an in-iframe detail card showing Annual Return, Volatility, Max Drawdown, Sharpe Ratio, Worst Year Return, Worst Year, and Risk Level, alongside a Chart.js radar plot of five normalized scores (Return, Low Vol, DD Protection, Sharpe, Worst Year). The card adopts the tile's color with a luminance-aware light/dark theme, and includes quick links to Yahoo Finance and TradingView.

### 3. Backtest & Pain Index

Runs a historical backtest of the chosen portfolio using lump-sum or dollar-cost-averaging contributions. Outputs an equity curve, rolling drawdown, and a "Pain Index" designed to convey the *experience* of holding through downturns — not just the final return. TWD/USD FX conversion is applied for Taiwan-denominated assets via the Yahoo Finance chart API.

### 4. FIRE Calculator

Takes your current savings, monthly contribution, target FIRE number, and chosen risk level, then projects how long it would take to reach FIRE at the portfolio's historical CAGR. CAGR values are pulled from the `asset_metrics` BigQuery table so the projection is grounded in real historical performance rather than assumed returns.

---

## Tech Stack

| Layer | Tools |
|---|---|
| Dashboard | Streamlit, `streamlit.components.v1` for embedded HTML |
| Visualization | Plotly (treemap, time series), Chart.js 4 (radar), custom inline SVG/CSS |
| Data processing | pandas, numpy |
| Data collection | yfinance, Yahoo Finance REST API, FRED API, BeautifulSoup (MoneyDJ scrape) |
| Storage | Google BigQuery (`raw_prices`, `asset_metrics` tables) |
| Config | python-dotenv |

---

## Project Structure

```
passive-portfolio-lab/
├── dashboard/
│   └── Passive_Portfolio_Lab.py      # Streamlit app: 4 sections, ~1150 lines
├── src/
│   ├── data_collection/
│   │   ├── fetch_prices.py           # yfinance → BigQuery raw_prices
│   │   └── fetch_macro.py            # FRED CPI YoY
│   └── processing/
│       ├── screening.py              # TW/US/defensive/crypto candidate universe
│       ├── metrics.py                # CAGR, vol, DD, Sharpe, worst-year — per-asset metrics
│       ├── backtest.py               # Lump-sum / DCA backtest, TWD FX handling
│       └── fire_calculator.py        # FIRE projection using BigQuery CAGRs
├── requirements.txt
├── .env.example
└── README.md
```

---

## Data Sources

| Source | Use | Access |
|---|---|---|
| Yahoo Finance (`yfinance`) | Historical daily prices for US equities, ETFs, crypto | Python library |
| Yahoo Finance REST API | TWD=X FX rate (v8 chart endpoint) | Direct HTTP — more reliable than `yfinance` in some regions |
| FRED | CPI YoY (inflation context) | HTTPS API, `verify=False` to bypass restrictive SSL environments |
| MoneyDJ | Taiwan ETF rankings by market cap / volume / 1Y return | HTML scraping via BeautifulSoup |
| Yahoo Finance crypto tickers | BTC-USD, ETH-USD, SOL-USD, BNB-USD, XRP-USD | Via `yfinance` |

---

## Methodology Notes

**Metrics** (`src/processing/metrics.py`). For each ticker, we compute CAGR, annualized volatility (stdev of daily returns × √N, where N = 365 for cryptocurrencies since they trade 24/7 and N = 252 for equities/ETFs), max drawdown, recovery period, Sharpe ratio (risk-free rate = 2% in the Sharpe numerator), and the worst calendar-year return with its label.

**Portfolio-level risk focus.** Per-asset risk is communicated through the raw metrics themselves (volatility, max drawdown, worst-year return, Sharpe) rather than a single categorical label — the numbers are more informative than a "Low / Medium / High" bucket. The dashboard emphasizes *portfolio-level* risk instead: the Risk Allocation section displays the weighted portfolio CAGR, volatility, max drawdown, and Sharpe, so the user sees the combined behavior of their holdings rather than the sum of individual classifications. The four tiers (Low / Medium / High / Extreme High) that appear in Risk Allocation, Backtest, and FIRE Calculator refer to a user-selected *target volatility* for the allocation algorithm, not a per-asset classification or a fixed composition.

**Allocation algorithm** (`compute_allocation()` in `dashboard/Passive_Portfolio_Lab.py`). Given the user's selected tickers and a target portfolio volatility (determined by the chosen risk tier), the dashboard computes weights in two steps: (1) inverse-volatility weighting as a starting point, then (2) up to 200 iterations that nudge the weights toward the target volatility — shifting mass away from high-volatility assets when the portfolio is too volatile, and toward them when it is too tame. Final weights are clipped at a 1% floor per asset and renormalized. This means the exact composition the user sees depends on which tickers they selected in Asset Screening, not on a fixed preset.

**Backtest** (`src/processing/backtest.py`) supports both lump-sum and monthly DCA contribution schedules, and runs against the weights produced by `compute_allocation()`. Taiwan-listed assets are priced in USD using the daily TWD=X rate. Missing FX days fall back to the most recent available rate.

**FIRE projection** (`src/processing/fire_calculator.py`) uses the user's current allocation (the same weights produced by `compute_allocation()`) to compute a blended historical CAGR — a weighted average of each constituent's CAGR from the `asset_metrics` table — and solves for the years needed for `current_savings + monthly_contribution × months` to compound into the target amount. The dashboard reports two horizons: a nominal years-to-FIRE (no inflation applied), and a real years-to-FIRE that deflates the projected portfolio value by `(1 + inflation_rate) ^ year` before comparing against the target. The default inflation rate is auto-fetched from FRED (US CPI YoY) and can be overridden in the FIRE Calculator's Advanced Settings.

---

## Known Limitations

- Historical CAGRs are not predictions. Crypto's high CAGR reflects a specific period and will not persist; take FIRE estimates for the High/Extreme High tiers with a grain of salt.
- Volatility-based metrics (Sharpe ratio, annualized stdev) assume daily returns follow a normal distribution. In reality, markets — especially crypto — have "fat tails": extreme drops happen far more often than the model predicts, so Sharpe ratios can overstate risk-adjusted returns for volatile assets. Treat the numbers as a lower bound on tail risk, not a ceiling.
- TW ETF metadata depends on MoneyDJ's page layout; if they change their HTML, the scraper will need updates.
