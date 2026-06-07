# Data 說明

`data/` 是專案內用來放「跨交付面共用資料」的資料夾。目前主要用途是 Asset Profiles / Web Scraping Showcase，也就是透過網頁爬蟲資料管線與資料正規化流程整理 ETF 與加密貨幣補充資訊，供 GitHub Web、Streamlit Dashboard 與 landing page 共用。

目前狀態：**已完成第一版，已接入 GitHub Web、Streamlit Dashboard、landing page、測試與 GitHub Actions workflow。**

## 資料夾結構

```text
data/
└── asset_profiles/
    ├── asset_profiles.json
    └── raw/
        ├── etf/
        └── crypto/
```

| 位置 | 角色 | 必要性 |
|---|---|---|
| `asset_profiles/asset_profiles.json` | 正規化後的共用 profile 資料，GitHub Web 與 Streamlit 都讀這份資料 | 必要，已建立 |
| `asset_profiles/raw/etf/` | ETF 來源頁面或中間解析資料 | 選用，用於除錯與資料來源追蹤 |
| `asset_profiles/raw/crypto/` | Crypto 來源頁面或中間解析資料 | 選用，用於除錯與資料來源追蹤 |

`raw/` 內不得保存 API key、cookie、token、登入頁內容或個人資料。正式前端只讀 `asset_profiles.json`，不直接讀 `raw/`。

## 資料契約

ETF profile 欄位：

```json
{
  "ticker": "GLD",
  "name": "SPDR Gold Shares",
  "assetType": "US ETF",
  "summary": "Brief profile text.",
  "issuer": "State Street",
  "expenseRatio": "0.40%",
  "managementFee": "",
  "custodianFee": "",
  "expenseRatioFormula": "officialExpenseRatio",
  "expenseRatioSourceName": "SPDR official ETF profile",
  "expenseRatioSourceUrl": "https://...",
  "expenseRatioCollectionMethod": "web_scraping",
  "dividendPolicy": "Not primarily income-focused",
  "category": "Gold / Commodities",
  "collectionMethod": "web_scraping",
  "sourceName": "SPDR Gold Shares official profile",
  "sourceUrl": "https://...",
  "sourceSummary": "Text extracted from the public HTML page.",
  "fetchedAt": "2026-06-08"
}
```

Crypto profile 欄位：

```json
{
  "ticker": "BTC-USD",
  "name": "Bitcoin",
  "assetType": "Crypto",
  "summary": "Brief profile text.",
  "cryptoCategory": "Store of Value",
  "blockchain": "Bitcoin",
  "issuer": "None / decentralized",
  "consensus": "Proof of Work",
  "collectionMethod": "web_scraping",
  "sourceName": "Bitcoin official website",
  "sourceUrl": "https://...",
  "sourceSummary": "Text extracted from the public HTML page.",
  "fetchedAt": "2026-06-08"
}
```

Asset Profiles 使用的是公開 HTML 頁面爬蟲，不使用 Yahoo Finance REST API、
CoinMarketCap API 或其他行情 API。價格與回測資料線仍可能使用 Yahoo Finance，
但 profile 補充資訊資料線的來源規則如下：

- 台股 ETF：優先使用 TWSE ETFortune 公開 ETF 資訊頁。
- 美股 ETF：優先使用 Vanguard、iShares、SPDR、Invesco 等官方 ETF profile 頁。
- Crypto：優先使用 Bitcoin、Ethereum、BNB Chain、XRP Ledger、Solana、TRON DAO、
  Dogecoin、Cardano 等官方網站或官方公開資料頁。

費率來源可與 profile 摘要來源不同。當主要 profile 頁沒有揭露經理費 / 保管費時，
pipeline 會改抓 allowlist 內可直接解析費率欄位的官方或公開 ETF 費率頁，並寫入
`expenseRatioSourceName` / `expenseRatioSourceUrl`。

費用率欄位只適用於 ETF。29 檔 ETF 都必須輸出可顯示的 `expenseRatio`，
不得再使用 `See source profile`、`約` 或 `+` 這類不明確文字；8 檔 crypto
沒有 fund expense ratio 概念，因此資料契約不包含 `expenseRatio`，前端會改顯示
crypto 類別、區塊鏈、發行 / 治理與共識機制。

台股 ETF 的費用率定義為：

```text
expenseRatio = managementFee + custodianFee
```

若官方或公開頁揭露級距費率，則以最低與最高級距分別相加，呈現為
`0.25%~0.40%` 這類範圍。美股 ETF / 商品型 ETF 若來源頁直接揭露
official / gross expense ratio，則 `expenseRatioFormula` 會標示為
`officialExpenseRatio`。

## Asset Profiles Pipeline 狀態

1. `data/asset_profiles/asset_profiles.json` 已建立。
2. ETF 與 crypto 共用欄位、專屬欄位與 fallback 規則已固定。
3. ticker 已對齊 `streamlit_dashboard/src/processing/screening.py` 的 `ASSET_POOL`。
4. `github_web/scripts/asset_intelligence/sources.py` 已定義允許來源 allowlist。
5. ETF / crypto fetcher 已建立，包含 timeout、user-agent、allowlist 與 HTML parser。
6. `normalize_profiles.py` 會輸出正規化後的 JSON。
7. `export_asset_profiles.py` 會產出 `github_web/src/ppl-asset-profiles.js`。
8. GitHub Web 的「組合配置」資產詳情已讀取 `PPL_ASSET_PROFILES`。
9. Streamlit Dashboard 的「投資組合組成」treemap 詳情已讀取同一份 profile。
10. Landing page 已加入「資產補充資訊 / Web Scraping Showcase」功能亮點。
11. 已補上 `tests/export/test_asset_profiles_schema.py`、`tests/export/test_asset_profiles_export.py`、`tests/streamlit/test_asset_profiles_loader.py`。
12. GitHub Actions workflow 已加入 asset profile JSON / JS 產生與 artifact。
13. 已驗證 37 個 asset profile 皆為 `collectionMethod = "web_scraping"`。
14. 已驗證 29 檔 ETF 皆有可顯示費用率，且不使用 `約` / `+` / `See source profile`。
15. 已驗證台股 ETF 皆有 `managementFee`、`custodianFee` 與
    `expenseRatioFormula = "managementFee + custodianFee"`。
16. 已完成 Bandit、pytest、README、CHANGELOG、SECURITY_REVIEW 更新。

驗證結果：

- `python3 -m pytest tests/`：121 passed。
- `python3 -m bandit -r streamlit_dashboard github_web/scripts looker_studio -x '*/__pycache__/*'`：No issues identified。
- `python3 github_web/scripts/validate_export.py`：Export validation passed。

## 安全規則

- 只允許 `sources.py` 中列出的固定來源。
- 不接受使用者輸入任意 URL。
- 所有 `requests` 必須設定 timeout。
- 不儲存 cookie、token、API key 或登入頁內容。
- 爬到的文字輸出到前端前必須 sanitize。
- 前端只讀靜態資料，不在瀏覽器或 Streamlit 使用者操作時即時爬取。
