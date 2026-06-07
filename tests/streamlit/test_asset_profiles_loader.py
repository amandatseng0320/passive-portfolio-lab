"""
Tests for streamlit_dashboard/src/asset_profiles/loader.py.
"""

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
STREAMLIT_DIR = REPO_ROOT / "streamlit_dashboard"

if str(STREAMLIT_DIR) not in sys.path:
    sys.path.insert(0, str(STREAMLIT_DIR))

from src.asset_profiles.loader import (
    fallback_profile,
    get_asset_profile,
    load_asset_profiles,
)
from src.processing.screening import ASSET_POOL


def test_load_asset_profiles_reads_valid_json(tmp_path):
    path = tmp_path / "asset_profiles.json"
    path.write_text(
        json.dumps({
            "profiles": [
                {"ticker": "GLD", "name": "SPDR Gold Shares", "summary": "Gold ETF"}
            ]
        }),
        encoding="utf-8",
    )
    load_asset_profiles.cache_clear()
    profiles = load_asset_profiles(str(path))
    assert profiles["GLD"]["name"] == "SPDR Gold Shares"


def test_get_asset_profile_returns_fallback_for_missing_ticker(tmp_path):
    path = tmp_path / "asset_profiles.json"
    path.write_text(json.dumps({"profiles": []}), encoding="utf-8")
    load_asset_profiles.cache_clear()
    profile = get_asset_profile("MISSING", str(path))
    assert profile["ticker"] == "MISSING"
    assert "尚無補充資訊" in profile["summary"]


def test_load_asset_profiles_bad_json_returns_empty_mapping(tmp_path):
    path = tmp_path / "asset_profiles.json"
    path.write_text("{bad json", encoding="utf-8")
    load_asset_profiles.cache_clear()
    assert load_asset_profiles(str(path)) == {}


def test_fallback_profile_shape():
    profile = fallback_profile("BTC-USD")
    for key in ["ticker", "name", "assetType", "summary", "sourceUrl", "sourceSummary", "collectionMethod"]:
        assert key in profile


def test_streamlit_loader_reads_materialized_etf_expense_ratios():
    load_asset_profiles.cache_clear()
    profiles = load_asset_profiles()
    etf_tickers = {
        asset["ticker"]
        for asset in ASSET_POOL
        if asset["category"] in {"TW_ETF", "US_ETF"}
    }
    for ticker in etf_tickers:
        expense_ratio = profiles[ticker]["expenseRatio"]
        assert "%" in expense_ratio
        assert expense_ratio != "See source profile"
        assert "約" not in expense_ratio
        assert "+" not in expense_ratio
        assert profiles[ticker]["expenseRatioSourceUrl"].startswith("https://")
