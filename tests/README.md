# Tests 說明

最後更新：2026-07-02

`tests/` 是 Passive Portfolio Lab 的自動化測試資料夾。這裡的測試保護四個高風險區塊：金融計算、TWD-based 回測 / FIRE 邏輯、GitHub Web 的 `ppl-data.js` 資料契約，以及 Asset Profiles / Web Scraping Showcase 的 schema、export 與 Streamlit loader。

所有測試都必須能在本機離線執行。BigQuery、Yahoo Finance、FRED、Gemini 等外部服務不能在測試中真的被呼叫；需要資料時使用 fixtures 或 mock。

## 執行方式

從 repo root 執行全部測試：

```bash
python3 -m pytest tests/
```

執行目前交付前最常用的核心測試組：

```bash
python3 -m pytest tests/processing/test_backtest.py tests/processing/test_metrics.py tests/export/test_export_web_data.py
```

測試依賴：

```bash
pip install -r tests/requirements_test.txt
```

## 資料夾結構

```text
tests/
├── README.md
├── conftest.py
├── requirements_test.txt
├── export/
│   └── test_export_web_data.py
├── processing/
│   ├── test_backtest.py
│   ├── test_drawdown_events.py
│   ├── test_fire_calculator.py
│   └── test_metrics.py
└── streamlit/
    └── test_asset_profiles_loader.py
```

分類規則：

| 位置 | 測什麼 | 說明 |
|---|---|---|
| `tests/export/` | GitHub Web data export | 保護 `ppl-data.js` schema、單位、TWD conversion 與 idempotency |
| `tests/processing/` | 金融計算與核心邏輯 | 保護 metrics、backtest、FIRE、drawdown events |
| `tests/streamlit/` | Streamlit-specific helper 測試 | 目前測 asset profile loader |
| `conftest.py` | 共用 fixtures | 提供 fake price data、fake metrics、constant FX 等測試資料 |
| `requirements_test.txt` | 測試依賴 | pytest、pandas、numpy、pandas-gbq 等 |

## 測試檔案角色

| 檔案 | 保護範圍 | 必要性 |
|---|---|---|
| `conftest.py` | 共用路徑設定與 fixtures，確保測試可匯入 `streamlit_dashboard` 與 `github_web/scripts` | 必要 |
| `export/test_export_web_data.py` | `PPL_ASSETS`、`PPL_PRICE_HISTORY`、`PPL_FX_RATE`、`PPL_HISTORY_UPDATED_AT` 的輸出契約 | 必要 |
| `processing/test_backtest.py` | `run_combined()` 的 lump-sum、DCA timing、MWRR、年度報酬、USD to TWD FX conversion、mixed portfolio、ticker validation | 必要 |
| `processing/test_drawdown_events.py` | 回撤 episode 偵測、peak / trough / recovery、min-depth filter、top N、歷史事件標籤 | 必要 |
| `processing/test_fire_calculator.py` | years-to-FIRE、projection structure、nominal / inflation-adjusted timeline、edge cases | 必要 |
| `processing/test_metrics.py` | CAGR、volatility、max drawdown、Sharpe ratio、worst year 與 edge cases | 必要 |
| `export/test_asset_profiles_schema.py` | `asset_profiles.json` schema、ticker 覆蓋率、欄位型別、source allowlist | 必要 |
| `export/test_asset_profiles_export.py` | `ppl-asset-profiles.js` 匯出格式、escape / sanitize、idempotency | 必要 |
| `streamlit/test_asset_profiles_loader.py` | Streamlit loader 正常讀取、缺資料 fallback、壞 JSON 防護 | 必要 |

## 測試原則

- 不連外部網路。
- 不讀寫真實 BigQuery。
- 不依賴目前日期或即時行情。
- 不使用真實 API key、service account 或 Streamlit secrets。
- 金融數值用小型 synthetic DataFrame 驗證公式。
- 匯出測試要檢查資料單位，避免 fraction / percentage 混用。
- Asset profile 測試要檢查來源 allowlist、文字 sanitize、缺資料 fallback 與 schema version。

## 維護規則

- 修改 `streamlit_dashboard/src/processing/metrics.py` 時，同步更新 `test_metrics.py`。
- 修改 `streamlit_dashboard/src/processing/backtest.py` 時，同步更新 `test_backtest.py`。
- 修改 `streamlit_dashboard/src/processing/fire_calculator.py` 時，同步更新 `test_fire_calculator.py`。
- 修改 `streamlit_dashboard/src/processing/drawdown_events.py` 時，同步更新 `test_drawdown_events.py`。
- 修改 `github_web/scripts/export_web_data.py` 或 `github_web/src/ppl-data.js` schema 時，同步更新 `test_export_web_data.py`。
- 修改 `data/asset_profiles/asset_profiles.json` schema 或 `github_web/scripts/asset_intelligence/` 時，同步更新 asset profile schema / export 測試。
- 修改 `streamlit_dashboard/src/asset_profiles/loader.py` 時，同步更新 `tests/streamlit/test_asset_profiles_loader.py`。
- 新增 asset universe ticker 時，確認 fixtures、ticker whitelist、web export 與相關測試仍通過。

## Asset Profiles 測試 Pipeline

1. 已建立 `asset_profiles.json` fixture / 實際資料。
2. 已測試 ETF / crypto profile 必填欄位。
3. 已測試所有 profile ticker 都存在於 `ASSET_POOL`。
4. 已測試 `sourceUrl` 只允許出現在 allowlist 內的來源。
5. 已測試 summary、issuer、dividendPolicy 等文字欄位不含可執行 HTML / script。
6. 已測試 GitHub Web JS export 可被前端安全讀取。
7. 已測試 Streamlit loader 在缺資料或壞資料時回傳 fallback。
8. 實際結果：`python3 -m pytest tests/` 為 136 passed。

## 本機產物

`__pycache__/`、`.pyc`、`.DS_Store` 都是本機產物，不應提交到 Git。若出現可直接刪除。
