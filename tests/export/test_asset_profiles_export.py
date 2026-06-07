"""
Tests for github_web/scripts/asset_intelligence/export_asset_profiles.py.
"""

import json
import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = REPO_ROOT / "github_web" / "scripts" / "asset_intelligence"
STREAMLIT_DIR = REPO_ROOT / "streamlit_dashboard"

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if str(STREAMLIT_DIR) not in sys.path:
    sys.path.insert(0, str(STREAMLIT_DIR))

import export_asset_profiles as exporter
from src.processing.screening import ASSET_POOL


def test_build_js_contains_expected_globals():
    payload = exporter.load_profiles()
    js = exporter.build_js(payload)
    assert "const PPL_ASSET_PROFILE_UPDATED_AT" in js
    assert "const PPL_ASSET_PROFILES" in js


def test_exported_js_contains_all_tickers():
    payload = exporter.load_profiles()
    js = exporter.build_js(payload)
    for asset in ASSET_POOL:
        assert f'"{asset["ticker"]}"' in js


def test_build_js_is_parseable_json_payload():
    payload = exporter.load_profiles()
    js = exporter.build_js(payload)
    match = re.search(r"const PPL_ASSET_PROFILES = (\{.*\});", js, re.DOTALL)
    assert match
    parsed = json.loads(match.group(1))
    assert len(parsed) == len(ASSET_POOL)
    assert parsed["BTC-USD"]["assetType"] == "Crypto"


def test_exported_js_materializes_all_etf_expense_ratios():
    payload = exporter.load_profiles()
    js = exporter.build_js(payload)
    match = re.search(r"const PPL_ASSET_PROFILES = (\{.*\});", js, re.DOTALL)
    assert match
    parsed = json.loads(match.group(1))
    etf_tickers = {
        asset["ticker"]
        for asset in ASSET_POOL
        if asset["category"] in {"TW_ETF", "US_ETF"}
    }
    for ticker in etf_tickers:
        expense_ratio = parsed[ticker]["expenseRatio"]
        assert "%" in expense_ratio
        assert expense_ratio != "See source profile"
        assert "約" not in expense_ratio
        assert "+" not in expense_ratio
        assert parsed[ticker]["expenseRatioSourceUrl"].startswith("https://")


def test_write_js_idempotent(tmp_path):
    output = tmp_path / "ppl-asset-profiles.js"
    exporter.write_js(output_path=output)
    first = output.read_text(encoding="utf-8")
    exporter.write_js(output_path=output)
    second = output.read_text(encoding="utf-8")
    assert first == second
