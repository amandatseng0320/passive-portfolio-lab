#!/usr/bin/env python3
"""Export normalized asset profiles to a static JavaScript data file."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
sys.path.insert(0, str(REPO_ROOT / "streamlit_dashboard"))
sys.path.insert(0, str(SCRIPT_DIR))

from src.processing.screening import ASSET_POOL
from schema import validate_profiles


INPUT = REPO_ROOT / "data" / "asset_profiles" / "asset_profiles.json"
OUTPUT = REPO_ROOT / "github_web" / "src" / "ppl-asset-profiles.js"


def load_profiles(path: Path = INPUT) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    validate_profiles(payload, {asset["ticker"] for asset in ASSET_POOL})
    return payload


def build_js(payload: dict) -> str:
    profile_map = {profile["ticker"]: profile for profile in payload["profiles"]}
    encoded = json.dumps(profile_map, ensure_ascii=False, indent=2)
    return (
        "// ppl-asset-profiles.js — normalized ETF and crypto profile data\n"
        "// Generated from data/asset_profiles/asset_profiles.json\n"
        f'const PPL_ASSET_PROFILE_UPDATED_AT = "{payload["generatedAt"]}";\n'
        f"const PPL_ASSET_PROFILES = {encoded};\n"
    )


def write_js(input_path: Path = INPUT, output_path: Path = OUTPUT) -> None:
    payload = load_profiles(input_path)
    output_path.write_text(build_js(payload), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=INPUT)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    write_js(args.input, args.output)
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
