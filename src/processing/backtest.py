import os
import numpy as np
import pandas as pd
import pandas_gbq
from dotenv import load_dotenv

load_dotenv()

def load_fx_rate(start_date: str, end_date: str) -> pd.Series:
    """
    Fetch daily TWD/USD exchange rate (how many TWD per 1 USD).
    Returns a pd.Series indexed by date.
    Falls back to the most recent available rate if a date is missing.
    """
    import yfinance as yf
    df = yf.download("TWD=X", start=start_date, end=end_date, progress=False, auto_adjust=True)
    if df.empty:
        raise ValueError("Could not fetch TWD=X exchange rate from yfinance.")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    series = df['Close'].squeeze()
    series.index = pd.to_datetime(series.index)
    return series

def load_prices_for_tickers(tickers: list) -> pd.DataFrame:
    """
    Load price data for specified tickers from BigQuery raw_prices table.
    Returns columns: date, ticker, close
    """
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    dataset_id = os.getenv("BIGQUERY_DATASET")
    if not project_id or not dataset_id:
        raise ValueError("Missing GOOGLE_CLOUD_PROJECT or BIGQUERY_DATASET in .env")

    tickers_sql = ", ".join(f"'{t}'" for t in tickers)

    query = f"""
        SELECT date, ticker, close
        FROM `{dataset_id}.raw_prices`
        WHERE ticker IN ({tickers_sql})
        ORDER BY ticker, date
    """
    df = pandas_gbq.read_gbq(query, project_id=project_id)
    df['date'] = pd.to_datetime(df['date'])
    return df

def run_lumpsum(
    prices_df: pd.DataFrame,
    tickers_weights: dict,
    start_date: str,
    end_date: str,
    initial_investment: float,
    currency: str = "USD"
) -> pd.DataFrame:
    """
    Lump Sum backtest: invest everything on the first available trading day.

    Parameters:
        prices_df          : output from load_prices_for_tickers()
        tickers_weights    : e.g. {"SPY": 0.6, "BTC-USD": 0.4}
        start_date         : "YYYY-MM-DD"
        end_date           : "YYYY-MM-DD"
        initial_investment : total amount invested at the start

    Returns:
        DataFrame with columns: date, portfolio_value, total_invested, total_return_pct, strategy
    """
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)

    df = prices_df[
        (prices_df['date'] >= start) &
        (prices_df['date'] <= end)
    ].copy()

    pivot = df.pivot(index='date', columns='ticker', values='close')
    pivot = pivot.sort_index().ffill().bfill()

    valid_tickers = [t for t in tickers_weights if t in pivot.columns]
    pivot = pivot[valid_tickers]

    total_weight = sum(tickers_weights[t] for t in valid_tickers)
    weights = {t: tickers_weights[t] / total_weight for t in valid_tickers}

    first_day = pivot.index[0]
    shares = {}
    for ticker in valid_tickers:
        allocated = initial_investment * weights[ticker]
        price_on_first_day = pivot.loc[first_day, ticker]
        shares[ticker] = allocated / price_on_first_day

    daily_values = pd.Series(0.0, index=pivot.index)
    for ticker in valid_tickers:
        daily_values += shares[ticker] * pivot[ticker]

    if currency == "TWD":
        fx = load_fx_rate(start_date, end_date)
        fx = fx.reindex(pivot.index).ffill().bfill()
        converted_values = daily_values.values * fx.values
        converted_invested = initial_investment * fx.values[-1]
    else:
        converted_values = daily_values.values
        converted_invested = initial_investment

    result = pd.DataFrame({
        'date': pivot.index,
        'portfolio_value': converted_values,
        'total_invested': converted_invested,
        'total_return_pct': (converted_values / converted_invested - 1) * 100,
        'strategy': 'LumpSum',
        'currency': currency
    })

    return result

def run_dca(
    prices_df: pd.DataFrame,
    tickers_weights: dict,
    start_date: str,
    end_date: str,
    monthly_amount: float,
    currency: str = "USD"
) -> pd.DataFrame:
    """
    DCA backtest: invest a fixed amount on the first trading day of each month.

    Parameters:
        prices_df      : output from load_prices_for_tickers()
        tickers_weights: e.g. {"SPY": 0.6, "BTC-USD": 0.4}
        start_date     : "YYYY-MM-DD"
        end_date       : "YYYY-MM-DD"
        monthly_amount : amount invested each month

    Returns:
        DataFrame with columns: date, portfolio_value, total_invested, total_return_pct, strategy
    """
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)

    df = prices_df[
        (prices_df['date'] >= start) &
        (prices_df['date'] <= end)
    ].copy()

    pivot = df.pivot(index='date', columns='ticker', values='close')
    pivot = pivot.sort_index().ffill().bfill()

    valid_tickers = [t for t in tickers_weights if t in pivot.columns]
    pivot = pivot[valid_tickers]

    total_weight = sum(tickers_weights[t] for t in valid_tickers)
    weights = {t: tickers_weights[t] / total_weight for t in valid_tickers}

    # Identify the first trading day of each month
    monthly_invest_dates = (
        pivot.resample('MS').first().index  # MS = Month Start frequency
    )
    # Keep only dates that actually exist in our price data
    monthly_invest_dates = [d for d in monthly_invest_dates if d in pivot.index]

    # Initialize share holdings
    shares = {ticker: 0.0 for ticker in valid_tickers}
    total_invested = 0.0

    portfolio_values = []
    total_invested_list = []

    for date in pivot.index:
        # Buy on the first trading day of each month
        if date in monthly_invest_dates:
            for ticker in valid_tickers:
                allocated = monthly_amount * weights[ticker]
                price = pivot.loc[date, ticker]
                shares[ticker] += allocated / price
            total_invested += monthly_amount

        # Calculate portfolio value for this day
        daily_value = sum(shares[ticker] * pivot.loc[date, ticker] for ticker in valid_tickers)
        portfolio_values.append(daily_value)
        total_invested_list.append(total_invested)

    total_invested_arr = np.array(total_invested_list, dtype=float)
    portfolio_values_arr = np.array(portfolio_values, dtype=float)

    # Avoid division by zero before first investment
    with np.errstate(invalid='ignore', divide='ignore'):
        return_pct = np.where(
            total_invested_arr > 0,
            (portfolio_values_arr / total_invested_arr - 1) * 100,
            0.0
        )

    if currency == "TWD":
        fx = load_fx_rate(start_date, end_date)
        fx = fx.reindex(pivot.index).ffill().bfill()
        converted_values = portfolio_values_arr * fx.values
        converted_invested = total_invested_arr * fx.values[-1]
    else:
        converted_values = portfolio_values_arr
        converted_invested = total_invested_arr

    with np.errstate(invalid='ignore', divide='ignore'):
        return_pct = np.where(
            converted_invested > 0,
            (converted_values / converted_invested - 1) * 100,
            0.0
        )

    result = pd.DataFrame({
        'date': pivot.index,
        'portfolio_value': converted_values,
        'total_invested': converted_invested,
        'total_return_pct': return_pct,
        'strategy': 'DCA',
        'currency': currency
    })

    return result

def run_backtest(
    strategy: str,
    portfolio_mode: str,
    start_date: str,
    end_date: str,
    initial_investment: float = 10000,
    monthly_amount: float = 1000,
    risk_level: str = None,
    tickers_weights: dict = None,
    currency: str = "USD"
) -> pd.DataFrame:
    """
    Unified entry point for running a backtest. Called by Streamlit pages.

    Parameters:
        strategy           : "LumpSum" or "DCA"
        portfolio_mode     : "auto" (risk-level based) or "custom" (user-defined)
        start_date         : "YYYY-MM-DD"
        end_date           : "YYYY-MM-DD"
        initial_investment : used when strategy="LumpSum"
        monthly_amount     : used when strategy="DCA"
        risk_level         : "Low" / "Medium" / "High" / "Extreme High" (auto mode only)
        tickers_weights    : e.g. {"SPY": 0.6, "BTC-USD": 0.4} (custom mode only)

    Returns:
        DataFrame with columns: date, portfolio_value, total_invested, total_return_pct, strategy
    """
    # --- Auto mode: assign default portfolios by risk level ---
    AUTO_PORTFOLIOS = {
        "Low":          {"0050.TW": 0.5, "SPY": 0.3, "GLD": 0.2},
        "Medium":       {"SPY": 0.5, "QQQ": 0.3, "0050.TW": 0.2},
        "High":         {"QQQ": 0.5, "BTC-USD": 0.3, "SPY": 0.2},
        "Extreme High": {"BTC-USD": 0.6, "ETH-USD": 0.4},
    }

    if portfolio_mode == "auto":
        if risk_level not in AUTO_PORTFOLIOS:
            raise ValueError(f"Invalid risk_level '{risk_level}'. Choose from: {list(AUTO_PORTFOLIOS.keys())}")
        tickers_weights = AUTO_PORTFOLIOS[risk_level]

    elif portfolio_mode == "custom":
        if not tickers_weights:
            raise ValueError("portfolio_mode='custom' requires tickers_weights to be provided.")

    else:
        raise ValueError(f"Invalid portfolio_mode '{portfolio_mode}'. Choose 'auto' or 'custom'.")

    # --- Load price data ---
    tickers = list(tickers_weights.keys())
    prices_df = load_prices_for_tickers(tickers)

    # --- Run selected strategy ---
    if strategy == "LumpSum":
        return run_lumpsum(prices_df, tickers_weights, start_date, end_date, initial_investment, currency)
    elif strategy == "DCA":
        return run_dca(prices_df, tickers_weights, start_date, end_date, monthly_amount, currency)
    else:
        raise ValueError(f"Invalid strategy '{strategy}'. Choose 'LumpSum' or 'DCA'.")

if __name__ == "__main__":
    print("=== Test: Auto mode, Medium risk, DCA, TWD ===")
    r = run_backtest(
        strategy="DCA",
        portfolio_mode="auto",
        risk_level="Medium",
        start_date="2020-01-01",
        end_date="2024-12-31",
        monthly_amount=30000,
        currency="TWD"
    )
    print(r.tail(5).to_string(index=False))
    print(f"\nFinal value (TWD): {r['portfolio_value'].iloc[-1]:,.0f}")
    print(f"Total invested (TWD): {r['total_invested'].iloc[-1]:,.0f}")
    print(f"Total return: {r['total_return_pct'].iloc[-1]:.2f}%")
