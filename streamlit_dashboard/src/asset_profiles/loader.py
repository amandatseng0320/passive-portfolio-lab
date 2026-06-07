"""Load normalized asset profiles for Streamlit display."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
PROFILE_PATH = REPO_ROOT / "data" / "asset_profiles" / "asset_profiles.json"


def fallback_profile(ticker: str) -> dict[str, Any]:
    """Return a safe fallback profile for missing or invalid data."""
    return {
        "ticker": ticker,
        "name": ticker,
        "assetType": "Unknown",
        "summary": "目前尚無補充資訊。",
        "category": "Unknown",
        "sourceName": "",
        "sourceUrl": "",
        "sourceSummary": "",
        "collectionMethod": "curated_fallback",
        "fetchedAt": "",
        "schemaVersion": "",
    }


@lru_cache(maxsize=1)
def load_asset_profiles(path: str | None = None) -> dict[str, dict[str, Any]]:
    """Load asset profiles keyed by ticker.

    Bad or missing JSON returns an empty mapping so the UI can fall back safely.
    """
    profile_path = Path(path) if path else PROFILE_PATH
    try:
        payload = json.loads(profile_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}

    profiles = payload.get("profiles", [])
    if not isinstance(profiles, list):
        return {}
    return {
        str(profile.get("ticker")): profile
        for profile in profiles
        if isinstance(profile, dict) and profile.get("ticker")
    }


def get_asset_profile(ticker: str, path: str | None = None) -> dict[str, Any]:
    """Return one asset profile or a safe fallback."""
    return load_asset_profiles(path).get(ticker, fallback_profile(ticker))
