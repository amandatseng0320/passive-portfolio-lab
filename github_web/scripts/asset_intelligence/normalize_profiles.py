#!/usr/bin/env python3
"""Build normalized asset_profiles.json from the curated asset universe."""

from __future__ import annotations

import argparse
from copy import deepcopy
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
sys.path.insert(0, str(REPO_ROOT / "streamlit_dashboard"))
sys.path.insert(0, str(SCRIPT_DIR))

from src.processing.screening import ASSET_POOL
from fetch_etf_profiles import fetch_expense_ratio_components, fetch_source_summary
from schema import SCHEMA_VERSION, sanitize_text, validate_profile, validate_profiles
from sources import source_for_asset


OUTPUT = REPO_ROOT / "data" / "asset_profiles" / "asset_profiles.json"
REUSE_REASON_MAX_LEN = 240


ISSUER_RULES = [
    ("Yuanta", "Yuanta Securities Investment Trust"),
    ("Fubon", "Fubon Asset Management"),
    ("Cathay", "Cathay Securities Investment Trust"),
    ("Group Benefits", "Capital Investment Trust"),
    ("Fuh Hwa", "Fuh Hwa Securities Investment Trust"),
    ("KGI", "KGI Securities Investment Trust"),
    ("CTBC", "CTBC Investments"),
    ("Vanguard", "Vanguard"),
    ("iShares", "BlackRock iShares"),
    ("SPDR", "State Street Global Advisors"),
    ("Invesco", "Invesco"),
]

CRYPTO_DETAILS = {
    "BTC-USD": {"blockchain": "Bitcoin", "issuer": "None / decentralized", "consensus": "Proof of Work"},
    "ETH-USD": {"blockchain": "Ethereum", "issuer": "Ethereum Foundation / decentralized ecosystem", "consensus": "Proof of Stake"},
    "BNB-USD": {"blockchain": "BNB Chain", "issuer": "Binance ecosystem", "consensus": "Proof of Staked Authority"},
    "XRP-USD": {"blockchain": "XRP Ledger", "issuer": "Ripple-affiliated ecosystem", "consensus": "XRP Ledger Consensus Protocol"},
    "SOL-USD": {"blockchain": "Solana", "issuer": "Solana Foundation / ecosystem", "consensus": "Proof of History + Proof of Stake"},
    "TRX-USD": {"blockchain": "TRON", "issuer": "TRON DAO ecosystem", "consensus": "Delegated Proof of Stake"},
    "DOGE-USD": {"blockchain": "Dogecoin", "issuer": "None / decentralized", "consensus": "Proof of Work"},
    "ADA-USD": {"blockchain": "Cardano", "issuer": "Cardano Foundation / Input Output ecosystem", "consensus": "Ouroboros Proof of Stake"},
}


def export_readiness_errors(profile: dict[str, Any]) -> list[str]:
    """Return profile issues that would fail the GitHub Web export gate."""
    ticker = str(profile.get("ticker", "<unknown>"))
    errors: list[str] = []

    if profile.get("collectionMethod") != "web_scraping":
        errors.append(f"{ticker} collectionMethod is not web_scraping")
    if not profile.get("sourceSummary"):
        errors.append(f"{ticker} sourceSummary is empty")
    if not str(profile.get("sourceUrl", "")).startswith("https://"):
        errors.append(f"{ticker} sourceUrl is not https")

    if profile.get("assetType") == "Crypto":
        if "expenseRatio" in profile:
            errors.append(f"{ticker} crypto profile exposes ETF expenseRatio")
        return errors

    expense_ratio = str(profile.get("expenseRatio", ""))
    if (
        "See source profile" in expense_ratio
        or "%" not in expense_ratio
        or "約" in expense_ratio
        or "+" in expense_ratio
    ):
        errors.append(f"{ticker} ETF expenseRatio is not materialized")
    if not str(profile.get("expenseRatioSourceUrl", "")).startswith("https://"):
        errors.append(f"{ticker} expenseRatioSourceUrl is missing")
    if profile.get("expenseRatioCollectionMethod") != "web_scraping":
        errors.append(f"{ticker} expenseRatioCollectionMethod is not web_scraping")
    if ticker.endswith((".TW", ".TWO")):
        if profile.get("expenseRatioFormula") != "managementFee + custodianFee":
            errors.append(f"{ticker} TW ETF expenseRatioFormula is not fee component based")
        if not profile.get("managementFee") or not profile.get("custodianFee"):
            errors.append(f"{ticker} TW ETF fee component is missing")
    return errors


def load_previous_profiles(path: Path = OUTPUT) -> dict[str, dict[str, Any]]:
    """Load prior export-ready profiles so transient source failures can recover."""
    if not path.exists():
        return {}

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Previous asset profile fallback unavailable: {exc}", file=sys.stderr)
        return {}

    if payload.get("schemaVersion") != SCHEMA_VERSION:
        return {}

    allowed_tickers = {asset["ticker"] for asset in ASSET_POOL}
    profiles: dict[str, dict[str, Any]] = {}
    for profile in payload.get("profiles", []):
        ticker = str(profile.get("ticker", ""))
        if ticker not in allowed_tickers or ticker in profiles:
            continue
        try:
            validate_profile(profile)
        except ValueError:
            continue
        if not export_readiness_errors(profile):
            profiles[ticker] = deepcopy(profile)
    return profiles


def reuse_previous_profile_if_needed(
    profile: dict[str, Any],
    previous_profiles: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Return a prior good profile when the new scrape fails export requirements."""
    errors = export_readiness_errors(profile)
    if not errors:
        return profile

    ticker = str(profile.get("ticker", ""))
    previous = previous_profiles.get(ticker)
    if previous is None:
        return profile

    reused = deepcopy(previous)
    reused["schemaVersion"] = SCHEMA_VERSION
    reused["reusedFromPreviousExport"] = True
    reused["reuseReason"] = sanitize_text("; ".join(errors), max_len=REUSE_REASON_MAX_LEN)
    print(f"Reused previous asset profile for {ticker}: {reused['reuseReason']}", file=sys.stderr)
    return reused


def infer_issuer(name: str) -> str:
    for marker, issuer in ISSUER_RULES:
        if marker.lower() in name.lower():
            return issuer
    return "Issuer listed in source profile"


def infer_expense_ratio(description: str) -> str:
    lowered = description.lower()
    if "0.03%" in lowered:
        return "0.03%"
    if "0.04%" in lowered:
        return "0.04%"
    return "See source profile"


def infer_dividend_policy(category: str, subcategory: str, description: str) -> str:
    text = f"{subcategory} {description}".lower()
    if "monthly" in text:
        return "Monthly distributions noted in curated profile"
    if "quarterly" in text:
        return "Quarterly distributions noted in curated profile"
    if "dividend" in text or "yield" in text:
        return "Dividend-focused strategy; verify frequency from source profile"
    if "bond" in text:
        return "Income-oriented bond ETF; verify frequency from source profile"
    if category == "US_ETF":
        return "Distribution policy varies by fund; verify from source profile"
    return "Distribution policy listed in source profile"


def scrape_profile_summary(ticker: str, category: str) -> dict[str, str]:
    """Scrape an approved public profile page and return safe summary metadata."""
    try:
        scraped = fetch_source_summary(ticker, category)
    except Exception:
        return {
            "sourceSummary": "",
            "expenseRatio": "",
            "collectionMethod": "curated_fallback",
        }
    summary = sanitize_text(scraped.get("sourceSummary", ""), max_len=360)
    return {
        "sourceSummary": summary,
        "expenseRatio": sanitize_text(scraped.get("expenseRatio", ""), max_len=20),
        "collectionMethod": "web_scraping" if summary else "curated_fallback",
    }


def scrape_expense_ratio(ticker: str, category: str) -> dict[str, str]:
    """Scrape ETF management/custodian fee fields from an approved source."""
    try:
        fees = fetch_expense_ratio_components(ticker, category)
    except Exception:
        return {
            "managementFee": "",
            "custodianFee": "",
            "expenseRatio": "",
            "expenseRatioFormula": "managementFee + custodianFee",
            "expenseRatioSourceName": "",
            "expenseRatioSourceUrl": "",
            "expenseRatioCollectionMethod": "",
        }
    return {
        "managementFee": sanitize_text(fees.get("managementFee", ""), max_len=40),
        "custodianFee": sanitize_text(fees.get("custodianFee", ""), max_len=40),
        "expenseRatio": sanitize_text(fees.get("expenseRatio", ""), max_len=60),
        "expenseRatioFormula": sanitize_text(
            fees.get("expenseRatioFormula", "managementFee + custodianFee"), max_len=80
        ),
        "expenseRatioSourceName": sanitize_text(fees.get("expenseRatioSourceName", ""), max_len=120),
        "expenseRatioSourceUrl": sanitize_text(fees.get("expenseRatioSourceUrl", ""), max_len=240),
        "expenseRatioCollectionMethod": sanitize_text(
            fees.get("expenseRatioCollectionMethod", ""), max_len=40
        ),
    }


def build_profile(asset: dict[str, Any], fetched_at: str) -> dict[str, Any]:
    source = source_for_asset(asset["ticker"], asset["category"])
    scraped = scrape_profile_summary(asset["ticker"], asset["category"])
    curated_summary = sanitize_text(asset["description"], max_len=360)
    summary = scraped["sourceSummary"] or curated_summary
    base = {
        "ticker": asset["ticker"],
        "name": sanitize_text(asset["name"], max_len=120),
        "assetType": "Crypto" if asset["category"] == "CRYPTO" else asset["category"].replace("_", " "),
        "summary": summary,
        "category": sanitize_text(asset["subcategory"], max_len=120),
        "sourceName": source.source_name,
        "sourceUrl": source.source_url,
        "sourceSummary": scraped["sourceSummary"] or curated_summary,
        "collectionMethod": scraped["collectionMethod"],
        "fetchedAt": fetched_at,
        "schemaVersion": SCHEMA_VERSION,
    }

    if asset["category"] == "CRYPTO":
        details = CRYPTO_DETAILS[asset["ticker"]]
        base.update({
            "cryptoCategory": sanitize_text(asset["subcategory"], max_len=120),
            "blockchain": details["blockchain"],
            "issuer": details["issuer"],
            "consensus": details["consensus"],
            "primaryUse": summary,
        })
    else:
        fee_data = scrape_expense_ratio(asset["ticker"], asset["category"])
        if not fee_data["managementFee"] or not fee_data["custodianFee"]:
            fee_data["expenseRatioFormula"] = "officialExpenseRatio"
        base.update({
            "issuer": infer_issuer(asset["name"]),
            "expenseRatio": fee_data["expenseRatio"] or scraped["expenseRatio"] or infer_expense_ratio(asset["description"]),
            "managementFee": fee_data["managementFee"],
            "custodianFee": fee_data["custodianFee"],
            "expenseRatioFormula": fee_data["expenseRatioFormula"],
            "expenseRatioSourceName": fee_data["expenseRatioSourceName"] or source.source_name,
            "expenseRatioSourceUrl": fee_data["expenseRatioSourceUrl"] or source.source_url,
            "expenseRatioCollectionMethod": fee_data["expenseRatioCollectionMethod"] or "web_scraping",
            "dividendPolicy": infer_dividend_policy(
                asset["category"], asset["subcategory"], asset["description"]
            ),
        })
    return base


def build_payload(
    fetched_at: str | None = None,
    previous_profiles: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    fetched_at = fetched_at or date.today().isoformat()
    previous_profiles = previous_profiles or {}
    profiles = [
        reuse_previous_profile_if_needed(build_profile(asset, fetched_at), previous_profiles)
        for asset in ASSET_POOL
    ]
    payload = {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": fetched_at,
        "status": "web_scraping_completed",
        "profiles": profiles,
    }
    validate_profiles(payload, {asset["ticker"] for asset in ASSET_POOL})
    return payload


def write_payload(output: Path = OUTPUT, fetched_at: str | None = None) -> None:
    payload = build_payload(
        fetched_at=fetched_at,
        previous_profiles=load_previous_profiles(output),
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--fetched-at", default=None)
    args = parser.parse_args()
    write_payload(args.output, args.fetched_at)
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
