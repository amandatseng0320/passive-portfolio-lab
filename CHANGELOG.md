# Changelog

All notable changes to Passive Portfolio Lab are recorded here.  
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased] — 2026-05-23 (Closing pipeline)

### Added

#### Documentation
- `DELIVERY_SCOPE.md` — Feature matrix (14 features × 3 surfaces), explicit per-surface limitations, and a binary "done" checklist for final delivery sign-off.
- `DATA_CONTRACT.md` — Authoritative schema reference for BigQuery source tables (`raw_prices`, `asset_metrics`), four Looker asset views, seven Looker portfolio tables, and the four `ppl-data.js` JavaScript globals. Includes unit conventions (CAGR/vol/maxDD stored as **percentages**, not fractions; all prices stored in **TWD**), the backtest output schema, and the FIRE projection schema. Defines a breaking-change update protocol.
- `TEST_STRATEGY.md` — Priority matrix (P0/P1), isolation rules (no BigQuery, Yahoo Finance, FRED, or Gemini calls in tests), float tolerance conventions (`rel=1e-4` / `abs=0.01`), and mock patterns for `load_fx_rate` and `load_cagr_from_bq`.
- `SECURITY_REVIEW.md` — Evidence-based static analysis + manual code review. 11 findings, 0 Critical. Two open Medium items: ticker SQL interpolation without whitelist (`backtest.py:70`, `fire_calculator.py:20`) and unverified service account IAM scope. All secrets remain gitignored and uncommitted.
- `MONITORING.md` — Gap analysis of the daily data refresh pipeline. Documents 7 observability gaps, recommends `validate_export.py` post-export validation script (asset count, freshness, FX plausibility, price recency), workflow summary block, artifact upload, and failure notification options.
- `HANDOFF.md` — Project state snapshot and 7-phase closing pipeline (created in prior session).

#### Test suite (`tests/`)
- `pytest.ini` — Configures `testpaths = tests` so pytest discovers all suites without arguments.
- `tests/requirements_test.txt` — Isolated test dependencies: pytest, pytest-mock, pandas, numpy, pandas-gbq, python-dotenv, pyarrow, requests.
- `tests/conftest.py` — Shared fixtures: `flat_twd_30` (constant TWD FX series), `constant_fx_30` (pandas Series at 30 TWD/USD), `minimal_metrics_df` (one row per ASSET_POOL ticker with fraction-unit CAGR=0.10, max_drawdown=-0.25).
- `tests/processing/test_metrics.py` — 25 tests covering `calculate_metrics()`: CAGR formula, annualized volatility (equity √252 vs crypto √365 ratio verified), max drawdown, Sharpe ratio, worst year, and edge cases (single row, all-flat prices).
- `tests/processing/test_backtest.py` — 18 tests covering `run_combined()`: lump-sum growth, DCA timing (investment starts on first available date), FX conversion (USD assets multiplied by TWD rate; TW tickers never trigger `load_fx_rate`), mixed-currency portfolios, output schema validation.
- `tests/processing/test_fire_calculator.py` — 16 tests covering FIRE calculation: target formula (expenses / rate), years-to-fire with zero growth, monthly growth rate, compound growth mechanics, projection DataFrame structure, and annual CAGR output.
- `tests/processing/test_drawdown_events.py` — 24 tests covering `identify_drawdown_events()` and `match_event_label()`: episode detection, peak/trough/recovery dates, drawdown depth, duration and recovery days, still-underwater episodes, `min_depth_pct` filter, `top_n` parameter, historical event labelling (COVID-19 window verified), and output schema completeness.
- `tests/export/test_export_web_data.py` — 15 tests covering `build_assets_block()`, `build_price_history_block()`, and `replace_assets_block()`: all tickers present, CAGR exported as percentage (not fraction), maxDD as negative percentage, TWD/USD currency flags, FX rate plausibility, `PPL_HISTORY_UPDATED_AT` format, replace idempotency, and missing-marker error.

**Total: 98 tests, all passing in < 1 second.**

#### GitHub Web — mobile responsiveness & instruction popup
- SEO meta tags: `<title>`, `<meta name="description">`, Open Graph and Twitter Card tags.
- Off-canvas sidebar drawer: `#ppl-sidebar` slides in from left on mobile (≤767 px) via CSS `transform: translateX(-100%)` / `.sidebar-open` toggle. Dark overlay (`#ppl-sidebar-overlay`) closes drawer on tap.
- Hamburger button (`#ppl-hamburger`): hidden on desktop, shown on mobile; toggles sidebar. Three-bar SVG spans, no icon library dependency.
- Sidebar close button (`.sidebar-close-btn`): visible on mobile only; positioned top-right inside the sidebar header.
- Header compaction: `#ppl-app-header` reduces padding to `14px 18px` on mobile; separator and tagline divs hidden via `.header-sep` / `.header-tagline` class selectors.
- Responsive layout rules: section padding tightened, tables scroll horizontally, charts capped at 100% width, `.ppl-metric-grid` collapses to 2-column (≤767 px) then 1-column (≤420 px).
- `InstructionPopup` React component: bilingual (EN/ZH), renders `t.introHowSteps` as numbered cards, auto-shows on first visit (localStorage `ppl_help_seen` flag), reopens via `❓ How to use / 使用說明` button in AppHeader.

---

## Prior history (selected)

> The entries below are derived from `git log`. Full commit details are in the git history.

### 2026-05 (pre-handoff)

- **HANDOFF.md** created to document project state, repo map, known gaps, and closing pipeline.
- **GitHub Pages overflow fix** (`62e168b`): prevented horizontal scroll on deployed site.
- **Looker Studio assets** added (`882e391`): dashboard screenshots and config files.
- **Full-width layout** (`453cbb6`): squarified treemap, sortable screening columns, select-all, correlation pairs, persona language fix, removed weight grid.
- **React SPA** (`428752a`): initial commit of `github_web/` as a single-page React 18 + Babel Standalone + Chart.js application.
- **Bilingual persona flow** (`7e3d684`): EN/ZH quick-start personas wired to correlation cleanup confirmation.
- **Dev Container** added (`d3e8fba`).

---

## Versioning note

This project is a personal portfolio analytics tool, not a versioned library. Releases are milestone-based rather than semver. The `[Unreleased]` block above represents the 2026-05-23 closing pipeline batch.
