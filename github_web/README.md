# GitHub Web 說明

這個資料夾是 Passive Portfolio Lab 的 GitHub Pages 靜態網頁版。它提供免登入、免後端的前端展示介面，讓使用者可以瀏覽資產指標、套用 persona、做靜態資料下的 TWD-based portfolio 分析。

## 入口檔案

```text
github_web/index.html
```

Landing page 入口：

```text
github_web/landing.html
```

## 資料夾結構

```text
github_web/
├── index.html
├── landing.html
├── README.md
├── serve.py
├── scripts/
│   ├── asset_intelligence/
│   ├── backfill_missing_web_assets.py
│   ├── export_web_data.py
│   └── validate_export.py
└── src/
    ├── colors_and_type.css
    ├── ppl-data.js
    └── ppl-asset-profiles.js
```

分類規則：

| 位置 | 放什麼 | 說明 |
|---|---|---|
| `index.html` / `landing.html` | 使用者會直接開啟的頁面 | `index.html` 是主 app，`landing.html` 是展示頁 |
| `scripts/` | Python 資料維護腳本 | 負責 BigQuery 匯出、schema 驗證、缺漏資產補齊 |
| `scripts/asset_intelligence/` | 網頁爬蟲資料管線與 asset profile 匯出 | 負責 ETF / crypto 補充資訊 schema、allowlist、sanitize 與 JS export |
| `src/` | 前端靜態資源與資料 | CSS token 與 `ppl-data.js` |
| `serve.py` | 本機預覽工具 | 啟動簡單 HTTP server 供測試 |

## 資料來源

GitHub Web 不會在瀏覽器中直接查 BigQuery。資料流程是：

1. GitHub Actions 執行資料更新。
2. `github_web/scripts/export_web_data.py` 從 BigQuery 匯出資料。
3. 匯出結果寫入：

```text
github_web/src/ppl-data.js
```

前端只讀取這個靜態 JavaScript data file。

`github_web/src/ppl-data.js` 是 auto-generated data snapshot。若要更新內容，應執行 export script 或等待 GitHub Actions，不建議手動改資料區塊。

Asset profile 資料流程會額外產生：

```text
github_web/src/ppl-asset-profiles.js
```

這份檔案會由 `data/asset_profiles/asset_profiles.json` 匯出，供「投資組合組成」與「組合配置」資產詳情顯示 ETF / crypto 補充資訊。pipeline 請見 `data/README.md`。

## `ppl-data.js` 內容

| 變數 | 用途 |
|---|---|
| `PPL_ASSETS` | 資產指標、metadata、分類與顯示資訊 |
| `PPL_PRICE_HISTORY` | 每日 TWD 價格歷史，用於靜態歷史回測 |
| `PPL_FX_RATE` | 最新 TWD/USD 顯示用換算匯率 |
| `PPL_HISTORY_UPDATED_AT` | 資料匯出時間 |
| `PPL_ASSET_PROFILES` | ETF / crypto 補充資訊，由網頁爬蟲資料管線正規化後匯出 |

## Web Scraping Showcase Pipeline

GitHub Web 是 asset profiles 的主要展示面之一。使用者在「組合配置」點進單一資產時，除了目前的 CAGR、volatility、max drawdown、Sharpe 等數值，也會看到：

- ETF：基本簡介、發行商、費用率、配息政策 / 配息頻率、資料來源。29 檔 ETF
  皆需顯示可讀費用率，不得退回 `See source profile`、`約` 或 `+` 這類不明確文字。
  台股 ETF 的經理費與保管費會以括號補充在同一個「費用率」欄位內，不額外拆成多個費用欄位。
- Crypto：基本簡介、類別、區塊鏈、發行商 / 去中心化狀態、共識機制、資料來源。

Asset profile 資料線使用公開 HTML 頁面爬蟲，不使用 Yahoo Finance REST API、
CoinMarketCap API 或其他行情 API。ETF 來源優先使用官方發行商 ETF profile 頁
或 TWSE ETFortune 公開 ETF 資訊頁；crypto 來源優先使用官方網站或官方公開資料頁。

實作狀態：

1. 已建立共用 `data/asset_profiles/asset_profiles.json`。
2. 已建立 `scripts/asset_intelligence/`，包含來源 allowlist、schema、sanitize、HTML fetcher、normalize 與 export。
3. 已匯出 `src/ppl-asset-profiles.js`。
4. 已在 `index.html` asset detail UI 顯示 profile。
5. 已在 `landing.html` 功能亮點加入「資產補充資訊 / Web Scraping Showcase」。
6. 已補上 `tests/export/test_asset_profiles_schema.py` 與 `tests/export/test_asset_profiles_export.py`。
7. 已驗證 37 個 asset profile 皆為 `collectionMethod = "web_scraping"`。
8. 已驗證 29 檔 ETF 皆有可顯示費用率，8 檔 crypto 不套用 ETF 費用率欄位。
9. 已驗證台股 ETF 費用率由 `managementFee + custodianFee` 計算，前端以單一費用率欄位呈現。
10. 已完成 security scan，並更新 `CHANGELOG.md` 與 `SECURITY_REVIEW.md`。

目前狀態：**已完成第一版，GitHub Actions 會產生並驗證 asset profile 靜態資料。**

## 部署流程

GitHub Actions workflow 位於：

```text
.github/workflows/update-and-deploy.yml
```

主要流程：

1. 使用 `GCP_SA_KEY` GitHub Secret 驗證 Google Cloud。
2. 從 BigQuery 匯出最新 web data。
3. 若 `github_web/src/ppl-data.js` 有變更，自動 commit。
4. 部署 `github_web/` 到 GitHub Pages。

`.github/workflows/` 必須留在 repo root，不能移進 `github_web/`，否則 GitHub Actions 不會執行。

## 本機預覽

從 repo root 執行：

```bash
python github_web/serve.py
```

然後開啟：

```text
http://localhost:3131/
```

本機預覽只讀取目前 repo 裡的 `github_web/src/ppl-data.js`，不會連 BigQuery。

## 補齊缺漏資產

若 asset universe 新增 ticker，但 BigQuery 尚未有資料，可從 repo root 執行：

```bash
python github_web/scripts/backfill_missing_web_assets.py 00646.TW 00955.TWO
python github_web/scripts/export_web_data.py
```

## 計算限制

- GitHub Web 是靜態版本，不直接呼叫 BigQuery。
- 資料新鮮度取決於最近一次 GitHub Actions export。
- 所有輸入與計算仍以 TWD 為主。
- TWD / USD toggle 只影響顯示，不改變底層計算。

## 維護注意事項

- 若修改 `ppl-data.js` schema，需同步更新 `scripts/export_web_data.py`、`scripts/validate_export.py` 與 `tests/export/test_export_web_data.py`。
- 若新增或修改 asset profile schema，需同步更新 `data/README.md`、`scripts/asset_intelligence/`、`src/ppl-asset-profiles.js`、GitHub Web UI、Streamlit loader 與測試。
- 若新增資產，需先確認 BigQuery 有價格資料，再執行 backfill / export。
- `.DS_Store`、`__pycache__/`、`.pyc` 等本機產物不應提交到 Git。
- `serve.py` 與 GitHub Pages 部署無關，只是本機測試工具。
