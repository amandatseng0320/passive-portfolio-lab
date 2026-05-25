"""Shared utilities for processing modules."""
import os
import pandas as pd
import pandas_gbq
from dotenv import load_dotenv

load_dotenv()

# Shared Yahoo Finance request headers — prevents 429/403 on direct REST calls.
YAHOO_HEADERS: dict[str, str] = {"User-Agent": "Mozilla/5.0"}

# Annualized risk-free rate used in Sharpe ratio calculations.
# Based on the long-run US short-term treasury yield.  Update when the
# prevailing rate environment shifts meaningfully.
RISK_FREE_RATE: float = 0.02


def get_bq_config() -> tuple[str, str]:
    """Return (project_id, dataset_id) from environment variables.

    Raises ValueError if either variable is missing, so callers don't need
    to repeat the same validation logic.
    """
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    dataset_id = os.getenv("BIGQUERY_DATASET")
    if not project_id or not dataset_id:
        raise ValueError("Missing GOOGLE_CLOUD_PROJECT or BIGQUERY_DATASET in .env")
    return project_id, dataset_id


def upload_to_bq(df: pd.DataFrame, table_name: str, if_exists: str = "replace") -> None:
    """Upload *df* to ``{dataset_id}.{table_name}`` using env-var BQ config.

    Args:
        df:         DataFrame to upload.
        table_name: Bare table name (e.g. ``"raw_prices"``). The dataset prefix
                    is resolved automatically from ``BIGQUERY_DATASET``.
        if_exists:  Passed to ``pandas_gbq.to_gbq`` (default ``"replace"``).

    Raises:
        ValueError: if BQ env vars are missing.
        Exception:  propagated from ``pandas_gbq.to_gbq`` on upload failure.
    """
    project_id, dataset_id = get_bq_config()
    destination = f"{dataset_id}.{table_name}"
    print(f"Uploading {len(df):,} rows to {project_id}.{destination}...")
    pandas_gbq.to_gbq(
        dataframe=df,
        destination_table=destination,
        project_id=project_id,
        if_exists=if_exists,
    )
    print("Upload completed successfully.")
