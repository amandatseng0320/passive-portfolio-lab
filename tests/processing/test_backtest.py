"""
Tests for streamlit_dashboard/src/processing/backtest.py

Covers: lump-sum only, DCA timing, USD→TWD FX conversion, mixed portfolios,
weight normalization, and input validation.

run_combined() is tested directly (no BigQuery call) by passing synthetic
prices_df. load_fx_rate is mocked wherever USD tickers appear.
"""

from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from src.processing.backtest import run_combined
from src.processing.screening import validate_tickers


# ── helpers ───────────────────────────────────────────────────────────────────

def _prices(tickers_closes: dict, start: str = "2021-01-04", freq: str = "D") -> pd.DataFrame:
    """
    Build a multi-ticker prices DataFrame.
    tickers_closes: {ticker: [closes]}
    All lists must be the same length.
    """
    rows = []
    n = len(next(iter(tickers_closes.values())))
    dates = pd.date_range(start, periods=n, freq=freq)
    for ticker, closes in tickers_closes.items():
        for date, close in zip(dates, closes):
            rows.append({"date": date, "ticker": ticker, "close": float(close)})
    return pd.DataFrame(rows)


def _fx(rate: float, start: str = "2021-01-04", periods: int = 30) -> pd.Series:
    dates = pd.date_range(start, periods=periods, freq="D")
    return pd.Series(rate, index=dates)


# ── Lump-sum only ─────────────────────────────────────────────────────────────

class TestLumpSum:
    def test_initial_value_equals_investment(self):
        prices = _prices({"0050.TW": [100.0] * 30})
        result = run_combined(prices, {"0050.TW": 1.0},
                              "2021-01-04", "2021-02-02",
                              initial_investment=10_000, monthly_contribution=0)
        assert result["portfolio_value"].iloc[0] == pytest.approx(10_000.0, rel=1e-6)

    def test_total_invested_stays_constant_with_zero_dca(self):
        prices = _prices({"0050.TW": [100.0] * 30})
        result = run_combined(prices, {"0050.TW": 1.0},
                              "2021-01-04", "2021-02-02",
                              initial_investment=10_000, monthly_contribution=0)
        assert (result["total_invested"] == 10_000.0).all()

    def test_value_tracks_price_change(self):
        # Price doubles from 100 to 200 over 10 days, no DCA
        # Shares bought = 10_000 / 100 = 100
        # Final value = 100 * 200 = 20_000
        closes = [100.0] * 9 + [200.0]
        prices = _prices({"0050.TW": closes})
        result = run_combined(prices, {"0050.TW": 1.0},
                              "2021-01-04", "2021-01-13",
                              initial_investment=10_000, monthly_contribution=0)
        assert result["portfolio_value"].iloc[-1] == pytest.approx(20_000.0, rel=1e-6)

    def test_total_return_pct_formula(self):
        closes = [100.0] * 5 + [150.0] * 5
        prices = _prices({"0050.TW": closes})
        result = run_combined(prices, {"0050.TW": 1.0},
                              "2021-01-04", "2021-01-13",
                              initial_investment=10_000, monthly_contribution=0)
        # Return should be (15000/10000 - 1) * 100 = 50.0
        assert result["total_return_pct"].iloc[-1] == pytest.approx(50.0, rel=1e-4)


# ── DCA timing ────────────────────────────────────────────────────────────────

class TestDCATiming:
    def test_total_invested_increments_monthly(self):
        # Cover at least 3 calendar months to get 2 DCA events.
        n = 95  # ~3 months from Jan 4
        prices = _prices({"0050.TW": [100.0] * n}, start="2021-01-04")
        result = run_combined(prices, {"0050.TW": 1.0},
                              "2021-01-04", "2021-04-08",
                              initial_investment=10_000,
                              monthly_contribution=5_000)

        # Initial + 2 DCA events (Feb 1 and Mar 1 fall within the range)
        final_invested = result["total_invested"].iloc[-1]
        assert final_invested >= 20_000.0  # at least 10k + 2*5k

    def test_day_one_gets_lump_sum_only(self):
        n = 90
        prices = _prices({"0050.TW": [100.0] * n}, start="2021-01-04")
        result = run_combined(prices, {"0050.TW": 1.0},
                              "2021-01-04", "2021-04-03",
                              initial_investment=50_000,
                              monthly_contribution=10_000)
        # On day one, total_invested must equal the initial_investment exactly
        assert result["total_invested"].iloc[0] == pytest.approx(50_000.0, rel=1e-6)

    def test_total_invested_is_non_decreasing(self):
        n = 90
        prices = _prices({"0050.TW": [100.0] * n}, start="2021-01-04")
        result = run_combined(prices, {"0050.TW": 1.0},
                              "2021-01-04", "2021-04-03",
                              initial_investment=10_000,
                              monthly_contribution=5_000)
        invested = result["total_invested"].values
        assert (np.diff(invested) >= 0).all()


# ── USD → TWD FX conversion ───────────────────────────────────────────────────

class TestFXConversion:
    def test_usd_asset_converted_via_fx(self):
        # SPY at USD 100, FX = 30 → TWD 3000 per share
        # initial_investment = 30_000 → 10 shares → value = 30_000
        prices = _prices({"SPY": [100.0] * 30})
        fx = _fx(30.0, start="2021-01-04", periods=30)

        with patch("src.processing.backtest.load_fx_rate", return_value=fx):
            result = run_combined(prices, {"SPY": 1.0},
                                  "2021-01-04", "2021-02-02",
                                  initial_investment=30_000,
                                  monthly_contribution=0)

        assert result["portfolio_value"].iloc[0] == pytest.approx(30_000.0, rel=1e-6)

    def test_usd_price_rise_reflected_in_twd(self):
        # USD price doubles from 100 to 200, FX constant at 30
        # Shares = 30_000 / (100*30) = 10; final value = 10 * (200*30) = 60_000
        closes = [100.0] * 9 + [200.0]
        prices = _prices({"SPY": closes})
        fx = _fx(30.0, start="2021-01-04", periods=10)

        with patch("src.processing.backtest.load_fx_rate", return_value=fx):
            result = run_combined(prices, {"SPY": 1.0},
                                  "2021-01-04", "2021-01-13",
                                  initial_investment=30_000,
                                  monthly_contribution=0)

        assert result["portfolio_value"].iloc[-1] == pytest.approx(60_000.0, rel=1e-4)

    def test_tw_ticker_not_converted(self):
        # 0050.TW ends with .TW → not converted; if load_fx_rate were called it
        # would raise (mock returns a series that would cause issues if used).
        prices = _prices({"0050.TW": [100.0] * 10})

        with patch("src.processing.backtest.load_fx_rate",
                   side_effect=AssertionError("load_fx_rate should not be called for TW tickers")):
            result = run_combined(prices, {"0050.TW": 1.0},
                                  "2021-01-04", "2021-01-13",
                                  initial_investment=10_000,
                                  monthly_contribution=0)

        assert result["portfolio_value"].iloc[0] == pytest.approx(10_000.0, rel=1e-6)


# ── Mixed TWD + USD portfolio ─────────────────────────────────────────────────

class TestMixedPortfolio:
    def test_mixed_portfolio_day_one_value(self):
        # 50% 0050.TW (TWD price 100), 50% SPY (USD 100, FX 30 → TWD 3000)
        # initial = 100_000
        # TW portion: 50_000 / 100 = 500 shares; value = 500 * 100 = 50_000
        # US portion: 50_000 / 3000 = 16.667 shares; value = 16.667 * 3000 = 50_000
        # Total: 100_000
        prices = _prices({
            "0050.TW": [100.0] * 30,
            "SPY": [100.0] * 30,
        })
        fx = _fx(30.0, start="2021-01-04", periods=30)

        with patch("src.processing.backtest.load_fx_rate", return_value=fx):
            result = run_combined(prices, {"0050.TW": 0.5, "SPY": 0.5},
                                  "2021-01-04", "2021-02-02",
                                  initial_investment=100_000,
                                  monthly_contribution=0)

        assert result["portfolio_value"].iloc[0] == pytest.approx(100_000.0, rel=1e-5)

    def test_weights_renormalized_when_ticker_missing(self):
        # Only 0050.TW has price data; "MISSING" has none.
        # 0050.TW should get 100% of the allocation.
        prices = _prices({"0050.TW": [100.0] * 10})  # MISSING not in prices_df

        result = run_combined(prices, {"0050.TW": 0.5, "MISSING": 0.5},
                              "2021-01-04", "2021-01-13",
                              initial_investment=10_000,
                              monthly_contribution=0)

        # All 10_000 invested in 0050.TW at 100 → 100 shares → value = 10_000
        assert result["portfolio_value"].iloc[0] == pytest.approx(10_000.0, rel=1e-6)


# ── Output schema ─────────────────────────────────────────────────────────────

class TestOutputSchema:
    def test_result_has_required_columns(self):
        prices = _prices({"0050.TW": [100.0] * 10})
        result = run_combined(prices, {"0050.TW": 1.0},
                              "2021-01-04", "2021-01-13",
                              initial_investment=10_000,
                              monthly_contribution=0)
        required = {"date", "portfolio_value", "total_invested",
                    "total_return_pct", "strategy"}
        assert required.issubset(set(result.columns))

    def test_strategy_column_is_combined(self):
        prices = _prices({"0050.TW": [100.0] * 10})
        result = run_combined(prices, {"0050.TW": 1.0},
                              "2021-01-04", "2021-01-13",
                              initial_investment=10_000,
                              monthly_contribution=0)
        assert (result["strategy"] == "Combined").all()

    def test_portfolio_value_is_positive(self):
        closes = [100.0, 50.0, 30.0, 20.0, 10.0]  # price collapses
        prices = _prices({"0050.TW": closes})
        result = run_combined(prices, {"0050.TW": 1.0},
                              "2021-01-04", "2021-01-08",
                              initial_investment=10_000,
                              monthly_contribution=0)
        assert (result["portfolio_value"] > 0).all()


class TestTickerWhitelist:
    """validate_tickers() must reject anything not in ASSET_POOL."""

    def test_valid_tickers_do_not_raise(self):
        # Sample of known-good tickers from ASSET_POOL
        validate_tickers(["0050.TW", "SPY", "BTC-USD"])

    def test_empty_list_does_not_raise(self):
        validate_tickers([])

    def test_unknown_ticker_raises(self):
        with pytest.raises(ValueError, match="not in ASSET_POOL"):
            validate_tickers(["AAPL"])

    def test_sql_injection_attempt_raises(self):
        with pytest.raises(ValueError, match="not in ASSET_POOL"):
            validate_tickers(["0050.TW', 'x'; DROP TABLE raw_prices; --"])

    def test_mix_of_valid_and_invalid_raises(self):
        with pytest.raises(ValueError, match="not in ASSET_POOL"):
            validate_tickers(["0050.TW", "NOTREAL"])
