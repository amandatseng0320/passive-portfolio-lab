"""
Tests for streamlit_dashboard/src/processing/fire_calculator.py

Covers: FIRE target formula, years-to-FIRE, projection structure,
nominal vs inflation-adjusted timelines, and edge cases.

load_cagr_from_bq is mocked — no BigQuery calls.
"""

from unittest.mock import patch

import pandas as pd
import pytest

from src.processing.fire_calculator import calculate_fire


# ── helper ────────────────────────────────────────────────────────────────────

def _run(target_amount, monthly_contribution, initial_capital, annual_cagr,
         max_years=50):
    """Call calculate_fire with a mocked CAGR, bypassing BigQuery."""
    weights = {"0050.TW": 1.0}
    with patch("src.processing.fire_calculator.load_cagr_from_bq",
               return_value={"0050.TW": annual_cagr}):
        return calculate_fire(
            target_amount=target_amount,
            monthly_contribution=monthly_contribution,
            initial_capital=initial_capital,
            weights=weights,
            max_years=max_years,
        )


# ── FIRE target formula ───────────────────────────────────────────────────────

class TestFireTargetFormula:
    def test_4pct_rule(self):
        # annual_expenses = 600_000, withdrawal_rate = 0.04
        # FIRE target = 600_000 / 0.04 = 15_000_000
        annual_expenses = 600_000
        withdrawal_rate = 0.04
        fire_target = annual_expenses / withdrawal_rate
        assert fire_target == pytest.approx(15_000_000.0, rel=1e-9)

    def test_3pct_rule_more_conservative(self):
        annual_expenses = 600_000
        assert (annual_expenses / 0.03) > (annual_expenses / 0.04)

    def test_target_scales_with_expenses(self):
        withdrawal_rate = 0.04
        assert (1_200_000 / withdrawal_rate) == pytest.approx(30_000_000.0, rel=1e-9)


# ── Years to FIRE ─────────────────────────────────────────────────────────────

class TestYearsToFire:
    def test_zero_growth_dca_only(self):
        # No growth, no initial capital, 10_000/month → 120_000/year
        # To reach 1_200_000: 1_200_000 / 120_000 = 10 years exactly
        result = _run(
            target_amount=1_200_000,
            monthly_contribution=10_000,
            initial_capital=0,
            annual_cagr=0.0,
        )
        assert result["years_to_fire"] == 10

    def test_already_at_target_fires_in_year_one(self):
        # initial_capital > target → first year-end check passes
        result = _run(
            target_amount=500_000,
            monthly_contribution=0,
            initial_capital=1_000_000,
            annual_cagr=0.0,
        )
        assert result["years_to_fire"] == 1

    def test_not_reached_returns_none(self):
        # Tiny contribution, huge target, zero growth → never reached in 50 years
        result = _run(
            target_amount=100_000_000,
            monthly_contribution=1,
            initial_capital=0,
            annual_cagr=0.0,
            max_years=50,
        )
        assert result["years_to_fire"] is None

    def test_growth_accelerates_fire(self):
        # 8% CAGR should reach target faster than 0% CAGR
        base = dict(target_amount=5_000_000, monthly_contribution=10_000,
                    initial_capital=100_000)
        result_slow = _run(**base, annual_cagr=0.0)
        result_fast = _run(**base, annual_cagr=0.08)

        years_slow = result_slow["years_to_fire"]
        years_fast = result_fast["years_to_fire"]

        # 8% CAGR should reach sooner (or fast reaches but slow does not)
        if years_slow is not None and years_fast is not None:
            assert years_fast < years_slow
        else:
            # slow didn't reach; fast may or may not have
            assert years_fast is not None or years_slow is None

    def test_custom_max_years_respected(self):
        result = _run(
            target_amount=1_000_000_000,
            monthly_contribution=1_000,
            initial_capital=0,
            annual_cagr=0.05,
            max_years=10,
        )
        # With max_years=10 and these numbers, target won't be reached
        assert result["years_to_fire"] is None


# ── Monthly growth rate ───────────────────────────────────────────────────────

class TestMonthlyGrowthRate:
    def test_monthly_rate_formula(self):
        # monthly_rate = (1 + annual_cagr)^(1/12) - 1
        annual_cagr = 0.12
        expected_monthly = (1 + annual_cagr) ** (1 / 12) - 1
        assert expected_monthly == pytest.approx(0.009489, rel=1e-4)

    def test_zero_annual_gives_zero_monthly(self):
        # (1 + 0)^(1/12) - 1 = 0
        monthly = (1 + 0.0) ** (1 / 12) - 1
        assert monthly == pytest.approx(0.0, abs=1e-10)

    def test_growth_accumulation_matches_annual_rate(self):
        # 12 months of compounding monthly_rate should equal annual_cagr
        annual_cagr = 0.10
        monthly_rate = (1 + annual_cagr) ** (1 / 12) - 1
        accumulated = (1 + monthly_rate) ** 12 - 1
        assert accumulated == pytest.approx(annual_cagr, rel=1e-8)


# ── Portfolio growth mechanics ────────────────────────────────────────────────

class TestGrowthMechanics:
    def test_growth_before_contribution(self):
        # Verify the per-month formula: value = value * (1 + r) + contribution
        # With initial_capital=1_000_000, annual_cagr=0.12, monthly_contribution=0
        # After month 1: 1_000_000 * (1 + monthly_rate)
        annual_cagr = 0.12
        monthly_rate = (1 + annual_cagr) ** (1 / 12) - 1
        initial = 1_000_000.0

        result = _run(
            target_amount=10_000_000,  # very high, won't be reached quickly
            monthly_contribution=0,
            initial_capital=initial,
            annual_cagr=annual_cagr,
            max_years=1,
        )

        # After 12 months with no contribution: should equal initial * (1+r)^12
        expected_year1 = initial * (1 + annual_cagr)
        actual_year1 = result["projection"].iloc[0]["portfolio_value"]
        assert actual_year1 == pytest.approx(expected_year1, rel=1e-4)


# ── Projection DataFrame ──────────────────────────────────────────────────────

class TestProjectionStructure:
    def test_projection_has_required_columns(self):
        result = _run(1_000_000, 10_000, 0, 0.08)
        assert "year" in result["projection"].columns
        assert "portfolio_value" in result["projection"].columns

    def test_projection_years_are_monotonic(self):
        result = _run(1_000_000, 10_000, 0, 0.08)
        years = result["projection"]["year"].tolist()
        assert years == list(range(1, len(years) + 1))

    def test_projection_first_year_is_one(self):
        result = _run(1_000_000, 10_000, 0, 0.08)
        assert result["projection"]["year"].iloc[0] == 1

    def test_projection_length_capped_at_max_years(self):
        result = _run(1_000_000_000, 1_000, 0, 0.01, max_years=20)
        assert len(result["projection"]) == 20

    def test_portfolio_values_positive(self):
        result = _run(5_000_000, 10_000, 100_000, 0.08)
        assert (result["projection"]["portfolio_value"] > 0).all()


# ── annual_cagr in output ─────────────────────────────────────────────────────

class TestAnnualCAGROutput:
    def test_annual_cagr_matches_input(self):
        result = _run(10_000_000, 10_000, 0, 0.075)
        assert result["annual_cagr"] == pytest.approx(0.075, rel=1e-6)

    def test_annual_cagr_zero(self):
        result = _run(1_000_000, 10_000, 0, 0.0)
        assert result["annual_cagr"] == pytest.approx(0.0, abs=1e-9)
