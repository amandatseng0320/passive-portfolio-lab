# Final Report — Passive Portfolio Lab

**Date:** 2026-05-23  
**Prepared by:** Amanda Tseng  
**Status:** Closing pipeline complete

---

## Executive Summary

Passive Portfolio Lab (PPL) is a data-driven investment analysis toolkit built for Taiwan-based passive investors. It ingests daily price data from Yahoo Finance via BigQuery, applies a curated universe of 37 assets (14 Taiwan ETFs, 15 US ETFs, 8 cryptocurrencies), and delivers analysis across three delivery surfaces: an interactive Streamlit dashboard, a static GitHub Pages web app, and a Looker Studio BI report. All monetary calculations are denominated in **New Taiwan Dollar (TWD)**; USD display is a toggle-only conversion.

The project is delivered in a fully operational state with automated daily data refresh, a 98-test suite with zero failures, documented security posture, and observability recommendations ready to implement.

---

## 1. What Was Built

### 1.1 Three Delivery Surfaces

| Surface | Technology | Audience | Live URL |
|---|---|---|---|
| **Streamlit Dashboard** | Python, Streamlit Cloud, BigQuery | Interactive users; personal finance deep-dives | `passive-portfolio-lab-new.streamlit.app` |
| **GitHub Web** | React 18, Babel Standalone, Chart.js, GitHub Pages | Public demo; mobile-friendly static display | `amandatseng0320.github.io/passive-portfolio-lab` |
| **Looker Studio** | Looker Studio, BigQuery views | Portfolio reporting; shareable read-only dashboards | (Looker Studio link in README) |

### 1.2 Asset Universe

37 assets across four categories, curated for passive investing suitability:

| Category | Count | Examples |
|---|---|---|
| Taiwan ETF | 14 | 0050.TW, 00878.TW, 00646.TW, 006208.TW |
| US ETF | 15 | SPY, QQQ, VTI, BND, GLD |
| Crypto | 8 | BTC-USD, ETH-USD, SOL-USD |

Selection criteria: passive index strategy, ≥5 years of price history, sufficient AUM/liquidity, multi-asset-class coverage.

### 1.3 Core Features

| Feature | Streamlit | GitHub Web | Looker |
|---|---|---|---|
| Asset screening (sort, filter, CAGR/vol/maxDD/Sharpe) | Full | Full | Read-only |
| Correlation analysis + overlap detection | Full | Full | Not available |
| Risk-level allocation (auto + manual) | Full | Full | Read-only |
| Backtest (lump-sum + DCA, TWD, daily prices) | Full (BigQuery) | Estimated (CAGR-based) | Chart only |
| Drawdown episodes + historical event labels | Full | Full | Chart only |
| FIRE calculator (savings rate, target, projection) | Full | Full | Scenarios only |
| Portfolio summary | Full | Full | Full |
| AI insights (Gemini 2.5 Flash) | Full | Not available | Not available |
| Currency toggle (TWD ↔ USD) | Full | Full | TWD only |
| Bilingual UI (EN / ZH) | Partial | Full | ZH only |

### 1.4 Data Pipeline

```
Yahoo Finance REST API
        ↓  (nightly, GitHub Actions)
BigQuery: raw_prices + asset_metrics
        ↓
export_web_data.py  →  ppl-data.js  →  GitHub Pages
        ↓
export_portfolio_tables.py  →  Looker BigQuery views
        ↓
Streamlit Cloud: reads BigQuery directly at runtime
```

The GitHub Actions workflow (`update-and-deploy.yml`) runs daily at 17:00 UTC (01:00 Taipei time), exports fresh data, commits `ppl-data.js`, and deploys GitHub Pages — fully automated with no manual intervention.

---

## 2. Key Design Decisions

### TWD as calculation base
All backtests and FIRE projections are computed in TWD. USD-denominated assets (US ETFs, crypto) are converted to TWD using **daily historical FX rates** (not a snapshot), so exchange rate movements are captured in portfolio returns. The USD display toggle is a cosmetic division only.

### Static GitHub Web
`github_web/` has no server-side runtime and makes no BigQuery calls from the browser. All data is bundled in `ppl-data.js` and served as static JavaScript globals. This eliminates credential exposure risk and ensures the page loads from any CDN or cache.

### Backtest estimation fallback
When BigQuery price history is not loaded (GitHub Web static mode), the backtest section estimates returns from the pre-exported CAGR metrics rather than daily prices. This is labelled clearly to users as "estimated from metrics."

### Volatility conventions
Annualized volatility uses **√252** for equity ETFs and **√365** for crypto, matching standard market conventions. The `category` field in `asset_metrics` drives this selection. Tests verify the ratio equals `√(365/252)` to prevent regression.

---

## 3. Test Suite

98 tests across five modules, all passing. Zero external network calls.

| File | Tests | What it covers |
|---|---|---|
| `test_metrics.py` | 25 | CAGR, volatility (equity vs crypto), maxDD, Sharpe, worst year |
| `test_backtest.py` | 18 | Lump-sum, DCA timing, FX conversion, mixed currency, output schema |
| `test_fire_calculator.py` | 16 | FIRE target formula, years-to-fire, growth mechanics, projection |
| `test_drawdown_events.py` | 24 | Episode detection, depth, duration, underwater, top_n, event labels |
| `test_export_web_data.py` | 15 | ppl-data.js globals, unit conventions, replace idempotency |

Run with: `cd tests && pip install -r requirements_test.txt && pytest -v`

---

## 4. Security Posture

Full analysis in [SECURITY_REVIEW.md](SECURITY_REVIEW.md). Summary:

| Severity | Count | Status |
|---|---|---|
| Critical | 0 | — |
| High | 0 | — |
| Medium | 3 | 2 open (ticker SQL whitelist, SA IAM scope); 1 accepted (SSL verify=False) |
| Low | 4 | All accepted or no-code-change mitigations |
| Info | 3 | No action required |

**Key accepted risks:**
- `credentials.json` and `.env` are gitignored and have never been committed.
- `verify=False` on Yahoo Finance calls is documented; a FX range filter (20–50 TWD/USD) provides a second line of defence.

**Open items before production hardening:**
1. Add ticker whitelist check in `backtest.py:70` and `fire_calculator.py:20`.
2. Verify service account `passive-portfolio-sa` does not hold `roles/editor` or `roles/owner`.

---

## 5. Observability

Full analysis in [MONITORING.md](MONITORING.md). Current state: workflow pass/fail is visible in GitHub Actions; export timestamp is shown in the GitHub Web footer.

**Recommended next steps (in priority order):**
1. Enable GitHub email notifications for workflow failures — zero code change needed.
2. Add `github_web/scripts/validate_export.py` — checks asset count, freshness, FX plausibility, price recency.
3. Add workflow summary block — human-readable export log in the GitHub Actions UI.
4. Add artifact upload — retain `ppl-data.js` for 7 days for post-incident debugging.

---

## 6. Known Limitations

| Limitation | Surface | Notes |
|---|---|---|
| Requires BigQuery credentials at runtime | Streamlit | App shows error banner if credentials missing or expired |
| Historical backtest uses estimated returns | GitHub Web | Clearly labelled; full daily-price backtest available in Streamlit |
| Looker Studio tables require manual re-export | Looker | Re-run `export_portfolio_tables.py` after major data updates |
| Crypto metrics have shorter history | All | 00955.TWO data starts 2023; crypto varies by asset |
| AI insights dependent on Gemini API key | Streamlit | Gracefully hidden if key not configured |
| Streamlit free tier hibernates after inactivity | Streamlit | Users see "waking up" spinner; no data loss |

---

## 7. File Map

```
passive-portfolio-lab/
├── .github/workflows/update-and-deploy.yml   # Daily CI/CD pipeline
├── github_web/
│   ├── index.html                            # React SPA (single file, ~1800 lines)
│   └── src/ppl-data.js                       # Auto-generated nightly data export
├── streamlit_dashboard/
│   ├── app.py                                # Main Streamlit app (~2300 lines)
│   └── src/
│       ├── data_collection/                  # fetch_prices.py, fetch_macro.py
│       └── processing/                       # backtest.py, fire_calculator.py,
│                                             # drawdown_events.py, screening.py, metrics.py
├── github_web/scripts/
│   └── export_web_data.py                    # BigQuery → ppl-data.js exporter
├── looker_studio/
│   ├── bigquery_views.sql                    # Four Looker asset views
│   └── export_portfolio_tables.py            # Portfolio table generator
├── tests/
│   ├── conftest.py                           # Shared fixtures
│   ├── processing/                           # test_metrics, test_backtest, test_fire_calculator,
│   │                                         # test_drawdown_events
│   └── export/                               # test_export_web_data
├── DELIVERY_SCOPE.md                         # Feature matrix + done checklist
├── DATA_CONTRACT.md                          # Schema reference + unit conventions
├── TEST_STRATEGY.md                          # Test priorities + isolation rules
├── SECURITY_REVIEW.md                        # 11 findings, severity ratings, mitigations
├── MONITORING.md                             # Observability gaps + recommendations
└── CHANGELOG.md                              # Change history
```

---

## 8. Handover Checklist

- [x] Three delivery surfaces operational
- [x] Daily data pipeline automated (GitHub Actions, 17:00 UTC)
- [x] 98 tests passing, zero external dependencies
- [x] All secrets gitignored, never committed
- [x] Security review completed (0 Critical, 2 Medium open items documented)
- [x] Monitoring gaps documented with actionable recommendations
- [x] GitHub Web: SEO meta tags, mobile responsive layout, bilingual instruction popup
- [x] DATA_CONTRACT.md: schema + unit conventions documented
- [x] CHANGELOG.md: all changes recorded
- [ ] Ticker SQL whitelist — recommended before production hardening
- [ ] Service account IAM scope verification — recommended before production hardening
- [ ] `validate_export.py` — recommended for automated data quality monitoring
