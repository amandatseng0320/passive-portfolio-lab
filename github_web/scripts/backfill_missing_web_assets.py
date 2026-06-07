#!/usr/bin/env python3
"""
Backfill selected assets into BigQuery raw_prices and asset_metrics.

This is intentionally targeted: it fetches only the tickers passed on the
command line, merges them into the existing raw_prices table, then recalculates
asset_metrics from the full refreshed raw_prices table.
"""

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
from src.processing.utils import get_bq_config, upload_to_bq


DEFAULT_TICKERS = ["00646.TW", "00955.TWO"]


def load_existing_raw_prices(project_id, dataset_id):
    # dataset_id is validated by get_bq_config() before this helper is called.
    query = f"SELECT * FROM `{dataset_id}.raw_prices`"  # nosec B608
    df = pandas_gbq.read_gbq(query, project_id=project_id)
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    return df


def main():
    tickers = sys.argv[1:] or DEFAULT_TICKERS
    project_id, dataset_id = get_bq_config()

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

    print(f"Replacing raw_prices with {len(raw_prices):,} rows...")
    upload_to_bq(raw_prices, "raw_prices")

    print("Recalculating full asset_metrics from refreshed raw_prices...")
    metrics_df = calculate_metrics(raw_prices)
    if metrics_df.empty:
        raise RuntimeError("Metric calculation returned no rows; asset_metrics was not updated.")
    upload_to_bq(metrics_df, "asset_metrics")

    print("Backfill complete.")
    print(metrics_df[metrics_df["ticker"].isin(tickers)][[
        "ticker", "data_start", "data_end", "cagr", "volatility", "max_drawdown", "sharpe_ratio"
    ]].to_string(index=False))


if __name__ == "__main__":
    main()
