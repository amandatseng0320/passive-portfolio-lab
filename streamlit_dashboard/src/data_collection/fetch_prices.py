import os
import sys
import time
import pandas as pd
import requests
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Ensure we can import from the src directory
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from src.processing.screening import get_all_candidates
from src.processing.utils import YAHOO_HEADERS, upload_to_bq

# ──────────────────────────────────────────────────────────────────────────────
# Direct Yahoo Finance v8 chart API fetch.
#
# Why not yfinance?
#   yfinance under-the-hood uses curl_cffi with browser fingerprinting. In
#   networks with custom proxy or CA setup, yfinance can return None for most
#   tickers and surface a confusing
#       TypeError: 'NoneType' object is not subscriptable
#   which makes debugging hard. The direct REST API keeps normal TLS
#   certificate verification enabled while making the request path explicit.
# ──────────────────────────────────────────────────────────────────────────────


def fetch_ticker_prices_yahoo(ticker: str, timeout: int = 30, max_retries: int = 3) -> pd.DataFrame:
    """
    Fetch full-history daily OHLCV for a single ticker via Yahoo's v8 chart API.
    Returns a DataFrame with columns: date, open, high, low, close, volume.
    'close' is the adjusted close (dividends/splits applied) so it is directly
    comparable to yfinance's auto_adjust=True output.
    """
    end_ts = int((pd.Timestamp.today() + pd.Timedelta(days=1)).timestamp())
    # period1=0 → 1970-01-01; Yahoo will return max available history for the ticker.
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
        f"?interval=1d&period1=0&period2={end_ts}"
    )

    last_err = None
    for attempt in range(max_retries):
        try:
            r = requests.get(url, headers=YAHOO_HEADERS, timeout=timeout)
            if r.status_code != 200:
                raise RuntimeError(f"HTTP {r.status_code}")
            data = r.json()
            chart = data.get("chart", {})
            err = chart.get("error")
            if err:
                # Yahoo returns a structured error for delisted / unknown tickers.
                raise RuntimeError(f"Yahoo error: {err.get('description') or err}")
            result = chart.get("result")
            if not result:
                return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])
            result = result[0]
            timestamps = result.get("timestamp") or []
            if not timestamps:
                return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])

            quote = result["indicators"]["quote"][0]
            opens = quote.get("open", [None] * len(timestamps))
            highs = quote.get("high", [None] * len(timestamps))
            lows = quote.get("low", [None] * len(timestamps))
            closes = quote.get("close", [None] * len(timestamps))
            volumes = quote.get("volume", [0] * len(timestamps))

            # Prefer adjusted close so dividends/splits are handled correctly.
            adjclose = None
            if "adjclose" in result.get("indicators", {}):
                adjclose = result["indicators"]["adjclose"][0].get("adjclose")
            close_series = adjclose if adjclose is not None else closes

            dates = pd.to_datetime(timestamps, unit="s").normalize().tz_localize(None)
            df = pd.DataFrame({
                "date": dates,
                "open": opens,
                "high": highs,
                "low": lows,
                "close": close_series,
                "volume": volumes,
            })
            df = df.dropna(subset=["close"])
            df = df.drop_duplicates(subset="date", keep="last").reset_index(drop=True)
            return df

        except Exception as e:
            last_err = e
            if attempt < max_retries - 1:
                time.sleep(1.5 * (attempt + 1))
                continue
            raise RuntimeError(f"Failed after {max_retries} attempts: {last_err}")

# 0050.TW underwent a 4:1 zero-share split (零股分割) on 2014-01-02.
# yfinance does not record this event; we correct it manually.
_0050_SPLIT_DATE  = "2014-01-02"
_0050_SPLIT_RATIO = 4.0


def apply_manual_adjustments(df: pd.DataFrame, ticker: str) -> pd.DataFrame:
    """
    Apply manual price adjustments for known issues not captured by yfinance.

    0050.TW: 4:1 zero-share split on 2014-01-02. Derived from observed
    price discontinuity (37.41 on 2013-12-31 vs 9.33 on 2014-01-02).
    """
    if ticker == '0050.TW' and not df.empty:
        mask = df['date'] < _0050_SPLIT_DATE

        for col in ['open', 'high', 'low', 'close']:
            if col in df.columns:
                df.loc[mask, col] = (df.loc[mask, col] / _0050_SPLIT_RATIO).astype(float).round(6)

        if 'volume' in df.columns:
            df.loc[mask, 'volume'] = (df.loc[mask, 'volume'] * _0050_SPLIT_RATIO).astype('int64')

    return df


def fetch_prices(tickers_df: pd.DataFrame) -> pd.DataFrame:
    """
    Fetch the longest available historical daily price data for all candidate assets.
    
    Dynamic composition is intentional here: each asset starts from its own 
    listing date, rather than a single fixed date for the entire portfolio.
    """
    all_data = []

    for _, row in tickers_df.iterrows():
        ticker = row['ticker']
        category = row['category']

        print(f"Fetching data for {ticker}...")
        try:
            df = fetch_ticker_prices_yahoo(ticker)

            if df.empty:
                print(f"No pricing data found for {ticker}. Skipping.")
                continue

            # Add ticker and category
            df['ticker'] = ticker
            df['category'] = category

            # Drop rows where close price is missing (defensive; usually already handled)
            df = df.dropna(subset=['close'])
            if df.empty:
                print(f"All records for {ticker} contained NaN close prices. Skipping.")
                continue

            # Convert date explicitly to a string in YYYY-MM-DD
            df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')

            # Clean numerical fields
            for col in ['open', 'high', 'low', 'close']:
                if col in df.columns:
                    df[col] = df[col].astype(float).round(6)

            if 'volume' in df.columns:
                df['volume'] = df['volume'].fillna(0).astype('int64')

            df = apply_manual_adjustments(df, ticker)

            all_data.append(df)

        except Exception as e:
            print(f"Error fetching data for {ticker}: {str(e)}. Skipping.")
            
    if not all_data:
        print("No viable ticker data collected.")
        return pd.DataFrame(columns=['date', 'ticker', 'category', 'open', 'high', 'low', 'close', 'volume'])
        
    # Combine everything and align to expected structure
    combined_df = pd.concat(all_data, ignore_index=True)
    expected_columns = ['date', 'ticker', 'category', 'open', 'high', 'low', 'close', 'volume']
    
    # Missing column handler just in case
    for col in expected_columns:
        if col not in combined_df.columns:
            combined_df[col] = None 
            
    return combined_df[expected_columns]

def upload_to_bigquery(df):
    """Upload the processed price DataFrame to BigQuery raw_prices (replaces table)."""
    try:
        upload_to_bq(df, "raw_prices")
    except ValueError as e:
        print(f"{e}. Skipping BQ upload.")
    except Exception as e:
        print(f"Failed to upload data to BigQuery: {e}")

def run_pipeline():
    """ Execute pipeline pulling candidates, prices, and pushing to database """
    print("Initiating candidate scan...")
    candidates = get_all_candidates()
    
    if candidates.empty:
        print("No candidates yielded. Pipeline halting prematurely.")
        return
        
    print(f"Pulled {len(candidates)} candidate assets. Transitioning to price fetch...")
    
    prices_df = fetch_prices(candidates)
    
    if prices_df.empty:
        print("Aborting upload; empty price dataframe generated.")
        return
        
    upload_to_bigquery(prices_df)
    
    # Provide the concluding stats wrapper explicitly outlined in requirements
    print("\n-------- DOWNLOAD SUMMARY --------")
    print(f"Total Rows Fetched: {len(prices_df)}\n")
    
    summary_df = prices_df.groupby('ticker').agg(
        row_count=('date', 'count'),
        start_date=('date', 'min'),
        end_date=('date', 'max')
    ).reset_index()
    
    print(summary_df.to_string(index=False))
    print("----------------------------------\n")

if __name__ == "__main__":
    run_pipeline()
