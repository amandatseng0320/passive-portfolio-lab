# Passive Portfolio Lab

Passive Portfolio Lab is a bilingual toolkit for long-term passive investors. It has three deployable surfaces:

- **Streamlit Dashboard** — interactive research app with BigQuery reads, live data helpers, and optional Gemini AI insights.
- **GitHub Web** — static GitHub Pages app with BigQuery-exported asset metrics and daily TWD price history.
- **Looker Studio** — six pre-built portfolio views as a shareable BI report, backed by BigQuery semantic layer.

## Live Apps

| Platform | URL |
|---|---|
| Streamlit Dashboard | https://passive-portfolio-lab.streamlit.app/ |
| GitHub Web | https://amandatseng0320.github.io/passive-portfolio-lab/ |
| Landing Page | https://amandatseng0320.github.io/passive-portfolio-lab/landing.html |
| Looker Studio | https://datastudio.google.com/reporting/c2e7b15c-bf18-460f-8daf-dc480bcbca67 |

The core question:

> If a portfolio's backtested return looks attractive, what is the risk, drawdown pain, and FIRE trade-off behind it?

All three surfaces support English and Traditional Chinese (`zh-TW`) and focus on TWD-based portfolio analysis for Taiwan-based investors.

For surface-specific setup, see:

- [Streamlit Dashboard](streamlit_dashboard/README.md)
- [GitHub Web](github_web/README.md)
- [Looker Studio](looker_studio/README.md)

---

## Key Features

### 1. Bilingual Interface

All three surfaces can switch between English and Traditional Chinese. The toggle updates navigation, section titles, controls, messages, chart labels, and AI insight language where applicable.

### 2. Asset Screening

Browse a curated universe of 37 assets:

- 14 Taiwan ETFs selected by AUM rank (includes 2 owner additions: 00646.TW, 00955.TWO)
- 15 US ETFs selected by AUM rank
- 8 major cryptocurrencies, excluding stablecoins and assets with insufficient history

The asset pool is static and curated; no web scraping occurs at runtime. Assets are filtered by liquidity, fee rate, coverage overlap, and minimum 3 years of reliable closing prices.

### 3. Correlation Analysis

The correlation module computes pairwise correlation using the last 3 years of daily returns.

For manually selected portfolios, it:

- Flags highly correlated asset groups
- Recommends one asset to keep from each group based on AUM / liquidity
- Requires asset confirmation before unlocking downstream calculations

For persona portfolios, it shows correlation diagnostics without requiring the manual confirmation step.

### 4. Risk Allocation & Portfolio Visualization

The app maps selected assets to an achievable risk range based on annualized volatility, then allocates weights toward a selected target risk tier:

| Risk Tier | Target Volatility |
|---|---:|
| Low | 12% |
| Medium | 20% |
| High | 35% |
| Extreme High | 65% |

The allocation section includes weighted CAGR, volatility, max drawdown, and Sharpe metrics, an interactive treemap, and a clickable asset detail view with a radar chart.

### 5. Backtest & Drawdown Analysis

Backtests are calculated in New Taiwan Dollar (TWD) using a combined contribution model:

- Initial lump-sum investment on the first available trading day
- Monthly contribution on the first trading day of each subsequent month
- USD-denominated assets converted to TWD using daily historical TWD/USD exchange rates

The backtest section shows final value, total invested, total return, CAGR, portfolio value over time, max drawdown over time, top 5 independent drawdown episodes with historical event labels, and annual returns.

### 6. FIRE Calculator

Estimates the path to financial independence based on portfolio CAGR assumptions and user inputs:

```
FIRE Target = Annual Expenses / Withdrawal Rate
```

Includes nominal and inflation-adjusted timelines. Inflation defaults to the latest US CPI year-over-year value from FRED when `FRED_API_KEY` is configured; falls back to 2.5% otherwise.

### 7. AI Insights (Streamlit only)

If `GEMINI_API_KEY` is configured, Gemini 2.5 Flash generates a concise portfolio review covering structure, drawdown context, FIRE timeline, and behavioural risk. Falls back to a rule-based summary if the key is absent.

### 8. Persona Quick Start (Streamlit only)

Three preset investor personas auto-fill the watchlist, risk level, backtest parameters, and FIRE assumptions:

- **Young Professional** — medium-risk accumulation
- **Pre-Retirement** — low-risk retirement sprint
- **Aggressive Growth** — high-risk growth portfolio

---

## Tech Stack

| Layer | Tools |
|---|---|
| Dashboard | Streamlit 1.35+, Streamlit-AgGrid |
| Visualization | Plotly 5.18+, Chart.js 4.4 |
| Data Processing | pandas 2.0+, NumPy 1.26+ |
| Data Collection | Yahoo Finance v8 REST API, FRED API |
| Storage | Google BigQuery |
| AI | Google Gemini 2.5 Flash |
| Static Web | HTML / CSS / JavaScript (React 18 via CDN) |
| CI/CD | GitHub Actions (daily cron + GitHub Pages deploy) |
| Testing | pytest 7.0+, pytest-mock 3.10+ |

---

## Project Structure

```text
passive-portfolio-lab/
├── streamlit_dashboard/
│   ├── app.py                             # Main Streamlit dashboard (2,278 LOC)
│   ├── requirements.txt                   # Streamlit app dependencies
│   └── src/
│       ├── data_collection/
│       │   ├── fetch_prices.py            # Yahoo Finance v8 REST price fetching
│       │   └── fetch_macro.py             # FRED CPI fetching
│       └── processing/
│           ├── screening.py               # Static asset universe (37 assets)
│           ├── utils.py                   # Shared BQ config + upload helper
│           ├── metrics.py                 # CAGR, volatility, max DD, Sharpe, worst year
│           ├── backtest.py                # Combined TWD backtesting engine
│           ├── drawdown_events.py         # Drawdown episode detection and event tagging
│           └── fire_calculator.py         # FIRE projection logic
├── github_web/
│   ├── index.html                         # Static web dashboard (GitHub Pages)
│   ├── landing.html                       # Project landing page
│   ├── scripts/
│   │   ├── export_web_data.py             # BigQuery → ppl-data.js export
│   │   ├── validate_export.py             # Post-export data validation
│   │   └── backfill_missing_web_assets.py
│   └── src/
│       ├── colors_and_type.css            # Design tokens (shared with Streamlit)
│       └── ppl-data.js                    # Exported asset metrics + price history (auto-generated)
├── looker_studio/
│   ├── export_portfolio_tables.py         # Generates 7 portfolio-level BigQuery tables
│   ├── generate_bigquery_views.py         # Creates 4 asset-level semantic views
│   └── generated/                         # CSV snapshots of Looker-facing tables
├── tests/
│   ├── conftest.py                        # Shared fixtures (no network calls)
│   ├── processing/
│   │   ├── test_metrics.py                # CAGR, volatility, max DD, Sharpe, worst year
│   │   ├── test_backtest.py               # TWD backtest engine + ticker whitelist
│   │   ├── test_fire_calculator.py        # FIRE projection logic
│   │   └── test_drawdown_events.py        # Drawdown episode detection + event labeling
│   └── export/
│       └── test_export_web_data.py        # ppl-data.js schema + idempotency
├── dashboard/
│   └── Passive_Portfolio_Lab.py           # Streamlit Cloud entry point shim
├── docs/
│   └── project_report.pptx               # Technical project report (15 slides)
├── .github/
│   └── workflows/
│       └── update-and-deploy.yml          # Daily data refresh + GitHub Pages deploy
├── CLAUDE.md                              # Claude Code project instructions
├── pytest.ini                             # pytest configuration
├── requirements.txt                       # Root-level shim for Streamlit Cloud
├── .env.example                           # Environment variable template
└── README.md
```

---

## Environment Variables

Create a local `.env` file using `.env.example` as a template:

```env
GOOGLE_CLOUD_PROJECT=your-project-id
BIGQUERY_DATASET=portfolio
GOOGLE_APPLICATION_CREDENTIALS=credentials.json
FRED_API_KEY=your-fred-api-key          # optional; falls back to 2.5% inflation
GEMINI_API_KEY=your-gemini-api-key      # optional; AI insights hidden if absent
APP_PASSWORD=your-password              # optional; enables Streamlit password gate
```

---

## Tests

```bash
pytest tests/
```

100 tests across 5 modules. All external I/O (BigQuery, Yahoo Finance, FRED, Gemini) is mocked — no network access required.

| Module | Coverage |
|---|---|
| `test_metrics.py` | CAGR, volatility (equity vs crypto annualisation), max drawdown, Sharpe, worst year |
| `test_backtest.py` | Combined TWD backtest engine, ticker whitelist, monthly contribution injection |
| `test_fire_calculator.py` | Years-to-FIRE, weighted CAGR, inflation adjustment, 50-year cap |
| `test_drawdown_events.py` | Episode detection, 12+ historical event labels, recovery period |
| `test_export_web_data.py` | PPL_ASSETS schema, PPL_PRICE_HISTORY structure, TWD conversion, idempotency |

---

## Data Pipeline

GitHub Actions runs daily at 01:00 Taiwan time (17:00 UTC):

1. `fetch_prices.py` — pulls closing prices for all 37 assets from Yahoo Finance v8 REST API
2. `fetch_macro.py` — pulls latest US CPI year-over-year from FRED
3. `metrics.py` — calculates CAGR, volatility, max drawdown, Sharpe ratio, worst year per asset
4. `export_web_data.py` — exports asset metrics + 3-year daily TWD price history to `ppl-data.js`
5. `validate_export.py` — validates schema and value ranges before commit
6. Git commit + GitHub Pages deploy

Streamlit and Looker Studio read from BigQuery directly (real-time). GitHub Pages consumes the static `ppl-data.js` snapshot.

---

## Methodology & Risk Notes

- Historical performance does not guarantee future results.
- All portfolio-level backtests are calculated in TWD to reflect the experience of a Taiwan-based investor.
- USD-denominated assets are converted using historical TWD/USD exchange rates from Yahoo Finance.
- The correlation engine is a diversification aid, not a full covariance optimisation model.
- Risk allocation uses annualized volatility as the primary risk proxy.
- Crypto metrics should be interpreted cautiously due to shorter history and extreme tail risk.
- The 4% withdrawal rule is a baseline; conservative investors may prefer 3.0–3.5%.
