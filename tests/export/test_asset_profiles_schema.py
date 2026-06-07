"""
Tests for data/asset_profiles/asset_profiles.json.

These tests protect the shared asset profile contract used by GitHub Web and
Streamlit Dashboard. They do not call external websites.
"""

import json
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
ASSET_PROFILE_PATH = REPO_ROOT / "data" / "asset_profiles" / "asset_profiles.json"
SCRIPT_DIR = REPO_ROOT / "github_web" / "scripts" / "asset_intelligence"
STREAMLIT_DIR = REPO_ROOT / "streamlit_dashboard"

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if str(STREAMLIT_DIR) not in sys.path:
    sys.path.insert(0, str(STREAMLIT_DIR))

from schema import SCHEMA_VERSION, validate_profiles, sanitize_text
from sources import is_allowed_url
from src.processing.screening import ASSET_POOL


@pytest.fixture
def asset_profile_payload():
    return json.loads(ASSET_PROFILE_PATH.read_text(encoding="utf-8"))


def test_asset_profiles_json_exists():
    assert ASSET_PROFILE_PATH.exists()


def test_payload_schema_version(asset_profile_payload):
    assert asset_profile_payload["schemaVersion"] == SCHEMA_VERSION


def test_payload_validates_against_asset_pool(asset_profile_payload):
    validate_profiles(asset_profile_payload, {asset["ticker"] for asset in ASSET_POOL})


def test_all_asset_pool_tickers_have_profile(asset_profile_payload):
    profile_tickers = {profile["ticker"] for profile in asset_profile_payload["profiles"]}
    pool_tickers = {asset["ticker"] for asset in ASSET_POOL}
    assert profile_tickers == pool_tickers


def test_source_urls_are_allowlisted(asset_profile_payload):
    for profile in asset_profile_payload["profiles"]:
        assert is_allowed_url(profile["sourceUrl"]), profile["sourceUrl"]


def test_profiles_use_web_scraping_not_price_or_market_api_sources(asset_profile_payload):
    blocked_domains = {"finance.yahoo.com", "tw.stock.yahoo.com", "coinmarketcap.com"}
    for profile in asset_profile_payload["profiles"]:
        assert profile["collectionMethod"] == "web_scraping"
        assert profile["sourceSummary"]
        assert not any(domain in profile["sourceUrl"] for domain in blocked_domains)


def test_all_etf_expense_ratios_are_materialized(asset_profile_payload):
    profiles = {profile["ticker"]: profile for profile in asset_profile_payload["profiles"]}
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
        assert profiles[ticker]["expenseRatioCollectionMethod"] == "web_scraping"


def test_tw_etf_expense_ratio_is_management_plus_custodian_fee(asset_profile_payload):
    profiles = {profile["ticker"]: profile for profile in asset_profile_payload["profiles"]}
    tw_etf_tickers = {
        asset["ticker"]
        for asset in ASSET_POOL
        if asset["category"] == "TW_ETF"
    }
    for ticker in tw_etf_tickers:
        profile = profiles[ticker]
        assert profile["managementFee"]
        assert profile["custodianFee"]
        assert profile["expenseRatioFormula"] == "managementFee + custodianFee"


def test_crypto_profiles_do_not_require_fund_expense_ratio(asset_profile_payload):
    profiles = {profile["ticker"]: profile for profile in asset_profile_payload["profiles"]}
    crypto_tickers = {
        asset["ticker"]
        for asset in ASSET_POOL
        if asset["category"] == "CRYPTO"
    }
    for ticker in crypto_tickers:
        assert "expenseRatio" not in profiles[ticker]
        assert profiles[ticker]["assetType"] == "Crypto"


def test_text_fields_do_not_contain_html_or_script(asset_profile_payload):
    text_fields = {
        "name",
        "summary",
        "sourceSummary",
        "category",
        "issuer",
        "dividendPolicy",
        "cryptoCategory",
        "blockchain",
        "consensus",
        "primaryUse",
    }
    for profile in asset_profile_payload["profiles"]:
        for field in text_fields:
            value = profile.get(field)
            if not isinstance(value, str):
                continue
            assert "<" not in value
            assert "script" not in value.lower()


def test_sanitize_text_removes_script_and_tags():
    dirty = "<script>alert(1)</script><b>ETF</b> profile"
    clean = sanitize_text(dirty)
    assert "<" not in clean
    assert "script" not in clean.lower()
    assert "ETF profile" in clean
