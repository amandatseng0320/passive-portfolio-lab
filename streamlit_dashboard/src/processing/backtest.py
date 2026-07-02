import numpy as np
import pandas as pd
import pandas_gbq
from .screening import validate_tickers
from .utils import get_bq_config


def _first_observed_date_per_month(index: pd.DatetimeIndex) -> list[pd.Timestamp]:
    """Return the first available row date for each month in an observed price index."""
    if index.empty:
        return []
    dates = pd.Series(index, index=index)
    return list(dates.groupby(index.to_period('M')).first())


def calculate_period_returns(result_df: pd.DataFrame) -> pd.Series:
    """Calculate portfolio period returns after neutralising new contributions."""
    if result_df.empty:
        return pd.Series(dtype=float)

    df = result_df.sort_values('date').reset_index(drop=True)
    portfolio_value = df['portfolio_value'].astype(float)
    total_invested = df['total_invested'].astype(float)
    contributions = total_invested.diff().fillna(total_invested)
    previous_value = portfolio_value.shift(1)

    with np.errstate(invalid='ignore', divide='ignore'):
        period_returns = (portfolio_value - contributions) / previous_value - 1

    period_returns = period_returns.replace([np.inf, -np.inf], np.nan).fillna(0.0)
    return period_returns


def calculate_annual_returns(result_df: pd.DataFrame) -> pd.DataFrame:
    """Return contribution-adjusted annual returns as percentages."""
    if result_df.empty:
        return pd.DataFrame(columns=['year', 'annual_return'])

    df = result_df.sort_values('date').reset_index(drop=True).copy()
    df['year'] = pd.to_datetime(df['date']).dt.year
    df['period_return'] = calculate_period_returns(df)
    annual = (
        df.groupby('year', as_index=False)['period_return']
        .agg(lambda x: (1 + x).prod() - 1)
        .rename(columns={'period_return': 'annual_return'})
    )
    annual['annual_return'] = annual['annual_return'] * 100
    return annual.replace([np.inf, -np.inf], np.nan).dropna(subset=['annual_return'])


def calculate_money_weighted_annual_return(result_df: pd.DataFrame) -> float:
    """
    Calculate a money-weighted annual return for a backtest with contributions.

    The cash-flow convention is investor perspective: contributions are negative
    cash flows, and the final portfolio value is a positive terminal cash flow.
    """
    if result_df.empty:
        return 0.0

    df = result_df.sort_values('date').reset_index(drop=True)
    if df['portfolio_value'].empty:
        return 0.0

    dates = pd.to_datetime(df['date'])
    portfolio_value = df['portfolio_value'].astype(float)
    total_invested = df['total_invested'].astype(float)
    contributions = total_invested.diff().fillna(total_invested)

    cashflows = -contributions.to_numpy(dtype=float)
    cashflows[-1] += float(portfolio_value.iloc[-1])

    if not np.any(cashflows < 0) or not np.any(cashflows > 0):
        return 0.0

    elapsed_years = (dates - dates.iloc[0]).dt.days.to_numpy(dtype=float) / 365.25

    def npv(rate: float) -> float:
        return float(np.sum(cashflows / np.power(1 + rate, elapsed_years)))

    low = -0.999999
    high = 1.0
    npv_low = npv(low)
    npv_high = npv(high)

    while npv_high > 0 and high < 1_000_000:
        high *= 2
        npv_high = npv(high)

    if not np.isfinite(npv_low) or not np.isfinite(npv_high) or npv_low * npv_high > 0:
        return 0.0

    for _ in range(100):
        mid = (low + high) / 2
        npv_mid = npv(mid)
        if abs(npv_mid) < 1e-7:
            return mid
        if npv_mid > 0:
            low = mid
        else:
            high = mid

    return (low + high) / 2


def load_fx_rate(start_date: str, end_date: str) -> pd.Series:
    """
    Fetch daily TWD/USD exchange rate using Yahoo Finance REST API.
    Returns a pd.Series indexed by date (timezone-naive).

    Notes on robustness:
    - Uses period1/period2 (unix timestamps) instead of `range=max`, because
      Yahoo silently downsamples older TWD=X data to monthly when `range=max`
      is used, which then propagates through ffill() and causes catastrophic
      portfolio-value spikes when backtests cross into those periods.
    - Filters out implausible rates as a second line of defence. TWD/USD has
      historically stayed in 25-40; anything outside 20-50 is treated as a
      bad tick and dropped (downstream ffill will then bridge over it).
    """
    import requests
    headers = {'User-Agent': 'Mozilla/5.0'}

    # Pull a wider window than requested so downstream reindex + ffill always
    # has a nearby anchor, but still use period1/period2 to keep daily granularity.
    start_ts = int(pd.Timestamp(start_date).timestamp())
    # End timestamp: end_date + 1 day to make sure the end_date itself is included.
    end_ts = int((pd.Timestamp(end_date) + pd.Timedelta(days=1)).timestamp())

    url = (
        'https://query1.finance.yahoo.com/v8/finance/chart/TWD=X'
        f'?interval=1d&period1={start_ts}&period2={end_ts}'
    )
    try:
        r = requests.get(url, headers=headers, timeout=15)
        data = r.json()
        result = data['chart']['result'][0]
        timestamps = result['timestamp']
        closes = result['indicators']['quote'][0]['close']
        index = pd.to_datetime(timestamps, unit='s').normalize().tz_localize(None)
        series = pd.Series(closes, index=index)
        series = series.dropna()
        series = series[~series.index.duplicated(keep='first')]

        # Second line of defence: drop implausible outliers.
        # TWD/USD has been between ~25 and ~40 since the early 1990s.
        series = series[(series >= 20) & (series <= 50)]

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
    validate_tickers(tickers)
    project_id, dataset_id = get_bq_config()
    tickers_sql = ", ".join(f"'{t}'" for t in tickers)

    # dataset_id is validated by get_bq_config(); tickers are validated against ASSET_POOL.
    query = f"SELECT date, ticker, close FROM `{dataset_id}.raw_prices` WHERE ticker IN ({tickers_sql}) ORDER BY ticker, date"  # nosec B608
    df = pandas_gbq.read_gbq(query, project_id=project_id)
    df['date'] = pd.to_datetime(df['date'])
    return df

def run_combined(
    prices_df: pd.DataFrame,
    tickers_weights: dict,
    start_date: str,
    end_date: str,
    initial_investment: float,
    monthly_contribution: float,
) -> pd.DataFrame:
    """
    Combined backtest: invest initial_investment as a lump sum on day one,
    then add monthly_contribution on the first trading day of each subsequent month.
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

    if pivot.empty or not valid_tickers:
        return pd.DataFrame(columns=['date', 'portfolio_value', 'total_invested',
                                     'total_return_pct', 'strategy'])

    # Convert USD assets to TWD using daily FX rates.
    # TWD assets end with '.TW' (e.g. 0050.TW) or '.TWO' (e.g. 00937B.TWO).
    usd_tickers = [t for t in valid_tickers if not (t.endswith('.TW') or t.endswith('.TWO'))]
    if usd_tickers:
        fx = load_fx_rate(start_date, end_date)
        fx = fx.reindex(pivot.index).ffill().bfill()
        for ticker in usd_tickers:
            pivot[ticker] = pivot[ticker] * fx.values

    total_weight = sum(tickers_weights[t] for t in valid_tickers)
    weights = {t: tickers_weights[t] / total_weight for t in valid_tickers}

    # Determine monthly DCA dates (first trading day of each month, excluding day one)
    first_day = pivot.index[0]
    monthly_dates = [d for d in _first_observed_date_per_month(pivot.index) if d != first_day]

    shares = {ticker: 0.0 for ticker in valid_tickers}
    total_invested = 0.0
    portfolio_values = []
    total_invested_list = []

    for date in pivot.index:
        # Day one: lump sum
        if date == first_day:
            for ticker in valid_tickers:
                allocated = initial_investment * weights[ticker]
                price = pivot.loc[date, ticker]
                shares[ticker] += allocated / price
            total_invested += initial_investment
        # Monthly: DCA contribution
        elif date in monthly_dates:
            for ticker in valid_tickers:
                allocated = monthly_contribution * weights[ticker]
                price = pivot.loc[date, ticker]
                shares[ticker] += allocated / price
            total_invested += monthly_contribution

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
        'strategy': 'Combined'
    })

    return result


def run_backtest(
    start_date: str,
    end_date: str,
    tickers_weights: dict,
    initial_investment: float = 300000,
    monthly_contribution: float = 15000,
) -> pd.DataFrame:
    """
    Unified entry point for running a backtest. Called by the Streamlit dashboard.

    Parameters:
        start_date          : "YYYY-MM-DD"
        end_date            : "YYYY-MM-DD"
        tickers_weights     : {ticker: weight} — e.g. {"SPY": 0.6, "BTC-USD": 0.4}
        initial_investment  : lump sum invested on day one
        monthly_contribution: amount added on the first trading day of each subsequent month

    Returns:
        DataFrame with columns: date, portfolio_value, total_invested, total_return_pct, strategy
    """
    if not tickers_weights:
        raise ValueError("tickers_weights must be provided and non-empty.")

    tickers = list(tickers_weights.keys())
    prices_df = load_prices_for_tickers(tickers)

    return run_combined(prices_df, tickers_weights, start_date, end_date, initial_investment, monthly_contribution)

if __name__ == "__main__":
    print("=== Test: Custom weights (SPY 50 / QQQ 30 / 0050.TW 20), Combined ===")
    r = run_backtest(
        start_date="2020-01-01",
        end_date="2024-12-31",
        tickers_weights={"SPY": 0.5, "QQQ": 0.3, "0050.TW": 0.2},
        initial_investment=300000,
        monthly_contribution=30000,
    )
    print(r.tail(5).to_string(index=False))
    print(f"\nFinal value: {r['portfolio_value'].iloc[-1]:,.0f}")
    print(f"Total invested: {r['total_invested'].iloc[-1]:,.0f}")
    print(f"Total return: {r['total_return_pct'].iloc[-1]:.2f}%")
