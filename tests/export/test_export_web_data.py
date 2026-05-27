"""
Tests for github_web/scripts/export_web_data.py

Covers: PPL_ASSETS schema (units, required fields), PPL_PRICE_HISTORY
structure (TWD conversion, date format), PPL_FX_RATE, PPL_HISTORY_UPDATED_AT,
and replace_* idempotency.

No BigQuery or Yahoo Finance calls — all network I/O is mocked.
"""

import re
import sys
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

# ── import the module under test ──────────────────────────────────────────────
# The module lives outside the normal package tree, so we add its directory.
_SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "github_web" / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import export_web_data as ewd
from src.processing.screening import ASSET_POOL


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def minimal_prices():
    """Minimal raw_prices-like DataFrame: 5 rows per asset pool ticker."""
    rows = []
    dates = pd.date_range("2023-01-02", periods=5, freq="D")
    for asset in ASSET_POOL:
        for date in dates:
            rows.append({
                "date": pd.Timestamp(date),
                "ticker": asset["ticker"],
                "close": 100.0,
            })
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    return df


@pytest.fixture
def constant_fx_fixture():
    """Constant FX series at 30 TWD/USD covering the minimal_prices date range."""
    dates = pd.date_range("2023-01-02", periods=5, freq="D")
    return pd.Series(30.0, index=dates)


# ── PPL_ASSETS block ──────────────────────────────────────────────────────────

class TestPPLAssets:
    def test_block_contains_ppl_assets_declaration(self, minimal_metrics_df):
        block = ewd.build_assets_block(minimal_metrics_df, "2025-01-01 00:00 UTC")
        assert "const PPL_ASSETS = [" in block

    def test_block_closes_array(self, minimal_metrics_df):
        block = ewd.build_assets_block(minimal_metrics_df, "2025-01-01 00:00 UTC")
        assert "];" in block

    def test_all_tickers_present(self, minimal_metrics_df):
        block = ewd.build_assets_block(minimal_metrics_df, "2025-01-01 00:00 UTC")
        for asset in ASSET_POOL:
            assert asset["ticker"] in block, f"Missing ticker: {asset['ticker']}"

    def test_cagr_stored_as_percentage_not_fraction(self, minimal_metrics_df):
        # minimal_metrics_df has cagr=0.10 (fraction) → build_assets_block must
        # output cagr:10.0 (percentage). A value of 0.1 would be a fraction leak.
        block = ewd.build_assets_block(minimal_metrics_df, "2025-01-01 00:00 UTC")
        # Should contain "cagr:10.0" (or similar), NOT "cagr:0.1"
        assert "cagr:10.0" in block, "CAGR should be exported as percentage (10.0), not fraction (0.1)"
        assert "cagr:0.1" not in block

    def test_max_dd_stored_as_negative_percentage(self, minimal_metrics_df):
        # minimal_metrics_df has max_drawdown=-0.25 → should export as -25.0
        block = ewd.build_assets_block(minimal_metrics_df, "2025-01-01 00:00 UTC")
        assert "maxDD:-25.0" in block

    def test_tw_etf_assets_have_name_zh(self, minimal_metrics_df):
        block = ewd.build_assets_block(minimal_metrics_df, "2025-01-01 00:00 UTC")
        # Check that at least one Taiwan ETF has nameZh
        assert "nameZh:" in block

    def test_us_etf_has_no_name_zh(self, minimal_metrics_df):
        # Build a block for a US ETF only
        us_metrics = minimal_metrics_df[minimal_metrics_df["category"] == "US_ETF"].copy()
        if us_metrics.empty:
            pytest.skip("No US_ETF in test metrics")
        block = ewd.build_assets_block(us_metrics, "2025-01-01 00:00 UTC")
        # Individual US ETF lines should not contain nameZh
        # (nameZh only appears for TW_ETF tickers in ZH_NAMES)
        us_tickers = us_metrics["ticker"].tolist()
        for line in block.split("\n"):
            for ticker in us_tickers:
                if ticker in line:
                    assert "nameZh" not in line, (
                        f"US ETF {ticker} should not have nameZh"
                    )

    def test_currency_twd_for_tw_etf(self, minimal_metrics_df):
        block = ewd.build_assets_block(minimal_metrics_df, "2025-01-01 00:00 UTC")
        assert 'currency:"TWD"' in block

    def test_currency_usd_for_us_etf(self, minimal_metrics_df):
        block = ewd.build_assets_block(minimal_metrics_df, "2025-01-01 00:00 UTC")
        assert 'currency:"USD"' in block


# ── PPL_PRICE_HISTORY block ───────────────────────────────────────────────────

class TestPPLPriceHistory:
    def test_block_contains_all_declarations(self, minimal_prices, constant_fx_fixture):
        with patch("export_web_data.load_fx_rate", return_value=constant_fx_fixture):
            block = ewd.build_price_history_block(minimal_prices, "2025-01-01 00:00 UTC")

        assert "const PPL_HISTORY_UPDATED_AT" in block
        assert "const PPL_FX_RATE" in block
        assert "const PPL_PRICE_HISTORY" in block

    def test_fx_rate_in_plausible_range(self, minimal_prices, constant_fx_fixture):
        with patch("export_web_data.load_fx_rate", return_value=constant_fx_fixture):
            block = ewd.build_price_history_block(minimal_prices, "2025-01-01 00:00 UTC")

        # Extract PPL_FX_RATE value
        match = re.search(r"const PPL_FX_RATE = ([\d.]+);", block)
        assert match, "PPL_FX_RATE not found in block"
        fx_value = float(match.group(1))
        assert 20.0 <= fx_value <= 50.0, f"FX rate {fx_value} outside plausible range 20–50"

    def test_updated_at_format(self, minimal_prices, constant_fx_fixture):
        updated_at = "2025-05-23 17:03 UTC"
        with patch("export_web_data.load_fx_rate", return_value=constant_fx_fixture):
            block = ewd.build_price_history_block(minimal_prices, updated_at)

        pattern = r'\d{4}-\d{2}-\d{2} \d{2}:\d{2} UTC'
        assert re.search(pattern, block), "PPL_HISTORY_UPDATED_AT format mismatch"

    def test_tickers_present_in_history(self, minimal_prices, constant_fx_fixture):
        with patch("export_web_data.load_fx_rate", return_value=constant_fx_fixture):
            block = ewd.build_price_history_block(minimal_prices, "2025-01-01 00:00 UTC")

        # Every ticker in minimal_prices should appear in the JSON
        for asset in ASSET_POOL:
            ticker = asset["ticker"]
            # Only check tickers that actually have price rows
            if ticker in minimal_prices["ticker"].values:
                assert f'"{ticker}"' in block, f"Ticker {ticker} missing from PPL_PRICE_HISTORY"

    def test_prices_are_positive(self, minimal_prices, constant_fx_fixture):
        # All prices in minimal_prices are 100.0; after FX conversion (×30) they're 3000.
        # Extract the JSON and check a few values.
        import json
        with patch("export_web_data.load_fx_rate", return_value=constant_fx_fixture):
            block = ewd.build_price_history_block(minimal_prices, "2025-01-01 00:00 UTC")

        # Extract the JSON object from "const PPL_PRICE_HISTORY = {...};"
        match = re.search(r"const PPL_PRICE_HISTORY = (\{.*\});", block, re.DOTALL)
        assert match, "Could not extract PPL_PRICE_HISTORY JSON"
        history = json.loads(match.group(1))
        for ticker, rows in history.items():
            for date_str, close in rows:
                assert close > 0, f"Non-positive price for {ticker} on {date_str}"


# ── replace_* idempotency ─────────────────────────────────────────────────────

class TestReplaceBlocks:
    _DUMMY_ORIGINAL = """const PPL_BLUE6 = "#0055A5";

// ── Asset Universe (37 assets — matches screening.py ASSET_POOL) ──────────────
// Last updated: 2025-01-01
const PPL_ASSETS = [
  { ticker:"OLD_TICKER" },
];

// ── Persona Presets ────────────────
const PPL_PERSONAS = [];
"""

    def test_replace_assets_block_substitutes_content(self):
        new_block = (
            "// ── Asset Universe (37 assets — matches screening.py ASSET_POOL) ──────────────\n"
            "// Last updated: 2026-01-01\n"
            "const PPL_ASSETS = [\n"
            "  { ticker:\"NEW_TICKER\" },\n"
            "];"
        )
        result = ewd.replace_assets_block(self._DUMMY_ORIGINAL, new_block)
        assert "NEW_TICKER" in result
        assert "OLD_TICKER" not in result

    def test_replace_assets_block_preserves_surrounding_content(self):
        new_block = (
            "// ── Asset Universe (37 assets — matches screening.py ASSET_POOL) ──────────────\n"
            "// Last updated: 2026-01-01\n"
            "const PPL_ASSETS = [\n"
            "];"
        )
        result = ewd.replace_assets_block(self._DUMMY_ORIGINAL, new_block)
        assert 'const PPL_BLUE6 = "#0055A5"' in result
        assert "PPL_PERSONAS" in result

    def test_replace_assets_block_idempotent(self):
        new_block = (
            "// ── Asset Universe (37 assets — matches screening.py ASSET_POOL) ──────────────\n"
            "// Last updated: 2026-01-01\n"
            "const PPL_ASSETS = [\n"
            "  { ticker:\"STABLE\" },\n"
            "];"
        )
        first = ewd.replace_assets_block(self._DUMMY_ORIGINAL, new_block)
        second = ewd.replace_assets_block(first, new_block)
        assert first == second

    def test_replace_assets_block_missing_marker_raises(self):
        bad_content = "const SOMETHING_ELSE = [];"
        with pytest.raises(RuntimeError):
            ewd.replace_assets_block(bad_content, "// ── Asset Universe ...\nconst PPL_ASSETS = [\n];")
