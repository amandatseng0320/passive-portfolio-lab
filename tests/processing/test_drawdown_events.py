"""
Tests for streamlit_dashboard/src/processing/drawdown_events.py

Covers: episode detection, peak/trough/recovery dates, drawdown depth,
duration and recovery days, min_depth filter, top_n parameter,
still-underwater episodes, and historical event labelling.

No mocking required — this module is pure pandas/numpy.
"""

import numpy as np
import pandas as pd
import pytest

from src.processing.drawdown_events import identify_drawdown_events, match_event_label


# ── helpers ───────────────────────────────────────────────────────────────────

def _run(closes, dates=None, top_n=5, min_depth_pct=0.02):
    if dates is None:
        dates = pd.date_range("2020-01-01", periods=len(closes), freq="D")
    return identify_drawdown_events(dates, closes, top_n=top_n,
                                   min_depth_pct=min_depth_pct)


# ── No drawdown ───────────────────────────────────────────────────────────────

class TestNoDrawdown:
    def test_monotonic_increase_returns_empty(self):
        result = _run(list(range(100, 200)))
        assert result.empty

    def test_flat_prices_returns_empty(self):
        result = _run([100.0] * 50)
        assert result.empty

    def test_empty_series_returns_empty_frame(self):
        result = identify_drawdown_events([], [])
        assert result.empty
        expected_cols = {"rank", "peak_date", "trough_date", "recovery_date",
                         "drawdown_pct", "duration_days", "recovery_days", "event_label"}
        assert expected_cols.issubset(set(result.columns))


# ── Single episode ────────────────────────────────────────────────────────────

class TestSingleEpisode:
    def test_peak_trough_recovery_dates_correct(self):
        # [100, 90, 80, 100]: peak=Jan1, trough=Jan3, recovery=Jan4
        dates = pd.date_range("2020-01-01", periods=4, freq="D")
        result = _run([100.0, 90.0, 80.0, 100.0], dates=dates)

        assert len(result) == 1
        row = result.iloc[0]
        assert row["peak_date"] == pd.Timestamp("2020-01-01")
        assert row["trough_date"] == pd.Timestamp("2020-01-03")
        assert row["recovery_date"] == pd.Timestamp("2020-01-04")

    def test_drawdown_depth_correct(self):
        # 80/100 - 1 = -0.20
        result = _run([100.0, 90.0, 80.0, 100.0])
        assert result.iloc[0]["drawdown_pct"] == pytest.approx(-0.20, rel=1e-6)

    def test_duration_and_recovery_days(self):
        dates = pd.date_range("2020-01-01", periods=4, freq="D")
        result = _run([100.0, 90.0, 80.0, 100.0], dates=dates)
        row = result.iloc[0]
        # peak Jan 1 → trough Jan 3 = 2 days
        assert row["duration_days"] == 2
        # trough Jan 3 → recovery Jan 4 = 1 day
        assert row["recovery_days"] == 1

    def test_rank_is_one(self):
        result = _run([100.0, 90.0, 80.0, 100.0])
        assert result.iloc[0]["rank"] == 1


# ── Still-underwater episode ──────────────────────────────────────────────────

class TestUnderwaterEpisode:
    def test_no_recovery_returns_nat_and_nan(self):
        result = _run([100.0, 80.0])  # only 2 points, never recovers
        assert len(result) == 1
        row = result.iloc[0]
        assert pd.isna(row["recovery_date"])
        assert pd.isna(row["recovery_days"])

    def test_drawdown_depth_still_computed(self):
        result = _run([100.0, 60.0])
        assert result.iloc[0]["drawdown_pct"] == pytest.approx(-0.40, rel=1e-6)


# ── Two independent episodes ──────────────────────────────────────────────────

class TestTwoEpisodes:
    def test_two_episodes_returned(self):
        # [100, 80, 120, 90, 120]
        # Episode 1: peak=100 trough=80 (-20%) recovery at 120
        # Episode 2: peak=120 trough=90 (-25%) recovery at 120
        result = _run([100.0, 80.0, 120.0, 90.0, 120.0])
        assert len(result) == 2

    def test_ranked_deepest_first(self):
        result = _run([100.0, 80.0, 120.0, 90.0, 120.0])
        assert result.iloc[0]["drawdown_pct"] < result.iloc[1]["drawdown_pct"]

    def test_second_episode_deeper_ranks_first(self):
        # Episode 2 (-25%) is deeper than Episode 1 (-20%)
        result = _run([100.0, 80.0, 120.0, 90.0, 120.0])
        assert result.iloc[0]["drawdown_pct"] == pytest.approx(-0.25, rel=1e-4)

    def test_first_episode_shallower_ranks_second(self):
        result = _run([100.0, 80.0, 120.0, 90.0, 120.0])
        assert result.iloc[1]["drawdown_pct"] == pytest.approx(-0.20, rel=1e-4)


# ── min_depth_pct filter ──────────────────────────────────────────────────────

class TestMinDepthFilter:
    def test_tiny_drawdown_filtered_out(self):
        # -1% drawdown, filter is 2% → should return empty
        result = _run([100.0, 99.0, 100.0], min_depth_pct=0.02)
        assert result.empty

    def test_exactly_at_threshold_included(self):
        # -2% drawdown, filter is 2% → should NOT be filtered
        result = _run([100.0, 98.0, 100.0], min_depth_pct=0.02)
        assert len(result) == 1

    def test_below_threshold_filtered(self):
        result = _run([100.0, 99.5, 100.0], min_depth_pct=0.02)
        assert result.empty


# ── top_n parameter ───────────────────────────────────────────────────────────

class TestTopN:
    def test_top_n_limits_output(self):
        # Build 5 episodes of varying depth
        closes = (
            [100, 85, 100]    # -15%
            + [110, 90, 110]  # -18%
            + [120, 95, 120]  # -21%
            + [130, 100, 130] # -23%
            + [140, 105, 140] # -25%
        )
        result_all = _run(closes, top_n=5)
        result_top3 = _run(closes, top_n=3)
        assert len(result_all) <= 5
        assert len(result_top3) <= 3

    def test_top_1_returns_deepest(self):
        closes = [100, 85, 100, 110, 70, 110]
        result = _run(closes, top_n=1)
        assert len(result) == 1
        # -70/110 drawdown should be deepest
        assert result.iloc[0]["drawdown_pct"] < -0.35


# ── Historical event labelling ────────────────────────────────────────────────

class TestEventLabels:
    def test_covid_crash_labelled(self):
        # Episode during COVID window: peak ≈ Feb 2020, trough ≈ Mar 2020
        dates = pd.date_range("2020-02-15", periods=50, freq="D")
        closes = list(np.linspace(100, 60, 20)) + list(np.linspace(60, 100, 30))
        result = _run(closes, dates=dates)
        assert len(result) > 0
        label = result.iloc[0]["event_label"]
        assert "COVID" in label

    def test_no_matching_event_gives_dash(self):
        # Episode in an obscure time with no curated events
        dates = pd.date_range("1995-01-01", periods=4, freq="D")
        result = _run([100.0, 80.0, 80.0, 100.0], dates=dates)
        if len(result) > 0:
            assert result.iloc[0]["event_label"] == "—"

    def test_match_event_label_function_directly(self):
        # Test the helper function independently
        label = match_event_label(
            peak_date=pd.Timestamp("2020-03-01"),
            recovery_date=pd.Timestamp("2020-04-20"),
            trough_date=pd.Timestamp("2020-03-23"),
        )
        assert "COVID" in label

    def test_match_event_label_none_recovery(self):
        # recovery_date=None should use trough_date as endpoint
        label = match_event_label(
            peak_date=pd.Timestamp("2020-03-01"),
            recovery_date=None,
            trough_date=pd.Timestamp("2020-03-23"),
        )
        assert "COVID" in label

    def test_match_event_label_nat_recovery(self):
        # NaT should behave the same as None
        label = match_event_label(
            peak_date=pd.Timestamp("2020-03-01"),
            recovery_date=pd.NaT,
            trough_date=pd.Timestamp("2020-03-23"),
        )
        assert "COVID" in label


# ── Output schema ─────────────────────────────────────────────────────────────

class TestOutputSchema:
    REQUIRED_COLS = {
        "rank", "peak_date", "trough_date", "recovery_date",
        "drawdown_pct", "duration_days", "recovery_days", "event_label",
    }

    def test_non_empty_result_has_all_columns(self):
        result = _run([100.0, 80.0, 100.0])
        assert self.REQUIRED_COLS.issubset(set(result.columns))

    def test_empty_result_has_all_columns(self):
        result = identify_drawdown_events([], [])
        assert self.REQUIRED_COLS.issubset(set(result.columns))

    def test_drawdown_pct_always_negative(self):
        result = _run([100.0, 80.0, 120.0, 90.0, 120.0])
        assert (result["drawdown_pct"] < 0).all()

    def test_rank_starts_at_one(self):
        result = _run([100.0, 80.0, 100.0])
        assert result.iloc[0]["rank"] == 1
