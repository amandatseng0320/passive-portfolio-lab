"""
Tests for github_web/scripts/validate_export.py.
"""

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "github_web" / "scripts"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import validate_export


def test_price_cliff_gate_rejects_etf_seven_x_gap():
    errors = validate_export.validate_price_history_cliffs(
        {"0052.TW": [["2025-11-14", 700.0], ["2025-11-17", 100.0]]},
        {"0052.TW": "TW_ETF"},
    )

    assert errors
    assert "0052.TW" in errors[0]


def test_price_cliff_gate_allows_real_crypto_four_point_five_x_move():
    errors = validate_export.validate_price_history_cliffs(
        {"DOGE-USD": [["2021-01-27", 0.2089], ["2021-01-28", 0.9521]]},
        {"DOGE-USD": "CRYPTO"},
    )

    assert errors == []


def test_price_cliff_gate_rejects_crypto_above_six_x_move():
    errors = validate_export.validate_price_history_cliffs(
        {"DOGE-USD": [["2021-01-27", 1.0], ["2021-01-28", 6.1]]},
        {"DOGE-USD": "CRYPTO"},
    )

    assert errors
    assert "exceeds 6.0x" in errors[0]


def test_price_cliff_gate_fails_closed_for_unknown_ticker():
    errors = validate_export.validate_price_history_cliffs(
        {"UNKNOWN": [["2026-01-01", 1.0], ["2026-01-02", 1.1]]},
        {},
    )

    assert errors
    assert "unknown category" in errors[0]
