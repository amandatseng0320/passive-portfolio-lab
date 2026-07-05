#!/usr/bin/env python3
"""
Validate that static GitHub Web data files were exported correctly.
Exits with code 1 if any check fails so GitHub Actions marks the step as failed.

Checks:
  1. Required JS globals are present
  2. Asset count is within expected range
  3. Export timestamp is fresh (< 25 hours old)
  4. FX rate is within plausible TWD/USD range (20–50)
"""
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
STREAMLIT_DIR = REPO_ROOT / "streamlit_dashboard"
ASSET_INTELLIGENCE_DIR = REPO_ROOT / "github_web" / "scripts" / "asset_intelligence"
for import_path in (STREAMLIT_DIR, ASSET_INTELLIGENCE_DIR):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from normalize_profiles import export_readiness_errors
from schema import validate_profile
from src.processing.screening import ASSET_POOL

OUTPUT = Path(__file__).resolve().parents[1] / "src" / "ppl-data.js"
PROFILE_OUTPUT = Path(__file__).resolve().parents[1] / "src" / "ppl-asset-profiles.js"
EXPECTED_MIN_ASSETS = 30   # alert if fewer than 30 assets exported
EXPECTED_ASSETS = len(ASSET_POOL)
MAX_STALENESS_HOURS = 25   # allow 1 hour of drift past the 24-hour schedule
PRICE_CLIFF_LIMITS = {
    "TW_ETF": 3.0,
    "US_ETF": 3.0,
    "CRYPTO": 6.0,
}


def extract_json_assignment(content: str, var_name: str):
    """Extract a JSON value assigned as `const VAR = ...;`."""
    marker = f"const {var_name} = "
    start = content.find(marker)
    if start < 0:
        raise ValueError(f"{var_name} assignment not found")
    json_start = start + len(marker)
    try:
        value, _ = json.JSONDecoder().raw_decode(content[json_start:])
    except json.JSONDecodeError as exc:
        raise ValueError(f"{var_name} JSON is not parseable ({exc})") from exc
    return value


def validate_price_history_cliffs(price_history: dict, ticker_categories: dict[str, str]) -> list[str]:
    """Return price-history discontinuities that exceed category-specific limits."""
    errors: list[str] = []
    for ticker, rows in price_history.items():
        category = ticker_categories.get(ticker)
        limit = PRICE_CLIFF_LIMITS.get(category or "")
        if limit is None:
            errors.append(f"PRICE CLIFF: {ticker} has unknown category {category!r}")
            continue
        for previous, current in zip(rows, rows[1:]):
            if len(previous) < 2 or len(current) < 2:
                errors.append(f"PRICE CLIFF: malformed price row for {ticker}")
                continue
            prev_date, prev_close = previous[0], float(previous[1])
            curr_date, curr_close = current[0], float(current[1])
            if prev_close <= 0 or curr_close <= 0:
                errors.append(f"PRICE CLIFF: non-positive price for {ticker} near {curr_date}")
                continue
            ratio = max(curr_close / prev_close, prev_close / curr_close)
            if ratio > limit:
                errors.append(
                    f"PRICE CLIFF: {ticker} {prev_date}->{curr_date} ratio {ratio:.2f}x exceeds {limit:.1f}x"
                )
    return errors


def main() -> None:
    if not OUTPUT.exists():
        print(f"ERROR: {OUTPUT} not found")
        sys.exit(1)

    content = OUTPUT.read_text(encoding="utf-8")
    errors: list[str] = []

    # 1. Required globals
    for var in ["PPL_ASSETS", "PPL_PRICE_HISTORY", "PPL_FX_RATE", "PPL_HISTORY_UPDATED_AT"]:
        if f"const {var}" not in content:
            errors.append(f"MISSING global: const {var}")

    # 2. Asset count — count distinct ticker values rather than relying on line formatting
    ticker_categories = {asset["ticker"]: asset["category"] for asset in ASSET_POOL}
    asset_count = len(re.findall(r'ticker:\s*["\']([^"\']+)["\']', content))
    if asset_count < EXPECTED_MIN_ASSETS:
        errors.append(
            f"ASSET COUNT: {asset_count} assets exported (expected >= {EXPECTED_MIN_ASSETS})"
        )
    elif asset_count != EXPECTED_ASSETS:
        print(f"WARNING: {asset_count} assets exported (expected {EXPECTED_ASSETS})")

    # 3. Freshness
    ts_match = re.search(r'PPL_HISTORY_UPDATED_AT = "(\d{4}-\d{2}-\d{2} \d{2}:\d{2} UTC)"', content)
    if ts_match:
        updated_at = datetime.strptime(ts_match.group(1), "%Y-%m-%d %H:%M UTC").replace(
            tzinfo=timezone.utc
        )
        age_hours = (datetime.now(timezone.utc) - updated_at).total_seconds() / 3600
        if age_hours > MAX_STALENESS_HOURS:
            errors.append(f"STALE: data is {age_hours:.1f}h old (limit {MAX_STALENESS_HOURS}h)")
    else:
        errors.append("FRESHNESS: PPL_HISTORY_UPDATED_AT timestamp missing or unparseable")

    # 4. FX rate plausibility
    fx_match = re.search(r"const PPL_FX_RATE = ([\d.]+);", content)
    if fx_match:
        fx = float(fx_match.group(1))
        if not (20.0 <= fx <= 50.0):
            errors.append(f"FX RATE: {fx} is outside plausible 20–50 TWD/USD range")
    else:
        errors.append("FX RATE: PPL_FX_RATE not found or not parseable")

    # 5. Price history cliff guard. ETF splits should be adjusted upstream; crypto
    # keeps a higher limit so real high-volatility days do not fail the export.
    try:
        price_history = extract_json_assignment(content, "PPL_PRICE_HISTORY")
    except ValueError as exc:
        errors.append(str(exc))
    else:
        errors.extend(validate_price_history_cliffs(price_history, ticker_categories))

    # 6. Optional asset profile export. Required once the web scraping showcase
    # pipeline has generated the static profile file.
    if PROFILE_OUTPUT.exists():
        profile_content = PROFILE_OUTPUT.read_text(encoding="utf-8")
        if "const PPL_ASSET_PROFILES" not in profile_content:
            errors.append("PROFILE: const PPL_ASSET_PROFILES missing")
        try:
            profiles = extract_json_assignment(profile_content, "PPL_ASSET_PROFILES")
        except ValueError as exc:
            errors.append(f"PROFILE: {exc}")
        else:
            if len(profiles) != EXPECTED_ASSETS:
                errors.append(
                    f"PROFILE COUNT: {len(profiles)} profiles exported (expected {EXPECTED_ASSETS})"
                )
            for ticker, profile in profiles.items():
                if profile.get("ticker") != ticker:
                    errors.append(f"PROFILE: key/ticker mismatch for {ticker}")
                try:
                    validate_profile(profile)
                except ValueError as exc:
                    errors.append(f"PROFILE: {exc}")
                for readiness_error in export_readiness_errors(profile):
                    errors.append(f"PROFILE: {readiness_error}")

    if errors:
        print("Export validation FAILED:")
        for e in errors:
            print(f"  {e}")
        sys.exit(1)

    fx_val = float(fx_match.group(1)) if fx_match else 0.0  # fx_match non-None here (else appended to errors)
    print(f"Export validation passed ({asset_count} assets, FX={fx_val:.2f})")


if __name__ == "__main__":
    main()
