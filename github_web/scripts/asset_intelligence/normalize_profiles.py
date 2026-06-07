#!/usr/bin/env python3
"""Build normalized asset_profiles.json from the curated asset universe."""

from __future__ import annotations

import argparse
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
from schema import SCHEMA_VERSION, sanitize_text, validate_profiles
from sources import source_for_asset


OUTPUT = REPO_ROOT / "data" / "asset_profiles" / "asset_profiles.json"


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


def build_payload(fetched_at: str | None = None) -> dict[str, Any]:
    fetched_at = fetched_at or date.today().isoformat()
    payload = {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": fetched_at,
        "status": "web_scraping_completed",
        "profiles": [build_profile(asset, fetched_at) for asset in ASSET_POOL],
    }
    validate_profiles(payload, {asset["ticker"] for asset in ASSET_POOL})
    return payload


def write_payload(output: Path = OUTPUT, fetched_at: str | None = None) -> None:
    payload = build_payload(fetched_at=fetched_at)
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
