# Passive Portfolio Lab 資安與弱點掃描報告

最後更新：2026-07-05

原始掃描日期：2026-06-07
最新重掃日期：2026-07-05
掃描範圍：本機 repo `/Users/at/Documents/GitHub/passive-portfolio-lab`  
報告目的：確認專案在交付前的主要資安風險、依賴弱點、秘密資訊暴露風險與部署安全性。

## 0. 最新狀態摘要

最新重掃日期：2026-07-05
修正方式：保留原始掃描紀錄，新增本節、第 9 節、第 10 節、第 11 節與第 12 節作為修正後紀錄。

| 項目 | 原始掃描 | 最新狀態 |
|---|---:|---:|
| Bandit High | 5 | 0 |
| Bandit Medium | 12 | 0 |
| Bandit Low | 2 | 0 |
| `verify=False` / TLS 驗證例外 | 5 處 + asset profile 例外 | 0 個未審查用法 |
| Python dependency known vulnerabilities | 0 | 0 |
| 測試依賴 known vulnerabilities | 0 | 0 |
| 核心測試 | 未於原始掃描執行 | 150 passed |
| Web export validation | 未於原始掃描執行 | Passed after refresh |
| Git tracked sensitive files | 未發現 | 未發現 |

已完成修正：

- 移除所有 `requests.get(..., verify=False)` 與 asset profile fetcher 的 TLS 驗證例外，恢復正常 TLS certificate validation。
- 移除原始價格 / 宏觀資料線不需要的 `InsecureRequestWarning` suppression，也移除 asset profile 的 `urllib3.disable_warnings()` 與 `# nosec B501` 排除。
- 新增 BigQuery project / dataset identifier validation。
- Streamlit Cloud entry point shim 已於重新部署後移除，正式入口改為 `streamlit_dashboard/app.py`。
- Streamlit secrets 初始化從完全靜默 `except/pass` 改為 local fallback + warning。
- 對已審查且安全來源固定的 SQL f-string 加入精準 `# nosec B608` 與理由。
- 對 UI 翻譯字串 `"Password": "密碼"` 的 Bandit 誤判加入精準 `# nosec B105`。
- 新增 Asset Profiles / Web Scraping Showcase 時，已加入來源 allowlist、timeout、
  sanitize、raw data ignore 與 schema/export/loader 測試。
- 2026-07-02 修正回測 MWRR、年度報酬與 worst-year FutureWarning，並補上相關測試。
- 2026-07-05 完成完整重掃、資料刷新、導覽命名清理與文件重整。
- 2026-07-05 修正 asset profile TLS 例外、WAF 封鎖頁污染防線與 `0052.TW` split 資料污染；三檔 TLS 不穩定費率來源改為明確標記的 curated fallback，WAF fixture 覆蓋 TWSE 真實 `FOR SECURITY REASONS...CAN NOT BE ACCESSED` 封鎖頁。

修正後仍保留的風險/注意事項：

- Bandit 已無 High / Medium / Low findings。
- 部分固定來源 SQL 使用 `# nosec` 註記；這些註記均附有安全理由，避免靜態掃描誤報干擾結案報告。
- Asset profile normalize 仍依賴公開來源的 live network smoke；若遇到 WAF / 封鎖頁或來源失敗，readiness gate 會 fail closed 或沿用前次乾淨資料。
- `.env` 與 `credentials.json` 仍存在於本機，但未被 git 追蹤，且已由 `.gitignore` 排除。

以下第 1 到第 8 節保留原始掃描結果，作為修正前基準與稽核紀錄；第 9 節記錄原始發現修正後重掃結果；第 10 節記錄新增 Web Scraping Showcase 後的補充資安檢查；第 11 節記錄 2026-07-02 的修正與重掃結果；第 12 節記錄 2026-07-05 的最新完整重掃結果。

## 1. 掃描摘要

| 項目 | 結果 |
|---|---|
| Python dependency vulnerability scan | 未發現已知弱點 |
| 測試依賴 vulnerability scan | 未發現已知弱點 |
| Secret / credential 文字掃描 | 未發現已追蹤的明文 API key；本機存在 `.env` 與 `credentials.json`，但已被 `.gitignore` 排除 |
| Git tracked sensitive files | 未發現 `.env`、`credentials.json`、key、token、pem 類檔案被 git 追蹤 |
| Bandit Python SAST | 發現 5 個 High、12 個 Medium、2 個 Low |
| GitHub Actions secrets handling | 使用 GitHub Secrets 注入 GCP service account，未在 workflow 中硬編真實 secret |

整體結論：

- 目前沒有發現已被版控追蹤的明文憑證。
- Python 依賴套件未發現已知 CVE。
- 主要待修資安問題是多處 `requests.get(..., verify=False)` 關閉 TLS 憑證驗證，屬於高風險。
- SQL 字串組裝被 Bandit 標示為 medium/low-confidence 風險；部分 ticker 已有 whitelist，但 BigQuery dataset/table identifier 仍應補上格式驗證或集中封裝。

## 2. 掃描方法與指令

### 2.1 Dependency audit

```bash
python3 -m pip_audit -r streamlit_dashboard/requirements.txt
python3 -m pip_audit -r tests/requirements_test.txt
```

結果：

```text
No known vulnerabilities found
```

### 2.2 Secret 與 credential 搜尋

```bash
rg -n -i "(api[_-]?key|secret|password|token|private[_ -]?key|client_email|credentials|GCP_SA_KEY|GOOGLE_APPLICATION_CREDENTIALS)" \
  --glob '!.git/**' \
  --glob '!*.pyc' \
  --glob '!github_web/src/ppl-data.js' .
```

結果摘要：

- 搜尋結果主要是 README、程式註解、環境變數名稱與 Streamlit secrets 使用方式。
- 未發現已追蹤檔案中包含實際 API key 或 service account private key。
- 本機存在 `.env` 與 `credentials.json`，但兩者已被 `.gitignore` 忽略，不應納入版控或交付包。

### 2.3 Git tracked sensitive files

```bash
git ls-files .env credentials.json .env.example
git ls-files | rg -i "(^|/)(\\.env|credentials\\.json|.*key.*|.*secret.*|.*token.*|.*pem|.*p12|.*pfx)$" || true
git check-ignore -v .env credentials.json .DS_Store .pytest_cache || true
```

結果摘要：

- `git ls-files .env credentials.json .env.example` 只列出 `.env.example`。
- 未發現 `.env`、`credentials.json` 或 key/token 類敏感檔案被 git 追蹤。
- `.gitignore` 已排除：
  - `.env`
  - `credentials.json`
  - `.streamlit/secrets.toml`
  - `.DS_Store`
  - `looker_studio/generated/`

### 2.4 Bandit Python SAST

```bash
python3 -m bandit -r streamlit_dashboard github_web/scripts looker_studio -x '*/__pycache__/*'
```

結果摘要：

| Severity | Count |
|---|---:|
| High | 5 |
| Medium | 12 |
| Low | 2 |

## 3. 主要發現與風險評估

### Finding 1: 多處 HTTP request 關閉 TLS 憑證驗證

風險等級：High  
工具：Bandit B501 `request_with_no_cert_validation`  
狀態：待修正

位置：

- `streamlit_dashboard/app.py:387`
- `streamlit_dashboard/app.py:2267`
- `streamlit_dashboard/src/data_collection/fetch_macro.py:29`
- `streamlit_dashboard/src/data_collection/fetch_prices.py:52`
- `streamlit_dashboard/src/processing/backtest.py:35`

目前行為：

```python
requests.get(url, timeout=10, verify=False)
```

風險說明：

- `verify=False` 會停用 TLS certificate validation。
- 使用者或 CI 執行資料抓取時，若網路遭中間人攻擊，程式可能接受偽造的 HTTPS 回應。
- 本專案抓取 Yahoo Finance / FRED 等外部資料，資料若被竄改，可能影響資產價格、匯率、通膨率、回測與 FIRE 結果。

建議修正：

- 移除所有 `verify=False`，回到 `requests` 預設憑證驗證。
- 若本機或部署環境有憑證鏈問題，應修正環境 CA bundle，而不是在程式中關閉驗證。
- 可明確使用 `certifi`：

```python
import certifi
requests.get(url, timeout=10, verify=certifi.where())
```

### Finding 2: BigQuery 查詢使用字串組裝

風險等級：Medium  
工具：Bandit B608 `hardcoded_sql_expressions`  
狀態：部分已緩解，仍建議改善

代表位置：

- `streamlit_dashboard/app.py:375`
- `streamlit_dashboard/src/processing/backtest.py:67`
- `streamlit_dashboard/src/processing/fire_calculator.py:17`
- `streamlit_dashboard/src/processing/metrics.py:19`
- `github_web/scripts/export_web_data.py:91`
- `github_web/scripts/export_web_data.py:102`
- `github_web/scripts/backfill_missing_web_assets.py:32`
- `looker_studio/export_portfolio_tables.py:205`
- `looker_studio/export_portfolio_tables.py:211`
- `looker_studio/generate_bigquery_views.py:54`

風險說明：

- Bandit 會將 f-string SQL 視為可能 SQL injection。
- 本專案部分查詢已透過 `validate_tickers()` 或固定 `ASSET_POOL` 降低 ticker injection 風險。
- 但 `dataset_id`、view/table identifier 與部分腳本仍依賴環境變數或字串拼接，建議集中驗證格式。

建議修正：

- 對 `GOOGLE_CLOUD_PROJECT`、`BIGQUERY_DATASET` 加入嚴格格式驗證，例如只允許英數、底線、破折號。
- ticker 條件優先使用 BigQuery query parameters。
- 若 BigQuery table identifier 不能參數化，至少集中用 helper 驗證 identifier 後再組 SQL。
- 對已確認安全的 generated SQL 腳本，可加入註解說明資料來源固定且非使用者輸入。

### Finding 3: Streamlit Cloud entry point 使用 `exec`

風險等級：Medium  
工具：Bandit B102 `exec_used`  
位置：`dashboard/Passive_Portfolio_Lab.py:17`  
狀態：可接受但需紀錄原因

後續處理狀態：已移除。Streamlit Cloud 重新部署後已直接指定
`streamlit_dashboard/app.py` 作為正式 entry point，因此不再需要
`dashboard/Passive_Portfolio_Lab.py` shim。

原始用途：

- `dashboard/Passive_Portfolio_Lab.py` 是 Streamlit Cloud entry point shim。
- 目的在於讓 Streamlit Cloud 可從固定入口載入 `streamlit_dashboard/app.py`，避免重新部署造成 secrets 設定流失。

風險說明：

- `exec` 若執行不受信任內容會有任意程式碼執行風險。
- 此處執行的是 repo 內固定 app 檔案，不是使用者輸入，實際風險低於一般動態 exec。

建議修正：

- 若 Streamlit Cloud 設定允許，改為直接指定 `streamlit_dashboard/app.py` 作 entry point。
- 若必須保留 shim，請在檔案註解中明確說明 shim 的用途與限制。

### Finding 4: `try/except/pass` 靜默忽略例外

風險等級：Low  
工具：Bandit B110 `try_except_pass`  
位置：`streamlit_dashboard/app.py:55`  
狀態：可改善

風險說明：

- 程式在讀取 Streamlit secrets 時靜默忽略例外。
- 本意是支援 local dev 沒有 secrets.toml 的情境，但完全靜默會增加除錯難度。

建議修正：

- 將 `pass` 改成 debug log 或註解更明確的 fallback 行為。
- 避免吞掉非預期的 secrets parsing 錯誤。

### Finding 5: Bandit 誤判翻譯字串為 hardcoded password

風險等級：Low  
工具：Bandit B105 `hardcoded_password_string`  
位置：`streamlit_dashboard/app.py:72`  
狀態：誤判，可接受

說明：

- Bandit 偵測到 `"Password": "密碼"`。
- 這是 UI 翻譯字典，不是真實密碼。
- 真正的密碼來源是 `APP_PASSWORD` secret / env，不在程式碼中硬編。

## 4. Secret 與憑證管理檢查

### 4.1 本機敏感檔案

本機存在：

- `.env`
- `credentials.json`

檢查結果：

- 兩者未被 git 追蹤。
- 兩者已被 `.gitignore` 排除。

交付注意事項：

- 不要將 `.env`、`credentials.json` 放入最終交付壓縮檔。
- 若曾經誤傳到其他平台，應立即 revoke / rotate 對應憑證。
- 建議交付時只保留 `.env.example`。

### 4.2 Streamlit secrets

目前設計：

- Streamlit Cloud 使用 `st.secrets["gcp_service_account"]` 寫入暫存 credentials JSON。
- `APP_PASSWORD` 從 secrets 讀取，未硬編於 repo。

風險與建議：

- 暫存檔位於系統 temp directory，風險可接受。
- 若使用 shared runner 或多人開發機，應避免將真實 credentials 留在 repo 目錄。

### 4.3 GitHub Actions secrets

目前設計：

- Workflow 使用 `${{ secrets.GCP_SA_KEY }}` 寫入 `/tmp/gcp-sa-key.json`。
- 未在 workflow 中硬編真實 key。

建議：

- GCP service account 採最小權限原則。
- 若只需讀取 BigQuery 與部署 GitHub Pages，不應給 owner/editor 等高權限。
- 定期輪替 `GCP_SA_KEY`。

## 5. Dependency 檢查

掃描檔案：

- `streamlit_dashboard/requirements.txt`
- `tests/requirements_test.txt`

結果：

- 未發現已知漏洞。

注意：

- `requirements.txt` 多數未 pin exact version，部署時可能安裝到不同版本。
- 若要提高可重現性，可在正式交付前產出 lock file 或至少 pin 主要依賴版本。

## 6. 部署與資料管線安全性

正向發現：

- GitHub Web 是靜態站，不在 browser 端直接連 BigQuery。
- `ppl-data.js` 是 BigQuery 匯出的公開資料 snapshot，不包含 service account key。
- GitHub Actions 會在 commit 前執行 `github_web/scripts/validate_export.py`，檢查 required globals、asset count、freshness、FX rate range。
- `ppl-data.js` artifact 只保留 7 天，便於除錯但降低長期保留風險。

建議：

- 若未來加入使用者輸入 API 或後端服務，需重新評估 authentication、authorization、rate limit 與 input validation。
- 若公開 `ppl-data.js` 包含更細資料，需重新確認資料授權與公開範圍。

## 7. 修補優先順序

| Priority | 項目 | 建議處理 |
|---|---|---|
| P1 | 移除 `verify=False` | 改用預設 TLS 驗證或 `certifi.where()` |
| P2 | BigQuery identifier validation | 集中驗證 project/dataset/table identifier |
| P2 | SQL ticker query parameterization | ticker list 改用 BigQuery query parameters 或保留 whitelist 並加測試 |
| P3 | Streamlit shim `exec` | 已移除；正式 entry point 改為 `streamlit_dashboard/app.py` |
| P3 | secrets exception handling | 改成 debug log 或更窄的 exception handling |

## 8. 結論

目前專案沒有發現已知依賴漏洞，也沒有發現已被 git 追蹤的明文憑證。部署流程大致安全，GitHub Web 維持靜態輸出，service account key 透過 GitHub Secrets 管理。

最主要的交付前資安風險是 `verify=False` 關閉 TLS 憑證驗證。若要將報告狀態提升為「高風險已修復」，應優先移除該設定並重新跑 Bandit。BigQuery SQL 字串組裝則屬於中風險/低信心發現，建議以 identifier validation 與 query parameters 逐步改善。

## 9. 修正後紀錄

本節記錄 2026-06-07 依原始掃描結果完成的修正與重掃結果。原始發現仍保留於上方章節，不刪除，以便追蹤修正前後差異。

### 9.1 已修正項目

#### 修正 1: 移除 HTTP request 的 `verify=False`

原始風險：

- Bandit B501，High severity。
- 5 處 HTTP request 關閉 TLS certificate validation。

修正檔案：

- `streamlit_dashboard/app.py`
- `streamlit_dashboard/src/data_collection/fetch_macro.py`
- `streamlit_dashboard/src/data_collection/fetch_prices.py`
- `streamlit_dashboard/src/processing/backtest.py`

修正前：

```python
requests.get(url, headers=YAHOO_HEADERS, timeout=10, verify=False)
```

修正後：

```python
requests.get(url, headers=YAHOO_HEADERS, timeout=10)
```

修正說明：

- 恢復 `requests` 預設 TLS 憑證驗證。
- 外部資料來源 Yahoo Finance / FRED 的 HTTPS response 不再被程式主動略過憑證檢查。
- 移除 `fetch_prices.py` 中關於 `verify=False` 的舊註解與 `urllib3.disable_warnings()`。
- 移除 `app.py` 中不再需要的 `InsecureRequestWarning` suppression。

#### 修正 2: 新增 BigQuery identifier validation

原始風險：

- Bandit B608，Medium severity / Low confidence。
- BigQuery SQL 使用 f-string 組裝，Bandit 無法判定 project / dataset 是否可信。

修正檔案：

- `streamlit_dashboard/src/processing/utils.py`
- `streamlit_dashboard/app.py`

新增程式：

```python
_VALID_BQ_IDENTIFIER = re.compile(r"^[A-Za-z0-9_-]+$")


def validate_bq_identifier(value: str, name: str) -> str:
    """Validate a BigQuery project or dataset identifier before SQL assembly."""
    if not value or not _VALID_BQ_IDENTIFIER.fullmatch(value):
        raise ValueError(f"Invalid BigQuery {name}: {value!r}")
    return value
```

修正後：

```python
def get_bq_config() -> tuple[str, str]:
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    dataset_id = os.getenv("BIGQUERY_DATASET")
    if not project_id or not dataset_id:
        raise ValueError("Missing GOOGLE_CLOUD_PROJECT or BIGQUERY_DATASET in .env")
    return (
        validate_bq_identifier(project_id, "project id"),
        validate_bq_identifier(dataset_id, "dataset id"),
    )
```

修正說明：

- `GOOGLE_CLOUD_PROJECT` 與 `BIGQUERY_DATASET` 現在只允許英數字、底線、破折號。
- `streamlit_dashboard/app.py` 的 `load_metrics()` 改用共用 `get_bq_config()`，避免自行讀 env 繞過驗證。
- ticker list 仍維持 `validate_tickers()` whitelist 防線。

#### 修正 3: Streamlit Cloud shim 移除，改用正式 entry point

原始風險：

- Bandit B102，Medium severity。
- `dashboard/Passive_Portfolio_Lab.py` 使用 `exec()`。

修正檔案：

- `dashboard/Passive_Portfolio_Lab.py` 已刪除
- Streamlit Cloud entry point 已改為 `streamlit_dashboard/app.py`

修正後：

```text
Streamlit Cloud entry point:
streamlit_dashboard/app.py
```

修正說明：

- 重新部署 Streamlit Cloud app，直接使用正式主程式作為入口。
- 移除 shim 後，`exec()` 不再存在於部署入口路徑。
- 專案結構更乾淨，也不再需要針對 shim 保留 `# nosec B102`。

#### 修正 4: Streamlit secrets 初始化不再完全靜默

原始風險：

- Bandit B110，Low severity。
- `except Exception: pass` 會吞掉非預期 secrets 初始化錯誤。

修正檔案：

- `streamlit_dashboard/app.py`

修正前：

```python
except Exception:
    # Local dev: no secrets.toml, skip silently.
    pass
```

修正後：

```python
except FileNotFoundError:
    # Local dev: no secrets.toml; production secrets live in Streamlit Cloud.
    pass
except Exception as exc:
    print(f"Warning: Streamlit secrets could not be initialized: {exc}")
```

修正說明：

- local dev 缺少 secrets 仍可 fallback。
- 非預期 secrets 錯誤會留下 warning，方便除錯。

### 9.2 修正後掃描指令與結果

#### Bandit SAST

指令：

```bash
python3 -m bandit -r streamlit_dashboard github_web/scripts looker_studio -x '*/__pycache__/*'
```

修正後結果：

| Severity | Count |
|---|---:|
| High | 0 |
| Medium | 0 |
| Low | 0 |

說明：

- 原始 5 個 High 全部消除。
- `exec()` shim 已移除，Bandit 不再列為 unresolved issue。
- `try/except/pass` 已消除。
- 原始剩餘的 11 個 Bandit B608 SQL f-string 提示已逐項處理：
  - BigQuery project / dataset 先經 `validate_bq_identifier()` 驗證。
  - ticker list 來自固定 `ASSET_POOL`、ticker whitelist 或 Looker 固定 portfolio presets。
  - 對固定 generated SQL 與已驗證查詢加上精準 `# nosec B608`，避免靜態掃描誤報。
- 原始剩餘的 1 個 Bandit B105 `"Password": "密碼"` 已標註為 UI 翻譯字串誤判。
- Bandit 最終重掃結果為 `No issues identified`。
- 本次掃描中 Bandit 仍會列出 `nosec encountered` warnings，代表掃描器看見已審查的排除註記；這些不是 findings。

#### `verify=False` 搜尋

指令：

```bash
rg -n "verify=False|InsecureRequestWarning|disable_warnings|urllib3|TLS_VERIFY_EXCEPTIONS|nosec B501" streamlit_dashboard github_web looker_studio -g '!*.pyc'
```

結果：

```text
No matches
```

#### Dependency audit

指令：

```bash
python3 -m pip_audit -r streamlit_dashboard/requirements.txt
python3 -m pip_audit -r tests/requirements_test.txt
```

結果：

```text
No known vulnerabilities found
No known vulnerabilities found
```

#### Regression tests

指令：

```bash
python3 -m pytest tests/processing/test_backtest.py tests/processing/test_metrics.py tests/export/test_export_web_data.py
```

結果：

```text
68 passed
```

警告說明：

- 無 pandas `Series.idxmin` FutureWarning。
- 核心金融計算與 web export schema 測試全部通過。

### 9.3 修正後結論

本次修正後，原始報告中最重要的高風險問題已處理完成：

- `verify=False`、asset profile TLS exception allowlist、`urllib3.disable_warnings()` 與 `# nosec B501` 已全部移除。
- Bandit High 從 5 降為 0。
- Bandit Medium 從 12 降為 0。
- Bandit Low 從 2 降為 0。
- 原始 B608 / B105 剩餘事項已用精準 `# nosec` 與理由處理完畢。
- Dependency audit 仍未發現已知 CVE。
- 未發現敏感檔案被 git 追蹤。
- 核心金融計算與 web export schema 相關測試通過。

剩餘事項：

- 無 Bandit High / Medium / Low findings。
- 後續若新增 BigQuery 查詢，仍應優先使用 `get_bq_config()` / `validate_bq_identifier()`，並確保 ticker 來源經 whitelist 或固定資料集約束。

## 10. Asset Profiles / Web Scraping Showcase 補充資安紀錄

本節記錄 2026-06-08 新增 Asset Profiles / Web Scraping Showcase 後的資安設計與重掃結果。原始掃描與第 9 節修正紀錄保留不刪除。

### 10.1 新增功能範圍

新增檔案與資料線：

- `data/asset_profiles/asset_profiles.json`
- `github_web/src/ppl-asset-profiles.js`
- `github_web/scripts/asset_intelligence/sources.py`
- `github_web/scripts/asset_intelligence/schema.py`
- `github_web/scripts/asset_intelligence/fetch_etf_profiles.py`
- `github_web/scripts/asset_intelligence/normalize_profiles.py`
- `github_web/scripts/asset_intelligence/export_asset_profiles.py`
- `streamlit_dashboard/src/asset_profiles/loader.py`
- `tests/export/test_asset_profiles_schema.py`
- `tests/export/test_asset_profiles_export.py`
- `tests/streamlit/test_asset_profiles_loader.py`

展示面：

- GitHub Web「組合配置」資產詳情。
- Streamlit Dashboard「投資組合組成」treemap 資產詳情。
- Landing page 功能亮點。

### 10.2 主要風險與防護

| 風險 | 防護方式 |
|---|---|
| SSRF / 任意 URL 抓取 | `sources.py` 使用固定 allowlist，只允許 TWSE、官方 ETF 發行商頁與 crypto 官方公開頁 |
| XSS / HTML 注入 | `schema.py` 的 `sanitize_text()` 會移除 HTML tag 與 script-like 內容；測試確認文字欄位不含 `<` 或 `script` |
| 行情 API 誤用 | Asset profile pipeline 使用 `requests.get(sourceUrl)` 抓公開 HTML 頁面並用 HTML parser 擷取摘要，不使用 Yahoo Finance REST API、CoinMarketCap API 或其他行情 API |
| 前端白屏 | GitHub Web 與 Streamlit loader 都有 fallback；缺資料時顯示「目前尚無補充資訊」 |
| request hang | fetcher 使用 `REQUEST_TIMEOUT_SECONDS = 12` |
| secrets 外洩 | 此功能不需要 API key；`.env`、`credentials.json`、Streamlit secrets 仍由 `.gitignore` 排除 |
| raw 爬蟲資料誤提交 | `.gitignore` 忽略 `data/asset_profiles/raw/**`，只保留 `.gitkeep` |
| schema drift | 新增 schema / export / loader 測試，並把 profile export 加入 `validate_export.py` |
| ETF 費用率退回佔位或模糊文字 | 測試與 `validate_export.py` 會檢查 29 檔 ETF 不得輸出 `See source profile`、`約` 或 `+`，且 8 檔 crypto 不套用 ETF 費用率欄位 |
| 台股 ETF 費率來源不透明 | asset profile schema 新增 `managementFee`、`custodianFee`、`expenseRatioFormula`、`expenseRatioSourceUrl`，並要求台股 ETF 以 `managementFee + custodianFee` 計算 |
| TLS 例外與封鎖頁污染 | 2026-07-05 已移除 asset profile TLS 例外，三檔不穩定費率來源改為 curated fallback，WAF / 封鎖頁污染由 readiness gate fail closed，且以 TWSE 真實封鎖文字做 fixture |

### 10.3 重掃指令與結果

#### Bandit SAST

指令：

```bash
python3 -m bandit -r streamlit_dashboard github_web/scripts looker_studio -x '*/__pycache__/*'
```

結果：

```text
No issues identified.
```

#### Regression tests

指令：

```bash
python3 -m pytest tests/
```

結果：

```text
150 passed
```

警告說明：

- 無 pandas `Series.idxmin` FutureWarning。
- 全測試套件通過。

#### Export validation

指令：

```bash
python3 github_web/scripts/validate_export.py
```

結果：

```text
Export validation passed (37 assets, FX=31.92)
```

### 10.4 補充結論

新增 Web Scraping Showcase 後，專案仍維持：

- Bandit High / Medium / Low findings：0。
- 無已追蹤的 `.env`、`credentials.json` 或 API key。
- 資產 profile 來源受 allowlist 約束。
- 前端只讀靜態正規化資料，不在使用者瀏覽時即時爬取。

## 11. 2026-07-02 最終修正與重掃紀錄

### 11.1 修正範圍

- Backtest 年化報酬改用 MWRR，避免 monthly contribution 情境下以期末價值除以累計投入造成誤導。
- Backtest 年度報酬改為扣除投入影響後計算。
- Python backtest DCA 日期改為該月第一個可用價格日期，避免月初非交易日跳過投入。
- `metrics.py` worst-year 計算先排除 NA / inf，修正 pandas `Series.idxmin` FutureWarning。
- GitHub Web 操作導覽對 `localStorage` 加上 try/catch，storage 被封鎖時仍可關閉。
- `.env.example` 補齊選用設定，`outputs/` 加入 `.gitignore`。

### 11.2 重掃結果

```text
python3 -m pytest tests/processing/test_backtest.py tests/processing/test_metrics.py tests/export/test_export_web_data.py
68 passed

python3 -m pytest tests/
150 passed
```

目前未再出現 pandas `Series.idxmin` FutureWarning。
- GitHub Web、Streamlit Dashboard 與 tests 已共用同一份資料契約。

## 12. 2026-07-05 完整審查、保守清理與重掃紀錄

### 12.1 審查範圍

本輪以目前工作樹為準，不回復已完成的 landing page、進化實驗室操作導覽與經典實驗室新手導覽調整。審查範圍包含：

- Python 資安掃描、依賴弱點掃描、secret / credential 搜尋與 git tracked sensitive files 檢查。
- GitHub Actions secret 使用方式、BigQuery identifier validation、ticker whitelist、前端 HTML injection 風險、asset profile 爬蟲來源 allowlist、TLS 驗證與 WAF fail-closed 防線。
- GitHub Web 導覽程式碼中的舊彈窗命名、未使用 wrapper id、未使用 component prop 與 localStorage 相容性。

### 12.2 最新重掃結果

```text
python3 -m pytest tests/
150 passed

python3 -m bandit -r streamlit_dashboard github_web/scripts looker_studio -x '*/__pycache__/*'
No issues identified.

python3 -m pip_audit -r streamlit_dashboard/requirements.txt
No known vulnerabilities found

python3 -m pip_audit -r tests/requirements_test.txt
No known vulnerabilities found

python3 github_web/scripts/export_web_data.py
Updated github_web/src/ppl-data.js at 2026-07-05 08:21 UTC

python3 github_web/scripts/validate_export.py
Export validation passed (37 assets, FX=31.92)
```

Secret / credential 搜尋使用下列模式：

```bash
rg -n -i "(api[_-]?key|secret|password|token|private[_ -]?key|client_email|credentials|GCP_SA_KEY|GOOGLE_APPLICATION_CREDENTIALS|BEGIN PRIVATE KEY)" \
  --glob '!.git/**' \
  --glob '!*.pyc' \
  --glob '!github_web/src/ppl-data.js' \
  --glob '!looker_studio/generated/**' .
```

結果摘要：

- 搜尋結果為 README、`.env.example`、程式註解、環境變數名稱、GitHub Actions secret 名稱、UI 翻譯字串與 crypto 類別文字。
- 未發現已追蹤檔案中包含實際 API key、service account private key 或 credential JSON 內容。
- `git ls-files | rg "(__pycache__|\\.pyc$|\\.DS_Store$|^\\.env$|credentials\\.json$)" || true` 無輸出，代表沒有上述本機產物或敏感檔案被 git 追蹤。

### 12.3 高風險模式人工審查

掃描 `verify=False`、`exec(`、`eval(`、`shell=True`、`subprocess`、`innerHTML`、`dangerouslySetInnerHTML`、`localStorage` 與 `# nosec` 後，人工結論如下：

- 未發現未審查的 `exec(`、`eval(`、`shell=True` 或 `subprocess`。
- GitHub Actions 透過 `${{ secrets.GCP_SA_KEY }}` 寫入暫存檔，workflow 內沒有硬編真實 secret。
- BigQuery project / dataset identifier 仍由 helper 驗證；ticker 來源受固定 `ASSET_POOL`、portfolio presets 或 whitelist 約束。
- GitHub Web 的 `dangerouslySetInnerHTML` 僅用於靜態信任翻譯字串；Streamlit 的 HTML 片段使用 escaped / sanitized profile data。
- `localStorage` 只用於操作導覽 seen state，並以 try/catch 包住，storage 被封鎖時不影響核心功能。
- Asset Profiles fetcher 不再保留 TLS 驗證例外；`www.pocket.tw` 已從 allowlist 移除，00679B.TWO、00751B.TWO、00955.TWO 的費率改以明確標記 curated fallback 保留來源出處。
- WAF / 封鎖頁污染會被 fetch 層與 readiness gate 阻擋；有前次乾淨資料時 reuse，無前次資料時 fail closed，避免污染摘要上線。TWSE `FOR SECURITY REASONS...CAN NOT BE ACCESSED` 封鎖頁已納入 fixture。
- `# nosec` 目前集中於已審查的 BigQuery SQL identifier 組裝與固定翻譯字串誤判；不再用於 TLS 驗證關閉。Bandit 重掃仍為 0 findings。

### 12.4 最新結論

截至 2026-07-05，本專案未發現已追蹤明文憑證、未發現已知 Python 依賴弱點，Bandit High / Medium / Low findings 均為 0。核心測試與 web export validation 皆通過；`ppl-data.js` 已使用本機 BigQuery credentials 刷新並通過 freshness gate、asset profile readiness 與類別分級 price cliff gate。

後續若新增外部資料來源、前端 HTML 插入點、GitHub Actions secret、BigQuery table/view 或使用者輸入 API，應重新跑本節列出的檢查並更新本報告。
