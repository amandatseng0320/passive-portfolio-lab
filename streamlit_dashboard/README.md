# Streamlit Dashboard

Interactive Streamlit version of Passive Portfolio Lab.

## Entry Point

Use this file in Streamlit Cloud:

```text
streamlit_dashboard/app.py
```

## Local Run

From the repository root:

```bash
pip install -r streamlit_dashboard/requirements.txt
streamlit run streamlit_dashboard/app.py
```

## Required Data Access

The dashboard reads from Google BigQuery:

- `raw_prices`
- `asset_metrics`

Set these environment variables locally or in Streamlit Cloud secrets:

```env
GOOGLE_CLOUD_PROJECT=your-project-id
BIGQUERY_DATASET=passive_portfolio
GOOGLE_APPLICATION_CREDENTIALS=credentials.json
```

Optional:

```env
FRED_API_KEY=your-fred-api-key
GEMINI_API_KEY=your-gemini-api-key
APP_PASSWORD=your-password
```

## Main Modules

- `src/processing/screening.py`: curated asset universe
- `src/processing/backtest.py`: TWD historical backtest engine
- `src/processing/metrics.py`: asset metrics calculation
- `src/data_collection/fetch_prices.py`: Yahoo Finance price collection
- `src/data_collection/fetch_macro.py`: FRED CPI helper
