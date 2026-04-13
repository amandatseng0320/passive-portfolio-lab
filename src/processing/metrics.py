import os
import sys
import numpy as np
import pandas as pd
import pandas_gbq
from sklearn.cluster import KMeans
from collections import Counter
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to sys.path to access src modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from src.processing.screening import get_all_candidates

def load_prices_from_bq():
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    dataset_id = os.getenv("BIGQUERY_DATASET")
    if not project_id or not dataset_id:
        raise ValueError("Missing GOOGLE_CLOUD_PROJECT or BIGQUERY_DATASET in .env")
        
    query = f"SELECT * FROM `{dataset_id}.raw_prices` ORDER BY ticker, date"
    df = pandas_gbq.read_gbq(query, project_id=project_id)
    df['date'] = pd.to_datetime(df['date'])
    return df

def get_top3_drawdowns(drawdown_series):
    events = []
    current_min = 0.0
    in_event = False
    
    for dd in drawdown_series:
        if not in_event:
            if dd < 0:
                in_event = True
                current_min = dd
        else:
            if dd < current_min:
                current_min = dd
            if dd >= -0.05:
                # Recovered above -5%, close event
                events.append(current_min)
                in_event = False
                current_min = 0.0
                
    if in_event:
        events.append(current_min)
        
    events.sort()
    top3 = events[:3]
    if not top3:
        return drawdown_series.min() if len(drawdown_series) > 0 else 0.0
    return float(np.mean(top3))

def calculate_metrics(df):
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
            daily_returns = t_df['close'].pct_change().dropna()
            vol = daily_returns.std()
            if category == 'CRYPTO':
                volatility = vol * np.sqrt(365)
            else:
                volatility = vol * np.sqrt(252)
                
            # Max Drawdown
            rolling_max = t_df['close'].cummax()
            drawdown = (t_df['close'] - rolling_max) / rolling_max
            max_drawdown = drawdown.min()
            
            # Recovery Period
            max_dd_idx = drawdown.idxmin()
            if max_drawdown == 0:
                recovery_period_days = 0
                recovery_status = "Recovered"
            else:
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
            yearly_returns = t_df.groupby('year').apply(
                lambda x: (x['close'].iloc[-1] - x['close'].iloc[0]) / x['close'].iloc[0]
            ).reset_index(name='return')
            
            worst_row = yearly_returns.loc[yearly_returns['return'].idxmin()]
            worst_year = float(worst_row['return'])
            worst_year_label = int(worst_row['year'])
            
            # Sharpe Ratio
            risk_free_rate = 0.02
            if volatility != 0:
                sharpe_ratio = (cagr - risk_free_rate) / volatility
            else:
                sharpe_ratio = 0.0
                
            # Top 3 avg drawdown
            top3_avg_drawdown = get_top3_drawdowns(drawdown)
            
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
                "top3_avg_drawdown": top3_avg_drawdown
            })
            
        except Exception as e:
            print(f"Error calculating metrics for {ticker}: {str(e)}")
            continue
            
    return pd.DataFrame(results)

def classify_risk(metrics_df):
    if metrics_df.empty:
        return metrics_df
        
    df = metrics_df.copy()
    drawdowns = df['top3_avg_drawdown'].values
    
    # Method 1 - Percentile
    mags = np.abs(drawdowns)
    p25 = np.percentile(mags, 25)
    p75 = np.percentile(mags, 75)
    p90 = np.percentile(mags, 90)
    
    def method1_risk(dd):
        m = abs(dd)
        if m <= p25: return "Low"
        elif m <= p75: return "Medium"
        elif m <= p90: return "High"
        else: return "Extreme High"
        
    df['risk_method1'] = df['top3_avg_drawdown'].apply(method1_risk)
    
    # Method 2 - K-Means
    kmeans = KMeans(n_clusters=4, random_state=42)
    preds = kmeans.fit_predict(drawdowns.reshape(-1, 1))
    centers = kmeans.cluster_centers_.flatten()
    
    sorted_idx = np.argsort(centers)
    label_map = {
        sorted_idx[0]: "Extreme High",
        sorted_idx[1]: "High",
        sorted_idx[2]: "Medium",
        sorted_idx[3]: "Low"
    }
    df['risk_method2'] = [label_map[p] for p in preds]
    
    # Method 3 - Standard Deviation
    mu = np.mean(drawdowns)
    sigma = np.std(drawdowns)
    
    def method3_risk(dd):
        if dd > mu + sigma:
            return "Low"
        elif mu <= dd <= mu + sigma:
            return "Medium"
        elif mu - sigma <= dd < mu:
            return "High"
        else:
            return "Extreme High"
            
    df['risk_method3'] = df['top3_avg_drawdown'].apply(method3_risk)
    
    # Ensemble Voting
    def get_ensemble_vote(row):
        severity = {"Low": 1, "Medium": 2, "High": 3, "Extreme High": 4}
        rev_severity = {1: "Low", 2: "Medium", 3: "High", 4: "Extreme High"}
        
        votes = [row['risk_method1'], row['risk_method2'], row['risk_method3']]
        counts = Counter(votes).most_common()
        
        if len(counts) == 3: # Tie across all 3
            avg_sev = round(sum(severity[v] for v in votes) / 3.0)
            return rev_severity[avg_sev]
        else:
            return counts[0][0]
            
    df['risk_level'] = df.apply(get_ensemble_vote, axis=1)
    df['risk_consensus'] = df.apply(lambda r: r['risk_method1'] == r['risk_method2'] == r['risk_method3'], axis=1)
    
    expected_cols = [
        "ticker", "name", "category", "data_start", "data_end",
        "cagr", "volatility", "max_drawdown", "sharpe_ratio",
        "recovery_period_days", "recovery_status",
        "worst_year", "worst_year_label", "top3_avg_drawdown",
        "risk_method1", "risk_method2", "risk_method3",
        "risk_level", "risk_consensus"
    ]
    return df[expected_cols]

def upload_to_bigquery(df):
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    dataset_id = os.getenv("BIGQUERY_DATASET")
    if not project_id or not dataset_id:
        print("Missing GOOGLE_CLOUD_PROJECT or BIGQUERY_DATASET in env. Skipping upload.")
        return
        
    table_id = f"{dataset_id}.asset_metrics"
    print(f"Uploading {len(df)} rows to {project_id}.{table_id}...")
    try:
        pandas_gbq.to_gbq(
            dataframe=df,
            destination_table=table_id,
            project_id=project_id,
            if_exists='replace'
        )
        print("BigQuery upload completed successfully.")
    except Exception as e:
        print(f"BigQuery upload failed: {str(e)}")

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
        
    print("Classifying risk profiles via ensemble model...")
    final_df = classify_risk(metrics_df)
    
    upload_to_bigquery(final_df)
    
    print("\n--- Pipeline Summary Table ---")
    print(final_df[['ticker', 'risk_level', 'risk_consensus', 'cagr', 'max_drawdown']].to_string(index=False))

if __name__ == "__main__":
    run_pipeline()
