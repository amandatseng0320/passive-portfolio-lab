import os
import numpy as np
import pandas as pd
import pandas_gbq
from dotenv import load_dotenv

load_dotenv()

def load_fx_rate(start_date: str, end_date: str) -> pd.Series:
    """
    Fetch daily TWD/USD exchange rate using Yahoo Finance REST API.
    Returns a pd.Series indexed by date (timezone-naive).
    """
    import requests
    headers = {'User-Agent': 'Mozilla/5.0'}
    url = 'https://query1.finance.yahoo.com/v8/finance/chart/TWD=X?interval=1d&range=max'
    try:
        r = requests.get(url, headers=headers, timeout=10, verify=False)
        data = r.json()
        result = data['chart']['result'][0]
        timestamps = result['timestamp']
        closes = result['indicators']['quote'][0]['close']
        index = pd.to_datetime(timestamps, unit='s').normalize().tz_localize(None)
        series = pd.Series(closes, index=index)
        series = series.dropna()
        series = series[~series.index.duplicated(keep='first')]
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        series = series[(series.index >= start) & (series.index <= end)]
        if series.empty:
            raise ValueError("No TWD=X data in date range")
        return series
    except Exception as e:
        raise ValueError(f"Could not fetch TWD=X exchange rate: {e}")

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
    initial_investment: float
) -> pd.DataFrame:
    """
    Lump Sum backtest: invest everything on the first available trading day.
    All calculations are performed in TWD.
    USD-denominated assets are converted to TWD using daily FX rates.
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

    # Convert USD assets to TWD using daily FX rates
    usd_tickers = [t for t in valid_tickers if not t.endswith('.TW')]
    if usd_tickers:
        fx = load_fx_rate(start_date, end_date)
        fx = fx.reindex(pivot.index).ffill().bfill()
        for ticker in usd_tickers:
            pivot[ticker] = pivot[ticker] * fx.values

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

    result = pd.DataFrame({
        'date': pivot.index,
        'portfolio_value': daily_values.values,
        'total_invested': initial_investment,
        'total_return_pct': (daily_values.values / initial_investment - 1) * 100,
        'strategy': 'LumpSum'
    })

    return result

def run_dca(
    prices_df: pd.DataFrame,
    tickers_weights: dict,
    start_date: str,
    end_date: str,
    monthly_amount: float
) -> pd.DataFrame:
    """
    DCA backtest: invest a fixed amount on the first trading day of each month.
    All calculations are performed in TWD.
    USD-denominated assets are converted to TWD using daily FX rates.
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

    # Convert USD assets to TWD using daily FX rates
    usd_tickers = [t for t in valid_tickers if not t.endswith('.TW')]
    if usd_tickers:
        fx = load_fx_rate(start_date, end_date)
        fx = fx.reindex(pivot.index).ffill().bfill()
        for ticker in usd_tickers:
            pivot[ticker] = pivot[ticker] * fx.values

    total_weight = sum(tickers_weights[t] for t in valid_tickers)
    weights = {t: tickers_weights[t] / total_weight for t in valid_tickers}

    monthly_invest_dates = (
        pivot.resample('MS').first().index
    )
    monthly_invest_dates = [d for d in monthly_invest_dates if d in pivot.index]

    shares = {ticker: 0.0 for ticker in valid_tickers}
    total_invested = 0.0
    portfolio_values = []
    total_invested_list = []

    for date in pivot.index:
        if date in monthly_invest_dates:
            for ticker in valid_tickers:
                allocated = monthly_amount * weights[ticker]
                price = pivot.loc[date, ticker]
                shares[ticker] += allocated / price
            total_invested += monthly_amount

        daily_value = sum(shares[ticker] * pivot.loc[date, ticker] for ticker in valid_tickers)
        portfolio_values.append(daily_value)
        total_invested_list.append(total_invested)

    total_invested_arr = np.array(total_invested_list, dtype=float)
    portfolio_values_arr = np.array(portfolio_values, dtype=float)

    with np.errstate(invalid='ignore', divide='ignore'):
        return_pct = np.where(
            total_invested_arr > 0,
            (portfolio_values_arr / total_invested_arr - 1) * 100,
            0.0
        )

    result = pd.DataFrame({
        'date': pivot.index,
        'portfolio_value': portfolio_values_arr,
        'total_invested': total_invested_arr,
        'total_return_pct': return_pct,
        'strategy': 'DCA'
    })

    return result

def run_backtest(
    strategy: str,
    start_date: str,
    end_date: str,
    tickers_weights: dict,
    initial_investment: float = 10000,
    monthly_amount: float = 1000,
) -> pd.DataFrame:
    """
    Unified entry point for running a backtest. Called by the Streamlit dashboard.

    Parameters:
        strategy           : "LumpSum" or "DCA"
        start_date         : "YYYY-MM-DD"
        end_date           : "YYYY-MM-DD"
        tickers_weights    : {ticker: weight} — e.g. {"SPY": 0.6, "BTC-USD": 0.4}
        initial_investment : used when strategy="LumpSum"
        monthly_amount     : used when strategy="DCA"

    Returns:
        DataFrame with columns: date, portfolio_value, total_invested, total_return_pct, strategy
    """
    if not tickers_weights:
        raise ValueError("tickers_weights must be provided and non-empty.")

    # --- Load price data ---
    tickers = list(tickers_weights.keys())
    prices_df = load_prices_for_tickers(tickers)

    # --- Run selected strategy ---
    if strategy == "LumpSum":
        return run_lumpsum(prices_df, tickers_weights, start_date, end_date, initial_investment)
    elif strategy == "DCA":
        return run_dca(prices_df, tickers_weights, start_date, end_date, monthly_amount)
    else:
        raise ValueError(f"Invalid strategy '{strategy}'. Choose 'LumpSum' or 'DCA'.")

if __name__ == "__main__":
    print("=== Test: Custom weights (SPY 50 / QQQ 30 / 0050.TW 20), DCA ===")
    r = run_backtest(
        strategy="DCA",
        start_date="2020-01-01",
        end_date="2024-12-31",
        tickers_weights={"SPY": 0.5, "QQQ": 0.3, "0050.TW": 0.2},
        monthly_amount=30000,
    )
    print(r.tail(5).to_string(index=False))
    print(f"\nFinal value: {r['portfolio_value'].iloc[-1]:,.0f}")
    print(f"Total invested: {r['total_invested'].iloc[-1]:,.0f}")
    print(f"Total return: {r['total_return_pct'].iloc[-1]:.2f}%")
