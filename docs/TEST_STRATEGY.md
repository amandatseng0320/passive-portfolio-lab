# Test Strategy

Last updated: 2026-05-23

This document defines the test strategy for Passive Portfolio Lab. It explains
what to test, how to test it, what fixtures to use, and what success looks like.

---

## 1. Goals

1. Protect the core financial calculations from silent regressions.
2. Validate that `ppl-data.js` export produces the expected schema.
3. Verify that drawdown detection and FIRE projection logic is deterministic.
4. Give reviewers evidence that the math is correct without requiring live
   network calls.

---

## 2. Principles

- **No network calls in unit tests.** Tests must not call BigQuery, Yahoo
  Finance, FRED, or Gemini. Use local fixtures.
- **Deterministic.** Given the same input, the same output is produced every
  time. No randomness, no time-dependent logic in tests.
- **Fixture-first.** Build small, hand-calculated datasets where the expected
  answer can be verified by inspection (pencil-and-paper math).
- **Fail loudly.** A test that silently passes when a formula changes is worse
  than no test. Pin expected values to within reasonable float tolerance.
- **Fast.** The entire test suite should run in under 30 seconds on a
  developer machine.
- **Isolated.** Tests must not depend on environment variables for production
  services. Mock any `os.getenv` calls that would trigger network I/O.

---

## 3. Test Framework and Directory Layout

**Framework:** `pytest`  
**Location:** `tests/` at the repository root

Suggested structure:

```text
tests/
├── conftest.py                         # shared fixtures
├── processing/
│   ├── test_metrics.py                 # CAGR, volatility, Sharpe, max drawdown
│   ├── test_backtest.py                # combined backtest engine
│   ├── test_fire_calculator.py         # FIRE target, projection, nominal vs real
│   └── test_drawdown_events.py         # episode detection, event labelling
└── export/
    └── test_export_web_data.py         # ppl-data.js schema validation
```

---

## 4. Priority Test Targets

Ranked by risk impact (highest first):

| Priority | Module | What could silently break |
|---|---|---|
| P0 | `backtest.run_combined` | TWD portfolio value calculation; DCA timing; FX conversion logic |
| P0 | `fire_calculator.calculate_fire` | FIRE target formula; years-to-FIRE; nominal vs real timeline |
| P0 | `metrics.calculate_metrics` | CAGR formula; volatility annualization; Sharpe ratio |
| P1 | `drawdown_events.identify_drawdown_events` | Episode boundaries; trough identification; event labelling |
| P1 | `export_web_data.build_assets_block` | PPL_ASSETS schema; cagr/vol/maxDD unit (pct not fraction) |
| P1 | `export_web_data.build_price_history_block` | PPL_PRICE_HISTORY structure; USD→TWD conversion |
| P2 | `backtest.load_fx_rate` | FX outlier filter; date-range alignment (requires network mock) |
| P2 | `metrics.calculate_metrics` | Worst year; recovery period; crypto vs equity annualization |

---

## 5. Test Cases by Module

### 5.1 `metrics.calculate_metrics`

#### 5.1.1 CAGR — simple two-point case

**Fixture:** price series that doubles over exactly 4 years.  
`start_price = 100, end_price = 200, years = 4`

**Expected CAGR:** `(200/100)^(1/4) - 1 = 0.18921` (≈ 18.92%)

**Formula under test:**
```python
years = (last_date - first_date).days / 365.0
cagr = (end_price / start_price) ** (1 / years) - 1
```

#### 5.1.2 Volatility — known daily returns

**Fixture:** 253 daily closes produced from a known constant daily return.
For a constant daily return `r = 0.001` (0.1%), `std(returns) = 0`.
Use a series with 252 points of `r = 0.001` and one point of `r = 0.05` to
give a known nonzero std, verifiable by hand.

**Key checks:**
- Non-crypto asset uses `sqrt(252)` annualization.
- Crypto asset (`category = 'CRYPTO'`) uses `sqrt(365)` annualization.
- Verify the formula matches `daily_return.std() * sqrt(n_trading_days)`.

#### 5.1.3 Max drawdown — simple series

**Fixture:** `[100, 90, 80, 100, 75, 90]`  
Rolling max: `[100, 100, 100, 100, 100, 100]`  
Drawdown: `[0, -0.10, -0.20, 0, -0.25, -0.10]`

**Expected max_drawdown:** `-0.25`

#### 5.1.4 Sharpe ratio

**Formula under test:**
```python
sharpe = (cagr - 0.02) / volatility
```

**Fixture:** `cagr = 0.12, volatility = 0.20`  
**Expected:** `(0.12 - 0.02) / 0.20 = 0.50`

**Edge case:** `volatility = 0` → should return `sharpe = 0.0` (no ZeroDivisionError).

#### 5.1.5 Worst year

**Fixture:** Two full calendar years.  
Year 1: Jan 1 price = 100, Dec 31 price = 130 → return = 0.30  
Year 2: Jan 1 price = 130, Dec 31 price = 91 → return = -0.30

**Expected:** `worst_year = -0.30, worst_year_label = <year_2>`

---

### 5.2 `backtest.run_combined`

All tests use a local `prices_df` DataFrame and a mocked FX series. Do **not**
call `load_prices_for_tickers` or `load_fx_rate` in these tests.

#### 5.2.1 Lump-sum only (zero monthly contribution)

**Fixture:**
- Single TWD asset (no FX conversion needed)
- Prices: 10 daily rows, starting at 100, ending at 110
- `initial_investment = 10_000, monthly_contribution = 0`

**Expected:**
- Day 1 `portfolio_value ≈ 10_000` (within float tolerance)
- Day 10 `portfolio_value ≈ 10_000 * (110/100) = 11_000`
- `total_invested` stays at `10_000` throughout
- `total_return_pct[-1] ≈ 10.0`

#### 5.2.2 Monthly DCA — contribution timing

**Fixture:**
- Prices covering 2 full months (Jan + Feb)
- `initial_investment = 10_000, monthly_contribution = 5_000`
- 3 distinct months means at most 2 DCA events after day 1

**Expected:**
- After the first trading day of month 2: `total_invested = 15_000`
- After the first trading day of month 3: `total_invested = 20_000`
- `total_return_pct` formula verified against known values

#### 5.2.3 USD asset FX conversion

**Fixture:**
- One USD asset (ticker = `"SPY"`, no `.TW` suffix)
- Constant price series in USD = 100
- Constant FX rate = 30 TWD/USD

**Expected:**
- All TWD prices are `100 * 30 = 3_000` per share
- Portfolio value on day 1 (with `initial_investment = 30_000`):
  shares = `30_000 / 3_000 = 10`; value = `10 * 3_000 = 30_000`

#### 5.2.4 Mixed TWD + USD portfolio

**Fixture:**
- `"0050.TW"` (TWD, price = 100) with weight 0.5
- `"SPY"` (USD, price = 100) with weight 0.5, FX = 30
- `initial_investment = 100_000, monthly_contribution = 0`

**Expected day-1 allocation:**
- TWD portion: `50_000 / 100 = 500 shares of 0050.TW`
- USD portion: `50_000 / 3_000 = 16.67 shares of SPY`
- Day-1 value ≈ 100_000

#### 5.2.5 Weight normalization when a ticker is missing

**Fixture:**
- `tickers_weights = {"0050.TW": 0.5, "MISSING": 0.5}`
- Only `"0050.TW"` has price rows in `prices_df`

**Expected:**
- "MISSING" is excluded
- `"0050.TW"` gets 100% of the allocation
- No KeyError or crash

#### 5.2.6 Empty `tickers_weights` raises ValueError

```python
with pytest.raises(ValueError):
    run_backtest(..., tickers_weights={})
```

---

### 5.3 `fire_calculator.calculate_fire`

All tests should mock `load_cagr_from_bq` to return a known cagr dict.
Do **not** call BigQuery.

#### 5.3.1 FIRE target formula

This is not directly in `calculate_fire` but is used in the dashboard and
Looker scripts. Add a standalone test:

```python
def test_fire_target():
    annual_expenses = 600_000
    withdrawal_rate = 0.04
    assert fire_target(annual_expenses, withdrawal_rate) == 15_000_000
```

#### 5.3.2 Years to FIRE — simple case

**Fixture:**
- `target_amount = 1_200_000`
- `monthly_contribution = 10_000`
- `initial_capital = 0`
- `annual_cagr = 0.0` (zero growth, purely DCA)

**Expected:** `1_200_000 / 10_000 / 12 = 10 years` (no compounding)

**Verify:** `years_to_fire = 10`

#### 5.3.3 Immediate FIRE (initial capital already ≥ target)

**Fixture:**
- `initial_capital = 2_000_000`
- `target_amount = 1_500_000`
- `annual_cagr = 0.08`
- `monthly_contribution = 0`

**Expected:** `years_to_fire = 1` (first year-end check should already pass)

#### 5.3.4 FIRE not reached within max_years

**Fixture:**
- `initial_capital = 0, monthly_contribution = 1`
- `target_amount = 100_000_000`
- `annual_cagr = 0.0`

**Expected:** `years_to_fire = None`

#### 5.3.5 Monthly growth rate formula

```python
monthly_rate = (1 + annual_cagr) ** (1/12) - 1
```

For `annual_cagr = 0.12`:  
`monthly_rate ≈ 0.009489` (verify to 6 decimal places)

#### 5.3.6 Projection DataFrame structure

For any valid call, verify:
- `projection` is a DataFrame
- Columns include `year` (int) and `portfolio_value` (float)
- First row has `year = 1`
- Rows are monotonically increasing in `year`
- `len(projection) == min(years_run, max_years)`

---

### 5.4 `drawdown_events.identify_drawdown_events`

#### 5.4.1 Single episode — known depth

**Fixture:** `[100, 90, 80, 100]` (dates: Jan 1–4)

**Expected:**
- 1 episode
- `peak_date = Jan 1, trough_date = Jan 3, recovery_date = Jan 4`
- `drawdown_pct ≈ -0.20`
- `duration_days = 2, recovery_days = 1`

#### 5.4.2 Two independent episodes

**Fixture:** `[100, 80, 100, 90, 100]`

**Expected:**
- Episode 1: peak=day1, trough=day2, drawdown=-0.20, recovery=day3
- Episode 2: peak=day3, trough=day4, drawdown=-0.10, recovery=day5
- Ranked by depth: episode 1 first

#### 5.4.3 Still-underwater episode (no recovery)

**Fixture:** `[100, 80]` (only 2 points)

**Expected:**
- 1 episode
- `recovery_date = NaT`
- `recovery_days = NaN`

#### 5.4.4 Minimum depth filter

**Fixture:** Drawdown of only 1% (`[100, 99, 100]`)

**Expected:** `identify_drawdown_events(...)` returns an empty DataFrame
(filtered out by `min_depth_pct = 0.02`).

#### 5.4.5 top_n parameter

**Fixture:** 5 episodes of varying depths

**Expected:** `top_n=3` returns exactly 3 rows, ranked by depth (most severe first).

#### 5.4.6 Event label matching

**Fixture:** Episode with `peak_date = "2020-02-20"` and `trough_date = "2020-03-23"`

**Expected:** `event_label` contains `"COVID-19 pandemic crash"`.

#### 5.4.7 Empty series returns empty DataFrame

```python
result = identify_drawdown_events([], [])
assert result.empty
assert list(result.columns) == ["rank", "peak_date", "trough_date", "recovery_date",
                                 "drawdown_pct", "duration_days", "recovery_days", "event_label"]
```

---

### 5.5 `export_web_data` schema validation

These tests validate the structure of the output rather than running the export
(which requires BigQuery). Construct fake `metrics_df` and `prices_df` DataFrames
that mirror BigQuery output and call the builder functions directly.

#### 5.5.1 `PPL_ASSETS` has all required fields

**Fixture:** Minimal `metrics_df` with one row per asset in `ASSET_POOL`.

**Check for each asset object in the output:**
- `ticker` is a string
- `name` is a non-empty string
- `category` is one of `TW_ETF`, `US_ETF`, `CRYPTO`
- `cagr`, `vol`, `maxDD`, `sharpe`, `worstYear` are numbers (not None/NaN)
- `cagr`, `vol`, `maxDD`, `worstYear` are percentages (no value should be
  in the range 0.0–1.0 for typical assets, which would indicate a fraction)

#### 5.5.2 `PPL_ASSETS` `maxDD` is negative

All `maxDD` values must be ≤ 0 (drawdowns are negative percentages).

#### 5.5.3 Taiwan ETFs have `nameZh`, non-TW assets do not

For each element in the parsed `PPL_ASSETS`:
- If `category == "TW_ETF"`: `nameZh` property must be present and non-empty
- If `category != "TW_ETF"`: `nameZh` property may be absent (no check)

#### 5.5.4 `PPL_PRICE_HISTORY` structure

**Fixture:** `prices_df` with 5 rows per ticker, constant FX rate.

**Checks:**
- Each key is a ticker string
- Each value is a list of `[date_string, close_twd]` pairs
- `date_string` matches `YYYY-MM-DD` pattern
- `close_twd` is a positive float (USD assets multiplied by FX > 0)

#### 5.5.5 `PPL_FX_RATE` is a positive float

`PPL_FX_RATE` must be a number in the plausible range 20–50 (TWD/USD).

#### 5.5.6 `PPL_HISTORY_UPDATED_AT` format

Must match `r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2} UTC$"`.

#### 5.5.7 `replace_assets_block` is idempotent

Calling `replace_assets_block(content, new_block)` twice in a row must
produce the same output as calling it once.

---

## 6. What Not to Test Here

The following are **not** covered by this test strategy:

- Streamlit UI rendering (visual tests are out of scope for the current phase)
- BigQuery query correctness (tested by running the pipeline with real credentials)
- Looker Studio chart rendering (vendor-managed)
- GitHub Pages deployment (tested by GitHub Actions)
- Yahoo Finance API responses (depends on live network; mock FX rate instead)
- FRED API responses (depends on live network; test fallback behavior with mock)
- Gemini API responses (optional feature; test the absence path only)

---

## 7. Fixtures and Helpers

All fixtures live in `tests/conftest.py`.

### Recommended fixtures

```python
# tests/conftest.py

import pandas as pd
import numpy as np
import pytest

@pytest.fixture
def simple_price_series():
    """100→200 over exactly 4 years (CAGR verification)."""
    dates = pd.date_range("2020-01-01", "2024-01-01", periods=1461)
    closes = np.linspace(100, 200, 1461)
    return pd.DataFrame({"date": dates, "close": closes})

@pytest.fixture
def flat_twd_prices():
    """30 days of constant TWD price = 100 for a single TW ticker."""
    dates = pd.date_range("2023-01-01", periods=30)
    return pd.DataFrame({
        "date": dates,
        "ticker": "0050.TW",
        "close": 100.0,
    })

@pytest.fixture
def constant_fx():
    """Constant TWD/USD rate = 30 over a 30-day period."""
    dates = pd.date_range("2023-01-01", periods=30)
    return pd.Series(30.0, index=dates)

@pytest.fixture
def minimal_metrics_df():
    """One row per ASSET_POOL ticker with plausible but fake metrics."""
    from streamlit_dashboard.src.processing.screening import ASSET_POOL
    rows = []
    for asset in ASSET_POOL:
        rows.append({
            "ticker": asset["ticker"],
            "name": asset["name"],
            "category": asset["category"],
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
        })
    return pd.DataFrame(rows)
```

### Mocking BigQuery calls

Use `pytest-mock` or `unittest.mock.patch` to stub out `pandas_gbq.read_gbq`
and `pandas_gbq.to_gbq` in any test that imports a module that would otherwise
call BigQuery.

Example:

```python
from unittest.mock import patch

def test_something(minimal_metrics_df):
    with patch("pandas_gbq.read_gbq", return_value=minimal_metrics_df):
        result = some_function_that_calls_bq()
    assert ...
```

---

## 8. Numeric Tolerance

All floating-point assertions use `pytest.approx` with `rel=1e-4` (0.01%
relative tolerance) unless a tighter tolerance is needed for a specific formula
verification.

```python
assert result == pytest.approx(expected, rel=1e-4)
```

For financial percentages, an absolute tolerance of `0.01` (1 basis point) is
also acceptable when the expected value is near zero.

---

## 9. Running the Tests

```bash
# Install test dependencies
pip install pytest pytest-mock

# Run all tests
pytest tests/

# Run with coverage report
pip install pytest-cov
pytest tests/ --cov=streamlit_dashboard/src --cov-report=term-missing

# Run a specific module
pytest tests/processing/test_backtest.py -v
```

---

## 10. Test Coverage Goals

| Module | Target line coverage |
|---|---|
| `processing/metrics.py` | ≥ 80% |
| `processing/backtest.py` | ≥ 80% |
| `processing/fire_calculator.py` | ≥ 85% |
| `processing/drawdown_events.py` | ≥ 90% |
| `github_web/scripts/export_web_data.py` | ≥ 70% (builder functions only) |

Coverage targets are guidelines for initial implementation. They will be
revised upward as the test suite matures.

---

## 11. Regression Policy

If a financial formula is changed:

1. Update the formula code.
2. Update the corresponding test expected values.
3. Update `DATA_CONTRACT.md` if the output schema changes.
4. Add a note in `CHANGELOG.md`.

Do not "fix" a failing test by loosening the tolerance without understanding
why the formula changed. A failing test is evidence that something changed
in the math — treat it as a red flag, not an inconvenience.
