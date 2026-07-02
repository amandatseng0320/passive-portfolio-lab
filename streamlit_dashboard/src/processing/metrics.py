import sys
import os
import numpy as np
import pandas as pd
import pandas_gbq

# Add project root to sys.path to access src modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from src.processing.screening import get_all_candidates
from src.processing.utils import get_bq_config, upload_to_bq, RISK_FREE_RATE

_EQUITY_ANNUALISE = np.sqrt(252)
_CRYPTO_ANNUALISE  = np.sqrt(365)


def load_prices_from_bq():
    project_id, dataset_id = get_bq_config()
        
    # dataset_id is validated by get_bq_config() before SQL assembly.
    query = f"SELECT * FROM `{dataset_id}.raw_prices` ORDER BY ticker, date"  # nosec B608
    df = pandas_gbq.read_gbq(query, project_id=project_id)
    df['date'] = pd.to_datetime(df['date'])
    return df

def calculate_metrics(df: pd.DataFrame) -> pd.DataFrame:
    print("Loading candidate names for mapping...")
    candidates_df = get_all_candidates()
    ticker_name_map = dict(zip(candidates_df['ticker'], candidates_df['name']))
    results = []
    
    for ticker, group in df.groupby('ticker'):
        try:
            print(f"Processing metrics for {ticker}...")
            # Sort chronologically just to be absolutely certain
            t_df = group.sort_values('date').reset_index(drop=True)
            if len(t_df) < 2:
                print(f"Not enough data to calculate metrics for {ticker}")
                continue
                
            category = t_df['category'].iloc[0]
            name = ticker_name_map.get(ticker, ticker) # Fallback to ticker if not found
            
            first_date = t_df['date'].iloc[0]
            last_date = t_df['date'].iloc[-1]
            start_price = t_df['close'].iloc[0]
            end_price = t_df['close'].iloc[-1]
            
            # CAGR
            years = (last_date - first_date).days / 365.0
            if years <= 0:
                cagr = 0.0
            else:
                cagr = (end_price / start_price) ** (1 / years) - 1
                
            # Volatility
            daily_returns = t_df['close'].pct_change(fill_method=None).dropna()
            vol = daily_returns.std()
            if category == 'CRYPTO':
                volatility = vol * _CRYPTO_ANNUALISE
            else:
                volatility = vol * _EQUITY_ANNUALISE

            # Max Drawdown
            rolling_max = t_df['close'].cummax()
            drawdown = (t_df['close'] - rolling_max) / rolling_max
            max_drawdown = drawdown.min()

            # Recovery Period
            if max_drawdown == 0 or pd.isna(max_drawdown):
                recovery_period_days = 0
                recovery_status = "Recovered"
            else:
                max_dd_idx = drawdown.idxmin()
                trough_date = t_df.loc[max_dd_idx, 'date']
                rolling_max_at_trough = rolling_max.loc[max_dd_idx]
                
                post_trough = t_df[t_df['date'] > trough_date]
                recovered = post_trough[post_trough['close'] >= rolling_max_at_trough]
                if not recovered.empty:
                    recovery_date = recovered['date'].iloc[0]
                    recovery_period_days = (recovery_date - trough_date).days
                    recovery_status = "Recovered"
                else:
                    recovery_period_days = None
                    recovery_status = "Not yet recovered"
                    
            # Worst Year
            t_df['year'] = t_df['date'].dt.year
            yearly_returns = (
                t_df.groupby('year', as_index=False)
                .agg(first_close=('close', 'first'), last_close=('close', 'last'))
            )
            with np.errstate(invalid='ignore', divide='ignore'):
                yearly_returns['return'] = (
                    yearly_returns['last_close'] - yearly_returns['first_close']
                ) / yearly_returns['first_close']
            yearly_returns = (
                yearly_returns
                .replace([np.inf, -np.inf], np.nan)
                .dropna(subset=['return'])
            )
            if yearly_returns.empty:
                print(f"No valid yearly returns to calculate worst year for {ticker}")
                continue

            worst_row = yearly_returns.loc[yearly_returns['return'].idxmin()]
            worst_year = float(worst_row['return'])
            worst_year_label = int(worst_row['year'])
            
            # Sharpe Ratio
            if volatility != 0:
                sharpe_ratio = (cagr - RISK_FREE_RATE) / volatility
            else:
                sharpe_ratio = 0.0
                
            results.append({
                "ticker": ticker,
                "name": name,
                "category": category,
                "data_start": first_date.strftime('%Y-%m-%d'),
                "data_end": last_date.strftime('%Y-%m-%d'),
                "cagr": cagr,
                "volatility": volatility,
                "max_drawdown": max_drawdown,
                "sharpe_ratio": sharpe_ratio,
                "recovery_period_days": recovery_period_days,
                "recovery_status": recovery_status,
                "worst_year": worst_year,
                "worst_year_label": worst_year_label,
            })
            
        except Exception as e:
            print(f"Error calculating metrics for {ticker}: {str(e)}")
            continue
            
    return pd.DataFrame(results)

def upload_to_bigquery(df):
    """Upload metrics DataFrame to BigQuery asset_metrics (replaces table)."""
    try:
        upload_to_bq(df, "asset_metrics")
    except ValueError as e:
        print(f"{e}. Skipping upload.")
    except Exception as e:
        print(f"BigQuery upload failed: {e}")

def run_pipeline():
    print("--- Starting Metrics Pipeline ---")
    try:
        prices_df = load_prices_from_bq()
    except Exception as e:
        print(f"Failed to load prices from BigQuery: {str(e)}")
        return
        
    if prices_df.empty:
        print("Raw prices DataFrame is empty. Aborting.")
        return
        
    print(f"Loaded {len(prices_df)} price records. Proceeding to calculations...")
    metrics_df = calculate_metrics(prices_df)

    if metrics_df.empty:
        print("No metrics successfully calculated. Aborting.")
        return

    upload_to_bigquery(metrics_df)

    print("\n--- Pipeline Summary Table ---")
    print(metrics_df[['ticker', 'cagr', 'volatility', 'max_drawdown', 'sharpe_ratio']].to_string(index=False))

if __name__ == "__main__":
    run_pipeline()
