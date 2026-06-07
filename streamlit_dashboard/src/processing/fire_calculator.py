import numpy as np
import pandas as pd
import pandas_gbq
from .screening import validate_tickers
from .utils import get_bq_config


def load_cagr_from_bq(tickers: list) -> dict:
    """
    Load CAGR values for specified tickers from BigQuery asset_metrics table.
    Returns a dict: {ticker: cagr}
    """
    validate_tickers(tickers)
    project_id, dataset_id = get_bq_config()

    tickers_sql = ", ".join(f"'{t}'" for t in tickers)
    # dataset_id is validated by get_bq_config(); tickers are validated against ASSET_POOL.
    query = f"SELECT ticker, cagr FROM `{dataset_id}.asset_metrics` WHERE ticker IN ({tickers_sql})"  # nosec B608
    df = pandas_gbq.read_gbq(query, project_id=project_id)
    return dict(zip(df['ticker'], df['cagr']))


def get_portfolio_cagr(weights: dict) -> float:
    """
    Calculate the weighted average CAGR for a portfolio defined by `weights`.

    Parameters:
        weights : {ticker: weight} — e.g. {"SPY": 0.6, "QQQ": 0.4}

    Returns:
        Weighted average CAGR (float). Weights are renormalized over the
        tickers for which CAGR data is actually available.
    """
    if not weights:
        raise ValueError("weights dict is empty; cannot compute portfolio CAGR.")

    tickers = list(weights.keys())
    cagr_map = load_cagr_from_bq(tickers)

    weighted_cagr = 0.0
    total_weight = 0.0
    for ticker, weight in weights.items():
        if ticker in cagr_map:
            weighted_cagr += cagr_map[ticker] * weight
            total_weight += weight

    if total_weight == 0:
        raise ValueError("No CAGR data found for any ticker in this portfolio.")

    return weighted_cagr / total_weight


def calculate_fire(
    target_amount: float,
    monthly_contribution: float,
    initial_capital: float,
    weights: dict,
    max_years: int = 50
) -> dict:
    """
    Estimate how many years to reach the target retirement amount.

    Parameters:
        target_amount        : retirement goal (e.g. 10_000_000)
        monthly_contribution : fixed monthly investment amount
        initial_capital      : current savings/investment balance
        weights              : {ticker: weight} portfolio composition — typically
                               the user's current allocation from the Risk
                               Allocation section (st.session_state['allocation'])
        max_years            : cap simulation at this many years (default 50)

    Returns:
        dict with:
            - years_to_fire    : int or None (None if not reached within max_years)
            - annual_cagr      : float (the weighted CAGR used)
            - projection       : DataFrame with columns: year, portfolio_value
    """
    annual_cagr = get_portfolio_cagr(weights)
    monthly_rate = (1 + annual_cagr) ** (1 / 12) - 1

    # Vectorized future-value formula (growth first, then contribution each month):
    #   P(n) = P0*(1+r)^n + C*((1+r)^n - 1)/r    when r != 0
    #   P(n) = P0 + C*n                             when r == 0
    months = np.arange(1, max_years * 12 + 1)
    growth = (1.0 + monthly_rate) ** months
    if monthly_rate != 0:
        values = initial_capital * growth + monthly_contribution * (growth - 1) / monthly_rate
    else:
        values = initial_capital + monthly_contribution * months

    # Keep only year-end snapshots (months 12, 24, …)
    year_months = months[months % 12 == 0]
    year_values = np.round(values[months % 12 == 0], 2)
    years_arr = year_months // 12

    reached = year_values >= target_amount
    years_to_fire = int(years_arr[reached][0]) if reached.any() else None

    projection_df = pd.DataFrame({"year": years_arr, "portfolio_value": year_values})

    return {
        "years_to_fire": years_to_fire,
        "annual_cagr": annual_cagr,
        "projection": projection_df
    }


if __name__ == "__main__":
    # Example: 50/30/20 SPY/QQQ/0050.TW portfolio
    example_weights = {"SPY": 0.5, "QQQ": 0.3, "0050.TW": 0.2}
    result = calculate_fire(
        target_amount=10_000_000,
        monthly_contribution=30000,
        initial_capital=500000,
        weights=example_weights
    )

    print(f"Annual CAGR used: {result['annual_cagr']:.2%}")
    print(f"Years to FIRE: {result['years_to_fire']}")
    print("\nProjection (first 10 years):")
    print(result['projection'].head(10).to_string(index=False))
