# Passive Portfolio Lab Handoff

Last updated: 2026-05-23

This document is for the next AI agent taking over Passive Portfolio Lab. It
summarizes the current project state, known delivery surfaces, and the suggested
closing pipeline.

## 1. Project Summary

Passive Portfolio Lab is a bilingual toolkit for long-term passive investors,
focused on TWD-based portfolio analysis for Taiwan-based users.

Core question:

```text
If a portfolio's backtested return looks attractive, what is the risk,
drawdown pain, and FIRE trade-off behind it?
```

The project currently has three delivery surfaces:

| Surface | Status | Purpose |
|---|---|---|
| Streamlit Dashboard | Live | Interactive research app with BigQuery reads, live data helpers, portfolio analysis, FIRE logic, and optional Gemini insights |
| GitHub Web | Live | Static GitHub Pages app using exported BigQuery data from `github_web/src/ppl-data.js` |
| Looker Studio | Live | BI/reporting dashboard backed by BigQuery views and portfolio tables |

Live links are documented in `README.md`:

- Streamlit Dashboard: `https://passive-portfolio-lab-new.streamlit.app/`
- GitHub Web: `https://amandatseng0320.github.io/passive-portfolio-lab/`
- Looker Studio Dashboard: `https://datastudio.google.com/reporting/c2e7b15c-bf18-460f-8daf-dc480bcbca67`

## 2. Repository Map

Important files and directories:

```text
passive-portfolio-lab/
├── README.md
├── HANDOFF.md
├── requirements.txt
├── .github/
│   └── workflows/
│       └── update-and-deploy.yml
├── streamlit_dashboard/
│   ├── README.md
│   ├── app.py
│   ├── requirements.txt
│   └── src/
│       ├── data_collection/
│       │   ├── fetch_macro.py
│       │   └── fetch_prices.py
│       └── processing/
│           ├── backtest.py
│           ├── drawdown_events.py
│           ├── fire_calculator.py
│           ├── metrics.py
│           └── screening.py
├── github_web/
│   ├── README.md
│   ├── index.html
│   ├── serve.py
│   ├── serve.rb
│   ├── scripts/
│   │   ├── backfill_missing_web_assets.py
│   │   └── export_web_data.py
│   └── src/
│       ├── colors_and_type.css
│       └── ppl-data.js
└── looker_studio/
    ├── README.md
    ├── bigquery_views.sql
    ├── export_portfolio_tables.py
    └── generate_bigquery_views.py
```

There is currently no committed `tests/` directory, no formal changelog, and no
formal data contract document.

## 3. Current Functional State

### Streamlit Dashboard

Entry point:

```bash
streamlit run streamlit_dashboard/app.py
```

Primary responsibilities:

- Bilingual UI: English and Traditional Chinese.
- Curated asset universe of Taiwan ETFs, US ETFs, and crypto assets.
- Asset screening and filtering.
- Persona quick start portfolios.
- Correlation analysis.
- Risk allocation and portfolio visualization.
- TWD-based backtest with initial investment plus monthly contributions.
- USD-denominated asset conversion into TWD using historical FX rates.
- Drawdown episode detection.
- FIRE calculator with nominal and inflation-adjusted timelines.
- Optional Gemini-generated summary when `GEMINI_API_KEY` is configured.

Important modules:

- `streamlit_dashboard/src/processing/screening.py`
- `streamlit_dashboard/src/processing/metrics.py`
- `streamlit_dashboard/src/processing/backtest.py`
- `streamlit_dashboard/src/processing/drawdown_events.py`
- `streamlit_dashboard/src/processing/fire_calculator.py`
- `streamlit_dashboard/src/data_collection/fetch_prices.py`
- `streamlit_dashboard/src/data_collection/fetch_macro.py`

Environment variables:

```env
GOOGLE_CLOUD_PROJECT=your-project-id
BIGQUERY_DATASET=passive_portfolio
GOOGLE_APPLICATION_CREDENTIALS=credentials.json
FRED_API_KEY=your-fred-api-key
GEMINI_API_KEY=your-gemini-api-key
APP_PASSWORD=your-password
```

### GitHub Web

Entry point:

```text
github_web/index.html
```

This app is static. It does not query BigQuery from the browser. Instead,
GitHub Actions runs:

```bash
python github_web/scripts/export_web_data.py
```

The generated web data lives in:

```text
github_web/src/ppl-data.js
```

`ppl-data.js` currently provides:

- `PPL_ASSETS`
- `PPL_PRICE_HISTORY`
- `PPL_FX_RATE`
- `PPL_HISTORY_UPDATED_AT`

Important notes:

- Static historical backtests in the web app use exported daily TWD price
  history.
- Inputs and calculations remain TWD-based.
- The TWD/USD toggle is display-only.
- Mobile layout and user-instruction popup are still planned work.

### Looker Studio

Important files:

- `looker_studio/generate_bigquery_views.py`
- `looker_studio/bigquery_views.sql`
- `looker_studio/export_portfolio_tables.py`
- `looker_studio/README.md`

The Looker semantic layer includes these asset-level views:

- `looker_asset_metrics`
- `looker_price_history`
- `looker_annual_returns`
- `looker_category_summary`

The portfolio export script creates these BigQuery tables:

- `looker_portfolio_allocations`
- `looker_portfolio_metrics`
- `looker_portfolio_history`
- `looker_portfolio_annual_returns`
- `looker_portfolio_drawdown_events`
- `looker_fire_scenarios`
- `looker_fire_projection`

The report compares six portfolios:

- Young Professional
- Pre-Retirement
- Aggressive Growth
- Taiwan Core
- US Core
- Crypto Core

## 4. Current Automation

GitHub Actions workflow:

```text
.github/workflows/update-and-deploy.yml
```

Current behavior:

1. Runs on push to `main`.
2. Runs daily at `17:00 UTC`, which is `01:00 Asia/Taipei`.
3. Can be manually triggered with `workflow_dispatch`.
4. Installs Python 3.11 dependencies.
5. Writes the `GCP_SA_KEY` secret to `/tmp/gcp-sa-key.json`.
6. Exports fresh BigQuery data into `github_web/src/ppl-data.js`.
7. Commits `ppl-data.js` if it changed.
8. Deploys `github_web/` to GitHub Pages.

Known next improvements:

- Add failure notification.
- Add data freshness check.
- Add export summary artifact/log.
- Add smoke checks after export.

## 5. Known Gaps

The following items were identified as remaining closing work:

- Code security and vulnerability scan report.
- Formal test strategy and tests.
- Fixed data contract for BigQuery views, Looker tables, and `ppl-data.js`.
- Mobile readability for the GitHub Web version.
- User-instruction popup.
- Deployment monitoring, data freshness checks, and failure notifications.
- Clear feature coverage matrix for Streamlit, GitHub Web, and Looker Studio.
- Formal `CHANGELOG.md`.
- Version/change-history report.
- Final closeout report and sales-kit style deliverables.
- Word document version of the final report.
- Web-facing final product package.
- Usage video introduction.
- Domain name setup.
- SEO metadata.
- Clear explanation of data collection / scraping boundaries.

## 6. Recommended Closing Pipeline

### Phase 1: Scope Freeze

Goal: define what each delivery surface officially supports before making final
changes.

Recommended output:

- `DELIVERY_SCOPE.md`
- Feature matrix for Streamlit, GitHub Web, and Looker Studio.
- Explicit limitations for each surface.

Suggested matrix columns:

- Feature
- Streamlit support
- GitHub Web support
- Looker Studio support
- Notes / limitations

Important features to cover:

- Asset screening
- Persona portfolios
- Manual portfolio selection
- Correlation analysis
- Risk allocation
- Backtest
- Drawdown events
- FIRE calculator
- AI insights
- Static data availability
- Live data availability
- Mobile support
- Export/reporting support

### Phase 2: Data Contract Freeze

Goal: prevent future field changes from silently breaking frontend charts,
Looker Studio reports, or exports.

Recommended output:

- `DATA_CONTRACT.md`

Must document:

- BigQuery source tables used by Streamlit.
- BigQuery Looker views.
- BigQuery Looker portfolio tables.
- `github_web/src/ppl-data.js` globals.
- Required fields, optional fields, data types, units, and nullability.
- Currency rules, especially TWD calculation vs USD display.
- Breaking-change policy.

Highest priority schemas:

- `PPL_ASSETS`
- `PPL_PRICE_HISTORY`
- `PPL_FX_RATE`
- `PPL_HISTORY_UPDATED_AT`
- `looker_asset_metrics`
- `looker_portfolio_metrics`
- `looker_portfolio_history`
- `looker_fire_scenarios`

### Phase 3: Test Strategy and Core Tests

Goal: protect the core finance calculations and export contracts.

Recommended output:

- `TEST_STRATEGY.md`
- `tests/` directory

Priority test targets:

- `streamlit_dashboard/src/processing/metrics.py`
- `streamlit_dashboard/src/processing/backtest.py`
- `streamlit_dashboard/src/processing/fire_calculator.py`
- `streamlit_dashboard/src/processing/drawdown_events.py`
- `github_web/scripts/export_web_data.py`
- `looker_studio/export_portfolio_tables.py`

Initial tests should cover:

- CAGR calculation.
- Volatility calculation.
- Max drawdown calculation.
- Sharpe ratio calculation.
- Backtest with initial investment.
- Backtest with monthly contribution.
- USD asset conversion to TWD.
- FIRE target equals annual expenses divided by withdrawal rate.
- Nominal vs real FIRE timeline.
- `ppl-data.js` has required exported variables.
- Exported assets have required fields.

Keep tests deterministic. Use small local fixtures instead of calling BigQuery,
Yahoo Finance, FRED, Gemini, or other network services in unit tests.

### Phase 4: Security and Vulnerability Review

Goal: produce an evidence-based security report suitable for final submission.

Recommended output:

- `SECURITY_REVIEW.md`

Review areas:

- Secret handling.
- `.env` and credentials handling.
- GitHub Actions permissions.
- BigQuery service account scope.
- Dependency vulnerabilities.
- Public static data exposure.
- Streamlit access control and `APP_PASSWORD`.
- Browser-side assumptions in GitHub Web.
- Third-party APIs: Yahoo Finance, FRED, Gemini.

Suggested checks:

```bash
git status --short
rg -n "API_KEY|SECRET|PASSWORD|TOKEN|PRIVATE KEY|GOOGLE_APPLICATION_CREDENTIALS|GCP_SA_KEY" .
python -m pip list --outdated
```

If adding tools, prefer lightweight and reproducible commands. Do not commit
real credentials, generated service account files, or local `.env` files.

### Phase 5: Deployment Monitoring

Goal: make daily data refresh and deploy behavior observable.

Recommended output:

- `MONITORING.md`
- Optional workflow updates in `.github/workflows/update-and-deploy.yml`

Recommended checks:

- `ppl-data.js` export completed.
- `PPL_HISTORY_UPDATED_AT` is recent.
- Number of exported assets is within expected range.
- Price history max date is recent.
- GitHub Pages deploy completed.
- Workflow emits a clear summary.
- Failure notification path is documented.

Possible implementation:

- Add a post-export validation script.
- Add a GitHub Actions summary block.
- Add artifact upload for export summary.
- Add issue/email/Slack notification only if user provides destination.

### Phase 6: GitHub Web UI/UX Final Polish

Goal: make the web version presentable as a final product, especially on mobile.

Recommended output:

- Updated `github_web/index.html`
- Updated `github_web/src/colors_and_type.css`
- Desktop and mobile verification notes

Planned improvements:

- Responsive mobile layout.
- Tables/cards/charts readable on phone screens.
- User-instruction popup.
- Clear labels for supported vs limited features.
- SEO basics: title, description, Open Graph tags.
- Optional domain setup documentation.

Verification:

- Test at desktop width.
- Test at mobile width.
- Confirm no text overlap.
- Confirm charts still render.
- Confirm `ppl-data.js` loads.
- Confirm no frontend console errors.

### Phase 7: Version History and Final Report

Goal: package the project for submission and presentation.

Recommended output:

- `CHANGELOG.md`
- `CHANGE_HISTORY_REPORT.md`
- `FINAL_REPORT.md`
- Optional `.docx` final report
- Optional web-facing sales-kit page
- Optional video script/checklist

`CHANGELOG.md` should be version-oriented:

```text
## [Unreleased]
- Added ...
- Changed ...
- Fixed ...
```

`CHANGE_HISTORY_REPORT.md` should be learning-oriented:

- What changed.
- Why it changed.
- Which files changed.
- What the code does.
- What risk or limitation remains.

`FINAL_REPORT.md` should be audience-oriented:

- Project motivation.
- User problem.
- Data sources.
- System architecture.
- Three delivery surfaces.
- Core financial logic.
- Risk and drawdown interpretation.
- FIRE methodology.
- Security and privacy notes.
- Testing strategy.
- Deployment and monitoring.
- Limitations.
- Future work.

## 7. Suggested Immediate Next Step

Start with the first three documents, in this order:

1. `DELIVERY_SCOPE.md`
2. `DATA_CONTRACT.md`
3. `TEST_STRATEGY.md`

Reason:

- `DELIVERY_SCOPE.md` decides what "done" means.
- `DATA_CONTRACT.md` prevents accidental breakage across BigQuery, Looker, and
  GitHub Web.
- `TEST_STRATEGY.md` turns the most important finance logic into verifiable
  behavior before the final report is written.

After those are drafted, continue with:

1. Add core tests.
2. Write `SECURITY_REVIEW.md`.
3. Write `MONITORING.md`.
4. Polish mobile UI and popup.
5. Write changelog and final report.

## 8. Suggested Acceptance Criteria

The project can be considered ready for final delivery when:

- Streamlit, GitHub Web, and Looker Studio support levels are documented.
- BigQuery, Looker, and web data schemas are documented.
- Core finance calculations have deterministic tests.
- BigQuery export and `ppl-data.js` schema are validated.
- Security review has no unaddressed high-risk finding.
- Daily data refresh has at least freshness validation and documented failure
  handling.
- GitHub Web is readable on mobile.
- User-instruction popup exists.
- `CHANGELOG.md` exists.
- Final report exists in Markdown, with Word export if required.
- Data collection boundaries are clear, including that the curated asset pool is
  static and no scraping occurs at browser runtime.

## 9. Notes for the Next Agent

- Be careful not to change financial formulas casually. If a formula changes,
  update tests, docs, and final report together.
- Treat TWD as the calculation base. USD display is a presentation layer unless
  a specific module says otherwise.
- Avoid network calls in tests. Use fixtures.
- Do not commit secrets or local credentials.
- Keep the GitHub Web app static. It should not require browser-side BigQuery
  credentials.
- Preserve bilingual behavior where user-facing UI changes are made.
- If modifying Looker or BigQuery outputs, update both the SQL/export script and
  the data contract.
- If modifying `ppl-data.js` structure, update `github_web/README.md`,
  `DATA_CONTRACT.md`, and any schema validation tests.
