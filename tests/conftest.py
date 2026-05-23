"""
conftest.py — shared fixtures for Passive Portfolio Lab tests.

All tests must run without network access. BigQuery, Yahoo Finance,
FRED, and Gemini calls are mocked at the call sites.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# ── sys.path setup ─────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "streamlit_dashboard"))
sys.path.insert(0, str(REPO_ROOT / "github_web" / "scripts"))


# ── Shared price fixtures ──────────────────────────────────────────────────────

def _make_price_df(ticker: str, category: str, closes, start: str = "2021-01-04") -> pd.DataFrame:
    """Helper: build a minimal prices DataFrame for a single ticker."""
    dates = pd.date_range(start, periods=len(closes), freq="D")
    return pd.DataFrame({
        "date": dates,
        "ticker": ticker,
        "close": np.array(closes, dtype=float),
        "category": category,
    })


@pytest.fixture
def flat_twd_30():
    """30 daily rows of constant price 100 for 0050.TW (TWD)."""
    return _make_price_df("0050.TW", "TW_ETF", [100.0] * 30)


@pytest.fixture
def constant_fx_30():
    """Constant TWD/USD rate of 30.0 over 30 days starting 2021-01-04."""
    dates = pd.date_range("2021-01-04", periods=30, freq="D")
    return pd.Series(30.0, index=dates)


@pytest.fixture
def minimal_metrics_df():
    """
    Fake asset_metrics DataFrame with one row per ASSET_POOL ticker.
    Values are plausible fractions (NOT percentages).
    """
    from src.processing.screening import ASSET_POOL

    rows = [
        {
            "ticker": a["ticker"],
            "name": a["name"],
            "category": a["category"],
            "data_start": "2018-01-01",
            "data_end": "2025-12-31",
            "cagr": 0.10,
            "volatility": 0.18,
            "max_drawdown": -0.25,
            "sharpe_ratio": 0.44,
            "recovery_period_days": 180,
            "recovery_status": "Recovered",
            "worst_year": -0.15,
            "worst_year_label": 2022,
        }
        for a in ASSET_POOL
    ]
    return pd.DataFrame(rows)
