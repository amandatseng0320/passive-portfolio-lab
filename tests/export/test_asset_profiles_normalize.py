"""
Tests for github_web/scripts/asset_intelligence/normalize_profiles.py.

These tests protect the fallback path without calling external websites.
"""

import json
import sys
from copy import deepcopy
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
ASSET_PROFILE_PATH = REPO_ROOT / "data" / "asset_profiles" / "asset_profiles.json"
SCRIPT_DIR = REPO_ROOT / "github_web" / "scripts" / "asset_intelligence"
STREAMLIT_DIR = REPO_ROOT / "streamlit_dashboard"

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if str(STREAMLIT_DIR) not in sys.path:
    sys.path.insert(0, str(STREAMLIT_DIR))

import normalize_profiles as normalizer
from src.processing.screening import ASSET_POOL


def load_profile_payload() -> dict:
    return json.loads(ASSET_PROFILE_PATH.read_text(encoding="utf-8"))


def load_profile_map() -> dict[str, dict]:
    payload = load_profile_payload()
    return {profile["ticker"]: profile for profile in payload["profiles"]}


def test_load_previous_profiles_keeps_export_ready_profiles(tmp_path):
    path = tmp_path / "asset_profiles.json"
    path.write_text(json.dumps(load_profile_payload()), encoding="utf-8")

    profiles = normalizer.load_previous_profiles(path)

    assert set(profiles) == {asset["ticker"] for asset in ASSET_POOL}
    assert profiles["0050.TW"]["collectionMethod"] == "web_scraping"


def test_reuse_previous_profile_if_needed_reuses_valid_previous_profile():
    profiles = load_profile_map()
    failed_profile = deepcopy(profiles["0050.TW"])
    failed_profile["collectionMethod"] = "curated_fallback"
    failed_profile["sourceSummary"] = ""

    reused = normalizer.reuse_previous_profile_if_needed(
        failed_profile,
        {"0050.TW": profiles["0050.TW"]},
    )

    assert reused["collectionMethod"] == "web_scraping"
    assert reused["sourceSummary"]
    assert reused["reusedFromPreviousExport"] is True
    assert "sourceSummary" in reused["reuseReason"]
    assert "reusedFromPreviousExport" not in profiles["0050.TW"]


def test_reuse_previous_profile_if_needed_leaves_export_ready_profile_unchanged():
    profiles = load_profile_map()
    ready_profile = deepcopy(profiles["0050.TW"])

    result = normalizer.reuse_previous_profile_if_needed(
        ready_profile,
        {"0050.TW": profiles["0050.TW"]},
    )

    assert result is ready_profile
    assert "reusedFromPreviousExport" not in result


def test_build_payload_reuses_previous_profile_for_single_bad_scrape(monkeypatch):
    profiles = load_profile_map()

    def fake_build_profile(asset: dict, fetched_at: str) -> dict:
        profile = deepcopy(profiles[asset["ticker"]])
        profile["fetchedAt"] = fetched_at
        if asset["ticker"] == "0050.TW":
            profile["collectionMethod"] = "curated_fallback"
            profile["sourceSummary"] = ""
        return profile

    monkeypatch.setattr(normalizer, "build_profile", fake_build_profile)

    payload = normalizer.build_payload(
        fetched_at="2026-07-01",
        previous_profiles={"0050.TW": profiles["0050.TW"]},
    )
    normalized_profiles = {profile["ticker"]: profile for profile in payload["profiles"]}

    assert normalized_profiles["0050.TW"]["collectionMethod"] == "web_scraping"
    assert normalized_profiles["0050.TW"]["reusedFromPreviousExport"] is True
    assert normalized_profiles["0050.TW"]["fetchedAt"] == profiles["0050.TW"]["fetchedAt"]
    assert normalized_profiles["006208.TW"]["fetchedAt"] == "2026-07-01"
