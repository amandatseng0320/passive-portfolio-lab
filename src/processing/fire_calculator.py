import os
import numpy as np
import pandas as pd
import pandas_gbq
from dotenv import load_dotenv

load_dotenv()

# Default portfolio weights per risk level (must match backtest.py AUTO_PORTFOLIOS)
AUTO_PORTFOLIOS = {
    "Low":          {"0050.TW": 0.5, "SPY": 0.3, "GLD": 0.2},
    "Medium":       {"SPY": 0.5, "QQQ": 0.3, "0050.TW": 0.2},
    "High":         {"QQQ": 0.5, "BTC-USD": 0.3, "SPY": 0.2},
    "Extreme High": {"BTC-USD": 0.6, "ETH-USD": 0.4},
}

def load_cagr_from_bq(tickers: list) -> dict:
    """
    Load CAGR values for specified tickers from BigQuery asset_metrics table.
    Returns a dict: {ticker: cagr}
    """
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    dataset_id = os.getenv("BIGQUERY_DATASET")
    if not project_id or not dataset_id:
        raise ValueError("Missing GOOGLE_CLOUD_PROJECT or BIGQUERY_DATASET in .env")

    tickers_sql = ", ".join(f"'{t}'" for t in tickers)
    query = f"""
        SELECT ticker, cagr
        FROM `{dataset_id}.asset_metrics`
        WHERE ticker IN ({tickers_sql})
    """
    df = pandas_gbq.read_gbq(query, project_id=project_id)
    return dict(zip(df['ticker'], df['cagr']))


def get_portfolio_cagr(risk_level: str) -> float:
    """
    Calculate the weighted average CAGR for a given risk level
    using the portfolio composition from AUTO_PORTFOLIOS.
    """
    if risk_level not in AUTO_PORTFOLIOS:
        raise ValueError(f"Invalid risk_level '{risk_level}'. Choose from: {list(AUTO_PORTFOLIOS.keys())}")

    weights = AUTO_PORTFOLIOS[risk_level]
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
    risk_level: str,
    max_years: int = 50
) -> dict:
    """
    Estimate how many years to reach the target retirement amount.

    Parameters:
        target_amount        : retirement goal (e.g. 10_000_000)
        monthly_contribution : fixed monthly investment amount
        initial_capital      : current savings/investment balance
        risk_level           : "Low" / "Medium" / "High" / "Extreme High"
        max_years            : cap simulation at this many years (default 50)

    Returns:
        dict with:
            - years_to_fire    : int or None (None if not reached within max_years)
            - annual_cagr      : float (the weighted CAGR used)
            - projection       : DataFrame with columns: year, portfolio_value
    """
    annual_cagr = get_portfolio_cagr(risk_level)
    monthly_rate = (1 + annual_cagr) ** (1 / 12) - 1

    portfolio_value = float(initial_capital)
    years_to_fire = None
    records = []

    for month in range(1, max_years * 12 + 1):
        # Growth first, then contribution
        portfolio_value = portfolio_value * (1 + monthly_rate) + monthly_contribution

        if month % 12 == 0:
            year = month // 12
            records.append({"year": year, "portfolio_value": round(portfolio_value, 2)})

            if years_to_fire is None and portfolio_value >= target_amount:
                years_to_fire = year

    projection_df = pd.DataFrame(records)

    return {
        "years_to_fire": years_to_fire,
        "annual_cagr": annual_cagr,
        "projection": projection_df
    }


if __name__ == "__main__":
    result = calculate_fire(
        target_amount=10_000_000,
        monthly_contribution=30000,
        initial_capital=500000,
        risk_level="Medium"
    )

    print(f"Annual CAGR used: {result['annual_cagr']:.2%}")
    print(f"Years to FIRE: {result['years_to_fire']}")
    print("\nProjection (first 10 years):")
    print(result['projection'].head(10).to_string(index=False))
