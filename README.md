# Passive Portfolio Lab

最後更新：2026-07-02

Passive Portfolio Lab 是一個以台灣投資人視角設計的長期被動投資分析專案。它把 ETF、加密貨幣、匯率、通膨、回測、FIRE 試算與 BI 報表整合在同一套資料流程中，核心問題是：

> 如果一個投資組合的歷史報酬看起來不錯，那背後承擔了多少風險、回撤痛苦，以及 FIRE 目標上的取捨？

本專案目前有三個主要交付面：

| 交付面 | 用途 | 狀態 |
|---|---|---|
| Streamlit Dashboard | 互動式研究儀表板，支援資產篩選、組合回測、FIRE 試算與 Gemini AI insights | 已完成主要功能 |
| GitHub Web | 靜態網頁版，透過 GitHub Pages 展示 BigQuery 匯出的資產指標與 TWD 歷史價格 | 已完成主要功能 |
| Looker Studio | BI 報表層，使用 BigQuery views / tables 建立資產與投資組合分析頁 | 已完成主要功能 |
| Asset Profiles / Web Scraping Showcase | 以網頁爬蟲資料管線與正規化 schema 整理 ETF / crypto 補充資訊，供 GitHub Web、Streamlit 與 landing page 展示 | 已完成第一版 |

三個交付面皆以 TWD 為主要分析基準，並支援英文與繁體中文介面或標籤。

## 線上成品

| 平台 | 連結 |
|---|---|
| Streamlit Dashboard | https://passive-portfolio-lab-tw.streamlit.app/ |
| GitHub Web | https://amandatseng0320.github.io/passive-portfolio-lab/ |
| Landing Page | https://amandatseng0320.github.io/passive-portfolio-lab/landing.html |
| Looker Studio | https://datastudio.google.com/reporting/c2e7b15c-bf18-460f-8daf-dc480bcbca67 |

## 功能摘要

### 1. 雙語投資分析介面

Streamlit 與 GitHub Web 皆支援英文 / 繁體中文切換。切換範圍包含導覽、區塊標題、控制項、提醒訊息、圖表標籤與 AI 摘要語言。

### 2. 靜態策展資產池

專案使用固定策展的 37 個資產，避免在使用者操作時即時爬取或任意加入未驗證標的：

- 14 檔台灣 ETF，包含 AUM 排名前段標的與專案額外加入的 `00646.TW`、`00955.TWO`
- 15 檔美國 ETF
- 8 個主要加密貨幣，排除 stablecoin 與歷史資料不足的資產

完整資產清單如下，canonical source 為 `streamlit_dashboard/src/processing/screening.py` 的 `ASSET_POOL`：

| 類別 | Ticker | 名稱 | 子類別 | AUM / 市值註記 |
|---|---|---|---|---|
| 台灣 ETF | `0050.TW` | Yuanta Taiwan 50 ETF | Market-Cap | approx. TWD 1,661.5B |
| 台灣 ETF | `0056.TW` | Yuanta High Dividend ETF | High Dividend | approx. TWD 584.1B |
| 台灣 ETF | `00878.TW` | Cathay Sustainable High Dividend ETF | High Dividend / ESG | approx. TWD 485.4B |
| 台灣 ETF | `00919.TW` | Group Benefits Taiwan Select High Yield ETF | High Dividend | approx. TWD 451.8B |
| 台灣 ETF | `006208.TW` | Fubon Taiwan 50 ETF | Market-Cap | approx. TWD 389.4B |
| 台灣 ETF | `00937B.TWO` | Group Benefits ESG IG Bond 20+ ETF | Bond | approx. TWD 267.9B |
| 台灣 ETF | `00679B.TWO` | Yuanta US Treasury 20+ Year ETF | Bond | approx. TWD 203.7B |
| 台灣 ETF | `00751B.TWO` | Yuanta AAA-A Corporate Bond ETF | Bond | approx. TWD 180.0B |
| 台灣 ETF | `0052.TW` | Fubon Technology ETF | Technology Theme | approx. TWD 132.0B |
| 台灣 ETF | `00929.TW` | Fuh Hwa Taiwan Tech High Yield ETF | Tech High Dividend | approx. TWD 115.2B |
| 台灣 ETF | `00713.TW` | Yuanta Taiwan High Dividend Low Volatility ETF | High Dividend Low Vol | approx. TWD 113.0B |
| 台灣 ETF | `00952.TW` | KGI Taiwan AI 50 ETF | AI Theme | approx. TWD 60.0B |
| 台灣 ETF | `00646.TW` | Yuanta S&P 500 ETF | S&P 500 Exposure | approx. TWD 25.0B |
| 台灣 ETF | `00955.TWO` | CTBC Japan Sogo Shosha ETF | Japan Sogo Shosha | approx. TWD 5.0B |
| 美國 ETF | `VOO` | Vanguard S&P 500 ETF | US Large-Cap Blend | approx. USD 827.0B |
| 美國 ETF | `IVV` | iShares Core S&P 500 ETF | US Large-Cap Blend | approx. USD 766.0B |
| 美國 ETF | `SPY` | SPDR S&P 500 ETF Trust | US Large-Cap Blend | approx. USD 672.0B |
| 美國 ETF | `VTI` | Vanguard Total Stock Market ETF | US Total Market | approx. USD 586.0B |
| 美國 ETF | `QQQ` | Invesco QQQ Trust | US Technology Growth | approx. USD 400.0B |
| 美國 ETF | `VUG` | Vanguard Growth ETF | US Growth | approx. USD 207.4B |
| 美國 ETF | `VEA` | Vanguard FTSE Developed Markets ETF | Developed International | approx. USD 219.9B |
| 美國 ETF | `IEFA` | iShares Core MSCI EAFE ETF | Developed International | approx. USD 180.9B |
| 美國 ETF | `VTV` | Vanguard Value ETF | US Value | approx. USD 169.3B |
| 美國 ETF | `GLD` | SPDR Gold Shares | Gold / Commodities | approx. USD 163.4B |
| 美國 ETF | `BND` | Vanguard Total Bond Market ETF | US Total Bond | approx. USD 152.6B |
| 美國 ETF | `IEMG` | iShares Core MSCI Emerging Markets ETF | Emerging Markets | approx. USD 148.9B |
| 美國 ETF | `VXUS` | Vanguard Total International Stock ETF | Global ex-US | approx. USD 144.0B |
| 美國 ETF | `AGG` | iShares Core U.S. Aggregate Bond ETF | US Total Bond | approx. USD 135.9B |
| 美國 ETF | `IEF` | iShares 7-10 Year Treasury Bond ETF | Intermediate US Treasury | approx. USD 45.0B |
| Crypto | `BTC-USD` | Bitcoin | Store of Value | approx. USD 1,300.0B |
| Crypto | `ETH-USD` | Ethereum | Smart Contract Platform | approx. USD 280.0B |
| Crypto | `BNB-USD` | BNB | Exchange Platform Token | approx. USD 85.0B |
| Crypto | `XRP-USD` | XRP | Cross-Border Payments | approx. USD 65.0B |
| Crypto | `SOL-USD` | Solana | High-Performance L1 | approx. USD 65.0B |
| Crypto | `TRX-USD` | TRON | Stablecoin Settlement Chain | approx. USD 25.0B |
| Crypto | `DOGE-USD` | Dogecoin | Meme Coin | approx. USD 25.0B |
| Crypto | `ADA-USD` | Cardano | Academic L1 | approx. USD 20.0B |

資產挑選考量包含流動性、費用率、類別覆蓋、歷史資料完整度與至少約 3 年可用價格資料。

### 3. 相關性分析與組合確認

Correlation 模組使用近 3 年日報酬計算 pairwise correlation。手動選擇投資組合時，系統會標示高度相關資產群組，並依 AUM / liquidity 建議保留標的。使用者確認組合後，才會進入後續 risk allocation、backtest 與 FIRE 試算。

Persona portfolio 則會顯示相關性診斷，但不強制進行手動刪除流程。

### 4. 風險分級與資產配置

系統會依照選定資產的年化波動度估計可達成的風險區間，並依目標風險等級配置權重：

| 風險等級 | 目標年化波動 |
|---|---:|
| Low | 12% |
| Medium | 20% |
| High | 35% |
| Extreme High | 65% |

分析結果包含 weighted CAGR、volatility、max drawdown、Sharpe ratio、treemap 與資產細節視覺化。

### 5. TWD-based 投資組合回測

回測引擎以台幣為主體，並模擬「初始投入 + 每月投入」的真實投資情境：

- 第一個可用交易日投入 initial lump-sum
- 後續每月第一個交易日投入 monthly contribution
- 台股 ETF 以 TWD 計算
- 美股 ETF 與 crypto 透過歷史 TWD/USD 匯率轉換為 TWD

回測結果包含 final value、total invested、total return、資金加權年化報酬（MWRR）、portfolio value、max drawdown、前 5 大獨立回撤事件與扣除投入影響後的年度報酬。

### 6. FIRE 試算

FIRE Calculator 依回測 MWRR 或投資組合 weighted CAGR、年度支出與 withdrawal rate 估算財務自由時間：

```text
FIRE Target = Annual Expenses / Withdrawal Rate
```

系統同時提供 nominal 與 inflation-adjusted timeline。若設定 `FRED_API_KEY`，通膨率會使用 FRED 最新 US CPI YoY；若未設定，預設使用 2.5%。

### 7. Gemini AI Insights

Streamlit 版本可選擇設定 `GEMINI_API_KEY`。設定後，系統會使用 Gemini 2.5 Flash 產生投資組合摘要，內容涵蓋配置結構、回撤脈絡、FIRE timeline 與行為風險。未設定 API key 時，系統會保留規則式 fallback，不影響核心分析功能。

### 8. Persona Quick Start

Streamlit 版本提供三種預設投資者 persona，讓使用者快速帶入 watchlist、risk level、backtest 參數與 FIRE 假設：

| Persona | 用途 |
|---|---|
| Young Professional | 中等風險、長期累積 |
| Pre-Retirement | 低風險、退休前衝刺 |
| Aggressive Growth | 高風險、成長型組合 |

### 9. Asset Profiles / Web Scraping Showcase

專案已建立 asset profiles 資料層，透過網頁爬蟲資料管線與資料正規化流程整理 ETF 與加密貨幣的補充資訊，例如基本簡介、發行商、費用率、配息政策、加密貨幣類別、區塊鏈與資料來源。費用率只適用於 ETF；目前 29 檔 ETF 皆已輸出可顯示費用率，8 檔 crypto 則改顯示鏈別、發行 / 治理與共識機制。

台股 ETF 的費用率定義為 `經理費 + 保管費`；前端只顯示一個「費用率」欄位，並在括號內標注其包含的經理費與保管費。美股 ETF 若官方頁直接揭露 official / gross expense ratio，則直接採用官方費用率。

這條資料線使用公開 HTML 頁面爬蟲，不使用 Yahoo Finance REST API、
CoinMarketCap API 或其他行情 API。ETF 來源優先使用官方發行商 ETF profile
頁或 TWSE ETFortune 公開 ETF 資訊頁；crypto 來源優先使用官方網站或官方公開資料頁。

這條資料線目前支援：

- GitHub Web 的「投資組合組成」與「組合配置」資產詳情。
- Streamlit Dashboard 的「投資組合組成」treemap 資產詳情。
- Landing page 的功能亮點展示。

完整 pipeline 與驗證結果請見 [Data 說明](data/README.md)。

## 技術架構

| 層級 | 工具 |
|---|---|
| Dashboard | Streamlit 1.35+、Streamlit-AgGrid |
| 視覺化 | Plotly 5.18+、Chart.js 4.4 |
| 資料處理 | pandas 2.0+、NumPy 1.26+ |
| 資料來源 | Yahoo Finance v8 REST API、FRED API |
| 資料倉儲 | Google BigQuery |
| AI | Google Gemini 2.5 Flash |
| 靜態網頁 | HTML / CSS / JavaScript、React 18 CDN |
| CI/CD | GitHub Actions、GitHub Pages |
| 測試 | pytest、pytest-mock |
| 資安掃描 | Bandit、pip-audit |

## 專案結構

```text
passive-portfolio-lab/
├── data/
│   ├── README.md
│   └── asset_profiles/
│       └── raw/
├── streamlit_dashboard/
│   ├── app.py
│   ├── requirements.txt
│   └── src/
│       ├── asset_profiles/
│       ├── data_collection/
│       │   ├── fetch_prices.py
│       │   └── fetch_macro.py
│       └── processing/
│           ├── screening.py
│           ├── utils.py
│           ├── metrics.py
│           ├── backtest.py
│           ├── drawdown_events.py
│           └── fire_calculator.py
├── github_web/
│   ├── index.html
│   ├── landing.html
│   ├── scripts/
│   │   ├── asset_intelligence/
│   │   ├── export_web_data.py
│   │   ├── validate_export.py
│   │   └── backfill_missing_web_assets.py
│   └── src/
│       ├── colors_and_type.css
│       └── ppl-data.js
├── looker_studio/
│   ├── export_portfolio_tables.py
│   ├── generate_bigquery_views.py
│   └── generated/
├── tests/
│   ├── processing/
│   ├── export/
│   └── streamlit/
├── .github/workflows/
│   └── update-and-deploy.yml
├── CHANGELOG.md
├── SECURITY_REVIEW.md
├── requirements.txt
└── README.md
```

子系統設定請看：

- [Streamlit Dashboard 說明](streamlit_dashboard/README.md)
- [GitHub Web 說明](github_web/README.md)
- [Looker Studio 說明](looker_studio/README.md)
- [Data 說明](data/README.md)
- [版本修訂紀錄](CHANGELOG.md)
- [資安與弱點掃描報告](SECURITY_REVIEW.md)

## 快速開始

### 1. 安裝依賴

建議從 repo root 執行：

```bash
pip install -r streamlit_dashboard/requirements.txt
pip install -r tests/requirements_test.txt
```

根目錄的 `requirements.txt` 是給 Streamlit Cloud 使用的 shim，實際 dashboard 依賴以 `streamlit_dashboard/requirements.txt` 為主。

### 2. 設定環境變數

可參考 `.env.example` 建立本機 `.env`：

```env
GOOGLE_CLOUD_PROJECT=your-project-id
BIGQUERY_DATASET=portfolio
GOOGLE_APPLICATION_CREDENTIALS=credentials.json
FRED_API_KEY=your-fred-api-key
GEMINI_API_KEY=your-gemini-api-key
APP_PASSWORD=your-password
```

必要設定：

| 變數 | 用途 |
|---|---|
| `GOOGLE_CLOUD_PROJECT` | BigQuery project id |
| `BIGQUERY_DATASET` | BigQuery dataset id |
| `GOOGLE_APPLICATION_CREDENTIALS` | 本機 service account credentials 路徑 |

選用設定：

| 變數 | 用途 |
|---|---|
| `FRED_API_KEY` | 抓取 US CPI YoY；未設定時使用 2.5% 通膨假設 |
| `GEMINI_API_KEY` | 啟用 Streamlit AI insights |
| `APP_PASSWORD` | 啟用 Streamlit password gate |

請勿將 `.env`、`credentials.json`、`.streamlit/secrets.toml` 或任何 key/token 檔案提交到 Git。

### 3. 執行 Streamlit

```bash
streamlit run streamlit_dashboard/app.py
```

Streamlit Cloud 正式部署入口請使用：

```text
streamlit_dashboard/app.py
```

## 測試與品質檢查

### 單元測試

```bash
pytest tests/
```

目前測試重點包含：

| 模組 | 覆蓋重點 |
|---|---|
| `test_metrics.py` | CAGR、volatility、max drawdown、Sharpe、worst year |
| `test_backtest.py` | TWD backtest engine、ticker whitelist、monthly contribution |
| `test_fire_calculator.py` | years-to-FIRE、weighted CAGR、inflation adjustment、50-year cap |
| `test_drawdown_events.py` | 回撤事件偵測、歷史事件標籤、recovery period |
| `test_export_web_data.py` | `ppl-data.js` schema、TWD conversion、export idempotency |
| `test_asset_profiles_*` | asset profiles schema、export 與 Streamlit loader |

### 資安掃描

```bash
python3 -m bandit -r streamlit_dashboard github_web/scripts looker_studio -x '*/__pycache__/*'
python3 -m pip_audit -r streamlit_dashboard/requirements.txt
python3 -m pip_audit -r tests/requirements_test.txt
```

目前 `SECURITY_REVIEW.md` 已記錄原始掃描結果與修正後重掃結果。修正後狀態為：

- Bandit High / Medium / Low findings：0
- Python dependency known vulnerabilities：0
- 測試依賴 known vulnerabilities：0
- 核心測試：136 passed

## 資料流程

GitHub Actions 每日執行資料更新與 GitHub Pages 部署。主要流程如下：

1. `fetch_prices.py` 從 Yahoo Finance v8 REST API 抓取 37 個資產收盤價
2. `fetch_macro.py` 從 FRED 抓取 US CPI YoY
3. `metrics.py` 計算 CAGR、volatility、max drawdown、Sharpe ratio、worst year
4. `export_web_data.py` 將 BigQuery 資料匯出成 `github_web/src/ppl-data.js`
5. `validate_export.py` 驗證 web data schema 與數值範圍
6. GitHub Actions commit 更新後的 `ppl-data.js`
7. GitHub Pages 部署 `github_web/`

Asset Profiles / Web Scraping Showcase 的流程另列於 [data/README.md](data/README.md)。此資料線已進入 GitHub Actions 靜態資料更新流程，會產出共用 `asset_profiles.json` 與 GitHub Web 靜態 `ppl-asset-profiles.js`。

資料使用方式：

| 交付面 | 資料來源 |
|---|---|
| Streamlit Dashboard | 直接讀取 BigQuery |
| GitHub Web | 使用每日匯出的 `ppl-data.js` 靜態資料 |
| Looker Studio | 使用 BigQuery semantic views / portfolio tables |
| Asset Profiles | 爬蟲資料管線整理後的 `data/asset_profiles/asset_profiles.json`，供 GitHub Web 與 Streamlit 共用 |

## BigQuery 與資料契約

本專案主要依賴下列 BigQuery 資料表或 views：

| 類型 | 名稱 |
|---|---|
| 原始價格 | `raw_prices` |
| 資產指標 | `asset_metrics` |
| Looker asset views | `looker_asset_metrics`、`looker_price_history`、`looker_annual_returns`、`looker_category_summary` |
| Looker portfolio tables | `looker_portfolio_allocations`、`looker_portfolio_metrics`、`looker_portfolio_history`、`looker_portfolio_annual_returns`、`looker_portfolio_drawdown_events`、`looker_fire_scenarios`、`looker_fire_projection` |
| Web 靜態資料 | `PPL_ASSETS`、`PPL_PRICE_HISTORY`、`PPL_FX_RATE`、`PPL_HISTORY_UPDATED_AT` |
| Asset Profiles | `asset_profiles.json`、`PPL_ASSET_PROFILES` |

若後續修改欄位名稱、ticker schema、portfolio metrics 或 FIRE / backtest 公式，需同步更新：

- Streamlit UI 與資料讀取邏輯
- GitHub Web 的 `ppl-data.js` export 與 validation
- Looker Studio views / tables
- 測試案例
- `CHANGELOG.md`
- `SECURITY_REVIEW.md` 或相關交付文件

## 交付範圍與限制

| 交付面 | 支援項目 | 主要限制 |
|---|---|---|
| Streamlit Dashboard | 完整互動分析、BigQuery 即時讀取、AI insights、persona quick start、FIRE 試算 | 需要 BigQuery credentials；Gemini 與 FRED 為選用功能 |
| GitHub Web | 靜態展示、資產指標、TWD 歷史價格、前端互動分析 | 不在瀏覽器直接連 BigQuery；資料取決於每日 export |
| Looker Studio | BI 報表、資產層與投資組合層比較、分享式 dashboard | 報表互動受 Looker Studio 控制；需先建立 BigQuery views / tables |

## 方法論與風險提醒

- 歷史績效不代表未來報酬。
- 所有投資組合回測皆以 TWD 計算，目的是貼近台灣投資人的實際資產波動。
- 美股 ETF 與 crypto 會用歷史 TWD/USD 匯率轉換。
- 回測年化報酬採 MWRR，會納入每月投入的時間點；年度報酬圖則扣除投入影響後再計算。
- Correlation analysis 是分散度輔助工具，不是完整 covariance optimization。
- Risk allocation 使用年化波動度作為主要風險 proxy。
- Crypto 資產歷史資料較短且尾端風險高，指標解讀需更保守。
- FIRE 的 4% withdrawal rule 是基準假設，保守使用者可改用 3.0% 到 3.5%。
- 本專案內容僅供學習與研究，不構成投資建議。

## 維護重點

後續維護請優先注意：

- 金融公式、FIRE 與 backtest 邏輯異動時，先補測試再改 UI。
- BigQuery schema、Looker tables 與 web data schema 需維持資料契約一致。
- 若新增資產，需同步更新 asset universe、ticker whitelist、BigQuery 資料、web export、Looker table 與測試。
- 若新增外部 API 或部署 secret，需同步更新 `.env.example`、README 與資安掃描報告。
- 每次重大功能或資安修正都應寫入 `CHANGELOG.md`。
