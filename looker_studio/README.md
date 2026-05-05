# Looker Studio Dashboard

This folder turns Passive Portfolio Lab's existing BigQuery tables into a
Looker Studio-ready semantic layer. The dashboard is designed in Chinese first,
with English financial labels as supporting context.

Published report:
https://datastudio.google.com/reporting/c2e7b15c-bf18-460f-8daf-dc480bcbca67

## 1. Asset-Level Views

From the repo root:

```bash
GOOGLE_CLOUD_PROJECT=your-project-id BIGQUERY_DATASET=portfolio \
python3 looker_studio/generate_bigquery_views.py
```

Then open `looker_studio/bigquery_views.sql` in BigQuery and run it.

The SQL creates four views:

| View | Purpose |
|---|---|
| `looker_asset_metrics` | One row per asset with CAGR, volatility, max drawdown, Sharpe, recovery period, and metadata |
| `looker_price_history` | Daily close, daily return, and cumulative return by ticker |
| `looker_annual_returns` | Annual return by ticker and year |
| `looker_category_summary` | Category-level average metrics |

## 2. Portfolio-Level Tables

After the asset views exist, generate portfolio tables:

```bash
GOOGLE_CLOUD_PROJECT=your-project-id BIGQUERY_DATASET=portfolio \
python3 looker_studio/export_portfolio_tables.py
```

To preview CSVs without uploading to BigQuery:

```bash
GOOGLE_CLOUD_PROJECT=your-project-id BIGQUERY_DATASET=portfolio \
python3 looker_studio/export_portfolio_tables.py --no-upload
```

This creates these BigQuery tables:

| Table | Purpose |
|---|---|
| `looker_portfolio_allocations` | Portfolio component weights and asset metadata |
| `looker_portfolio_metrics` | Portfolio CAGR, volatility, max drawdown, Sharpe, FIRE assumptions |
| `looker_portfolio_history` | Daily TWD portfolio value, invested amount, return, and drawdown |
| `looker_portfolio_annual_returns` | Annual return by portfolio |
| `looker_portfolio_drawdown_events` | Top drawdown episodes by portfolio |
| `looker_fire_scenarios` | FIRE target and years-to-FIRE by portfolio |
| `looker_fire_projection` | 50-year nominal and real FIRE projection by portfolio |

The script converts USD-denominated assets to TWD using historical TWD/USD rates
from the same Yahoo Finance helper used by the Streamlit dashboard.

## 3. Portfolio Presets

The report compares six portfolios:

| Portfolio | Type | Annual Expenses |
|---|---|---:|
| 年輕上班族 / Young Professional | Persona | NT$600,000 |
| 準退休族 / Pre-Retirement | Persona | NT$1,200,000 |
| 積極成長型 / Aggressive Growth | Persona | NT$800,000 |
| 台股核心 / Taiwan Core | Core | NT$800,000 |
| 美股核心 / US Core | Core | NT$800,000 |
| 加密貨幣核心 / Crypto Core | Core | NT$800,000 |

Core portfolio weights:

| Portfolio | Weights |
|---|---|
| 台股核心 / Taiwan Core | `0050.TW` 27.78%, `0056.TW` 22.22%, `00679B.TWO` 16.67%, `0052.TW` 16.67%, `00646.TW` 16.67% |
| 美股核心 / US Core | `VOO` 30%, `QQQ` 20%, `VEA` 15%, `VTV` 15%, `GLD` 10%, `BND` 10% |
| 加密貨幣核心 / Crypto Core | `BTC-USD` 45%, `ETH-USD` 25%, `BNB-USD` 10%, `XRP-USD` 8%, `SOL-USD` 8%, `TRX-USD` 4% |

## 4. Connect Looker Studio

1. Open [Looker Studio](https://lookerstudio.google.com/).
2. Create a new report.
3. Add a BigQuery data source.
4. Select the project and dataset from your `.env`.
5. Add these views and tables as data sources:
   - `looker_asset_metrics`
   - `looker_price_history`
   - `looker_annual_returns`
   - `looker_category_summary`
   - `looker_portfolio_allocations`
   - `looker_portfolio_metrics`
   - `looker_portfolio_history`
   - `looker_portfolio_annual_returns`
   - `looker_portfolio_drawdown_events`
   - `looker_fire_scenarios`
   - `looker_fire_projection`

Set field types:

| Field | Type |
|---|---|
| `date` | Date |
| `year` | Number |
| `portfolio_id`, `portfolio_name_zh`, `portfolio_name_en`, `ticker`, `name`, `category`, `subcategory`, `currency` | Text |
| `cagr`, `volatility`, `max_drawdown`, `sharpe_ratio`, `daily_return`, `cumulative_return`, `annual_return` | Number / Percent |

## 5. Recommended Dashboard Layout

### Page 1: 資產池與資產細節 / Asset Universe

- Scorecards: asset count, average CAGR, average volatility, average max drawdown, average Sharpe
- Bar chart: `cagr_pct` by `ticker`
- Scatter chart: `volatility_pct` vs `cagr_pct`, bubble dimension by `category`
- Table: ticker, name, category, CAGR, volatility, max drawdown, Sharpe, worst year
- Controls: category, subcategory, ticker

Primary data source: `looker_asset_metrics`

### Page 2: 投資組合比較與細節 / Portfolio Comparison

- Scorecards: CAGR, volatility, max drawdown, Sharpe, years to FIRE
- Time series: `portfolio_value_twd` by `date`, breakdown by `portfolio_name_zh`
- Bar chart: `annual_return_pct` by `year`, breakdown by `portfolio_name_zh`
- Pie or treemap: `weight_pct` by `ticker` filtered by selected portfolio
- Table: portfolio allocation detail
- Controls: portfolio name, portfolio type, risk level

Primary data sources: `looker_portfolio_metrics`, `looker_portfolio_history`,
`looker_portfolio_annual_returns`, `looker_portfolio_allocations`

### Page 3: 投資組合的風險與回撤 / Risk & Drawdown

- Bar chart: `max_drawdown_pct` by `portfolio_name_zh`
- Time series: `drawdown_pct` by `date`, breakdown by `portfolio_name_zh`
- Table: `looker_portfolio_drawdown_events`
- Scatter chart: `volatility_pct` vs `cagr_pct`, dimension by portfolio, color by risk level

Primary data sources: `looker_portfolio_metrics`,
`looker_portfolio_history`, `looker_portfolio_drawdown_events`

### Page 4: FIRE 試算 / FIRE Calculator

- Scorecards: FIRE target, years to FIRE nominal, years to FIRE real
- Time series: nominal and real portfolio projection by `year`
- Bar chart: `years_to_fire_real` by `portfolio_name_zh`
- Table: FIRE assumptions by portfolio

Primary data sources: `looker_fire_scenarios`, `looker_fire_projection`

### Optional: Historical Returns

- Time series: `cumulative_return_pct` by `date`, breakdown by `ticker`
- Time series: `daily_return_pct` by `date`, breakdown by `ticker`
- Bar chart: `annual_return_pct` by `year`, breakdown by `ticker`
- Controls: date range, ticker, category

Primary data sources: `looker_price_history`, `looker_annual_returns`

### Optional: Asset Risk And Drawdown

- Table sorted by `max_drawdown_pct`
- Scatter chart: `max_drawdown_pct` vs `sharpe_ratio`
- Bar chart: `worst_year_pct` by `ticker`
- Category summary table from `looker_category_summary`

Primary data sources: `looker_asset_metrics`, `looker_category_summary`

## 6. Suggested Looker Studio Calculated Fields

Risk label:

```text
CASE
  WHEN volatility < 0.12 THEN "Low"
  WHEN volatility < 0.20 THEN "Medium"
  WHEN volatility < 0.35 THEN "High"
  ELSE "Extreme High"
END
```

Drawdown severity:

```text
CASE
  WHEN max_drawdown > -0.20 THEN "Mild"
  WHEN max_drawdown > -0.40 THEN "Moderate"
  WHEN max_drawdown > -0.60 THEN "Severe"
  ELSE "Extreme"
END
```

Return/risk score:

```text
cagr / volatility
```

## Notes

- Asset-level views use native asset prices. Taiwan ETFs are TWD, while US ETFs
  and crypto are USD.
- Portfolio-level tables are calculated in TWD by `export_portfolio_tables.py`.
