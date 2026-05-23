# Monitoring

Last updated: 2026-05-23

This document describes the current observability posture of the daily data
refresh pipeline and the three delivery surfaces, identifies gaps, and
recommends improvements.

---

## 1. What Runs Automatically

The GitHub Actions workflow `.github/workflows/update-and-deploy.yml` runs:

| Trigger | Schedule / Condition |
|---|---|
| Push to `main` | On every merge / direct push |
| Scheduled | Daily at `17:00 UTC` (01:00 Asia/Taipei) |
| Manual | `workflow_dispatch` in GitHub UI |

### Pipeline steps

1. Checkout repository
2. Install Python 3.11 + dependencies
3. Authenticate to Google Cloud via `GCP_SA_KEY` secret
4. Run `export_web_data.py` → writes `github_web/src/ppl-data.js`
5. Commit and push `ppl-data.js` if changed
6. Deploy `github_web/` to GitHub Pages

---

## 2. Current Observability

### What is observable today

| Signal | Where to find it |
|---|---|
| Workflow pass / fail | GitHub Actions tab → `update-and-deploy.yml` runs |
| Last successful run time | GitHub Actions run list |
| Data commit message | `git log --oneline github_web/src/ppl-data.js` |
| Pages deployment status | GitHub Pages settings tab |
| Export timestamp | `PPL_HISTORY_UPDATED_AT` string inside `ppl-data.js` |

### What is NOT currently observable

| Gap | Impact |
|---|---|
| No data freshness check | A workflow that runs but produces stale data (e.g., BigQuery query succeeds but returns old rows) will not fail |
| No asset count validation | If `asset_metrics` returns fewer rows than expected, the export silently drops assets |
| No price history date range check | If `raw_prices` stops updating, `PPL_PRICE_HISTORY` will contain old data with no alert |
| No export summary artifact | There is no downloadable log of what was exported |
| No failure notification | If the workflow fails at 01:00 Taipei time, no one is alerted until they manually check |
| No Streamlit app health check | Dashboard availability is only visible to users who visit the URL |
| No Looker Studio freshness indicator | Looker data depends on manually re-running `export_portfolio_tables.py` |

---

## 3. Recommended Improvements

### 3.1 Post-export validation script

Add a lightweight validation step after `export_web_data.py` completes.

**Suggested file:** `github_web/scripts/validate_export.py`

```python
#!/usr/bin/env python3
"""
Validate that ppl-data.js was exported correctly.
Fails with exit code 1 if any check fails.
"""
import sys
import re
from pathlib import Path
from datetime import datetime, timezone

OUTPUT = Path(__file__).resolve().parents[1] / "src" / "ppl-data.js"

EXPECTED_MIN_ASSETS = 30        # alert if fewer than 30 assets exported
EXPECTED_EXACT_ASSETS = 37      # currently 37 in ASSET_POOL
MAX_STALENESS_HOURS = 25        # allow 1 hour of drift past the 24-hour schedule

errors = []
content = OUTPUT.read_text(encoding="utf-8")

# 1. Required globals present
for var in ["PPL_ASSETS", "PPL_PRICE_HISTORY", "PPL_FX_RATE", "PPL_HISTORY_UPDATED_AT"]:
    if f"const {var}" not in content:
        errors.append(f"MISSING: const {var} not found in ppl-data.js")

# 2. Asset count
asset_lines = [l for l in content.split("\n") if l.strip().startswith("{ ticker:")]
if len(asset_lines) < EXPECTED_MIN_ASSETS:
    errors.append(f"ASSET COUNT: only {len(asset_lines)} assets (expected >= {EXPECTED_MIN_ASSETS})")

# 3. Freshness
match = re.search(r'PPL_HISTORY_UPDATED_AT = "(\d{4}-\d{2}-\d{2} \d{2}:\d{2} UTC)"', content)
if match:
    updated_at = datetime.strptime(match.group(1), "%Y-%m-%d %H:%M UTC").replace(tzinfo=timezone.utc)
    age_hours = (datetime.now(timezone.utc) - updated_at).total_seconds() / 3600
    if age_hours > MAX_STALENESS_HOURS:
        errors.append(f"STALE: data is {age_hours:.1f} hours old (limit {MAX_STALENESS_HOURS}h)")
else:
    errors.append("FRESHNESS: PPL_HISTORY_UPDATED_AT timestamp not parseable")

# 4. FX rate plausibility
match = re.search(r"const PPL_FX_RATE = ([\d.]+);", content)
if match:
    fx = float(match.group(1))
    if not (20.0 <= fx <= 50.0):
        errors.append(f"FX RATE: {fx} outside plausible 20–50 TWD/USD range")
else:
    errors.append("FX RATE: PPL_FX_RATE not found or not parseable")

if errors:
    print("❌ Export validation FAILED:")
    for e in errors:
        print(f"  • {e}")
    sys.exit(1)
else:
    print(f"✅ Export validation passed ({len(asset_lines)} assets, FX={fx:.2f})")
```

### 3.2 Workflow summary block

Add a GitHub Actions job summary at the end of the workflow:

```yaml
- name: Export summary
  run: |
    echo "## Export Summary" >> $GITHUB_STEP_SUMMARY
    echo "| Item | Value |" >> $GITHUB_STEP_SUMMARY
    echo "|---|---|" >> $GITHUB_STEP_SUMMARY
    UPDATED_AT=$(grep -o 'PPL_HISTORY_UPDATED_AT = "[^"]*"' github_web/src/ppl-data.js \
      | cut -d'"' -f2)
    ASSET_COUNT=$(grep -c '{ ticker:' github_web/src/ppl-data.js || echo "?")
    FX=$(grep -o 'PPL_FX_RATE = [0-9.]*' github_web/src/ppl-data.js | cut -d' ' -f3)
    echo "| Updated at | $UPDATED_AT |" >> $GITHUB_STEP_SUMMARY
    echo "| Assets exported | $ASSET_COUNT |" >> $GITHUB_STEP_SUMMARY
    echo "| FX rate (TWD/USD) | $FX |" >> $GITHUB_STEP_SUMMARY
```

### 3.3 Export artifact upload

Upload `ppl-data.js` as a workflow artifact for 7 days:

```yaml
- name: Upload export artifact
  uses: actions/upload-artifact@v4
  with:
    name: ppl-data-${{ github.run_id }}
    path: github_web/src/ppl-data.js
    retention-days: 7
```

### 3.4 Failure notification

GitHub does not send email notifications for workflow failures by default unless
the user configures notification settings. Options:

**Option A — GitHub email notifications (no code change needed)**  
In the GitHub repository → Settings → Notifications, enable "Failed workflows"
email notifications for the repository owner.

**Option B — GitHub Issue on failure (automated)**  
Add a final step that only runs on failure:

```yaml
- name: Open issue on failure
  if: failure()
  uses: actions/github-script@v7
  with:
    script: |
      github.rest.issues.create({
        owner: context.repo.owner,
        repo: context.repo.repo,
        title: `[Auto] Daily data refresh failed — ${new Date().toISOString().slice(0,10)}`,
        body: `The \`update-and-deploy\` workflow failed at ${new Date().toISOString()}.\n\n` +
              `Run: https://github.com/${context.repo.owner}/${context.repo.repo}/actions/runs/${context.runId}`,
        labels: ['monitoring']
      })
```

**Option C — Slack webhook (requires a destination)**  
Only implement if a Slack workspace and channel are provided. Requires a
`SLACK_WEBHOOK_URL` secret in GitHub repository settings.

---

## 4. Looker Studio Monitoring

Looker Studio reads directly from BigQuery views and portfolio tables. It has
no automatic refresh outside of the browser session.

| Risk | Mitigation |
|---|---|
| `looker_portfolio_*` tables go stale | Re-run `export_portfolio_tables.py` after each major data update. Add this to a monthly or quarterly schedule. |
| BigQuery query costs spike | Monitor BigQuery costs in GCP Console → Billing. Consider caching the Looker data source or setting a per-query byte limit. |
| View definition becomes stale | Re-run `bigquery_views.sql` in BigQuery after any schema change to `raw_prices` or `asset_metrics`. |

---

## 5. Streamlit Dashboard Monitoring

The Streamlit Cloud platform provides basic uptime monitoring. For this project:

| Signal | How to check |
|---|---|
| App is live | Visit `https://passive-portfolio-lab-new.streamlit.app/` |
| App is restarting | Streamlit Cloud dashboard shows app status |
| BigQuery connectivity | App shows an error banner when BQ credentials are missing or expired |

The Streamlit Cloud free tier will hibernate the app after prolonged inactivity.
Users may see a "waking up" spinner on first load.

---

## 6. Data Freshness Indicators

### What users can see today

- GitHub Web footer: `PPL_HISTORY_UPDATED_AT` shows the last export timestamp
  (e.g., `2026-05-23 17:03 UTC`).

### What users cannot see today

- Whether the underlying BigQuery price data itself is current.
- Whether the Looker Studio portfolio tables have been regenerated recently.

**Recommendation:** Add a max price date check to `validate_export.py`:

```python
# 5. Price history recency — extract max date from PPL_PRICE_HISTORY JSON
import json, re
match = re.search(r"const PPL_PRICE_HISTORY = (\{.*?\});", content, re.DOTALL)
if match:
    history = json.loads(match.group(1))
    all_dates = [row[0] for rows in history.values() for row in rows]
    if all_dates:
        max_date = max(all_dates)
        max_dt = datetime.strptime(max_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        price_age_days = (datetime.now(timezone.utc) - max_dt).days
        if price_age_days > 5:
            errors.append(f"PRICE DATA: latest price date is {max_date} ({price_age_days} days ago)")
```

---

## 7. Current vs Target Observability

| Capability | Current | Target |
|---|---|---|
| Workflow pass/fail | ✅ GitHub UI | ✅ Keep |
| Export timestamp visible in app | ✅ Footer | ✅ Keep |
| Post-export data validation | ❌ None | ✅ Add `validate_export.py` |
| Workflow summary in GitHub UI | ❌ None | ✅ Add summary block |
| Export artifact for debugging | ❌ None | ✅ Upload as artifact |
| Failure notification | ❌ None | ✅ GitHub email settings (no code) or Issue bot |
| Price data recency check | ❌ None | ✅ Add to `validate_export.py` |
| Asset count validation | ❌ None | ✅ Add to `validate_export.py` |
| Looker freshness indicator | ❌ None | Acceptable gap — manual re-run |
| Streamlit uptime alerting | Streamlit Cloud native | Acceptable — Cloud handles this |

---

## 8. Priority Implementation Order

1. **Enable GitHub email notifications** for workflow failures (zero code
   change, immediate value).
2. **Add `validate_export.py`** to catch silent data quality failures.
3. **Add workflow summary block** for a human-readable export log in the
   GitHub Actions UI.
4. **Add artifact upload** to enable debugging of past exports.
5. **Failure notification issue bot** (optional, only if email is insufficient).
