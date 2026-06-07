# Passive Portfolio Lab 版本修訂紀錄

本文件記錄 Passive Portfolio Lab 的主要版本變更。格式參考
Keep a Changelog，但目前專案尚未建立正式 Git tag，因此先以「里程碑版本」
整理開發歷程。

## 重大程式碼變更詳解 Top 10

以下整理本專案最重要的 10 個程式碼層級變更。每一項都包含「改哪裡」、
「為什麼改」、「更改前後差異」與「實際程式碼範例」，方便未來回顧技術決策
與維護脈絡。

### 1. 建立 Streamlit 互動式投資儀表板

改哪裡：

- `streamlit_dashboard/app.py`
- `streamlit_dashboard/src/processing/screening.py`
- `streamlit_dashboard/src/processing/metrics.py`

原因：

- 專案初始目標是讓使用者能篩選 ETF / crypto 資產，並用風險指標比較長期被動投資組合。
- 單純資料表不足以回答「報酬背後的風險與回撤痛苦」這個核心問題，因此需要互動式 dashboard。

更改前：

- 沒有可操作的投資組合分析介面。
- 資產資料、指標計算與使用者流程尚未整合。

更改後：

- 建立 Streamlit app，支援資產篩選、AgGrid 表格、CAGR / volatility /
  max drawdown / Sharpe 等指標。
- 將資產池與金融指標計算拆入 `src/processing/`，讓 UI 與計算邏輯開始分層。

實際程式碼範例：

```python
# streamlit_dashboard/src/processing/screening.py
class AssetInfo(TypedDict):
    ticker: str
    name: str
    category: str
    subcategory: str
    aum_rank: int
    aum_note: str
    description: str


ASSET_POOL: list[AssetInfo] = [
    {
        "ticker": "0050.TW",
        "name": "Yuanta Taiwan 50 ETF",
        "category": "TW_ETF",
        "subcategory": "Market-Cap",
        "aum_rank": 1,
        "aum_note": "approx. TWD 1,661.5B",
        "description": "Tracks the top 50 Taiwan companies by market cap; the core passive investment vehicle for the Taiwan stock market.",
    },
]
```

### 2. 加入 Persona quick start、雙語流程與 Gemini AI insights

改哪裡：

- `streamlit_dashboard/app.py`
- `streamlit_dashboard/src/processing/screening.py`
- README 相關功能說明

原因：

- 一般使用者不一定知道如何從 37 個資產中建立初始投資組合。
- 專案目標使用者包含台灣投資人，因此需要繁體中文與英文雙語體驗。
- 投資結果需要轉成可讀的策略摘要，而不只是表格與圖表。

更改前：

- 使用者需要手動挑選資產並理解所有指標。
- UI 文案與投資摘要較偏單一語言與技術呈現。
- 沒有 AI 輔助解釋 portfolio structure、drawdown、FIRE timeline。

更改後：

- 新增 Young Professional、Pre-Retirement、Aggressive Growth 三種 persona。
- Persona 可自動帶入 watchlist、risk level、backtest 與 FIRE 假設。
- 加入繁體中文 / 英文切換。
- 若設定 `GEMINI_API_KEY`，可產生 Gemini 2.5 Flash 投資組合摘要；未設定時保留規則式 fallback。

實際程式碼範例：

```javascript
// github_web/src/ppl-data.js
const PPL_PERSONAS = {
  '🐣 Young Professional': {
    watchlist: ['0050.TW','VTI','VEA','BND','GLD','BTC-USD'],
    weights: {
      '0050.TW':0.25, 'VTI':0.25, 'VEA':0.15,
      'BND':0.20, 'GLD':0.10, 'BTC-USD':0.05
    },
    risk: 'Medium',
    initial: 100000,
    monthly: 10000,
    annual_expenses: 600000,
  },
};
```

```python
# streamlit_dashboard/app.py
@st.cache_data(ttl=300, show_spinner=False)
def get_gemini_insights(
    watchlist: tuple,
    allocation: tuple,
    cagr_bt: float,
    max_drawdown: float,
    total_return: float,
    fire_years: float,
    fire_target: int,
    risk_level: str,
    initial_cap: float,
    monthly_cont: float,
    annual_exp: float,
    existing_summaries: list = None
) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return ""

    client = genai.Client(api_key=api_key)
    allocation_str = ", ".join([f"{t} ({w*100:.0f}%)" for t, w in allocation])
    prompt = f"""You are a professional financial advisor helping a Taiwan-based passive investor.
Financial Context:
- Current Portfolio: {allocation_str}
- Risk Level: {risk_level}
- Historical Performance: {cagr_bt*100:.1f}% CAGR, {max_drawdown*100:.1f}% Max Drawdown, {total_return:.1f}x Total Return
- FIRE Target: NT${fire_target:,}
- Years to FIRE (Real): {fire_years:.1f}
"""
```

### 3. 重構 correlation analysis 與投資組合確認流程

改哪裡：

- `streamlit_dashboard/app.py`
- correlation groups / overlap count / suggested removal 相關流程

原因：

- 高度相關的資產會讓投資組合看似多元，實際上卻重複曝險。
- 使用者在進入回測與 FIRE 前，需要先確認資產組合是否真的分散。

更改前：

- correlation 結果較偏診斷資訊，使用者不一定知道下一步要刪哪個資產。
- Persona 與手動選股流程沒有清楚區分，容易讓預設投資組合也被要求手動確認。

更改後：

- 對手動 portfolio：找出高相關群組，推薦每組保留 AUM / liquidity 較佳的資產。
- 對 persona portfolio：顯示 correlation diagnostics，但不強制刪除或重新確認。
- 下游 risk allocation / backtest / FIRE 只在 portfolio 確認後解鎖，降低使用者誤用未確認組合的機率。

實際程式碼範例：

```javascript
// github_web/index.html
const CorrelationSection = ({ watchlist, setWatchlist, confirmed, setConfirmed, persona }) => {
  if (!watchlist.length) return <InfoBanner>{t.corrAddFirst}</InfoBanner>;

  if (persona) return (
    <InfoBanner type="success">{t.corrPersonaApplied(persona)}</InfoBanner>
  );

  const activeGroups = CORR_GROUPS.map(g => ({
    ...g,
    present: g.tickers.filter(tk => watchlist.includes(tk)),
  })).filter(g => g.present.length >= 2);

  const removeOthers = (group) => {
    const keeper = group.present.includes(group.recommend)
      ? group.recommend
      : group.present[0];
    const toRemove = group.present.filter(tk => tk !== keeper);
    setConfirmed(false);
    setWatchlist(w => w.filter(tk => !toRemove.includes(tk)));
  };
};
```

### 4. 建立 TWD-based combined backtest engine

改哪裡：

- `streamlit_dashboard/src/processing/backtest.py`
- `tests/processing/test_backtest.py`

原因：

- 專案面向台灣投資人，投資結果需要以 TWD 為主體，而不是只看 USD 資產原幣績效。
- 真實投資常見情境是「初始投入 + 每月定期投入」，不是單純 buy-and-hold。

更改前：

- 回測邏輯較難完整表達台灣投資人的跨幣別投入經驗。
- USD ETF / crypto 與台幣 ETF 的 portfolio value 容易混用不同貨幣基準。

更改後：

- `run_combined()` 支援 initial investment + monthly contribution。
- 台股 ETF 保持 TWD，USD-denominated assets 透過 TWD/USD 歷史匯率轉成 TWD。
- 測試覆蓋 lump-sum、DCA timing、USD to TWD conversion、mixed portfolio、weight normalization。

實際程式碼範例：

```python
# streamlit_dashboard/src/processing/backtest.py
usd_tickers = [
    t for t in valid_tickers
    if not (t.endswith(".TW") or t.endswith(".TWO"))
]
if usd_tickers:
    fx = load_fx_rate(start_date, end_date)
    fx = fx.reindex(pivot.index).ffill().bfill()
    for ticker in usd_tickers:
        pivot[ticker] = pivot[ticker] * fx.values

for date in pivot.index:
    if date == first_day:
        for ticker in valid_tickers:
            allocated = initial_investment * weights[ticker]
            shares[ticker] += allocated / pivot.loc[date, ticker]
        total_invested += initial_investment
    elif date in monthly_dates:
        for ticker in valid_tickers:
            allocated = monthly_contribution * weights[ticker]
            shares[ticker] += allocated / pivot.loc[date, ticker]
        total_invested += monthly_contribution
```

### 5. 修正 TWD/USD 匯率抓取方式，避免長期回測失真

改哪裡：

- `streamlit_dashboard/src/processing/backtest.py`

原因：

- Yahoo Finance 使用 `range=max` 抓 `TWD=X` 時，較舊資料可能被降頻成 monthly。
- 若 monthly FX data 被 `ffill()` 套到 daily portfolio，可能造成回測跨期時出現不合理的 portfolio value spike。

更改前：

- 匯率資料可能在長時間區間被 Yahoo 自動降頻。
- 資料粒度不一致會污染 USD 資產轉 TWD 的計算。

更改後：

- 改用 `period1` / `period2` unix timestamp 明確抓指定期間 daily data。
- 加入匯率合理範圍過濾，將 20-50 以外的 TWD/USD 異常值排除。
- 回測引擎在 FX 層多了一層資料品質防線。

實際程式碼範例：

```python
# streamlit_dashboard/src/processing/backtest.py
start_ts = int(pd.Timestamp(start_date).timestamp())
end_ts = int((pd.Timestamp(end_date) + pd.Timedelta(days=1)).timestamp())

url = (
    "https://query1.finance.yahoo.com/v8/finance/chart/TWD=X"
    f"?interval=1d&period1={start_ts}&period2={end_ts}"
)
r = requests.get(url, headers=headers, timeout=15, verify=False)
data = r.json()
result = data["chart"]["result"][0]

series = pd.Series(closes, index=index).dropna()
series = series[~series.index.duplicated(keep="first")]
series = series[(series >= 20) & (series <= 50)]
```

### 6. 新增 GitHub Web 靜態版與 BigQuery to `ppl-data.js` 匯出

改哪裡：

- `github_web/index.html`
- `github_web/scripts/export_web_data.py`
- `github_web/src/ppl-data.js`
- `.github/workflows/update-and-deploy.yml`

原因：

- Streamlit 適合互動研究，但公開展示與快速載入需要一個不依賴後端 credentials 的靜態版本。
- Browser 端不應直接連 BigQuery 或暴露 service account。

更改前：

- 主要交付面是 Streamlit app。
- Web 公開展示需要依賴互動 app 或外部服務。

更改後：

- GitHub Web 成為靜態 GitHub Pages app。
- BigQuery 資料由 CI 匯出成 `ppl-data.js`，包含 `PPL_ASSETS`、
  `PPL_PRICE_HISTORY`、`PPL_FX_RATE`、`PPL_HISTORY_UPDATED_AT`。
- Browser 只讀取靜態資料，不需要 BigQuery credentials。

實際程式碼範例：

```python
# github_web/scripts/export_web_data.py
def load_metrics() -> pd.DataFrame:
    project_id, dataset_id = get_bq_config()
    query = f"SELECT * FROM `{dataset_id}.asset_metrics`"
    df = pandas_gbq.read_gbq(query, project_id=project_id)
    return df


def load_raw_prices(tickers: list[str]) -> pd.DataFrame:
    project_id, dataset_id = get_bq_config()
    tickers_sql = ", ".join(sql_string(t) for t in tickers)
    query = f"""
        SELECT date, ticker, close
        FROM `{dataset_id}.raw_prices`
        WHERE ticker IN ({tickers_sql})
        ORDER BY ticker, date
    """
    df = pandas_gbq.read_gbq(query, project_id=project_id)
    return df
```

```javascript
// github_web/src/ppl-data.js
const PPL_HISTORY_UPDATED_AT = "2026-06-01 23:50 UTC";
const PPL_FX_RATE = 31.569;
const PPL_PRICE_HISTORY = {
  "0050.TW": [["2009-01-02", 5.117], ["2009-01-05", 5.6961]]
};
```

### 7. 新增 Looker Studio semantic layer 與 portfolio-level tables

改哪裡：

- `looker_studio/generate_bigquery_views.py`
- `looker_studio/bigquery_views.sql`
- `looker_studio/export_portfolio_tables.py`
- `looker_studio/README.md`

原因：

- 專案不只需要互動工具，也需要可分享、可簡報、可視覺比較的 BI 報表。
- Looker Studio 需要穩定的 views / tables 作為語意層，避免 dashboard 直接綁 raw table。

更改前：

- BigQuery 資料主要服務 Streamlit 與 web export。
- 沒有針對 Looker Studio 設計的資產層與 portfolio 層資料。

更改後：

- 建立 asset-level views：`looker_asset_metrics`、`looker_price_history`、
  `looker_annual_returns`、`looker_category_summary`。
- 建立 portfolio-level tables：allocation、metrics、history、annual returns、
  drawdown events、FIRE scenarios、FIRE projection。
- Looker Studio 可用六個預設投資組合做比較與展示。

實際程式碼範例：

```python
# looker_studio/generate_bigquery_views.py
def generate_sql(project_id: str, dataset_id: str) -> str:
    metadata = asset_metadata_cte()
    return f"""-- Passive Portfolio Lab Looker Studio semantic layer
CREATE OR REPLACE VIEW `{project_id}.{dataset_id}.looker_asset_metrics` AS
WITH
{metadata}
SELECT
  m.ticker,
  md.name,
  md.category,
  md.subcategory,
  CASE WHEN md.category = 'TW_ETF' THEN 'TWD' ELSE 'USD' END AS currency,
  m.cagr,
  m.volatility,
  m.max_drawdown,
  m.sharpe_ratio
FROM `{project_id}.{dataset_id}.asset_metrics` AS m
LEFT JOIN asset_metadata AS md USING (ticker);
"""
```

### 8. 新增 export validation、GitHub Actions summary 與 artifact

改哪裡：

- `github_web/scripts/validate_export.py`
- `.github/workflows/update-and-deploy.yml`

原因：

- 每日自動更新 `ppl-data.js` 若產出壞資料，會直接影響 GitHub Pages 前端。
- 需要在 commit / deploy 前檢查資料新鮮度、資產數量與 FX rate 合理性。

更改前：

- CI 會匯出並部署資料，但缺少明確的資料品質 gate。
- 出錯時較難從 workflow 快速知道更新時間、資產數量與 FX rate。

更改後：

- `validate_export.py` 檢查 required JS globals、asset count、freshness、FX range。
- GitHub Actions 在 commit 前先跑 validation，壞資料不應落入 repo。
- Workflow summary 顯示 updated_at、asset count、FX rate。
- 上傳 `ppl-data.js` artifact，保留 7 天供除錯。

實際程式碼範例：

```python
# github_web/scripts/validate_export.py
for var in ["PPL_ASSETS", "PPL_PRICE_HISTORY", "PPL_FX_RATE", "PPL_HISTORY_UPDATED_AT"]:
    if f"const {var}" not in content:
        errors.append(f"MISSING global: const {var}")

asset_count = len(re.findall(r'ticker:\s*["\']([^"\']+)["\']', content))
if asset_count < EXPECTED_MIN_ASSETS:
    errors.append(
        f"ASSET COUNT: {asset_count} assets exported (expected >= {EXPECTED_MIN_ASSETS})"
    )

fx_match = re.search(r"const PPL_FX_RATE = ([\d.]+);", content)
if fx_match and not (20.0 <= float(fx_match.group(1)) <= 50.0):
    errors.append("FX RATE is outside plausible 20-50 TWD/USD range")
```

```yaml
# .github/workflows/update-and-deploy.yml
- name: Validate export
  run: python github_web/scripts/validate_export.py

- name: Upload export artifact
  uses: actions/upload-artifact@v4
  with:
    name: ppl-data-${{ github.run_id }}
    path: github_web/src/ppl-data.js
    retention-days: 7
```

### 9. 加入 ticker whitelist，降低 SQL interpolation 風險

改哪裡：

- `streamlit_dashboard/src/processing/screening.py`
- `streamlit_dashboard/src/processing/backtest.py`
- `streamlit_dashboard/src/processing/fire_calculator.py`
- `tests/processing/test_backtest.py`

原因：

- 部分 BigQuery 查詢會將 ticker list 組成 SQL `IN (...)` 條件。
- 即使 ticker 多數來自固定資產池，仍需要明確驗證，避免未受控字串進入 SQL。

更改前：

- ticker 輸入與 SQL 組裝之間缺少一致的防線。
- 若未來 UI 或腳本允許外部 ticker，可能增加 injection 風險。

更改後：

- 透過 `validate_tickers()` 限制 ticker 必須屬於 curated asset universe。
- backtest / FIRE 等查詢前先驗證 ticker。
- 測試補上 ticker validation 情境，避免未來重構時拿掉安全檢查。

實際程式碼範例：

```python
# streamlit_dashboard/src/processing/screening.py
def validate_tickers(tickers: list[str]) -> None:
    """Raise ValueError if any ticker is not in ASSET_POOL.

    Call this before interpolating tickers into SQL to prevent injection.
    """
    allowed = {a["ticker"] for a in ASSET_POOL}
    invalid = [t for t in tickers if t not in allowed]
    if invalid:
        raise ValueError(f"Ticker(s) not in ASSET_POOL: {invalid}")
```

```python
# tests/processing/test_backtest.py
def test_rejects_sql_injection_like_ticker(self):
    with pytest.raises(ValueError, match="not in ASSET_POOL"):
        validate_tickers(["0050.TW', 'x'; DROP TABLE raw_prices; --"])
```

### 10. 建立核心測試，保護金融計算與資料契約

改哪裡：

- `tests/conftest.py`
- `tests/processing/test_metrics.py`
- `tests/processing/test_backtest.py`
- `tests/processing/test_fire_calculator.py`
- `tests/processing/test_drawdown_events.py`
- `tests/export/test_export_web_data.py`
- `pytest.ini`

原因：

- 金融計算錯誤會直接破壞專案可信度。
- BigQuery export schema 若改動，GitHub Web 可能靜默壞掉。
- 測試需避免依賴 BigQuery、Yahoo Finance、FRED、Gemini 等外部服務。

更改前：

- 專案主要靠手動驗證與互動測試。
- 金融公式、FX conversion、FIRE projection、drawdown episode 與 `ppl-data.js`
  schema 缺少可重跑的自動保護。

更改後：

- 建立 pytest 測試架構。
- 使用 synthetic fixtures 與 mocks，避免網路呼叫。
- 覆蓋 CAGR、volatility、max drawdown、Sharpe、worst year、combined backtest、
  USD/TWD conversion、FIRE、drawdown events、web export schema 與 idempotency。

實際程式碼範例：

```python
# tests/processing/test_backtest.py
def test_usd_asset_converted_via_fx(self):
    prices = _prices({"SPY": [100.0] * 30})
    fx = _fx(30.0, start="2021-01-04", periods=30)

    with patch("src.processing.backtest.load_fx_rate", return_value=fx):
        result = run_combined(
            prices,
            {"SPY": 1.0},
            "2021-01-04",
            "2021-02-02",
            initial_investment=30_000,
            monthly_contribution=0,
        )

    assert result["portfolio_value"].iloc[0] == pytest.approx(30_000.0, rel=1e-6)
```

```python
# tests/export/test_export_web_data.py
def test_cagr_stored_as_percentage_not_fraction(self, minimal_metrics_df):
    block = ewd.build_assets_block(minimal_metrics_df, "2025-01-01 00:00 UTC")
    assert "cagr:10.0" in block
    assert "cagr:0.1" not in block
```

## 版本更新紀錄

## [0.10.0] - 2026-06-07

### 新增

- 新增正式資安與弱點掃描報告 `SECURITY_REVIEW.md`，記錄 dependency audit、
  secret scan、Bandit SAST、主要風險與修補建議。

### 變更

- 重整 `CHANGELOG.md`，保留既有重大版本更新，並新增「重大程式碼變更詳解
  Top 10」。
- 移除原本 `[Unreleased]` 待完成區塊，避免 changelog 混入已決定省略或已完成的
  待辦事項。
- 依 `SECURITY_REVIEW.md` 修正高風險資安項目：移除所有 `verify=False`、新增
  BigQuery identifier validation、補上 Streamlit Cloud shim 安全註解與 nosec、
  並改善 secrets 初始化錯誤處理。
- 處理剩餘 Bandit B608 / B105 靜態掃描提示：對已驗證的 BigQuery SQL 組裝、
  固定 generated SQL、Streamlit shim 與 UI 翻譯誤判加入精準 `# nosec` 與理由，
  使 Bandit 重掃達到 0 findings。
- 更新 `SECURITY_REVIEW.md`，保留原始掃描結果並新增修正後掃描紀錄。

## [0.9.0] - 2026-06-02

### 新增

- 將 README 重寫為目前專案狀態版本，明確說明三個可部署交付面：
  Streamlit Dashboard、GitHub Web、Looker Studio。
- 在 README 補上 live app links、技術架構、專案結構、測試方式、資料管線、
  方法論與風險說明。
- 補上目前測試涵蓋範圍摘要，說明 `pytest tests/` 會執行金融計算、backtest、
  FIRE、drawdown events、web data export schema 等測試。

### 修正

- 修正 `metrics.py` 中 worst-year groupby 計算造成的 pandas FutureWarning，
  降低未來 pandas 版本升級時的相容性風險。

### 變更

- 將專案定位從單一 dashboard 擴充為三面交付的 bilingual toolkit。
- README 中明確標示 GitHub Web 使用靜態 `ppl-data.js` snapshot，Streamlit
  與 Looker Studio 則讀取 BigQuery / semantic layer。

## [0.8.0] - 2026-05-27

### 變更

- 清理 magic numbers、dead code 與 inline styles，降低維護成本。
- 整理重複邏輯與可讀性問題，讓金融計算、UI 呈現與資料處理的責任分工更清楚。

### 修正

- 修正 landing page 的 hero、平台區塊導覽、按鈕點擊區域、文案換行與 Looker
  說明等展示頁細節。
- 修正 hero overlay 攔截點擊事件的問題，確保主要 CTA 可正常互動。

## [0.7.0] - 2026-05-26

### 新增

- 新增專案 landing page，作為 GitHub Pages 上的展示與導覽入口。
- 重新整理 landing page 內容，改成以使用者問題與三個平台交付價值為主軸。
- 新增專案報告簡報檔 `docs/project_report.pptx`，作為技術與成果展示素材。

### 變更

- 調整 landing page 的平台比較、功能說明、導覽錨點與 Streamlit 連結。
- 移除簡報產生腳本，只保留產出的簡報檔，避免 repo 保留不必要的生成工具。
- 更新首頁文案，讓專案主張更聚焦於長期投資、風險、回撤與 FIRE 權衡。

### 修正

- 修正 landing page compare table、Looker Studio 描述、hero 按鈕導向與文案換行。

## [0.6.0] - 2026-05-25

### 新增

- 將三個交付面的預設語言統一為繁體中文，符合台灣使用者情境。
- 新增 Streamlit Cloud entry point shim，提升 Streamlit Cloud 部署相容性。
- 新增不同平台/頁面的 favicon 與一致化 button styling。

### 變更

- 重整 repo 結構，將 Streamlit、GitHub Web、Looker Studio、tests、dashboard
  shim 與文件位置整理得更清楚。
- 統一 GitHub Web 和 landing page 的視覺元件與按鈕樣式。
- 清理 `docs/` 內容，保留更接近最終交付的文件與素材。

### 修正

- 修正手機版 card grid、full-width layout、FIRE 與 Summary 區塊在窄螢幕上的
  排版問題。
- 修正一批 P1 正確性問題，提升金融計算與資料呈現的可靠度。
- 修正 landing page pipeline 單列呈現、導覽錨點與 Streamlit URL。

## [0.5.0] - 2026-05-24

### 新增

- 新增 export validation，讓 `ppl-data.js` 產出後可檢查 schema 與資料範圍。
- 在 GitHub Actions 加入 job summary 與 artifact upload，讓每日資料更新更容易追蹤。
- 新增 project-level AI agent instructions，協助後續 AI agent 依專案規則接手。

### 安全性

- 在 SQL interpolation 前加入 ticker whitelist，降低未受控 ticker 輸入造成查詢風險。

### 變更

- 降低重複邏輯並改善整體 maintainability。
- 重整 repo 結構與 README 中的專案結構描述。

### 修正

- 修正 mobile horizontal overflow 與 section padding，在手機版避免頁面左右溢出。

## [0.4.0] - 2026-05-23

### 新增

- 新增 `HANDOFF.md`，整理專案目前狀態、交付面、已知缺口與下一階段 pipeline。
- 建立結案 pipeline，包括測試、文件、手機 UX、landing page、資料契約、
  監控與資安方向。
- 補上核心測試與文件基礎，將專案從功能開發推進到結案整理階段。

### 變更

- 明確化三個交付面：
  Streamlit Dashboard、GitHub Web、Looker Studio。
- 將後續工作拆成 scope freeze、data contract、test strategy、security review、
  monitoring、UI polish、final report 等階段。

## [0.3.0] - 2026-05-05

### 新增

- 新增 Looker Studio dashboard assets。
- 建立 Looker Studio 語意層，包含 asset-level views 與 portfolio-level tables。
- 新增 Looker Studio README，說明 BigQuery views、portfolio exports、六個預設
  投資組合與建議儀表板頁面。

### 變更

- 將專案從 Streamlit + GitHub Web 擴充為三面交付：
  interactive app、static web、BI report。

### 修正

- 修正 GitHub Pages 部署版的水平溢出問題。

## [0.2.0] - 2026-05-02

### 新增

- 新增 GitHub Pages 靜態 Web 版本。
- 新增 `github_web/index.html` 作為 GitHub Web 入口。
- 新增 BigQuery 匯出流程，將資產 metrics 與每日 TWD price history 匯出到
  `github_web/src/ppl-data.js`。
- 新增 GitHub Actions workflow，自動更新 `ppl-data.js` 並部署 GitHub Pages。
- 在 README 補上 live app links。

### 變更

- 重整 app 結構以支援部署，讓 Streamlit app、GitHub Web 與資料匯出腳本分離。
- GitHub Web 採靜態資料模式，不在瀏覽器端直接讀取 BigQuery。

### 修正

- 修正 GitHub Web 透過 Pages artifact 部署的流程。

## [0.1.0] - 2026-04-30

### 新增

- 建立 Streamlit Dashboard 初版。
- 新增 AgGrid asset screening table、risk filters、資產篩選與排序功能。
- 新增 quick start persona presets，讓使用者可直接套用常見投資情境。
- 新增 Gemini 2.5 Flash AI portfolio insights。
- 新增繁體中文 / 英文 bilingual persona quick-start flow。
- 新增 correlation analysis、risk allocation、treemap、FIRE calculator、AI summary
  與 portfolio review flow。
- 新增 Dev Container 設定與雲端執行需要的 dependencies。

### 變更

- 調整 backtest dependencies 與 config。
- 重構 persona presets 與 correlation cleanup flow。
- 將 React Web SPA 合併為單一 inline script，並切換到 production builds。
- 改善 Streamlit UI：全寬 layout、sortable columns、select-all、correlation pairs、
  persona language handling、treemap label positioning。

### 修正

- 修正 single-page layout、treemap、FIRE CAGR、AI insights 與 review button。
- 修正 correlation groups、overlap count 與 treemap top-left labels。
- 修正 sidebar 文字亮度與主頁 header banner 呈現。

## 資料自動更新紀錄

自 2026-05-02 起，專案透過 GitHub Actions 例行更新
`github_web/src/ppl-data.js`，commit 訊息通常為：

```text
chore: auto-update ppl-data.js from BigQuery [skip ci]
```

這類 commit 代表 BigQuery 匯出的 web 靜態資料更新，不一定代表功能或程式碼邏輯
變更。因此本 changelog 不逐筆列出每日資料快照，只在相關功能、資料契約或部署流程
變更時記錄。

## 維護規則

- 新增功能時，請加到對應版本的「新增」。
- 修改既有行為時，請加到「變更」。
- 修 bug 時，請加到「修正」。
- 涉及憑證、SQL injection、資料暴露、權限或依賴弱點時，請加到「安全性」。
- 若改動金融公式、資料 schema、BigQuery views、Looker tables 或
  `ppl-data.js` 結構，必須同步更新測試、README、資料契約與本文件。
