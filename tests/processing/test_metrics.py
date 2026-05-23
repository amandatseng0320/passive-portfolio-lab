"""
Tests for streamlit_dashboard/src/processing/metrics.py

Covers: CAGR, volatility (equity vs crypto annualization), max drawdown,
Sharpe ratio, worst year, and edge cases.

All tests use local DataFrames — no BigQuery calls.
"""

import numpy as np
import pandas as pd
import pytest

from src.processing.metrics import calculate_metrics


# ── helpers ───────────────────────────────────────────────────────────────────

def _df(ticker: str, category: str, closes, start: str = "2021-01-04") -> pd.DataFrame:
    dates = pd.date_range(start, periods=len(closes), freq="D")
    return pd.DataFrame({
        "date": dates,
        "ticker": ticker,
        "close": np.array(closes, dtype=float),
        "category": category,
    })


def _row(ticker: str, category: str, closes, start: str = "2021-01-04") -> pd.Series:
    """Run calculate_metrics and return the single result row."""
    df = _df(ticker, category, closes, start)
    result = calculate_metrics(df)
    assert len(result) == 1, f"Expected 1 row, got {len(result)}"
    return result.iloc[0]


# ── CAGR ─────────────────────────────────────────────────────────────────────

class TestCAGR:
    def test_flat_price_gives_zero_cagr(self):
        row = _row("0050.TW", "TW_ETF", [100.0] * 366)
        assert row["cagr"] == pytest.approx(0.0, abs=1e-6)

    def test_known_return_over_one_year(self):
        # 2021-01-04 to 2022-01-04 is 365 days → years ≈ 1.0
        # Price goes 100 → 121 → CAGR should be close to 0.21
        # (exact depends on (last_date - first_date).days / 365.0)
        closes = [100.0] + [100.0] * 364 + [121.0]  # 366 points
        row = _row("0050.TW", "TW_ETF", closes, start="2021-01-04")
        first_date = pd.Timestamp("2021-01-04")
        last_date = first_date + pd.Timedelta(days=365)
        years = 365 / 365.0  # exactly 1 for this span
        expected_cagr = (121.0 / 100.0) ** (1 / years) - 1
        assert row["cagr"] == pytest.approx(expected_cagr, rel=1e-4)

    def test_price_doubles_cagr_positive(self):
        closes = [100.0] + [100.0] * 729 + [200.0]  # 731 points ≈ 2 years
        row = _row("0050.TW", "TW_ETF", closes, start="2021-01-04")
        assert row["cagr"] > 0.40  # sqrt(2) - 1 ≈ 0.414
        assert row["cagr"] < 0.43

    def test_only_two_rows_still_computes(self):
        row = _row("0050.TW", "TW_ETF", [100.0, 110.0])
        assert row["cagr"] > 0.0


# ── Volatility ────────────────────────────────────────────────────────────────

class TestVolatility:
    def test_flat_price_zero_volatility(self):
        row = _row("0050.TW", "TW_ETF", [100.0] * 260)
        assert row["volatility"] == pytest.approx(0.0, abs=1e-10)

    def test_crypto_annualization_is_365(self):
        # Same alternating price series, different category.
        # Ratio of volatilities should equal sqrt(365/252).
        pattern = ([100.0, 101.0, 99.0, 102.0, 98.0] * 52)[:260]
        row_eq = _row("0050.TW", "TW_ETF",  pattern)
        row_cr = _row("BTC-USD", "CRYPTO", pattern)

        vol_eq = row_eq["volatility"]
        vol_cr = row_cr["volatility"]

        assert vol_eq > 0, "Equity vol should be nonzero with alternating prices"
        expected_ratio = np.sqrt(365 / 252)
        assert vol_cr / vol_eq == pytest.approx(expected_ratio, rel=1e-6)

    def test_equity_uses_252_annualization(self):
        # Create a single-return-of-1% series (2 points), verify formula.
        # std of [0.01] with ddof=1 → NaN; with 3 points std is nonzero.
        # Use: [100, 101, 100] → daily returns [0.01, -0.0099...]
        closes = [100.0, 101.0, 100.0] + [100.0] * 10
        row = _row("SPY", "US_ETF", closes)
        daily_returns = pd.Series(closes).pct_change().dropna()
        expected_vol = daily_returns.std() * np.sqrt(252)
        assert row["volatility"] == pytest.approx(expected_vol, rel=1e-6)


# ── Max Drawdown ──────────────────────────────────────────────────────────────

class TestMaxDrawdown:
    def test_no_drawdown_gives_zero(self):
        # Monotonically increasing prices
        row = _row("0050.TW", "TW_ETF", list(range(100, 200)))
        assert row["max_drawdown"] == pytest.approx(0.0, abs=1e-10)

    def test_simple_drawdown(self):
        # 100 → 120 → 80 → 120
        # Rolling max: [100, 120, 120, 120]
        # Drawdown at 80: (80/120) - 1 = -0.3333...
        row = _row("0050.TW", "TW_ETF", [100.0, 120.0, 80.0, 120.0])
        assert row["max_drawdown"] == pytest.approx(-1 / 3, rel=1e-4)

    def test_max_drawdown_is_most_severe(self):
        # Two crashes: -20% and -40%. The -40% should be reported.
        closes = (
            [100.0, 80.0, 100.0]    # -20% crash, recover
            + [200.0, 120.0, 200.0] # -40% crash, recover
        )
        row = _row("0050.TW", "TW_ETF", closes)
        assert row["max_drawdown"] == pytest.approx(-0.40, rel=1e-3)

    def test_max_drawdown_always_negative_or_zero(self):
        closes = [100.0, 90.0, 85.0, 110.0, 105.0, 120.0]
        row = _row("0050.TW", "TW_ETF", closes)
        assert row["max_drawdown"] <= 0.0


# ── Sharpe Ratio ──────────────────────────────────────────────────────────────

class TestSharpeRatio:
    def test_zero_volatility_returns_zero_sharpe(self):
        # Flat prices → volatility = 0 → sharpe = 0 (guarded in code)
        row = _row("0050.TW", "TW_ETF", [100.0] * 260)
        assert row["sharpe_ratio"] == pytest.approx(0.0, abs=1e-6)

    def test_sharpe_formula_matches_expected(self):
        # Use a series with computable CAGR and volatility, then verify.
        closes = [100.0 * (1.001 ** i) for i in range(252)]  # ~28% annual
        row = _row("0050.TW", "TW_ETF", closes)

        cagr = row["cagr"]
        vol = row["volatility"]
        expected_sharpe = (cagr - 0.02) / vol
        assert row["sharpe_ratio"] == pytest.approx(expected_sharpe, rel=1e-4)

    def test_negative_sharpe_when_cagr_below_risk_free(self):
        # Price declines over time → CAGR < 0 < 0.02 → Sharpe < 0
        closes = [100.0] + [99.0 * (0.999 ** i) for i in range(1, 100)]
        row = _row("0050.TW", "TW_ETF", closes)
        assert row["sharpe_ratio"] < 0.0


# ── Worst Year ────────────────────────────────────────────────────────────────

class TestWorstYear:
    def test_correct_worst_year_identified(self):
        # 2021: 100→130 (+30%)
        # 2022: 130→91 (-30%)
        dates_2021 = pd.date_range("2021-01-04", "2021-12-31", freq="D")
        dates_2022 = pd.date_range("2022-01-03", "2022-12-30", freq="D")
        closes_2021 = np.linspace(100.0, 130.0, len(dates_2021))
        closes_2022 = np.linspace(130.0, 91.0, len(dates_2022))

        df = pd.DataFrame({
            "date": list(dates_2021) + list(dates_2022),
            "ticker": "0050.TW",
            "close": np.concatenate([closes_2021, closes_2022]),
            "category": "TW_ETF",
        })
        result = calculate_metrics(df)
        row = result.iloc[0]

        assert row["worst_year_label"] == 2022
        # (91 - 130) / 130 = -0.3
        assert row["worst_year"] == pytest.approx(-0.3, rel=1e-2)

    def test_worst_year_is_negative_for_declining_year(self):
        # Create a series with one clearly bad year
        dates = pd.date_range("2020-01-04", periods=730, freq="D")
        # Year 1: flat, Year 2: sharp decline
        closes = [100.0] * 366 + list(np.linspace(100.0, 60.0, 364))
        df = pd.DataFrame({
            "date": dates,
            "ticker": "0050.TW",
            "close": np.array(closes, dtype=float),
            "category": "TW_ETF",
        })
        result = calculate_metrics(df)
        assert result.iloc[0]["worst_year"] < 0.0


# ── Edge cases ────────────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_single_row_skipped(self):
        df = _df("0050.TW", "TW_ETF", [100.0])
        result = calculate_metrics(df)
        assert len(result) == 0

    def test_multiple_tickers_processed_independently(self):
        df1 = _df("0050.TW", "TW_ETF",  [100.0] * 100)
        df2 = _df("BTC-USD",  "CRYPTO", [200.0] * 100)
        combined = pd.concat([df1, df2], ignore_index=True)
        result = calculate_metrics(combined)
        assert len(result) == 2
        tickers = set(result["ticker"].tolist())
        assert tickers == {"0050.TW", "BTC-USD"}

    def test_result_contains_required_columns(self):
        row = _row("0050.TW", "TW_ETF", [100.0, 110.0, 105.0, 115.0] * 10)
        required = {"ticker", "name", "category", "cagr", "volatility",
                    "max_drawdown", "sharpe_ratio", "worst_year", "worst_year_label"}
        assert required.issubset(set(row.index))
