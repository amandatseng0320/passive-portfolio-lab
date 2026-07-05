#!/usr/bin/env python3
"""Schema, sanitization, and validation for asset profile data."""

from __future__ import annotations

import html
import re
from datetime import datetime
from typing import Any

from sources import CURATED_EXPENSE_RATIO_FALLBACKS, validate_source_url


SCHEMA_VERSION = "1.0"

COMMON_REQUIRED_FIELDS = {
    "ticker",
    "name",
    "assetType",
    "summary",
    "category",
    "sourceName",
    "sourceUrl",
    "sourceSummary",
    "collectionMethod",
    "fetchedAt",
    "schemaVersion",
}

ETF_REQUIRED_FIELDS = {
    "issuer",
    "expenseRatio",
    "managementFee",
    "custodianFee",
    "expenseRatioFormula",
    "expenseRatioSourceName",
    "expenseRatioSourceUrl",
    "expenseRatioCollectionMethod",
    "dividendPolicy",
}

CRYPTO_REQUIRED_FIELDS = {
    "cryptoCategory",
    "blockchain",
    "issuer",
    "consensus",
}


_SCRIPT_RE = re.compile(r"<\s*/?\s*script\b", re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")
_SPACE_RE = re.compile(r"\s+")


def sanitize_text(value: Any, max_len: int = 500) -> str:
    """Return plain text safe for JSON and frontend display."""
    text = "" if value is None else str(value)
    text = html.unescape(text)
    text = _SCRIPT_RE.sub("", text)
    text = _TAG_RE.sub(" ", text)
    text = _SPACE_RE.sub(" ", text).strip()
    return text[:max_len]


def validate_profile(profile: dict[str, Any]) -> None:
    """Validate one normalized asset profile."""
    missing = sorted(COMMON_REQUIRED_FIELDS - set(profile))
    if missing:
        raise ValueError(f"{profile.get('ticker', '<unknown>')} missing fields: {missing}")

    validate_source_url(str(profile["sourceUrl"]))
    if profile.get("collectionMethod") not in {"web_scraping", "curated_fallback"}:
        raise ValueError(f"{profile['ticker']} has invalid collectionMethod")

    if profile["assetType"] == "Crypto":
        required = CRYPTO_REQUIRED_FIELDS
    else:
        required = ETF_REQUIRED_FIELDS

    missing = sorted(required - set(profile))
    if missing:
        raise ValueError(f"{profile['ticker']} missing {profile['assetType']} fields: {missing}")

    if profile["assetType"] != "Crypto":
        validate_source_url(str(profile["expenseRatioSourceUrl"]))
        if profile.get("expenseRatioFormula") not in {
            "managementFee + custodianFee",
            "officialExpenseRatio",
        }:
            raise ValueError(f"{profile['ticker']} has invalid expenseRatioFormula")
        collection_method = profile.get("expenseRatioCollectionMethod")
        allowed_methods = {"web_scraping"}
        if profile["ticker"] in CURATED_EXPENSE_RATIO_FALLBACKS:
            allowed_methods.add("curated_fallback")
        if collection_method not in allowed_methods:
            raise ValueError(f"{profile['ticker']} has invalid expenseRatioCollectionMethod")

    for key, value in profile.items():
        if isinstance(value, str) and "<script" in value.lower():
            raise ValueError(f"{profile['ticker']} contains script-like text in {key}")

    datetime.strptime(str(profile["fetchedAt"]), "%Y-%m-%d")


def validate_profiles(payload: dict[str, Any], allowed_tickers: set[str]) -> None:
    """Validate the full asset profile JSON payload."""
    if payload.get("schemaVersion") != SCHEMA_VERSION:
        raise ValueError(f"schemaVersion must be {SCHEMA_VERSION}")

    profiles = payload.get("profiles")
    if not isinstance(profiles, list):
        raise ValueError("profiles must be a list")

    seen = set()
    for profile in profiles:
        validate_profile(profile)
        ticker = str(profile["ticker"])
        if ticker not in allowed_tickers:
            raise ValueError(f"profile ticker not in ASSET_POOL: {ticker}")
        if ticker in seen:
            raise ValueError(f"duplicate profile ticker: {ticker}")
        seen.add(ticker)


def profile_map(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Return ticker-keyed profiles after validation by the caller."""
    return {str(profile["ticker"]): profile for profile in payload.get("profiles", [])}
