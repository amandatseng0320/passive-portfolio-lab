import os
import sys
import datetime
import pandas as pd
import yfinance as yf
import pandas_gbq
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Ensure we can import from the src directory
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from src.processing.screening import get_all_candidates

def apply_manual_adjustments(df, ticker):
    """
    Apply manual price adjustments for known issues not captured by yfinance.
    
    Known adjustments:
    - 0050.TW: On 2014-01-02, a 4:1 stock split occurred.
      This adjustment is based on observed price discontinuity 
      in the raw data (37.41 on 2013-12-31 vs 9.33 on 2014-01-02).
      The split ratio 4:1 is derived from 37.41 / 9.33 ≈ 4.0.
      yfinance does not record this split because it is a Taiwan 
      market zero-share split (零股分割), not a standard 
      international stock split.
    """
    if ticker == '0050.TW' and not df.empty:
        mask = df['date'] < '2014-01-02'
        
        for col in ['open', 'high', 'low', 'close']:
            if col in df.columns:
                df.loc[mask, col] = (df.loc[mask, col] / 4.0).astype(float).round(6)
                
        if 'volume' in df.columns:
            df.loc[mask, 'volume'] = (df.loc[mask, 'volume'] * 4).astype('int64')
            
    return df

def fetch_prices(tickers_df):
    """
    Fetch the longest available historical daily price data for all candidate assets.
    
    Dynamic composition is intentional here: each asset starts from its own 
    listing date, rather than a single fixed date for the entire portfolio.
    """
    all_data = []
    start_date = "1900-01-01"
    end_date = datetime.date.today().strftime('%Y-%m-%d')
    
    for index, row in tickers_df.iterrows():
        ticker = row['ticker']
        category = row['category']
        
        print(f"Fetching data for {ticker}...")
        try:
            # Fetch data from Yahoo Finance
            df = yf.download(ticker, start=start_date, end=end_date, progress=False, auto_adjust=True)
            
            if df.empty:
                print(f"No pricing data found for {ticker}. Skipping.")
                continue
                
            # Flatten MultiIndex columns if present
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
                
            # Filter solely for our required columns
            cols_to_keep = ['Open', 'High', 'Low', 'Close', 'Volume']
            existing_cols = [c for c in cols_to_keep if c in df.columns]
            df = df[existing_cols].copy()
            
            # Reset index so 'Date' becomes a manipulatable column
            df = df.reset_index()
            
            # Add ticker and category
            df['ticker'] = ticker
            df['category'] = category
            
            # Standardize names to lowercase to match the prompt's specified single DataFrame
            df.columns = [c.lower() for c in df.columns]
            
            # Drop rows where close price is missing
            if 'close' in df.columns:
                df = df.dropna(subset=['close'])
                
            if df.empty:
                print(f"All records for {ticker} contained NaN close prices. Skipping.")
                continue
                
            # Convert date explicitly to a string in YYYY-MM-DD
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
                
            # Clean numerical fields
            price_columns = ['open', 'high', 'low', 'close']
            for col in price_columns:
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
    """
    Uploads the fully processed and combined price DataFrame to BigQuery.
    Replaces table contents upon execution.
    """
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    dataset_id = os.getenv("BIGQUERY_DATASET")
    
    if not project_id or not dataset_id:
        print("Missing 'GOOGLE_CLOUD_PROJECT' or 'BIGQUERY_DATASET' mapped in .env. Skipping BQ upload.")
        return
        
    table_id = f"{dataset_id}.raw_prices"
    print(f"Uploading ~{len(df)} records directly to BigQuery '{table_id}'...")
    
    try:
        pandas_gbq.to_gbq(
            dataframe=df,
            destination_table=table_id,
            project_id=project_id,
            if_exists='replace'
        )
        print("Upload completed successfully!")
    except Exception as e:
        print(f"Failed to upload data to BigQuery: {str(e)}")

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
