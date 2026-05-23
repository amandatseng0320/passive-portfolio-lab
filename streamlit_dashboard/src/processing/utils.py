"""Shared utilities for processing modules."""
import os
from dotenv import load_dotenv

load_dotenv()


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
