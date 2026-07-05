# Passive Portfolio Lab 版本修訂紀錄

最後更新：2026-07-05

本文件記錄 Passive Portfolio Lab 的主要版本變更。格式參考
Keep a Changelog，但目前專案尚未建立正式 Git tag，因此先以「里程碑版本」
整理開發歷程。

## [修正 11.1] - 2026-07-05

### 新增

- 新增 GitHub Web export 價格斷崖檢查，依資產類別套用門檻：ETF 為 3.0x、Crypto 為 6.0x，避免未校正分割資料進入靜態回測，同時保留 DOGE-USD 這類真實高波動行情。
- 新增 WAF / 封鎖頁防線，fetch 層以多重訊號辨識封鎖頁，normalize / validate gate 會阻擋污染摘要並優先沿用前次乾淨資料；fixture 覆蓋 TWSE 真實 `FOR SECURITY REASONS...CAN NOT BE ACCESSED` 封鎖頁。
- 新增 TLS 與資料污染回歸測試，阻擋 `verify=False`、`disable_warnings`、`TLS_VERIFY_EXCEPTIONS`、`# nosec B501` 與未校正價格斷層回歸。

### 變更

- `validate_export.py` 改為直接讀取 `ASSET_POOL` 取得 expected asset count 與 ticker category，不再手動維護 `EXPECTED_ASSETS = 37`。
- Asset profile readiness 收斂到 `normalize_profiles.export_readiness_errors()`，`validate_export.py` 直接重用同一份 gate。
- 00679B.TWO、00751B.TWO、00955.TWO 的費率改為明確標記的 curated fallback，保留原公開來源 URL 作為出處，但不再依賴 TLS 失敗或 404 的 live scrape。

### 修正

- 修正 `0052.TW` 於 `2025-11-17` 前的 7:1 分割資料污染：fetch 層統一調整 pre-split OHLC 除以 7、volume 乘以 7，並使用 BigQuery backfill 重算 `raw_prices` 與 `asset_metrics`。
- 重新匯出 `github_web/src/ppl-data.js`，`0052.TW` 最大相鄰日價格比值由約 6.99x 降至約 1.13x。
- 移除 Looker 匯出端對 `0052.TW` 的單點 hardcode，讓 Looker、Streamlit 與 GitHub Web 都使用同一份已校正 BigQuery 價格資料。

### 安全性

- 移除 Asset Profiles fetcher 的 TLS 驗證例外、`urllib3.disable_warnings()` 與 Bandit `# nosec B501` 排除。
- `github_web/serve.py` 改為只綁定 `127.0.0.1`。
- Streamlit password gate 改用 `hmac.compare_digest()` 比較密碼。
- 刪除未使用的 `fetch_crypto_profiles.py`，降低未維護爬蟲入口。

### 驗證

- `python3 -m pytest tests/`：150 passed。
- `python3 -m bandit -r streamlit_dashboard github_web/scripts looker_studio -x '*/__pycache__/*'`：No issues identified。
- `python3 -m pip_audit -r streamlit_dashboard/requirements.txt`：No known vulnerabilities found。
- `python3 -m pip_audit -r tests/requirements_test.txt`：No known vulnerabilities found。
- `python3 github_web/scripts/backfill_missing_web_assets.py 0052.TW`：成功刷新 0052.TW 並重算 full `asset_metrics`。
- `python3 github_web/scripts/export_web_data.py`：成功匯出 37 assets。
- `python3 github_web/scripts/validate_export.py`：Export validation passed，37 assets，FX=31.92。

## [新增 11] - 2026-07-05

### 版本修訂記錄

- 進化實驗室與 landing page 使用體驗改版
   - 進化實驗室加入操作導覽，改用分步高亮與導覽卡片，引導使用者完成資產篩選、預設投資人角色、重疊檢查、風險配置、回測、FIRE 與總結。
   - Landing page 完成資產池三欄分類、獨立展開 / 收合按鈕、真實資產名稱、投資哲學區塊重排、深色引言區與下滑出現動畫。
   - 使用方式區塊統一使用「經典實驗室」、「進化實驗室」、「決策儀表板」，並在內容中保留 Streamlit、GitHub Web、Looker Studio 作為原始技術說明。

- 經典實驗室新手導覽補強
   - Streamlit 主頁加入非彈窗式新手提醒與分析流程圖，協助第一次使用者理解從挑選資產到閱讀總結的完整順序。
   - 側邊欄新手導覽保留為輔助 checklist，不再用彈窗打斷操作，也移除重複的說明文字。

- 資安、品質與資料新鮮度重掃
   - `python3 -m pytest tests/`：136 passed。
   - `python3 -m bandit -r streamlit_dashboard github_web/scripts looker_studio -x '*/__pycache__/*'`：No issues identified。
   - `python3 -m pip_audit -r streamlit_dashboard/requirements.txt` 與 `python3 -m pip_audit -r tests/requirements_test.txt`：No known vulnerabilities found。
   - secret / credential 搜尋與 git tracked sensitive files 檢查未發現已追蹤的明文 key、private key、`.env`、`credentials.json`、`.DS_Store`、`__pycache__` 或 `.pyc`。
   - 使用本機 BigQuery credentials 重新匯出 `github_web/src/ppl-data.js`，`validate_export.py` 於資料刷新後通過，37 assets，FX=31.57。

- 保守程式碼清理與文件維護
   - 清理進化實驗室導覽中舊彈窗命名、未使用 wrapper id 與未使用 component prop，保留 `ppl_help_seen` 只作為舊 localStorage key 的相容讀寫。
   - 更新 root README、子系統 README、`SECURITY_REVIEW.md` 與本 changelog，讓文件反映 2026-07-05 的實際狀態。
   - 移除舊的長篇技術附錄，改以版本修訂記錄維護歷史。

## [修正 10.1.1] - 2026-07-02

### 修正

- 修正 TWD-based 回測年化報酬：有 monthly contribution 時改用 MWRR，不再以期末價值除以累計投入計算。
- 修正回測年度報酬圖，改為扣除每月投入影響後再複利計算。
- 修正 Python 回測 DCA 日期，月初非交易日時改用該月第一個可用價格日期。
- 修正 `metrics.py` worst-year 計算的 pandas FutureWarning，避免未來 pandas 版本升級時因全 NA 年度報酬而失效。
- 修正 GitHub Web 操作導覽的 `localStorage` 防護，storage 被封鎖時仍可正常關閉。
- 將 `outputs/` 加入 `.gitignore`，並移除空的 `.sixth/skills` 本機目錄。
- 補齊 `.env.example` 的 `GEMINI_API_KEY` 與 `APP_PASSWORD` 選用設定。

### 文件

- 更新 README、子系統 README、測試說明、資料說明與資安掃描報告的測試數字與更新日期。

### 驗證

- `python3 -m pytest tests/processing/test_backtest.py tests/processing/test_metrics.py tests/export/test_export_web_data.py`：68 passed。
- `python3 -m pytest tests/`：136 passed。


## [新增 10] - 2026-06-08

### 新增

- 新增 Asset Profiles / Web Scraping Showcase 第一版資料線：
  - `data/asset_profiles/asset_profiles.json`
  - `github_web/src/ppl-asset-profiles.js`
  - `github_web/scripts/asset_intelligence/`
  - `streamlit_dashboard/src/asset_profiles/loader.py`
- 新增 ETF / crypto profile schema，涵蓋基本簡介、發行商、費用率、配息政策、
  crypto 類別、區塊鏈、共識機制、資料來源與更新時間。
- 新增 `tests/export/test_asset_profiles_schema.py`、
  `tests/export/test_asset_profiles_export.py`、
  `tests/streamlit/test_asset_profiles_loader.py`。

### 變更

- GitHub Web 載入 `ppl-asset-profiles.js`，並在「組合配置」資產詳情中顯示
  資產補充資訊。
- GitHub Web 資產詳情改為左右並排：左側保留原本績效數值卡，右側顯示
  資產補充資訊，避免補充資訊被推到頁面下方。
- Streamlit Dashboard 在「投資組合組成」treemap 資產詳情中顯示同一份
  asset profile 資料。
- Streamlit Dashboard 資產詳情改為三欄一致透明框：績效數值、資產補充資訊、
  雷達圖，並讓雷達圖在右欄置中。
- 修正 Streamlit Dashboard 三欄詳情卡的排版溢出問題：原本資產補充資訊卡用
  `margin-top:auto` 將「更新時間 / 來源」推到卡片底部，內容較長時會掉出
  外層藍色區塊；修正後三欄統一使用透明框、提高 HTML component 高度，並讓
  資料來源 footer 回到正常文字流，雷達圖則以 flex 水平與垂直置中。
- Asset profile 來源改為官方或公開 HTML 頁面爬蟲：台股 ETF 使用 TWSE ETF
  資訊頁，美股 ETF 使用 Vanguard / iShares / SPDR / Invesco 等官方頁，
  crypto 使用官方網站或官方公開資料頁。
- 修正 asset profile 費用率佔位問題：29 檔 ETF 皆輸出可顯示的費用率文字，
  GitHub Web 與 Streamlit 共同讀取同一份 `asset_profiles.json` /
  `ppl-asset-profiles.js`；8 檔 crypto 不再套用 ETF 費用率欄位。
- 重定義 ETF 費用率資料契約：台股 ETF 的 `expenseRatio` 改由爬蟲取得的
  `managementFee + custodianFee` 計算，並新增 `managementFee`、`custodianFee`、
  `expenseRatioFormula`、`expenseRatioSourceName`、`expenseRatioSourceUrl` 與
  `expenseRatioCollectionMethod`；前端改為只顯示單一「費用率」欄位，台股 ETF
  以括號標注其包含的經理費與保管費，不再額外拆出「經理費」、「保管費」或
  「計算方式」欄位，也不再使用 `約` 或 `+` 這類模糊 wording。
- Landing page 新增「資產補充資訊 / Web Scraping Showcase」功能亮點。
- GitHub Actions workflow 新增 asset profile JSON / JS 產生、驗證、artifact 與
  自動 commit 流程。
- `github_web/scripts/validate_export.py` 新增 `PPL_ASSET_PROFILES` 檢查。

### 安全性

- 新增來源 allowlist，僅允許固定公開來源 URL。
- `validate_export.py` 與 schema tests 會阻擋 Yahoo Finance quote page、
  CoinMarketCap 交易頁或行情 API 成為 asset profile 來源。
- 新增文字 sanitize，移除 HTML tag / script-like 內容後才輸出到前端。
- fetcher 設定固定 user-agent 與 request timeout。
- raw 爬蟲資料維持 ignored，只追蹤正規化後的安全 JSON / JS。

### 驗證

- `python3 -m pytest tests/`：136 passed。
- `python3 -m bandit -r streamlit_dashboard github_web/scripts looker_studio -x '*/__pycache__/*'`：No issues identified。
- `python3 github_web/scripts/validate_export.py`：Export validation passed。

## [變更 9.1] - 2026-06-08

### 變更

- Streamlit Cloud 已重新部署並直接使用 `streamlit_dashboard/app.py` 作為正式
  entry point。
- 移除舊的 `dashboard/Passive_Portfolio_Lab.py` compatibility shim，讓 repo
  結構更集中於 `streamlit_dashboard/`。
- 更新 README 與 `SECURITY_REVIEW.md`，將 Streamlit 部署入口與 shim 移除狀態
  改為目前實際狀態。

### 修正

- 移除 Streamlit shim 後，原本 Bandit B102 `exec_used` 的部署相容層不再存在，
  不需再以 `# nosec B102` 排除。

## [新增 9] - 2026-06-07

### 新增

- 新增正式資安與弱點掃描報告 `SECURITY_REVIEW.md`，記錄 dependency audit、
  secret scan、Bandit SAST、主要風險與修補建議。

### 變更

- 重整 `CHANGELOG.md`，保留既有重大版本更新與資安修補脈絡。
- 移除原本 `[Unreleased]` 待完成區塊，避免 changelog 混入已決定省略或已完成的
  待辦事項。
- 依 `SECURITY_REVIEW.md` 修正高風險資安項目：移除所有 `verify=False`、新增
  BigQuery identifier validation、補上 Streamlit Cloud shim 安全註解與 nosec、
  並改善 secrets 初始化錯誤處理。
- 處理剩餘 Bandit B608 / B105 靜態掃描提示：對已驗證的 BigQuery SQL 組裝、
  固定 generated SQL、Streamlit shim 與 UI 翻譯誤判加入精準 `# nosec` 與理由，
  使 Bandit 重掃達到 0 findings。
- 更新 `SECURITY_REVIEW.md`，保留原始掃描結果並新增修正後掃描紀錄。

## [新增 8] - 2026-06-02

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

## [變更 7.1] - 2026-05-27

### 變更

- 清理 magic numbers、dead code 與 inline styles，降低維護成本。
- 整理重複邏輯與可讀性問題，讓金融計算、UI 呈現與資料處理的責任分工更清楚。

### 修正

- 修正 landing page 的 hero、平台區塊導覽、按鈕點擊區域、文案換行與 Looker
  說明等展示頁細節。
- 修正 hero overlay 攔截點擊事件的問題，確保主要 CTA 可正常互動。

## [新增 7] - 2026-05-26

### 新增

- 新增專案 landing page，作為 GitHub Pages 上的展示與導覽入口。
- 重新整理 landing page 內容，改成以使用者問題與三個平台交付價值為主軸。
- 新增專案報告簡報檔，作為技術與成果展示素材；目前交付版為本機 ignored 的 `outputs/passive-portfolio-lab-final-report-deliverable-style.pptx`。

### 變更

- 調整 landing page 的平台比較、功能說明、導覽錨點與 Streamlit 連結。
- 移除簡報產生腳本，只保留產出的簡報檔，避免 repo 保留不必要的生成工具。
- 更新首頁文案，讓專案主張更聚焦於長期投資、風險、回撤與 FIRE 權衡。

### 修正

- 修正 landing page compare table、Looker Studio 描述、hero 按鈕導向與文案換行。

## [新增 6] - 2026-05-25

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

## [新增 5] - 2026-05-24

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

## [新增 4] - 2026-05-23

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

## [新增 3] - 2026-05-05

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

## [新增 2] - 2026-05-02

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

## [新增 1] - 2026-04-30

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

- 發布里程碑若以新增功能為主，版本標題使用第一層編號，例如 `[新增 1]`、`[新增 2]`。
- 發布里程碑若以修改既有行為為主，版本標題使用第二層編號，例如 `[變更 1.1]`、`[變更 1.2]`。
- 發布里程碑若以修 bug 為主，版本標題使用第三層編號，例如 `[修正 1.1.1]`、`[修正 1.1.2]`。
- 版本內文使用一般條列即可，不需要套用特殊編號規則。
- 涉及憑證、SQL injection、資料暴露、權限或依賴弱點時，請加到「安全性」。
- 若改動金融公式、資料 schema、BigQuery views、Looker tables 或
  `ppl-data.js` 結構，必須同步更新測試、README、資料契約與本文件。
