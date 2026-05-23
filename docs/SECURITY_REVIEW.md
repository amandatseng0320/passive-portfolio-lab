# Security Review

Last updated: 2026-05-23  
Reviewer: automated static analysis + manual code inspection

This document records the evidence-based security posture of Passive Portfolio
Lab. Each finding includes the evidence observed, a severity rating, and the
recommended or current mitigation.

Severity scale: **Critical** (exploitable, data loss risk) · **High** (exploitable under realistic conditions) · **Medium** (mitigated but suboptimal) · **Low** (best-practice gap with minimal real risk) · **Info** (observation, no action required)

---

## 1. Secret Handling

### 1.1 `credentials.json` in the repository root — Low

**Evidence:** A live Google Cloud service account key (`type: service_account`,
project `passive-portfolio-lab`) exists at `credentials.json` in the working
tree.

**Status:** The file is correctly listed in `.gitignore` and has never been
committed to the git history (verified via `git log -- credentials.json`
returning no output). It is local-only.

**Residual risk:** If the working tree is accidentally archived, shared, or
synced to cloud storage without respecting `.gitignore`, the key would be
exposed.

**Recommendation:**
- Consider using Google Cloud Application Default Credentials (ADC) or
  Workload Identity Federation instead of a key file for local development.
- Document in `README.md` that `credentials.json` must never be committed.

### 1.2 `.env` file contains real API keys — Low

**Evidence:** `.env` exists in the repo root with real values for
`GOOGLE_CLOUD_PROJECT`, `BIGQUERY_DATASET`, `GOOGLE_APPLICATION_CREDENTIALS`,
and `GEMINI_API_KEY`.

**Status:** The file is in `.gitignore` and has not been committed.

**Recommendation:** Rotate keys if the file is ever accidentally shared. Ensure
CI/CD never copies `.env` to artifacts or logs.

### 1.3 GitHub Actions: GCP_SA_KEY written to disk — Info

**Evidence:** `.github/workflows/update-and-deploy.yml` line 43:
```yaml
run: echo '${{ secrets.GCP_SA_KEY }}' > /tmp/gcp-sa-key.json
```

**Assessment:** Writing to `/tmp` on the ephemeral runner is the standard
pattern for GitHub Actions service account authentication. The runner is
destroyed after the job. The key is not uploaded as an artifact.

**Observation:** The `echo '...'` approach is correct (single quotes prevent
variable expansion). However, if the secret itself contained a single quote,
the echo would malform the JSON. GitHub's `${{ secrets.X }}` with `echo '...'`
is safe for well-formed JSON service account keys.

**No action required**, but consider using `google-github-actions/auth` with
Workload Identity Federation to eliminate the key file entirely.

---

## 2. GitHub Actions Workflow Permissions

**Evidence:** `.github/workflows/update-and-deploy.yml`:
```yaml
permissions:
  contents: write   # commits updated ppl-data.js
  pages: write
  id-token: write
```

**Assessment:**
- `contents: write` is the minimum needed to push the daily `ppl-data.js`
  commit. It grants write access to the entire repository.
- `pages: write` and `id-token: write` are required for GitHub Pages
  deployment.
- These permissions apply to the single workflow job. There is no unnecessary
  separation between the data-export step and the deploy step, which means
  the deploy step also runs with `contents: write`.

**Recommendation (Low):** Split the workflow into two jobs — one for data
export (needs `contents: write`) and one for deployment (needs only
`pages: write` + `id-token: write`). This reduces the blast radius if
the deploy step is compromised.

---

## 3. SQL Injection Risk in Ticker Interpolation

**Evidence:** Two modules use f-string interpolation for ticker values in
BigQuery SQL without escaping:

```python
# streamlit_dashboard/src/processing/backtest.py line 70
tickers_sql = ", ".join(f"'{t}'" for t in tickers)

# streamlit_dashboard/src/processing/fire_calculator.py line 20
tickers_sql = ", ".join(f"'{t}'" for t in tickers)
```

The `github_web/scripts/export_web_data.py` and
`looker_studio/export_portfolio_tables.py` use the safer `sql_string()` helper
that escapes backslashes and single quotes.

**Mitigating factors:**
- Tickers originate from the static `ASSET_POOL` list in `screening.py`, which
  contains only well-formed tickers (e.g., `0050.TW`, `BTC-USD`). No ticker
  in `ASSET_POOL` contains a single quote or SQL metacharacter.
- The Streamlit dashboard selects tickers from a predefined UI widget backed
  by `ASSET_POOL`. Arbitrary string injection through the UI is not possible
  in the normal flow.
- The Streamlit app is optionally protected by `APP_PASSWORD`.

**Severity: Medium** — not exploitable in the current UI flow, but the code
does not enforce a whitelist before building the SQL. If a future code path
passes caller-supplied tickers to these functions, it would become a real
injection surface.

**Recommendation:** Add a whitelist check before building the SQL query:
```python
valid_tickers = set(get_all_tickers())
tickers = [t for t in tickers if t in valid_tickers]
```
Or use the `sql_string()` helper from `export_web_data.py` consistently.

---

## 4. SSL Certificate Verification Disabled

**Evidence:** `verify=False` appears in five locations across four modules:
```
streamlit_dashboard/app.py (lines 329, 2232)
streamlit_dashboard/src/data_collection/fetch_prices.py (line 53)
streamlit_dashboard/src/processing/backtest.py (line 37)
streamlit_dashboard/src/data_collection/fetch_macro.py (line 28)
```

**Rationale documented in code:** `fetch_prices.py` includes a comment that
Yahoo Finance's CDN has intermittent SSL chain issues with certain Python
`requests` builds; `verify=False` was a deliberate choice to prioritize
reliability of data fetching.

**Assessment:** In a network-proxied or corporate environment, disabling SSL
verification exposes the app to man-in-the-middle attacks that could inject
crafted price data. In a typical cloud or home network, the risk is low.

**Severity: Medium** — accepted risk with documented rationale, but worth
revisiting.

**Recommendation:** Try `certifi` bundle upgrade or per-host certificate pinning
as an alternative. If `verify=False` is retained, add a
`urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)`
suppression to prevent log noise (note: `fetch_prices.py` already does this;
the other modules do not).

---

## 5. Streamlit Password Gate

**Evidence:** `streamlit_dashboard/app.py` lines 51–52 and 212–225:
```python
_app_password = st.secrets.get("APP_PASSWORD")
# ...
if _app_password:
    # password gate logic
```

**Assessment:**
- Password gate is optional. If `APP_PASSWORD` is not set in Streamlit secrets,
  the app is fully public with no authentication.
- The password comparison uses a simple equality check, not a constant-time
  comparison. Timing attacks are not practical via the Streamlit UI, but
  this is technically a best-practice gap.
- Passwords are sent in plain text over HTTPS (Streamlit Cloud enforces HTTPS).

**Severity: Low** — the password gate is a convenience barrier, not a
security control. It does not replace BigQuery IAM or GCP project-level access
control.

**Recommendation:**
- If the app stores or displays sensitive personal financial data, consider a
  proper authentication layer (e.g., Google OAuth via `streamlit-authenticator`).
- Document clearly that the password gate is optional and the app is designed to
  be public.

---

## 6. Public Static Data Exposure (GitHub Web)

**Evidence:** `github_web/src/ppl-data.js` is a public file on GitHub Pages.
It contains asset metrics and historical price data for all 37 assets in the
universe.

**Assessment:** The data contains no user PII and no sensitive business data.
It consists of:
- ETF tickers and public metrics (CAGR, volatility, max drawdown, Sharpe)
- Historical daily close prices (publicly available from Yahoo Finance)
- A TWD/USD snapshot rate

**Severity: Info** — the data is by design public. No action required.

---

## 7. No User PII Collected

**Evidence:** Code review of all three delivery surfaces shows no user
data collection, authentication tokens stored client-side, cookies, or
analytics beyond Streamlit Cloud's built-in usage metrics.

**Assessment:** The project does not collect, store, or transmit any
Personally Identifiable Information.

**Severity: Info** — no action required.

---

## 8. BigQuery Service Account Scope

**Evidence:** The service account `passive-portfolio-sa@passive-portfolio-lab.iam.gserviceaccount.com`
is used for both the Streamlit dashboard and the GitHub Actions workflow.

**Recommended minimum IAM roles:**
- `roles/bigquery.dataViewer` — for Streamlit reads
- `roles/bigquery.dataEditor` — for the pipeline's `to_gbq` writes (metrics upload, portfolio table creation)
- `roles/bigquery.jobUser` — to run queries

**Current state:** Unable to verify the actual IAM bindings without connecting
to GCP. Ensure the service account does not have `roles/editor` or
`roles/owner` which would be overly broad.

**Severity: Medium (unverified)** — verify that the service account does not
have project-level editor or owner permissions.

---

## 9. Third-Party API Data Trust

Three external APIs are used: Yahoo Finance REST, FRED, and Google Gemini.

| API | Data type | Trust level | Risk |
|---|---|---|---|
| Yahoo Finance v8 REST | Price data, FX rates | Unauthenticated, public endpoint | Crafted responses could inject bad prices if a MITM attack were possible (combined with `verify=False`) |
| FRED (St. Louis Fed) | CPI/inflation rate | API key required | Low — FRED is a government data source |
| Gemini 2.5 Flash | AI-generated text | API key required | Medium — model outputs should not be treated as financial advice; the app correctly labels them as illustrative |

**The `verify=False` issue (Section 4) is the primary risk amplifier for Yahoo
Finance data.** A crafted FX rate injection would affect backtest portfolio
values.

**Mitigation already in place:** `backtest.py` already filters implausible FX
rates (accepts only values in the 20–50 TWD/USD range) as a second line of
defence.

---

## 10. Dependency Vulnerabilities

Key packages observed in the test environment (2026-05-23):

| Package | Version | Known CVE |
|---|---|---|
| requests | 2.34.2 | None in current stable |
| urllib3 | 2.7.0 | None in current stable |
| certifi | 2026.5.20 | Current |
| cryptography | 48.0.0 | Current |

**Recommendation:** Run `pip list --outdated` before final delivery and update
any packages with known CVEs. Consider adding a `requirements.txt` version pin
freeze for the Streamlit Cloud deployment.

---

## 11. Summary

| # | Finding | Severity | Status |
|---|---|---|---|
| 1.1 | `credentials.json` in working tree (gitignored) | Low | Accepted — gitignored |
| 1.2 | `.env` with real keys (gitignored) | Low | Accepted — gitignored |
| 1.3 | SA key written to `/tmp` in CI | Info | Accepted — standard pattern |
| 2 | Broad workflow permissions | Low | Open — split jobs recommended |
| 3 | Ticker SQL interpolation without whitelist | Medium | Open — add whitelist validation |
| 4 | `verify=False` for all Yahoo Finance calls | Medium | Accepted with documented rationale |
| 5 | Streamlit password gate is optional | Low | Accepted — app is designed to be public |
| 6 | Public ppl-data.js | Info | By design |
| 7 | No PII collected | Info | No action |
| 8 | SA scope unverified | Medium | Open — verify IAM roles |
| 9 | Third-party API data trust | Medium | Partially mitigated (FX range filter) |
| 10 | Dependencies | Low | Verify before final delivery |

**No Critical findings.** The two Open/Medium items (ticker SQL injection and
SA scope) should be addressed before final submission.
