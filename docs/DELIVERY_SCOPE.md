# Delivery Scope

Last updated: 2026-05-23

This document defines what each delivery surface officially supports, what it
does not support, and what explicit limitations apply. It serves as the scope
freeze for final delivery.

---

## 1. The Three Delivery Surfaces

| Surface | URL | Purpose |
|---|---|---|
| Streamlit Dashboard | https://passive-portfolio-lab-new.streamlit.app/ | Interactive research app — BigQuery reads, live data, full financial analysis, AI insights |
| GitHub Web | https://amandatseng0320.github.io/passive-portfolio-lab/ | Static GitHub Pages app — pre-exported daily data, no server-side code at runtime |
| Looker Studio | https://datastudio.google.com/reporting/c2e7b15c-bf18-460f-8daf-dc480bcbca67 | BI / reporting dashboard — BigQuery-backed, read-only, visualization-focused |

---

## 2. Feature Coverage Matrix

| Feature | Streamlit | GitHub Web | Looker Studio | Notes / Limitations |
|---|---|---|---|---|
| **Asset Screening** | Full | Partial | Read-only table | Streamlit: live price + filter controls. GitHub Web: static table with sort/filter in JS. Looker: filter by category/ticker only. |
| **Persona Quick Start** | Full | Full | Display only | Three presets: Young Professional, Pre-Retirement, Aggressive Growth. Looker shows preset portfolios but not the interactive selection flow. |
| **Manual Portfolio Selection** | Full | Full | Not available | Users select individual assets in Streamlit and GitHub Web. Looker shows six fixed portfolios. |
| **Correlation Analysis** | Full | Not available | Not available | Pairwise correlation matrix using last 3 years of daily returns. Only in Streamlit. |
| **Risk Allocation** | Full | Partial | Not available | Streamlit: risk-tier targeting (Low/Medium/High/Extreme High) with rebalancing. GitHub Web: weight input only, no automated risk targeting. |
| **Portfolio Backtest** | Full | Full | Display only | Both Streamlit and GitHub Web compute TWD backtest (lump sum + monthly DCA). Looker shows six pre-computed portfolio histories. |
| **Drawdown Events** | Full | Full | Display only | Top-5 independent drawdown episodes with historical-event labels. Streamlit and GitHub Web compute dynamically; Looker shows pre-computed episodes for six portfolios. |
| **Annual Returns** | Full | Full | Full | Available on all three surfaces. |
| **FIRE Calculator** | Full | Full | Display only | Streamlit: interactive inputs with live CAGR from BigQuery. GitHub Web: browser-side FIRE projection from exported CAGR. Looker: shows six pre-computed FIRE scenarios. |
| **FIRE Inflation Adjustment** | Full | Full | Partial | Streamlit: uses FRED CPI (falls back to 2.5%). GitHub Web: user-provided inflation rate. Looker: nominal only in main view; real timeline in `looker_fire_projection`. |
| **AI Insights (Gemini)** | Optional | Not available | Not available | Available in Streamlit only when `GEMINI_API_KEY` is configured. Hidden if key is absent. |
| **Live Price / Volume** | Full | Not available | Not available | Streamlit fetches current price and volume via Yahoo Finance v8 REST at session load. GitHub Web and Looker use pre-exported metrics only. |
| **Live FX Rate** | Full | Not available | Not available | Streamlit fetches daily TWD/USD via Yahoo Finance REST for backtest. GitHub Web uses exported `PPL_FX_RATE` (snapshot at last export). |
| **Static Data Availability** | Not applicable | Full | Full | GitHub Web: data exported daily from BigQuery via GitHub Actions. Looker: reads live from BigQuery views updated by pipeline scripts. |
| **Bilingual UI (EN / zh-TW)** | Full | Full | Partial | Streamlit: sidebar toggle switches all labels. GitHub Web: sidebar toggle or URL param. Looker: primarily Chinese labels with English field names. |
| **Mobile Support** | Partial | Partial | Full (native) | Streamlit: Streamlit Cloud default layout, not optimized for phone screens. GitHub Web: basic responsive CSS exists but mobile polish is incomplete (planned). Looker Studio: fully responsive. |
| **User-Instruction Popup** | Not available | Planned | Not applicable | GitHub Web instruction popup is planned but not yet built. |
| **Export / Download** | Partial | Not available | Full | Streamlit: CSV export not built, but chart PNG download available via Plotly controls. Looker: native CSV/PDF/Google Sheets export from report UI. |
| **Portfolio Comparison** | Single portfolio | Single portfolio | Six portfolios | Streamlit and GitHub Web analyze one portfolio at a time. Looker shows six fixed portfolios side-by-side. |
| **SEO Metadata** | Not available | Partial | Not applicable | GitHub Web has basic `<title>`. Open Graph tags, description meta, and sitemap are planned work. |
| **Password Gate** | Optional | Not available | GCP IAM | Streamlit: optional `APP_PASSWORD` in Streamlit secrets. GitHub Web: fully public static site. Looker: access controlled via Google account and GCP project IAM. |

---

## 3. Surface-Level Limitations

### 3.1 Streamlit Dashboard

- Requires BigQuery credentials (`GOOGLE_CLOUD_PROJECT`, `BIGQUERY_DATASET`,
  `GOOGLE_APPLICATION_CREDENTIALS`) to load price history and metrics. If
  credentials are missing or BigQuery is unreachable, the app fails to start.
- FRED integration is optional. If `FRED_API_KEY` is absent, inflation defaults
  to 2.5% with no notification to the user.
- Gemini insights are optional. If `GEMINI_API_KEY` is absent, the AI section
  is silently hidden.
- The backtest engine calls Yahoo Finance REST API for live FX rates during
  each backtest. Network failures cause the backtest to fail.
- Streamlit Cloud free tier has cold-start and memory limits. Portfolios with
  very long date ranges or many tickers may be slow.
- No session persistence between browser refreshes.
- No PDF/CSV download button for backtest results.
- Mobile layout is not specifically optimized; the default Streamlit layout
  applies.

### 3.2 GitHub Web

- Fully static. No server-side code runs in the browser. All data comes from
  `github_web/src/ppl-data.js` which is updated by GitHub Actions.
- Data freshness depends on the daily GitHub Actions workflow. If the workflow
  fails, the web app serves stale data with no visible warning.
- Asset metrics (`cagr`, `vol`, `maxDD`, `sharpe`, `worstYear`) are point-in-
  time snapshots from the last BigQuery export. They do not reflect intraday
  price movements.
- TWD/USD conversion for USD assets uses the `PPL_FX_RATE` snapshot from the
  last export, not a live rate. This affects display accuracy but not
  historical backtest correctness (historical backtests use per-day prices
  already converted to TWD in `PPL_PRICE_HISTORY`).
- No AI insights. No correlation analysis. No risk-tier targeting.
- Mobile layout is partially responsive but has known issues with table
  overflow and chart sizing on narrow screens (planned fix).
- User-instruction popup does not yet exist (planned).
- The asset pool is static (37 assets). Adding new tickers requires updating
  `screening.py`, running the backfill script, and re-exporting.

### 3.3 Looker Studio

- Read-only. No user input. The dashboard is a reporting surface, not an
  interactive calculator.
- Shows six fixed portfolios (Young Professional, Pre-Retirement, Aggressive
  Growth, Taiwan Core, US Core, Crypto Core). Custom portfolios are not
  supported.
- Asset-level views (`looker_price_history`, `looker_annual_returns`) use
  native asset currencies (TWD for Taiwan ETFs, USD for US ETFs and Crypto).
  Portfolio-level tables are converted to TWD by `export_portfolio_tables.py`.
- FIRE scenarios use fixed assumptions per portfolio (see
  `looker_studio/export_portfolio_tables.py`). No user-adjustable inputs.
- Dashboard accuracy depends on the Looker SQL views and portfolio tables being
  regenerated after BigQuery pipeline updates. Stale Looker data will not
  trigger any automatic alert.
- BigQuery query costs apply when the Looker Studio report is loaded or
  refreshed. Large date-range queries on `looker_price_history` can be
  expensive.

---

## 4. Shared Constraints (All Surfaces)

- **TWD is the calculation base.** Portfolio values, invested amounts, return
  percentages, and FIRE projections are in TWD. USD display is a presentation
  layer only.
- **The asset pool is static and curated.** 14 Taiwan ETFs + 15 US ETFs +
  8 Crypto = 37 assets. No web scraping occurs at runtime on any surface.
- **Historical performance does not guarantee future results.** All backtest
  and FIRE outputs are illustrative only.
- **Risk allocation uses annualized volatility as the primary risk proxy.**
  It does not model full covariance or factor exposures.
- **Crypto assets use 365-day annualization for volatility.** All other
  assets use 252-day.
- **The 4% withdrawal rule is the default FIRE baseline.** Conservative
  users should use 3.0–3.5%.
- **No user PII is collected or stored** on any surface.

---

## 5. What "Done" Means for Final Delivery

The project is ready for final delivery when all items in this checklist pass:

- [ ] All three surfaces are reachable and functional at their live URLs.
- [ ] This document (`DELIVERY_SCOPE.md`) accurately reflects the current
      feature set.
- [ ] `DATA_CONTRACT.md` is up to date with current BigQuery schemas and
      `ppl-data.js` globals.
- [ ] Core financial calculations have passing deterministic tests
      (see `TEST_STRATEGY.md`).
- [ ] `SECURITY_REVIEW.md` exists with no unaddressed high-risk finding.
- [ ] GitHub Web is readable on mobile (320px–430px viewport).
- [ ] GitHub Web user-instruction popup exists.
- [ ] `CHANGELOG.md` exists.
- [ ] `FINAL_REPORT.md` exists.
- [ ] Daily GitHub Actions workflow has freshness validation and documented
      failure-handling behavior (`MONITORING.md`).
