# Passive Portfolio Lab

Passive Portfolio Lab is a bilingual toolkit for long-term passive investors. It has two deployable surfaces:

- **Streamlit Dashboard**: interactive research app with BigQuery reads, live data helpers, and optional Gemini insights.
- **GitHub Web**: static GitHub Pages app with BigQuery-exported asset metrics and daily TWD price history.

The core question:

**If a portfolio's backtested return looks attractive, what is the risk, drawdown pain, and FIRE trade-off behind it?**

Both versions support English and Traditional Chinese (`zh-TW`) and focus on TWD-based portfolio analysis for Taiwan-based investors.

For app-specific setup, see:

- [Streamlit Dashboard](streamlit_dashboard/README.md)
- [GitHub Web](github_web/README.md)

---

## Key Features

### 1. Bilingual Dashboard

The dashboard can switch between English and Traditional Chinese from the sidebar. The toggle updates navigation, section titles, controls, messages, chart labels, and AI insight language where applicable.

### 2. Asset Screening

Browse a curated universe of 37 assets:

- 14 Taiwan ETFs selected by AUM rank (includes 2 owner additions: 00646.TW, 00955.TWO)
- 15 US ETFs selected by AUM rank
- 8 major cryptocurrencies, excluding stablecoins and assets with insufficient history

The asset pool is static and curated; no web scraping occurs at runtime.

The screening table uses Streamlit-AgGrid and supports:

- Search by ticker or name
- Category filtering
- CAGR, Sharpe, and max drawdown filters
- Current price and volume display via Yahoo Finance v8 REST API
- Native currency display while keeping cross-currency sorting mathematically consistent

### 3. Persona Quick Start

After browsing the asset pool, users can choose one of three preset investor personas:

- Young Professional: medium-risk accumulation with Taiwan, US, developed-market, bond, gold, and Bitcoin exposure
- Pre-Retirement: low-risk retirement sprint with diversified equity, bond, and gold exposure
- Aggressive Growth: high-risk growth portfolio with VTI, QQQ, Taiwan equity, developed markets, Bitcoin, and gold

The persona buttons sit below the asset table, matching the intended flow: users first see the asset universe, then use a preset if they are not sure where to start.

When a persona is applied, the app fills in the watchlist, risk level, backtest parameters, and FIRE assumptions. The correlation section remains visible as a diagnostic view, but persona portfolios are auto-confirmed and do not require the manual "Confirm Assets" step.

### 4. Correlation Analysis

The correlation module computes pairwise correlation using the last 3 years of daily returns.

For manually selected portfolios, it:

- Flags highly correlated asset groups
- Shows a "keep only one asset from each group" action prompt
- Recommends one asset to keep based on AUM / liquidity
- Lets users choose the one asset they want to keep from each correlated group
- Removes the unselected overlapping assets only after users confirm the keep choices
- Requires asset confirmation before unlocking downstream calculations

For persona portfolios, it:

- Shows selected asset count, overlap count, and average correlation
- Skips the suggested-removal and confirmation workflow
- Keeps the preset portfolio intact for the downstream calculations

### 5. Risk Allocation & Portfolio Visualization

The app maps selected assets to an achievable risk range based on annualized volatility, then allocates weights toward a selected target risk tier:

| Risk Tier | Target Volatility |
|---|---:|
| Low | 12% |
| Medium | 20% |
| High | 35% |
| Extreme High | 65% |

The allocation section includes:

- Weighted CAGR, volatility, max drawdown, and Sharpe metrics
- Interactive Plotly treemap
- Clickable asset detail view with metrics and radar chart
- Links to Yahoo Finance and TradingView for individual assets

### 6. Backtest & Pain Index

Backtests are calculated in New Taiwan Dollar (TWD).

The current backtest engine uses a combined contribution model:

- Initial lump-sum investment on the first available trading day
- Monthly contribution on the first trading day of each subsequent month
- USD-denominated assets converted to TWD using daily historical TWD/USD exchange rates
- Web version uses BigQuery-exported daily TWD price history for static historical backtests
- TWD / USD display toggle for portfolio values while keeping inputs and calculations in TWD

The backtest section shows:

- Final value
- Total invested
- Total return
- CAGR
- Portfolio value over time
- Max drawdown over time
- Top 5 independent drawdown episodes with historical event context
- Annual returns

### 7. FIRE Calculator

The FIRE calculator estimates financial independence based on the portfolio's historical return assumptions and user inputs.

The FIRE target is derived from:

```text
Annual Expenses / Withdrawal Rate
```

The calculator includes:

- Annual expenses
- Withdrawal rate
- Current savings
- Monthly contribution
- Inflation rate
- Nominal and inflation-adjusted FIRE timelines

Inflation defaults to the latest US CPI year-over-year value from FRED when `FRED_API_KEY` is configured. If FRED is unavailable, the app falls back to 2.5%.

### 8. Summary & AI Insights

The summary section provides a plain-English or Traditional Chinese portfolio review covering:

- Portfolio structure
- Drawdown meaning
- FIRE timeline
- Behavioral risk
- Tail-risk caveats for crypto-heavy or high-risk portfolios

If `GEMINI_API_KEY` is configured, Gemini 2.5 Flash generates concise strategic next steps.

---

## Tech Stack

| Layer | Tools |
|---|---|
| Dashboard | Streamlit, Streamlit-AgGrid |
| Visualization | Plotly, Chart.js |
| Data Processing | Pandas, NumPy |
| Data Collection | Yahoo Finance v8 REST API, FRED API |
| Storage | Google BigQuery |
| AI | Google Gemini 2.5 Flash |

---

## Project Structure

```text
passive-portfolio-lab/
├── streamlit_dashboard/
│   ├── app.py                        # Main Streamlit dashboard
│   ├── requirements.txt              # Streamlit app dependencies
│   └── src/
│       ├── data_collection/
│       │   ├── fetch_prices.py       # Yahoo Finance REST price fetching
│       │   └── fetch_macro.py        # FRED CPI fetching
│       └── processing/
│           ├── screening.py          # Static asset universe
│           ├── metrics.py            # Financial metric calculations
│           ├── backtest.py           # Combined TWD backtesting engine
│           ├── drawdown_events.py    # Drawdown episode detection and tagging
│           └── fire_calculator.py    # FIRE projection logic
├── github_web/
│   ├── index.html                    # Static web dashboard for GitHub Pages
│   ├── scripts/
│   │   ├── export_web_data.py        # BigQuery export for static web data
│   │   └── backfill_missing_web_assets.py
│   └── src/
│       ├── colors_and_type.css       # Web design tokens
│       └── ppl-data.js               # Exported asset metrics and price history
├── .github/
│   └── workflows/
│       └── update-and-deploy.yml     # Scheduled data refresh and Pages deploy
├── requirements.txt                  # Compatibility wrapper for Streamlit Cloud
├── .env.example                      # Environment variable template
└── README.md
```

---

## Environment Variables

Create a local `.env` file using `.env.example` as a template:

```env
GOOGLE_CLOUD_PROJECT=your-project-id
BIGQUERY_DATASET=portfolio
GOOGLE_APPLICATION_CREDENTIALS=credentials.json
FRED_API_KEY=your-fred-api-key
GEMINI_API_KEY=your-gemini-api-key
```

Notes:

- `GOOGLE_CLOUD_PROJECT`, `BIGQUERY_DATASET`, and credentials are required for BigQuery reads.
- `FRED_API_KEY` is optional; the app falls back to 2.5% inflation if unavailable.
- `GEMINI_API_KEY` is optional; AI insights are hidden if unavailable.
- `APP_PASSWORD` can be configured in Streamlit secrets to enable the dashboard password gate.

---

## Methodology & Risk Notes

- Historical performance does not guarantee future results.
- All portfolio-level backtests are calculated in TWD to reflect the experience of a Taiwan-based investor.
- USD-denominated assets are converted using historical TWD/USD exchange rates.
- The correlation engine is a diversification aid, not an optimization model.
- Risk allocation uses annualized volatility as the primary risk proxy and does not fully model covariance.
- Crypto metrics should be interpreted cautiously because of shorter history and extreme tail risk.
- The 4% withdrawal rule is a baseline; conservative users may prefer 3.0-3.5%.
