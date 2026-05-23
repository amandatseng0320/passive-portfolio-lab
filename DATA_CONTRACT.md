# Data Contract

Last updated: 2026-05-23

This document is the authoritative reference for all data schemas in Passive
Portfolio Lab. Any change to field names, types, units, or nullability rules
across BigQuery tables, Looker views, or `ppl-data.js` globals **must** be
reflected here before or simultaneously with the code change.

---

## 0. Ground Rules

### Currency convention

| Layer | Currency | Notes |
|---|---|---|
| BigQuery `raw_prices` | Native (TWD or USD) | Taiwan ETFs quoted in TWD; US ETFs and Crypto in USD |
| BigQuery `asset_metrics` | Dimensionless ratios | CAGR, volatility, max_drawdown are fractional (e.g., 0.12 = 12%) |
| Looker asset-level views | Native (per asset) | `currency` field identifies TWD vs USD |
| Looker portfolio-level tables | TWD | `export_portfolio_tables.py` converts USD assets via daily FX |
| `PPL_PRICE_HISTORY` | TWD | All tickers pre-converted to TWD during export |
| `PPL_FX_RATE` | TWD/USD (rate) | Snapshot of the latest daily close of TWD=X |
| Backtest output | TWD | `portfolio_value`, `total_invested` are TWD amounts |
| FIRE output | TWD | `target_amount`, `portfolio_value` in projection are TWD amounts |

### Annualization convention

| Asset category | Trading days / year |
|---|---|
| CRYPTO | 365 |
| TW_ETF, US_ETF | 252 |

Volatility formula: `daily_return.std() * sqrt(trading_days_per_year)`

### Risk-free rate

The Sharpe ratio uses a fixed risk-free rate of **2% per year** (`risk_free_rate = 0.02`).

### Breaking-change policy

A **breaking change** is any modification that can cause an existing consumer
(Streamlit app, GitHub Web app, or Looker Studio report) to produce wrong
output or crash without a coordinated update:

- Renaming or removing a field.
- Changing a field's type (e.g., fraction → percentage).
- Changing a field's unit or sign convention (e.g., max_drawdown sign flip).
- Removing a required global from `ppl-data.js`.
- Renaming a BigQuery table or view.

When making a breaking change:

1. Update the code (export script, SQL view, or processing module).
2. Update this document (`DATA_CONTRACT.md`).
3. Update the corresponding surface README.
4. Update any schema validation tests in `tests/`.
5. Mention the change in `CHANGELOG.md`.

---

## 1. BigQuery Source Tables

These tables are written by the pipeline scripts and read by the Streamlit
dashboard.

### 1.1 `raw_prices`

Written by: `streamlit_dashboard/src/data_collection/fetch_prices.py`
Read by: Streamlit backtest, `export_web_data.py`, Looker `looker_price_history`

| Field | Type | Nullable | Unit / Notes |
|---|---|---|---|
| `date` | DATE | No | Trading date in YYYY-MM-DD format |
| `ticker` | STRING | No | Asset ticker (e.g., `0050.TW`, `BTC-USD`) |
| `close` | FLOAT64 | No | Adjusted close price in native currency (TWD for TW_ETF, USD for US_ETF / CRYPTO) |
| `category` | STRING | No | `TW_ETF`, `US_ETF`, or `CRYPTO` |

Primary key: `(date, ticker)`
Expected row count: 37 tickers × trading days of history

### 1.2 `asset_metrics`

Written by: `streamlit_dashboard/src/processing/metrics.py`
Read by: Streamlit screening/FIRE, `export_web_data.py`, Looker `looker_asset_metrics`

| Field | Type | Nullable | Unit / Notes |
|---|---|---|---|
| `ticker` | STRING | No | Asset ticker |
| `name` | STRING | No | English display name |
| `category` | STRING | No | `TW_ETF`, `US_ETF`, or `CRYPTO` |
| `data_start` | STRING | No | First available date in `raw_prices` for this ticker (YYYY-MM-DD) |
| `data_end` | STRING | No | Last available date in `raw_prices` for this ticker (YYYY-MM-DD) |
| `cagr` | FLOAT64 | No | Compound Annual Growth Rate as a fraction (e.g., 0.12 = 12%) |
| `volatility` | FLOAT64 | No | Annualized volatility as a fraction; CRYPTO uses 365-day, others use 252-day |
| `max_drawdown` | FLOAT64 | No | Maximum drawdown as a fraction; always ≤ 0 (e.g., -0.35 = -35%) |
| `sharpe_ratio` | FLOAT64 | No | (CAGR − 0.02) / volatility; dimensionless |
| `recovery_period_days` | INT64 | Yes | Calendar days from trough to recovery of the max drawdown; NULL if not yet recovered |
| `recovery_status` | STRING | No | `"Recovered"` or `"Not yet recovered"` |
| `worst_year` | FLOAT64 | No | Return of the single worst calendar year as a fraction (e.g., -0.30 = -30%) |
| `worst_year_label` | INT64 | No | Calendar year number of the worst year (e.g., 2022) |

Primary key: `ticker`
Expected row count: up to 37 (one row per asset that has price history)

---

## 2. BigQuery Looker Asset-Level Views

These views are created by running `looker_studio/bigquery_views.sql`.

### 2.1 `looker_asset_metrics`

Joins `asset_metrics` with static asset metadata embedded in the SQL.

| Field | Type | Nullable | Unit / Notes |
|---|---|---|---|
| `ticker` | STRING | No | Asset ticker |
| `name` | STRING | No | English display name |
| `category` | STRING | No | `TW_ETF`, `US_ETF`, or `CRYPTO` |
| `subcategory` | STRING | No | Investment style (e.g., `Market-Cap`, `High Dividend`, `Store of Value`) |
| `aum_rank` | INT64 | No | AUM rank within category (lower = larger; 99 = owner addition) |
| `aum_note` | STRING | No | Human-readable AUM string (e.g., `approx. TWD 1,661.5B`) |
| `description` | STRING | No | One-paragraph asset description |
| `currency` | STRING | No | `TWD` for TW_ETF; `USD` for US_ETF / CRYPTO |
| `data_start` | DATE | No | First price date |
| `data_end` | DATE | No | Latest price date |
| `cagr` | FLOAT64 | No | Fraction — same as `asset_metrics.cagr` |
| `volatility` | FLOAT64 | No | Fraction |
| `max_drawdown` | FLOAT64 | No | Fraction, ≤ 0 |
| `sharpe_ratio` | FLOAT64 | No | Dimensionless |
| `recovery_period_days` | INT64 | Yes | Calendar days; NULL if not recovered |
| `recovery_status` | STRING | No | `"Recovered"` or `"Not yet recovered"` |
| `worst_year` | FLOAT64 | No | Fraction |
| `worst_year_label` | INT64 | No | Calendar year |
| `cagr_pct` | FLOAT64 | No | `cagr * 100`, rounded to 2 decimal places |
| `volatility_pct` | FLOAT64 | No | `volatility * 100`, rounded to 2 decimal places |
| `max_drawdown_pct` | FLOAT64 | No | `max_drawdown * 100`, rounded to 2 decimal places |
| `worst_year_pct` | FLOAT64 | No | `worst_year * 100`, rounded to 2 decimal places |

### 2.2 `looker_price_history`

Derived from `raw_prices` enriched with metadata.

| Field | Type | Nullable | Unit / Notes |
|---|---|---|---|
| `date` | DATE | No | Trading date |
| `ticker` | STRING | No | Asset ticker |
| `name` | STRING | No | English display name |
| `category` | STRING | No | Asset category |
| `subcategory` | STRING | No | Investment style |
| `currency` | STRING | No | Native currency of the asset |
| `close` | FLOAT64 | No | Adjusted close in native currency |
| `daily_return` | FLOAT64 | Yes | `close / prev_close − 1`; NULL on the first row per ticker |
| `cumulative_return` | FLOAT64 | Yes | `close / first_close − 1`; NULL if first_close is NULL |
| `daily_return_pct` | FLOAT64 | Yes | `daily_return * 100`, rounded to 4 decimal places |
| `cumulative_return_pct` | FLOAT64 | Yes | `cumulative_return * 100`, rounded to 2 decimal places |

### 2.3 `looker_annual_returns`

Derived from `looker_price_history`.

| Field | Type | Nullable | Unit / Notes |
|---|---|---|---|
| `year` | INT64 | No | Calendar year |
| `ticker` | STRING | No | Asset ticker |
| `name` | STRING | No | English display name |
| `category` | STRING | No | Asset category |
| `subcategory` | STRING | No | Investment style |
| `currency` | STRING | No | Native currency |
| `annual_return` | FLOAT64 | Yes | `last_close / first_close − 1` within the year; fraction |
| `annual_return_pct` | FLOAT64 | Yes | `annual_return * 100`, rounded to 2 decimal places |

### 2.4 `looker_category_summary`

Aggregated from `looker_asset_metrics`.

| Field | Type | Nullable | Unit / Notes |
|---|---|---|---|
| `category` | STRING | No | `TW_ETF`, `US_ETF`, or `CRYPTO` |
| `asset_count` | INT64 | No | Number of assets in the category |
| `avg_cagr` | FLOAT64 | No | Average CAGR as a fraction |
| `avg_volatility` | FLOAT64 | No | Average volatility as a fraction |
| `avg_max_drawdown` | FLOAT64 | No | Average max drawdown as a fraction, ≤ 0 |
| `avg_sharpe_ratio` | FLOAT64 | No | Average Sharpe ratio |
| `avg_cagr_pct` | FLOAT64 | No | `avg_cagr * 100` |
| `avg_volatility_pct` | FLOAT64 | No | `avg_volatility * 100` |
| `avg_max_drawdown_pct` | FLOAT64 | No | `avg_max_drawdown * 100` |

---

## 3. BigQuery Looker Portfolio-Level Tables

Written by: `looker_studio/export_portfolio_tables.py`
All portfolio values are in **TWD**.

### 3.1 `looker_portfolio_allocations`

| Field | Type | Nullable | Unit / Notes |
|---|---|---|---|
| `portfolio_id` | STRING | No | Snake-case ID (e.g., `young_professional`) |
| `portfolio_name_zh` | STRING | No | Chinese portfolio name |
| `portfolio_name_en` | STRING | No | English portfolio name |
| `portfolio_type` | STRING | No | `Persona` or `Core` |
| `risk_level` | STRING | No | `Low`, `Medium`, or `High` |
| `ticker` | STRING | No | Asset ticker |
| `name` | STRING | No | Asset English name |
| `category` | STRING | No | Asset category |
| `subcategory` | STRING | No | Investment style |
| `currency` | STRING | No | Native asset currency |
| `weight` | FLOAT64 | No | Fractional allocation weight (0.0–1.0); all weights within a portfolio sum to 1.0 |
| `weight_pct` | FLOAT64 | No | `weight * 100` |

### 3.2 `looker_portfolio_metrics`

One row per portfolio, summarizing overall performance.

| Field | Type | Nullable | Unit / Notes |
|---|---|---|---|
| `portfolio_id` | STRING | No | |
| `portfolio_name_zh` | STRING | No | |
| `portfolio_name_en` | STRING | No | |
| `portfolio_type` | STRING | No | `Persona` or `Core` |
| `risk_level` | STRING | No | |
| `initial_investment` | FLOAT64 | No | TWD; lump sum on day one |
| `monthly_contribution` | FLOAT64 | No | TWD; DCA amount per month |
| `backtest_start` | STRING | No | YYYY-MM-DD |
| `backtest_end` | STRING | No | YYYY-MM-DD |
| `final_value` | FLOAT64 | No | TWD; portfolio value on last day |
| `total_invested` | FLOAT64 | No | TWD; cumulative invested amount |
| `total_return_pct` | FLOAT64 | No | `(final_value / total_invested − 1) * 100` |
| `cagr` | FLOAT64 | No | Fraction |
| `volatility` | FLOAT64 | No | Fraction, 252-day annualized |
| `max_drawdown` | FLOAT64 | No | Fraction, ≤ 0 |
| `sharpe_ratio` | FLOAT64 | No | (portfolio CAGR − 0.02) / portfolio volatility |
| `annual_expenses` | FLOAT64 | No | TWD; used for FIRE target calculation |
| `withdrawal_rate` | FLOAT64 | No | Fraction (e.g., 0.04 = 4%) |
| `fire_target` | FLOAT64 | No | TWD; `annual_expenses / withdrawal_rate` |
| `inflation_rate` | FLOAT64 | No | Fraction (e.g., 0.025 = 2.5%) |

### 3.3 `looker_portfolio_history`

Daily portfolio value series for each portfolio.

| Field | Type | Nullable | Unit / Notes |
|---|---|---|---|
| `portfolio_id` | STRING | No | |
| `portfolio_name_zh` | STRING | No | |
| `portfolio_name_en` | STRING | No | |
| `date` | DATE | No | Trading date |
| `portfolio_value_twd` | FLOAT64 | No | TWD; current market value of all holdings |
| `total_invested_twd` | FLOAT64 | No | TWD; cumulative invested capital |
| `total_return_pct` | FLOAT64 | No | `(portfolio_value / total_invested − 1) * 100` |
| `drawdown_pct` | FLOAT64 | No | Current drawdown from all-time high as a percentage (≤ 0) |

### 3.4 `looker_portfolio_annual_returns`

| Field | Type | Nullable | Unit / Notes |
|---|---|---|---|
| `portfolio_id` | STRING | No | |
| `portfolio_name_zh` | STRING | No | |
| `portfolio_name_en` | STRING | No | |
| `year` | INT64 | No | Calendar year |
| `annual_return_pct` | FLOAT64 | No | Year-over-year return as percentage |

### 3.5 `looker_portfolio_drawdown_events`

Top drawdown episodes per portfolio.

| Field | Type | Nullable | Unit / Notes |
|---|---|---|---|
| `portfolio_id` | STRING | No | |
| `portfolio_name_zh` | STRING | No | |
| `portfolio_name_en` | STRING | No | |
| `rank` | INT64 | No | 1 = deepest episode |
| `peak_date` | DATE | No | Date of the pre-drawdown high |
| `trough_date` | DATE | No | Date of the maximum drawdown within the episode |
| `recovery_date` | DATE | Yes | Date the portfolio recovered to the prior peak; NULL if still underwater |
| `drawdown_pct` | FLOAT64 | No | `(trough / peak − 1) * 100`; always ≤ 0 |
| `duration_days` | INT64 | No | Calendar days from peak to trough |
| `recovery_days` | INT64 | Yes | Calendar days from trough to recovery; NULL if not recovered |
| `event_label` | STRING | No | Human-readable historical event label or `"—"` if no curated event matched |

### 3.6 `looker_fire_scenarios`

One row per portfolio showing FIRE summary.

| Field | Type | Nullable | Unit / Notes |
|---|---|---|---|
| `portfolio_id` | STRING | No | |
| `portfolio_name_zh` | STRING | No | |
| `portfolio_name_en` | STRING | No | |
| `portfolio_type` | STRING | No | |
| `risk_level` | STRING | No | |
| `annual_expenses` | FLOAT64 | No | TWD |
| `withdrawal_rate` | FLOAT64 | No | Fraction |
| `fire_target` | FLOAT64 | No | TWD; `annual_expenses / withdrawal_rate` |
| `initial_capital` | FLOAT64 | No | TWD; starting savings |
| `monthly_contribution` | FLOAT64 | No | TWD |
| `portfolio_cagr` | FLOAT64 | No | Weighted average CAGR (fraction) from backtest |
| `inflation_rate` | FLOAT64 | No | Fraction |
| `years_to_fire_nominal` | INT64 | Yes | Years to reach FIRE target under nominal (no inflation adjustment); NULL if not reached within 50 years |
| `years_to_fire_real` | INT64 | Yes | Years to reach inflation-adjusted FIRE target; NULL if not reached within 50 years |

### 3.7 `looker_fire_projection`

Year-by-year FIRE projection for each portfolio, up to 50 years.

| Field | Type | Nullable | Unit / Notes |
|---|---|---|---|
| `portfolio_id` | STRING | No | |
| `portfolio_name_zh` | STRING | No | |
| `portfolio_name_en` | STRING | No | |
| `year` | INT64 | No | 1 through 50 |
| `nominal_value` | FLOAT64 | No | TWD; projected portfolio value without inflation adjustment |
| `real_value` | FLOAT64 | No | TWD; projected portfolio value adjusted for inflation |
| `fire_target` | FLOAT64 | No | TWD; nominal FIRE target (constant) |

---

## 4. `github_web/src/ppl-data.js` Globals

This file is regenerated nightly by GitHub Actions via `export_web_data.py`.
It is a JavaScript file loaded synchronously by `github_web/index.html`.

### 4.1 `PPL_ASSETS`

Type: JavaScript array of objects  
Required: yes  
Source: `asset_metrics` (BigQuery) joined with `ASSET_POOL` (screening.py) metadata

Each element represents one asset. Required fields per object:

| JS Property | Type | Nullable | Unit / Notes |
|---|---|---|---|
| `ticker` | string | No | Asset ticker (e.g., `"0050.TW"`) |
| `name` | string | No | English display name |
| `nameZh` | string | Yes | Chinese name; present only for Taiwan ETFs (14 tickers) |
| `category` | string | No | `"TW_ETF"`, `"US_ETF"`, or `"CRYPTO"` |
| `subcategory` | string | No | Investment style label |
| `currency` | string | No | `"TWD"` for TW_ETF; `"USD"` for US_ETF / CRYPTO |
| `aumNote` | string | No | Human-readable AUM string |
| `cagr` | number | No | Percentage (e.g., `12.3` means 12.3%). **Note: percentage, not fraction.** |
| `vol` | number | No | Annualized volatility percentage |
| `maxDD` | number | No | Maximum drawdown percentage; always ≤ 0 |
| `sharpe` | number | No | Sharpe ratio; dimensionless, 2 decimal places |
| `worstYear` | number | No | Worst calendar year return percentage |
| `worstYearLabel` | number | No | Calendar year of worst performance (integer) |

Expected element count: up to 37 (any ticker missing from `asset_metrics` and
without a defined fallback in `METRIC_FALLBACKS` will be silently skipped).

### 4.2 `PPL_PRICE_HISTORY`

Type: JavaScript object (dictionary)  
Required: yes  
Source: `raw_prices` (BigQuery); USD assets converted to TWD using Yahoo Finance FX

Structure:
```
{
  "<ticker>": [
    ["YYYY-MM-DD", <close_twd_float>],
    ...
  ],
  ...
}
```

| Component | Type | Notes |
|---|---|---|
| Key | string | Asset ticker matching `PPL_ASSETS[i].ticker` |
| Value | array of arrays | Each inner array is `[date_string, close_twd]` |
| `date_string` | string | `"YYYY-MM-DD"` format |
| `close_twd` | number | Adjusted close price in TWD; rounded to 4 decimal places. USD assets are multiplied by the daily TWD/USD rate before storage. |

Expected key count: up to 37 tickers that exist in `raw_prices`.

### 4.3 `PPL_FX_RATE`

Type: number  
Required: yes  
Unit: TWD per USD (e.g., `31.85`)  
Source: latest daily close of `TWD=X` from Yahoo Finance, fetched during export  
Note: This is a display rate for the USD toggle. It does **not** affect
historical backtest accuracy, which uses the per-day rates already embedded
in `PPL_PRICE_HISTORY`.

### 4.4 `PPL_HISTORY_UPDATED_AT`

Type: string  
Required: yes  
Format: `"YYYY-MM-DD HH:MM UTC"` (e.g., `"2026-05-23 17:03 UTC"`)  
Source: UTC timestamp at the moment `export_web_data.py` runs  
Note: This timestamp is shown in the GitHub Web footer to indicate data
freshness.

---

## 5. Backtest Output Schema

Returned by `backtest.run_combined()` and `backtest.run_backtest()`.  
Not stored in BigQuery; used by Streamlit and GitHub Web in-memory.

| Column | Type | Unit / Notes |
|---|---|---|
| `date` | datetime | Trading date |
| `portfolio_value` | float | TWD; current market value of all holdings |
| `total_invested` | float | TWD; cumulative invested capital (initial + all DCA to date) |
| `total_return_pct` | float | `(portfolio_value / total_invested − 1) * 100`; percentage |
| `strategy` | string | Always `"Combined"` in the current implementation |

### 5.1 Backtest key formulas

**Total return %**
```
total_return_pct = (portfolio_value / total_invested - 1) * 100
```

**Weight normalization**  
If a ticker in `tickers_weights` has no price data in the given date range,
it is excluded and the remaining weights are re-normalized to sum to 1.0.

**USD to TWD conversion**  
A ticker is treated as USD if its ticker string does not end with `.TW`.
`pivot[ticker] *= fx.reindex(pivot.index).ffill().bfill()`

---

## 6. FIRE Calculator Output Schema

Returned by `fire_calculator.calculate_fire()`.  
Not stored in BigQuery; used in-memory by Streamlit.

| Key | Type | Unit / Notes |
|---|---|---|
| `years_to_fire` | int or None | Years until portfolio value ≥ `target_amount`; None if not reached within `max_years` (default 50) |
| `annual_cagr` | float | Weighted CAGR used in the simulation; fraction |
| `projection` | DataFrame | Year-by-year projection (columns: `year` INT, `portfolio_value` FLOAT TWD) |

### 6.1 FIRE key formulas

**FIRE target (displayed in UI)**
```
fire_target = annual_expenses / withdrawal_rate
```

**Monthly growth rate**
```
monthly_rate = (1 + annual_cagr) ^ (1/12) - 1
```

**Portfolio growth per month**
```
portfolio_value = portfolio_value * (1 + monthly_rate) + monthly_contribution
```

**Nominal vs real FIRE target**  
For real (inflation-adjusted) FIRE calculations, the target itself is
inflated each year:
```
real_target_at_year_n = fire_target * (1 + inflation_rate) ^ n
```

---

## 7. Drawdown Episode Schema

Returned by `drawdown_events.identify_drawdown_events()`.  
Used by Streamlit, GitHub Web, and stored in `looker_portfolio_drawdown_events`.

| Column | Type | Nullable | Unit / Notes |
|---|---|---|---|
| `rank` | int | No | 1 = deepest episode |
| `peak_date` | Timestamp | No | Pre-drawdown all-time high |
| `trough_date` | Timestamp | No | Day of maximum drawdown within episode |
| `recovery_date` | Timestamp | Yes | Day the portfolio returned to or above the prior peak; NaT if still underwater |
| `drawdown_pct` | float | No | Fraction, always ≤ 0 (e.g., -0.35 = -35%) |
| `duration_days` | int | No | Calendar days from peak to trough |
| `recovery_days` | int | Yes | Calendar days from trough to recovery; NaN if not recovered |
| `event_label` | string | No | Curated event label (e.g., `"COVID-19 pandemic crash"`) or `"—"` |

**Episode definition:**  
A contiguous stretch during which the portfolio trades below its prior
all-time high. A new episode begins the first day the value falls below the
running maximum. It ends the first day the value returns to or exceeds the
prior peak.

**Minimum depth filter:** episodes with `abs(drawdown_pct) < 0.02` (< 2%)
are excluded from output.

---

## 8. Asset Universe

The asset universe is defined in `streamlit_dashboard/src/processing/screening.py`
as `ASSET_POOL` and is the single source of truth for which tickers are
supported. As of 2026-05-23:

- 14 Taiwan ETFs (`.TW` / `.TWO` suffix)
- 15 US ETFs (no suffix or `-USD`)
- 8 Crypto assets (`-USD` suffix)
- Total: **37 assets**

New tickers must be added to `ASSET_POOL` first, then backfilled via
`github_web/scripts/backfill_missing_web_assets.py` and re-exported.
Any addition is a non-breaking additive change. Any removal is a breaking
change that requires updating all three surfaces.
