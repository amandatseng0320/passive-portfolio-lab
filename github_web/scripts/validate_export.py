#!/usr/bin/env python3
"""
Validate that ppl-data.js was exported correctly.
Exits with code 1 if any check fails so GitHub Actions marks the step as failed.

Checks:
  1. Required JS globals are present
  2. Asset count is within expected range
  3. Export timestamp is fresh (< 25 hours old)
  4. FX rate is within plausible TWD/USD range (20–50)
"""
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

OUTPUT = Path(__file__).resolve().parents[1] / "src" / "ppl-data.js"
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

    if errors:
        print("Export validation FAILED:")
        for e in errors:
            print(f"  {e}")
        sys.exit(1)

    fx_val = float(fx_match.group(1)) if fx_match else 0.0  # fx_match non-None here (else appended to errors)
    print(f"Export validation passed ({asset_count} assets, FX={fx_val:.2f})")


if __name__ == "__main__":
    main()
