# Streamlit Dashboard 說明

`streamlit_dashboard/` 是 Passive Portfolio Lab 的互動式研究介面，也是目前 Streamlit Cloud 的正式部署入口。使用者可在這裡完成資產篩選、相關性檢查、風險配置、TWD-based 回測、FIRE 試算與 AI 投資組合摘要。

線上版本：

```text
https://passive-portfolio-lab-tw.streamlit.app/
```

## 目前交付狀態

| 項目 | 狀態 |
|---|---|
| Streamlit entry point | `streamlit_dashboard/app.py` |
| 資產池 | 37 個固定策展 ETF / crypto |
| BigQuery 資料讀取 | `raw_prices`、`asset_metrics` |
| 幣別基準 | Portfolio-level 統一以 TWD 計算 |
| Gemini AI insights | 選用，需設定 `GEMINI_API_KEY` |
| Password gate | 選用，需設定 `APP_PASSWORD` |
| Asset Profiles / Web Scraping Showcase | 已接入「投資組合組成」資產詳情 |

## 資料夾結構

```text
streamlit_dashboard/
├── README.md
├── app.py
├── requirements.txt
└── src/
    ├── asset_profiles/
    │   ├── __init__.py
    │   └── loader.py
    ├── data_collection/
    │   ├── __init__.py
    │   ├── fetch_macro.py
    │   └── fetch_prices.py
    └── processing/
        ├── __init__.py
        ├── backtest.py
        ├── drawdown_events.py
        ├── fire_calculator.py
        ├── metrics.py
        ├── screening.py
        └── utils.py
```

分類規則：

| 位置 | 放什麼 | 說明 |
|---|---|---|
| `app.py` | Streamlit UI 與使用者流程 | 串接資料讀取、互動控制、圖表、回測、FIRE 與 AI insights |
| `src/asset_profiles/` | 資產補充資訊讀取層 | 讀取共用 `data/asset_profiles/asset_profiles.json` |
| `src/data_collection/` | 外部資料抓取 | Yahoo Finance 價格資料與 FRED CPI 通膨資料 |
| `src/processing/` | 核心金融邏輯 | 資產池、指標計算、回測、FIRE、回撤事件、BigQuery helper |
| `requirements.txt` | Streamlit app 依賴 | Streamlit Cloud 與本機執行都使用這份依賴 |

## 執行方式

從 repo root 執行：

```bash
pip install -r streamlit_dashboard/requirements.txt
streamlit run streamlit_dashboard/app.py
```

Streamlit Cloud 的 app file path：

```text
streamlit_dashboard/app.py
```

## 資料存取

Dashboard 直接讀取 Google BigQuery：

| BigQuery table | 用途 |
|---|---|
| `raw_prices` | 每個 ticker 的歷史價格 |
| `asset_metrics` | CAGR、volatility、max drawdown、Sharpe、worst year 等資產指標 |

必要環境變數：

```env
GOOGLE_CLOUD_PROJECT=your-project-id
BIGQUERY_DATASET=passive_portfolio
GOOGLE_APPLICATION_CREDENTIALS=credentials.json
```

選用環境變數：

```env
FRED_API_KEY=your-fred-api-key
GEMINI_API_KEY=your-gemini-api-key
APP_PASSWORD=your-password
```

| 變數 | 用途 |
|---|---|
| `FRED_API_KEY` | 從 FRED 抓取 US CPI YoY；未設定時使用 2.5% 通膨假設 |
| `GEMINI_API_KEY` | 啟用 Gemini AI portfolio insights |
| `APP_PASSWORD` | 啟用 Streamlit password gate |

`.env`、`credentials.json`、`.streamlit/secrets.toml` 不應提交到 Git。

## 主要功能

| 功能 | 說明 |
|---|---|
| Asset Screening | 從 37 個固定策展資產中篩選 ETF / crypto |
| Persona Quick Start | 套用 Young Professional、Pre-Retirement、Aggressive Growth 三種預設角色 |
| Correlation Analysis | 檢查高相關資產組合，避免重複曝險 |
| Risk Allocation | 依 Low / Medium / High / Extreme High 風險層級配置權重 |
| TWD Backtest | 使用 initial investment + monthly contribution 模型回測 portfolio value |
| Drawdown Analysis | 顯示最大回撤、回撤曲線與主要歷史事件 |
| FIRE Calculator | 依年度支出、withdrawal rate、通膨與 CAGR 推估 FIRE timeline |
| Gemini AI Insights | 產生投資組合結構、回撤、FIRE 與行為風險摘要 |
| Asset Profiles / Web Scraping Showcase | 在「投資組合組成」點進單一資產時展示 ETF / crypto 補充資訊 |

## 模組角色

| 檔案 | 角色 | 必要性 |
|---|---|---|
| `app.py` | Streamlit 主程式與 UI flow | 必要 |
| `src/data_collection/fetch_prices.py` | Yahoo Finance v8 REST 歷史價格抓取，並寫入 BigQuery `raw_prices` | 必要 |
| `src/data_collection/fetch_macro.py` | FRED CPI YoY 抓取，供 FIRE 通膨假設使用 | 必要 |
| `src/asset_profiles/` | Streamlit asset profile loader package | 由 `data/README.md` 維護 pipeline 與資料契約 |
| `src/processing/screening.py` | 固定策展資產池、ticker metadata、ticker whitelist | 必要 |
| `src/processing/metrics.py` | 資產 CAGR、volatility、max drawdown、Sharpe、worst year 計算 | 必要 |
| `src/processing/backtest.py` | TWD-based combined backtest，引入 initial / monthly contribution 與 FX conversion | 必要 |
| `src/processing/drawdown_events.py` | 回撤 episode 偵測與歷史事件標籤 | 必要 |
| `src/processing/fire_calculator.py` | FIRE target、years-to-FIRE、nominal / real projection | 必要 |
| `src/processing/utils.py` | BigQuery identifier validation、upload helper、Yahoo request headers | 必要 |

## 資料與幣別規則

- 台股 ETF 以 TWD 計算。
- 美股 ETF 與 crypto 會透過歷史 TWD/USD 匯率轉換成 TWD。
- Portfolio-level backtest、FIRE 與金額輸入都以 TWD 為主。
- TWD/USD 匯率來自 Yahoo Finance `TWD=X`。
- FIRE 通膨率優先使用 FRED CPI YoY；未設定 API key 時使用 2.5% fallback。

## Asset Profiles Pipeline

Streamlit Dashboard 會展示網頁爬蟲資料管線整理後的資產補充資訊。使用者在「Portfolio Composition / 投資組合組成」treemap 點擊單一資產時，除了既有配比、CAGR、波動率、最大回撤與 Sharpe，也會看到：

- ETF：基本簡介、資產類型、發行商、費用率、配息政策 / 配息頻率、資料來源與更新時間。29 檔 ETF
  皆需顯示可讀費用率，不得退回 `See source profile`、`約` 或 `+` 這類不明確文字。
  台股 ETF 的經理費與保管費會以括號補充在同一個「費用率」欄位內，不額外拆成多個費用欄位。
- Crypto：基本簡介、加密貨幣類別、區塊鏈、發行商 / 去中心化狀態、共識機制、主要用途、資料來源與更新時間。

此資料線使用公開 HTML 頁面爬蟲，不使用 Yahoo Finance REST API、CoinMarketCap API
或其他行情 API。ETF 來源優先使用官方發行商 ETF profile 頁或 TWSE ETFortune
公開 ETF 資訊頁；crypto 來源優先使用官方網站或官方公開資料頁。

實作狀態：

1. 已建立共用 `data/asset_profiles/asset_profiles.json`。
2. 已建立 `streamlit_dashboard/src/asset_profiles/loader.py`。
3. 已在 `app.py` 的 treemap detail HTML 中加入「資產補充資訊」區塊。
4. Detail view 已調整為三欄一致透明框：績效數值、資產補充資訊、雷達圖；雷達圖在右欄置中。
5. 缺資料時會顯示 fallback，不影響原本數值資料。
6. 已補上 `tests/streamlit/test_asset_profiles_loader.py`。
7. 已驗證 29 檔 ETF 皆有可顯示費用率，8 檔 crypto 不套用 ETF 費用率欄位。
8. 已驗證台股 ETF 費用率由 `managementFee + custodianFee` 計算，前端以單一費用率欄位呈現。
9. 已完成 security scan，並更新 `CHANGELOG.md`、`SECURITY_REVIEW.md` 與本 README。

目前狀態：**已完成第一版。**

## 維護規則

- 新增資產時，要同步更新 `screening.py`、BigQuery price data、metrics、GitHub Web export、Looker Studio tables 與測試。
- 修改 backtest / FIRE / metrics 公式時，要同步更新 `tests/processing/`。
- 修改 BigQuery schema 時，要同步更新 `app.py`、`utils.py`、GitHub Web export、Looker Studio 與 README。
- 修改 asset profile schema 時，要同步更新共用 JSON、GitHub Web 匯出、Streamlit loader、tests、CHANGELOG 與 SECURITY_REVIEW。
- Gemini 與 password gate 都是選用功能，不能讓缺少 API key 影響核心 dashboard。
- `__pycache__/`、`.pyc`、`.DS_Store` 等本機產物不應提交到 Git。
