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

OUTPUT = Path(__file__).resolve().parents[1] / "src" / "ppl-data.js"
PROFILE_OUTPUT = Path(__file__).resolve().parents[1] / "src" / "ppl-asset-profiles.js"
EXPECTED_MIN_ASSETS = 30   # alert if fewer than 30 assets exported
# Keep EXPECTED_ASSETS in sync with ASSET_POOL in screening.py when adding/removing assets
EXPECTED_ASSETS = 37
MAX_STALENESS_HOURS = 25   # allow 1 hour of drift past the 24-hour schedule


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

    # 5. Optional asset profile export. Required once the web scraping showcase
    # pipeline has generated the static profile file.
    if PROFILE_OUTPUT.exists():
        profile_content = PROFILE_OUTPUT.read_text(encoding="utf-8")
        if "const PPL_ASSET_PROFILES" not in profile_content:
            errors.append("PROFILE: const PPL_ASSET_PROFILES missing")
        profile_match = re.search(r"const PPL_ASSET_PROFILES = (\{.*\});", profile_content, re.DOTALL)
        if profile_match:
            try:
                profiles = json.loads(profile_match.group(1))
            except json.JSONDecodeError as exc:
                errors.append(f"PROFILE: PPL_ASSET_PROFILES is not valid JSON ({exc})")
            else:
                if len(profiles) != EXPECTED_ASSETS:
                    errors.append(
                        f"PROFILE COUNT: {len(profiles)} profiles exported (expected {EXPECTED_ASSETS})"
                    )
                for ticker, profile in profiles.items():
                    if profile.get("ticker") != ticker:
                        errors.append(f"PROFILE: key/ticker mismatch for {ticker}")
                    if not profile.get("summary"):
                        errors.append(f"PROFILE: missing summary for {ticker}")
                    if profile.get("collectionMethod") != "web_scraping":
                        errors.append(f"PROFILE: {ticker} was not collected by web scraping")
                    if not profile.get("sourceSummary"):
                        errors.append(f"PROFILE: missing sourceSummary for {ticker}")
                    source_url = str(profile.get("sourceUrl", ""))
                    if not source_url.startswith("https://"):
                        errors.append(f"PROFILE: invalid sourceUrl for {ticker}: {source_url}")
                    if any(
                        blocked in source_url
                        for blocked in ("finance.yahoo.com", "tw.stock.yahoo.com", "coinmarketcap.com")
                    ):
                        errors.append(f"PROFILE: disallowed profile source for {ticker}: {source_url}")
                    if profile.get("assetType") != "Crypto":
                        expense_ratio = str(profile.get("expenseRatio", ""))
                        if (
                            "See source profile" in expense_ratio
                            or "%" not in expense_ratio
                            or "約" in expense_ratio
                            or "+" in expense_ratio
                        ):
                            errors.append(f"PROFILE: missing ETF expense ratio for {ticker}")
                        if not str(profile.get("expenseRatioSourceUrl", "")).startswith("https://"):
                            errors.append(f"PROFILE: missing expenseRatioSourceUrl for {ticker}")
                        if profile.get("expenseRatioCollectionMethod") != "web_scraping":
                            errors.append(f"PROFILE: invalid expense ratio collection for {ticker}")
                        if ticker.endswith((".TW", ".TWO")):
                            if profile.get("expenseRatioFormula") != "managementFee + custodianFee":
                                errors.append(f"PROFILE: invalid TW ETF expense formula for {ticker}")
                            if not profile.get("managementFee") or not profile.get("custodianFee"):
                                errors.append(f"PROFILE: missing TW ETF fee component for {ticker}")
                    elif "expenseRatio" in profile:
                        errors.append(f"PROFILE: crypto should not expose ETF expenseRatio for {ticker}")
        else:
            errors.append("PROFILE: PPL_ASSET_PROFILES JSON block not parseable")

    if errors:
        print("Export validation FAILED:")
        for e in errors:
            print(f"  {e}")
        sys.exit(1)

    fx_val = float(fx_match.group(1)) if fx_match else 0.0  # fx_match non-None here (else appended to errors)
    print(f"Export validation passed ({asset_count} assets, FX={fx_val:.2f})")


if __name__ == "__main__":
    main()
