# GitHub Web

Static GitHub Pages version of Passive Portfolio Lab.

## Entry Point

```text
github_web/index.html
```

The app is static. It does not query BigQuery in the browser. Instead, GitHub Actions runs:

```bash
python github_web/scripts/export_web_data.py
```

That script exports BigQuery data into:

```text
github_web/src/ppl-data.js
```

## Data Export

`ppl-data.js` contains:

- `PPL_ASSETS`: asset metrics and metadata
- `PPL_PRICE_HISTORY`: daily TWD price history for true static historical backtests
- `PPL_FX_RATE`: latest TWD/USD display conversion rate
- `PPL_HISTORY_UPDATED_AT`: export timestamp

## Deployment

The GitHub Actions workflow at `.github/workflows/update-and-deploy.yml`:

1. Authenticates to Google Cloud using `GCP_SA_KEY`
2. Exports fresh web data from BigQuery
3. Commits updated `github_web/src/ppl-data.js` when changed
4. Deploys `github_web/` to GitHub Pages

## Backfill Missing Assets

If a new ticker exists in the asset universe but not in BigQuery:

```bash
python github_web/scripts/backfill_missing_web_assets.py 00646.TW 00955.TWO
python github_web/scripts/export_web_data.py
```

Inputs and calculations remain TWD-based. The TWD / USD toggle changes display only.
