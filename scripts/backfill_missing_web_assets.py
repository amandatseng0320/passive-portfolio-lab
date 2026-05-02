#!/usr/bin/env python3
"""
Backfill selected assets into BigQuery raw_prices and asset_metrics.

This is intentionally targeted: it fetches only the tickers passed on the
command line, merges them into the existing raw_prices table, then recalculates
asset_metrics from the full refreshed raw_prices table.
"""

import os
import sys
from pathlib import Path

import pandas as pd
import pandas_gbq
from dotenv import load_dotenv

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(REPO_ROOT / "streamlit_dashboard"))

from src.data_collection.fetch_prices import fetch_prices
from src.processing.metrics import calculate_metrics
from src.processing.screening import get_all_candidates


DEFAULT_TICKERS = ["00646.TW", "00955.TWO"]


def require_env():
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    dataset_id = os.getenv("BIGQUERY_DATASET")
    if not project_id or not dataset_id:
        raise ValueError("Missing GOOGLE_CLOUD_PROJECT or BIGQUERY_DATASET")
    return project_id, dataset_id


def load_existing_raw_prices(project_id, dataset_id):
    query = f"SELECT * FROM `{dataset_id}.raw_prices`"
    df = pandas_gbq.read_gbq(query, project_id=project_id)
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    return df


def upload_replace(df, project_id, table_id):
    pandas_gbq.to_gbq(
        dataframe=df,
        destination_table=table_id,
        project_id=project_id,
        if_exists="replace",
    )


def main():
    tickers = sys.argv[1:] or DEFAULT_TICKERS
    project_id, dataset_id = require_env()

    candidates = get_all_candidates()
    selected = candidates[candidates["ticker"].isin(tickers)].copy()
    if selected.empty:
        raise ValueError(f"No matching tickers found in ASSET_POOL: {tickers}")

    print(f"Fetching missing assets: {', '.join(selected['ticker'])}")
    new_prices = fetch_prices(selected)
    if new_prices.empty:
        raise RuntimeError("No new price rows fetched; aborting BigQuery update.")

    existing = load_existing_raw_prices(project_id, dataset_id)
    existing = existing[~existing["ticker"].isin(tickers)].copy()
    raw_prices = pd.concat([existing, new_prices], ignore_index=True)
    raw_prices = raw_prices[["date", "ticker", "category", "open", "high", "low", "close", "volume"]]
    raw_prices["date"] = pd.to_datetime(raw_prices["date"])

    raw_table = f"{dataset_id}.raw_prices"
    print(f"Replacing {project_id}.{raw_table} with {len(raw_prices):,} rows...")
    upload_replace(raw_prices, project_id, raw_table)

    print("Recalculating full asset_metrics from refreshed raw_prices...")
    metrics_df = calculate_metrics(raw_prices)
    if metrics_df.empty:
        raise RuntimeError("Metric calculation returned no rows; asset_metrics was not updated.")
    metrics_table = f"{dataset_id}.asset_metrics"
    print(f"Replacing {project_id}.{metrics_table} with {len(metrics_df):,} rows...")
    upload_replace(metrics_df, project_id, metrics_table)

    print("Backfill complete.")
    print(metrics_df[metrics_df["ticker"].isin(tickers)][[
        "ticker", "data_start", "data_end", "cagr", "volatility", "max_drawdown", "sharpe_ratio"
    ]].to_string(index=False))


if __name__ == "__main__":
    main()
