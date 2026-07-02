# Looker Studio 說明

最後更新：2026-07-02

`looker_studio/` 是 Passive Portfolio Lab 的 BI 報表資料層。它把 Streamlit / BigQuery 已有的價格與資產指標整理成 Looker Studio 可直接連接的 views、portfolio tables 與 CSV snapshots。

已發布報表：

```text
https://datastudio.google.com/reporting/c2e7b15c-bf18-460f-8daf-dc480bcbca67
```

## 目前交付狀態

| 項目 | 狀態 |
|---|---|
| Asset-level BigQuery views | 已建立產生腳本與 SQL |
| Portfolio-level BigQuery tables | 已建立產生腳本 |
| CSV snapshots | 已產出於 `looker_studio/generated/` |
| 預設 portfolios | 已內建 6 組 |
| 報表幣別 | Portfolio-level 統一為 TWD |

## 資料夾結構

```text
looker_studio/
├── README.md
├── bigquery_views.sql
├── generate_bigquery_views.py
├── export_portfolio_tables.py
└── generated/
    ├── looker_fire_projection.csv
    ├── looker_fire_scenarios.csv
    ├── looker_portfolio_allocations.csv
    ├── looker_portfolio_annual_returns.csv
    ├── looker_portfolio_drawdown_events.csv
    ├── looker_portfolio_history.csv
    └── looker_portfolio_metrics.csv
```

| 路徑 | 角色 | 必要性 |
|---|---|---|
| `generate_bigquery_views.py` | 產生 asset-level semantic views SQL | 必要 |
| `bigquery_views.sql` | 已產出的 BigQuery SQL，可直接到 BigQuery 執行 | 保留 |
| `export_portfolio_tables.py` | 產生 portfolio-level tables 與 CSV snapshots | 必要 |
| `generated/` | 已產出的 CSV snapshots，方便檢查資料長相與交付展示 | 保留 |

## Asset-level views

`generate_bigquery_views.py` 會根據 `streamlit_dashboard/src/processing/screening.py` 的固定資產池，產出 BigQuery semantic layer SQL。

重建指令：

```bash
GOOGLE_CLOUD_PROJECT=your-project-id BIGQUERY_DATASET=portfolio \
python3 looker_studio/generate_bigquery_views.py
```

輸出檔案：

```text
looker_studio/bigquery_views.sql
```

`bigquery_views.sql` 會建立四個 views：

| View | 用途 |
|---|---|
| `looker_asset_metrics` | 每個 asset 一列，包含 CAGR、volatility、max drawdown、Sharpe、recovery period 與 metadata |
| `looker_price_history` | 每個 ticker 的 daily close、daily return、cumulative return |
| `looker_annual_returns` | 每個 ticker / year 的年度報酬 |
| `looker_category_summary` | 各 category 的平均指標 |

## Portfolio-level tables

`export_portfolio_tables.py` 會讀取 BigQuery 的 `raw_prices` 與 `asset_metrics`，再依照內建 portfolio presets 產出 portfolio-level 資料表。

上傳 BigQuery：

```bash
GOOGLE_CLOUD_PROJECT=your-project-id BIGQUERY_DATASET=portfolio \
python3 looker_studio/export_portfolio_tables.py
```

只產出 CSV、不上傳 BigQuery：

```bash
GOOGLE_CLOUD_PROJECT=your-project-id BIGQUERY_DATASET=portfolio \
python3 looker_studio/export_portfolio_tables.py --no-upload
```

目前產出的 tables / CSV：

| Table / CSV | 用途 |
|---|---|
| `looker_portfolio_allocations` | 投資組合成分權重與 asset metadata |
| `looker_portfolio_metrics` | Portfolio CAGR、volatility、max drawdown、Sharpe、FIRE assumptions |
| `looker_portfolio_history` | Daily TWD portfolio value、invested amount、return、drawdown |
| `looker_portfolio_annual_returns` | 每個 portfolio 的年度報酬 |
| `looker_portfolio_drawdown_events` | 每個 portfolio 的主要回撤事件 |
| `looker_fire_scenarios` | FIRE target 與 years-to-FIRE |
| `looker_fire_projection` | 50 年 nominal / real FIRE projection |

USD-denominated assets 會使用與 Streamlit dashboard 相同的 TWD/USD 歷史匯率 helper 轉換成 TWD。

## 內建 portfolios

目前 Looker Studio 報表使用 6 組 portfolio：

| Portfolio | Type | Annual Expenses |
|---|---|---:|
| 年輕上班族 / Young Professional | Persona | NT$600,000 |
| 準退休族 / Pre-Retirement | Persona | NT$1,200,000 |
| 積極成長型 / Aggressive Growth | Persona | NT$800,000 |
| 台股核心 / Taiwan Core | Core | NT$800,000 |
| 美股核心 / US Core | Core | NT$800,000 |
| 加密貨幣核心 / Crypto Core | Core | NT$800,000 |

Core portfolio weights：

| Portfolio | Weights |
|---|---|
| 台股核心 / Taiwan Core | `0050.TW` 27.78%、`0056.TW` 22.22%、`00679B.TWO` 16.67%、`0052.TW` 16.67%、`00646.TW` 16.67% |
| 美股核心 / US Core | `VOO` 30%、`QQQ` 20%、`VEA` 15%、`VTV` 15%、`GLD` 10%、`BND` 10% |
| 加密貨幣核心 / Crypto Core | `BTC-USD` 45%、`ETH-USD` 25%、`BNB-USD` 10%、`XRP-USD` 8%、`SOL-USD` 8%、`TRX-USD` 4% |

這些 presets 的 source of truth 在：

```text
looker_studio/export_portfolio_tables.py
```

## Looker Studio 目前資料來源

報表連接下列 BigQuery views / tables：

```text
looker_asset_metrics
looker_price_history
looker_annual_returns
looker_category_summary
looker_portfolio_allocations
looker_portfolio_metrics
looker_portfolio_history
looker_portfolio_annual_returns
looker_portfolio_drawdown_events
looker_fire_scenarios
looker_fire_projection
```

欄位型態：

| Field | Type |
|---|---|
| `date` | Date |
| `year` | Number |
| `portfolio_id`、`portfolio_name_zh`、`portfolio_name_en`、`ticker`、`name`、`category`、`subcategory`、`currency` | Text |
| `cagr`、`volatility`、`max_drawdown`、`sharpe_ratio`、`daily_return`、`cumulative_return`、`annual_return` | Number / Percent |

## 報表頁面

目前 Looker Studio 交付面涵蓋：

| 頁面 | 內容 |
|---|---|
| 資產池與資產細節 / Asset Universe | 資產數量、CAGR、volatility、max drawdown、Sharpe、ticker table 與 category filter |
| 投資組合比較與細節 / Portfolio Comparison | Portfolio value、annual return、allocation、CAGR、volatility、Sharpe、years to FIRE |
| 投資組合的風險與回撤 / Risk & Drawdown | Max drawdown、drawdown time series、drawdown events、risk scatter |
| FIRE 試算 / FIRE Calculator | FIRE target、nominal / real years to FIRE、50 年 projection |
| Historical Returns | Ticker-level cumulative return、daily return、annual return |
| Asset Risk And Drawdown | Asset-level max drawdown、Sharpe、worst year 與 category summary |

## Calculated fields

目前報表使用下列 calculated fields。

Risk label：

```text
CASE
  WHEN volatility < 0.12 THEN "Low"
  WHEN volatility < 0.20 THEN "Medium"
  WHEN volatility < 0.35 THEN "High"
  ELSE "Extreme High"
END
```

Drawdown severity：

```text
CASE
  WHEN max_drawdown > -0.20 THEN "Mild"
  WHEN max_drawdown > -0.40 THEN "Moderate"
  WHEN max_drawdown > -0.60 THEN "Severe"
  ELSE "Extreme"
END
```

Return/risk score：

```text
cagr / volatility
```

## 維護規則

- Asset-level views 使用原始資產幣別：台灣 ETF 為 TWD，美股 ETF 與 crypto 為 USD。
- Portfolio-level tables 統一由 `export_portfolio_tables.py` 轉成 TWD。
- 若修改 asset universe，需重新產生 `bigquery_views.sql` 與 portfolio tables。
- 若修改 portfolio presets，需更新 `export_portfolio_tables.py`、CSV snapshots、Looker Studio data source 與 `CHANGELOG.md`。
- 若修改 FIRE / backtest 公式，需同步更新 Streamlit、tests、Looker tables 與本 README。
- `generated/` 是可重建的輸出物，但目前保留作為結案展示與資料契約檢查 snapshot。
