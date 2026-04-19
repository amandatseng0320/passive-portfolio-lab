import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import pandas_gbq
import plotly.graph_objects as go
import plotly.express as px
from datetime import date
from dotenv import load_dotenv
from src.processing.screening import get_all_candidates
from src.processing.backtest import run_backtest
from src.processing.fire_calculator import calculate_fire
from src.data_collection.fetch_macro import get_latest_cpi_yoy

load_dotenv()

st.set_page_config(page_title="Passive Portfolio Lab", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
[data-testid="metric-container"] {
    font-size: 14px !important;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    font-size: 1.4rem !important;
}
</style>
""", unsafe_allow_html=True)

# ── Sidebar ────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("""
<style>
.nav-link {
    display: block;
    padding: 6px 12px;
    margin: 2px 0;
    color: #555 !important;
    text-decoration: none !important;
    font-size: 14px;
    font-weight: 400;
    border-radius: 6px;
}
.nav-link:hover {
    background-color: #f0f2f6;
    color: #111 !important;
}
</style>
<a class="nav-link" href="#introduction">Introduction</a>
<a class="nav-link" href="#asset-screening">Asset Screening</a>
<a class="nav-link" href="#risk-allocation">Risk Allocation</a>
<a class="nav-link" href="#backtest">Backtest & Pain Index</a>
<a class="nav-link" href="#fire-calculator">FIRE Calculator</a>
<a class="nav-link" href="#summary">Summary</a>
""", unsafe_allow_html=True)

# ── Session State ──────────────────────────────────────────────────────────────

if 'watchlist' not in st.session_state:
    st.session_state.watchlist = []

# ── Load Data ──────────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def load_candidates():
    return get_all_candidates()

@st.cache_data(ttl=3600)
def load_metrics():
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    dataset_id = os.getenv("BIGQUERY_DATASET")
    query = f"SELECT * FROM `{dataset_id}.asset_metrics`"
    return pandas_gbq.read_gbq(query, project_id=project_id)

def fetch_price_and_volume(tickers: list) -> dict:
    """
    Fetch current price and volume directly from Yahoo Finance REST API.
    More stable than yfinance library which breaks when Yahoo changes their backend.
    """
    import requests
    result = {}
    headers = {'User-Agent': 'Mozilla/5.0'}
    for ticker in tickers:
        try:
            url = f'https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=5d'
            r = requests.get(url, headers=headers, timeout=10, verify=False)
            data = r.json()
            close = data['chart']['result'][0]['indicators']['quote'][0]['close']
            volume = data['chart']['result'][0]['indicators']['quote'][0]['volume']
            close = [x for x in close if x is not None]
            volume = [x for x in volume if x is not None]
            result[ticker] = {
                'price': round(close[-1], 2),
                'volume': int(volume[-1]) if volume else None
            }
        except Exception:
            result[ticker] = {'price': None, 'volume': None}
    return result


@st.cache_data(ttl=86400)
def fetch_inflation_default():
    return get_latest_cpi_yoy()

def convert_display(amount, display_usd, rate):
    """Convert TWD amount to USD for display if needed."""
    if display_usd and rate:
        return amount / rate, "$"
    return amount, "NT$"

candidates_df = load_candidates()
metrics_df = load_metrics()
default_inflation = fetch_inflation_default()

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — INTRODUCTION
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("<div id='introduction' style='padding-top: 70px; margin-top: -70px;'></div>", unsafe_allow_html=True)
st.title("Passive Portfolio Lab")
st.subheader("A data-driven toolkit for long-term passive investors")
st.markdown("""
> *"The stock market is a device for transferring money from the impatient to the patient."*
> — Benjamin Graham, as cited in **A Random Walk Down Wall Street** (Burton Malkiel)

The academic evidence is clear: most active managers fail to beat the market over time.
**A Random Walk Down Wall Street** (Malkiel) argues that a passive index strategy — buying and holding
a diversified portfolio without stock-picking or market-timing — consistently outperforms active management after fees.
**The Simple Path to Wealth** (JL Collins) and **Your Money or Your Life** (Vicki Robin) extend this logic
into the FIRE movement: by minimizing costs, maximizing savings rate, and staying invested through market cycles,
financial independence becomes a matter of time, not luck.

This dashboard helps you explore that thesis with real data:
- **Asset Screening** — browse and select assets into your watchlist
- **Risk Allocation** — auto-allocate weights based on each asset's risk profile
- **Backtest & Pain Index** — see historical returns and the drawdowns you'd have to endure
- **FIRE Calculator** — estimate when you can retire based on your allocation

> *All portfolio calculations are performed in New Taiwan Dollar (TWD). For USD-denominated assets (US ETFs, bonds, commodities, and crypto), daily prices are converted to TWD using historical exchange rates — meaning currency fluctuations are factored into the returns. This reflects the real experience of a Taiwan-based investor holding foreign assets. All input amounts should be entered in TWD.*
""")

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — ASSET SCREENING
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("<div id='asset-screening' style='padding-top: 70px; margin-top: -70px;'></div>", unsafe_allow_html=True)
st.title("Asset Screening")
st.caption("Filter and sort assets from the pool below. Click ＋ to add an asset to your watchlist.")
with st.expander("📋 How assets are selected", expanded=False):
    st.markdown("""
    The **24 assets** in this pool were selected using a two-step process. The asset pool is dynamically sourced — categories and rankings may shift over time as market conditions change.

    **Step 1 — Universe by trading volume ranking:**
    Assets were sourced from four categories ranked by AUM or market cap:
    - **TW ETF** (5): Top 5 Taiwan ETFs by AUM from MoneyDJ
    - **US ETF** (10): Top 10 US ETFs by AUM from TradingView (includes GLD as a commodity ETF)
    - **Defensive** (4): Bond and commodity ETFs representing stable, low-correlation asset classes — TLT, IEF, BND, DBC
    - **Crypto** (5): Top 5 cryptocurrencies by market cap from CoinGecko — BTC, ETH, XRP, BNB, SOL (stablecoins, wrapped tokens, and exchange-native tokens excluded)

    **Step 2 — Data quality filter:**
    Assets were retained only if sufficient historical price data was available to calculate CAGR, volatility, max drawdown, and Sharpe ratio. Assets with incomplete data were excluded.

    All metrics are calculated from the full available price history for each asset using daily closing prices from Yahoo Finance, stored in Google BigQuery.
    """)

# ── Merge candidates with metrics ─────────────────────────────────────────────
candidates_with_currency = candidates_df[['ticker', 'category', 'currency']].drop_duplicates(subset='ticker')

pool_df = candidates_with_currency.merge(
    metrics_df[['ticker', 'name', 'cagr', 'volatility', 'max_drawdown',
                'sharpe_ratio', 'worst_year', 'worst_year_label']],
    on='ticker', how='inner'
)

# ── Fetch current prices ───────────────────────────────────────────────────────
with st.spinner("Fetching current prices and volume..."):
    price_data = fetch_price_and_volume(pool_df['ticker'].tolist())
    # Only update session state if we got valid data
    has_valid = any(v.get('price') is not None for v in price_data.values())
    if has_valid or 'market_data' not in st.session_state:
        st.session_state.market_data = price_data

pool_df['price'] = pool_df['ticker'].map(lambda t: st.session_state.market_data.get(t, {}).get('price'))
pool_df['volume'] = pool_df['ticker'].map(lambda t: st.session_state.market_data.get(t, {}).get('volume'))

CURRENCY_MAP = {
    'TW_ETF': 'TWD',
    'US_ETF': 'USD',
    'DEFENSIVE': 'USD',
    'CRYPTO': 'USD'
}
pool_df['price_display'] = pool_df.apply(
    lambda row: f"{row['price']:,.2f} {CURRENCY_MAP.get(row['category'], 'USD')}"
    if pd.notnull(row['price']) else "N/A", axis=1
)
pool_df['volume_display'] = pool_df['volume'].apply(
    lambda x: f"{x/1e6:.2f}M" if pd.notnull(x) and x >= 1e6
    else (f"{x/1e3:.1f}K" if pd.notnull(x) and x >= 1e3 else (str(x) if pd.notnull(x) else "N/A"))
)

# ── Helper: build display dataframe ───────────────────────────────────────────
def build_display_df(df):
    d = df[['ticker', 'name', 'category', 'price_display', 'volume',
            'cagr', 'volatility', 'max_drawdown', 'worst_year', 'worst_year_label']].copy()
    # Multiply by 100 so column_config format="%.2f%%" displays correctly
    for col in ['cagr', 'volatility', 'max_drawdown', 'worst_year']:
        d[col] = d[col].apply(lambda x: round(x * 100, 4) if pd.notnull(x) else None)
    d['worst_year_label'] = d['worst_year_label'].apply(lambda x: str(int(x)) if pd.notnull(x) else "N/A")
    d.columns = ['Ticker', 'Name', 'Category', 'Price', 'Volume',
                 'Ann. Return', 'Volatility', 'Max Drawdown', 'Worst Year Ret.', 'Worst Year']
    return d

# ── Asset Pool ─────────────────────────────────────────────────────────────────
@st.fragment
def render_asset_pool():
    st.markdown("#### Asset Pool")
    fc1, fc2, fc3, fc4, fc5, fc6 = st.columns([1, 1, 2, 2, 2, 2])
    with fc1:
        if st.button("☑ Select All", key="select_all_btn", use_container_width=True):
            st.session_state['select_all'] = True
    with fc2:
        if st.button("☐ Deselect All", key="deselect_all_btn", use_container_width=True):
            st.session_state['select_all'] = False
    with fc3:
        all_categories = ["All Categories"] + sorted(pool_df['category'].dropna().unique().tolist())
        selected_category = st.selectbox("Category", all_categories, key="pool_category", label_visibility="collapsed")
    with fc4:
        vol_filter_options = ["All Volumes", "> 1B", "100M – 1B", "10M – 100M", "< 10M"]
        selected_vol_filter = st.selectbox("Volume", vol_filter_options, key="pool_vol_filter", label_visibility="collapsed")
    with fc5:
        cagr_options = ["All Returns", ">30%", "10–30%", "0–10%", "<0%"]
        selected_cagr = st.selectbox("Ann. Return", cagr_options, key="pool_cagr", label_visibility="collapsed")
    with fc6:
        vol_options = ["All Volatility", "<15%", "15–30%", "30–60%", ">60%"]
        selected_vol = st.selectbox("Volatility", vol_options, key="pool_vol", label_visibility="collapsed")

    filtered = pool_df.copy()
    if selected_category != "All Categories":
        filtered = filtered[filtered['category'] == selected_category]
    if selected_vol_filter != "All Volumes":
        def vol_range_filter(v):
            if pd.isna(v): return False
            if selected_vol_filter == "> 1B": return v >= 1_000_000_000
            if selected_vol_filter == "100M – 1B": return 100_000_000 <= v < 1_000_000_000
            if selected_vol_filter == "10M – 100M": return 10_000_000 <= v < 100_000_000
            if selected_vol_filter == "< 10M": return v < 10_000_000
            return True
        filtered = filtered[filtered['volume'].apply(vol_range_filter)]
    cagr_filter_map = {
        ">30%":   lambda x: x >= 0.30,
        "10–30%": lambda x: (x >= 0.10) & (x < 0.30),
        "0–10%":  lambda x: (x >= 0.00) & (x < 0.10),
        "<0%":    lambda x: x < 0.00,
    }
    if selected_cagr != "All Returns":
        filtered = filtered[filtered['cagr'].apply(cagr_filter_map[selected_cagr])]
    vol_filter_map = {
        "<15%":   lambda x: x < 0.15,
        "15–30%": lambda x: (x >= 0.15) & (x < 0.30),
        "30–60%": lambda x: (x >= 0.30) & (x < 0.60),
        ">60%":   lambda x: x >= 0.60,
    }
    if selected_vol != "All Volatility":
        filtered = filtered[filtered['volatility'].apply(vol_filter_map[selected_vol])]

    CATEGORY_ORDER = {'TW_ETF': 0, 'US_ETF': 1, 'DEFENSIVE': 2, 'CRYPTO': 3}
    filtered['_cat_order'] = filtered['category'].map(CATEGORY_ORDER).fillna(99)
    filtered = filtered.sort_values(['_cat_order', 'cagr'], ascending=[True, False]).drop(columns=['_cat_order'])
    filtered_reset = filtered.reset_index(drop=True)
    display_df = build_display_df(filtered_reset)

    editor_df = display_df.copy()
    select_all_state = st.session_state.get('select_all', False)
    editor_df.insert(0, 'Add', select_all_state)

    edited = st.data_editor(
        editor_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Add": st.column_config.CheckboxColumn("＋", width="small"),
            "Volume": st.column_config.NumberColumn("Volume", format="%d"),
            "Ann. Return": st.column_config.NumberColumn("Ann. Return", format="%.2f%%", help="Annualized return"),
            "Volatility": st.column_config.NumberColumn("Volatility", format="%.2f%%"),
            "Max Drawdown": st.column_config.NumberColumn("Max Drawdown", format="%.2f%%"),
            "Worst Year Ret.": st.column_config.NumberColumn("Worst Year Ret.", format="%.2f%%"),
        },
        disabled=[c for c in editor_df.columns if c != 'Add'],
        key="asset_pool_editor"
    )

    selected_tickers = filtered_reset.loc[edited['Add'] == True, 'ticker'].tolist()
    if selected_tickers:
        if st.button(f"Add {len(selected_tickers)} asset(s) to Watchlist", type="primary", key="add_to_watchlist"):
            for t in selected_tickers:
                if t not in st.session_state.watchlist:
                    st.session_state.watchlist.append(t)
            st.session_state.watchlist = list(dict.fromkeys(st.session_state.watchlist))
            st.rerun(scope="app")

render_asset_pool()

# ── Watchlist ──────────────────────────────────────────────────────────────────
st.markdown("#### Watchlist")
if not st.session_state.watchlist:
    st.info("No assets selected yet. Tick the checkbox in the Asset Pool above to add assets.")
else:
    wl_raw = pool_df[pool_df['ticker'].isin(st.session_state.watchlist)].copy()
    wl_display = build_display_df(wl_raw)
    st.dataframe(wl_display, use_container_width=True, hide_index=True)

    if st.button("Clear Watchlist", type="secondary", key="clear_watchlist"):
        st.session_state.watchlist = []
        st.rerun()

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — RISK ALLOCATION
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("<div id='risk-allocation' style='padding-top: 70px; margin-top: -70px;'></div>", unsafe_allow_html=True)
st.title("Risk Allocation")
st.caption("Based on your watchlist, the system automatically allocates weights to match your target risk level.")

if not st.session_state.watchlist:
    st.info("Add assets to your watchlist in Asset Screening first.")
else:
    selected_metrics = metrics_df[metrics_df['ticker'].isin(st.session_state.watchlist)].copy()

    if selected_metrics.empty:
        st.warning("No metric data found for your selected assets.")
    else:
        # ── Calculate achievable risk range ────────────────────────────────────
        vols = selected_metrics.set_index('ticker')['volatility']
        min_vol = float(vols.min())
        max_vol = float(vols.max())

        def vol_to_risk_label(v):
            if v < 0.16: return "Low"
            elif v < 0.27: return "Medium"
            elif v < 0.50: return "High"
            else: return "Extreme High"

        RISK_ORDER = {"Low": 1, "Medium": 2, "High": 3, "Extreme High": 4}
        RISK_VOL_TARGET = {"Low": 0.12, "Medium": 0.20, "High": 0.35, "Extreme High": 0.65}

        min_risk = vol_to_risk_label(min_vol)
        max_risk = vol_to_risk_label(max_vol)
        min_risk_num = RISK_ORDER[min_risk]
        max_risk_num = RISK_ORDER[max_risk]

        achievable = [k for k, v in RISK_ORDER.items() if min_risk_num <= v <= max_risk_num]

        st.info(f"Based on your selected assets, achievable risk range: **{min_risk}** to **{max_risk}**")

        # ── Risk preference selector (only show achievable levels) ─────────────
        risk_pref = st.radio(
            "Target Risk Level",
            options=achievable,
            horizontal=True,
            key="risk_pref"
        )

        target_vol = RISK_VOL_TARGET[risk_pref]

        # ── Auto-allocation algorithm ──────────────────────────────────────────
        def compute_allocation(df, target_vol):
            df = df.copy()
            tickers = df['ticker'].tolist()
            vols = df['volatility'].values.astype(float)

            # Step 1: inverse volatility weights as starting point
            inv_vol = 1.0 / np.where(vols == 0, 0.001, vols)
            weights = inv_vol / inv_vol.sum()

            # Step 2: iteratively nudge weights toward target volatility
            for _ in range(200):
                port_vol = float(np.dot(weights, vols))
                if abs(port_vol - target_vol) < 0.001:
                    break
                if port_vol > target_vol:
                    # reduce weight of highest-vol assets
                    adj = weights * (1 - 0.05 * (vols / vols.max()))
                else:
                    # increase weight of highest-vol assets
                    adj = weights * (1 + 0.05 * (vols / vols.max()))
                weights = np.clip(adj, 0.01, None)
                weights = weights / weights.sum()

            df['weight'] = weights
            df['weight'] = df['weight'] / df['weight'].sum()
            return df

        alloc_df = compute_allocation(selected_metrics, target_vol)

        # Final portfolio metrics
        port_vol = float(np.dot(alloc_df['weight'].values, alloc_df['volatility'].values))
        port_cagr = float(np.dot(alloc_df['weight'].values, alloc_df['cagr'].values))
        port_dd = float(np.dot(alloc_df['weight'].values, alloc_df['max_drawdown'].values))
        port_sharpe = float(np.dot(alloc_df['weight'].values, alloc_df['sharpe_ratio'].values))

        # Store in session state for downstream use
        st.session_state['allocation'] = dict(zip(alloc_df['ticker'], alloc_df['weight']))
        st.session_state['allocation_cagr'] = port_cagr

        # ── Display ────────────────────────────────────────────────────────────
        m1, m2, m3, m4 = st.columns(4)
        m1.metric(
            "Weighted CAGR",
            f"{port_cagr:.2%}",
            help="This is the weighted average of each asset's historical CAGR based on original currency. "
                 "It may differ from the Backtest CAGR below, which reflects actual TWD-converted portfolio "
                 "performance including currency fluctuation effects over the selected backtest period."
        )
        m2.metric("Portfolio Volatility", f"{port_vol:.1%}", delta=f"Target: {target_vol:.0%}")
        m3.metric("Weighted Max Drawdown", f"{port_dd:.2%}")
        m4.metric("Weighted Sharpe", f"{port_sharpe:.2f}")

        alloc_df['weight_pct'] = (alloc_df['weight'] * 100).round(1)

        # ── Treemap via HTML component with click support ──────────────────────
        BLUE_6 = [
            'rgb(210, 228, 245)',
            'rgb(168, 202, 232)',
            'rgb(114, 168, 212)',
            'rgb(65, 130, 185)',
            'rgb(30, 90, 150)',
            'rgb(10, 50, 110)',
        ]
        all_vols = metrics_df[['ticker', 'volatility']].copy()
        all_vols = all_vols.sort_values('volatility').reset_index(drop=True)
        all_vols['vol_rank'] = range(1, len(all_vols) + 1)
        all_vols['tier'] = ((all_vols['vol_rank'] - 1) // 4).clip(upper=5)
        vol_tier_map = dict(zip(all_vols['ticker'], all_vols['tier']))
        alloc_df['tier'] = alloc_df['ticker'].map(vol_tier_map).fillna(2).astype(int)
        alloc_df['color'] = alloc_df['tier'].apply(lambda t: BLUE_6[t])
        alloc_df['label'] = alloc_df.apply(
            lambda r: f"{r['ticker']}<br>{r['weight_pct']}%<br>CAGR: {r['cagr']:.1%}", axis=1
        )
        import json
        # Pre-calculate radar scores in Python
        pool_cagr_max = float(metrics_df['cagr'].max())
        pool_vol_max = float(metrics_df['volatility'].max())
        pool_dd_min = float(metrics_df['max_drawdown'].min())
        pool_sharpe_max = float(metrics_df['sharpe_ratio'].max())
        def calc_radar(r):
            cagr_score = round(min(100, max(0, (r['cagr'] / pool_cagr_max) * 100)) if pool_cagr_max else 0, 1)
            vol_score = round(min(100, max(0, (1 - r['volatility'] / pool_vol_max) * 100)) if pool_vol_max else 0, 1)
            dd_score = round(min(100, max(0, (1 - abs(r['max_drawdown']) / abs(pool_dd_min)) * 100)) if pool_dd_min else 0, 1)
            sharpe_score = round(min(100, max(0, (r['sharpe_ratio'] / pool_sharpe_max) * 100)) if pool_sharpe_max else 0, 1)
            worst_score = round(min(100, max(0, (1 - abs(r['worst_year']) / 1.0) * 100)), 1)
            return [cagr_score, vol_score, dd_score, sharpe_score, worst_score]
        treemap_data_list = []
        for _, row in alloc_df.iterrows():
            metrics_row = metrics_df[metrics_df['ticker'] == row['ticker']]
            if not metrics_row.empty:
                mr = metrics_row.iloc[0]
                radar = calc_radar(mr)
                yf_ticker = row['ticker']
                tv_ticker = row['ticker'].replace('-USD', 'USD').replace('.TW', '')
                treemap_data_list.append({
                    'label': row['label'],
                    'value': row['weight_pct'],
                    'color': row['color'],
                    'ticker': row['ticker'],
                    'name': str(mr['name']),
                    'cagr': f"{mr['cagr']:.2%}",
                    'vol': f"{mr['volatility']:.2%}",
                    'maxdd': f"{mr['max_drawdown']:.2%}",
                    'sharpe': f"{mr['sharpe_ratio']:.2f}",
                    'worst_ret': f"{mr['worst_year']:.2%}",
                    'worst_yr': str(int(mr['worst_year_label'])),
                    'radar': radar,
                    'yf_url': f"https://finance.yahoo.com/quote/{yf_ticker}",
                    'tv_url': f"https://www.tradingview.com/symbols/{tv_ticker}/",
                })
        treemap_data = json.dumps(treemap_data_list)
        st.caption("💡 Click any asset block in the treemap to see its details.")
        html_code = f"""
        <style>
            g.pathbar, .pathbar, .slice.pathbar {{ display: none !important; }}
        </style>
        <div id="main-container" style="width:100%; height:460px; position:relative;">
            <div id="treemap-container" style="width:100%; height:460px;"></div>
            <div id="detail-card" style="display:none; width:100%; height:460px; box-sizing:border-box; padding:24px 28px; font-family:sans-serif; border-radius:8px; position:absolute; top:0; left:0;"></div>
        </div>
        <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
        <script>
        var allData = {treemap_data};
        var dataMap = {{}};
        allData.forEach(function(d) {{ dataMap[d.ticker] = d; }});
        var labels = allData.map(d => d.label);
        var values = allData.map(d => d.value);
        var colors = allData.map(d => d.color);
        var trace = {{
            type: 'treemap',
            labels: labels,
            parents: labels.map(() => ''),
            values: values,
            textinfo: 'label',
            hovertemplate: '<b>%{{label}}</b><extra></extra>',
            marker: {{ colors: colors }},
            pathbar: {{ visible: false }},
        }};
        var layout = {{
            margin: {{t:10, b:10, l:10, r:10}},
            paper_bgcolor: 'rgba(0,0,0,0)',
        }};
        var config = {{displayModeBar: false}};
        var radarChart = null;
        function hexToRgb(hex) {{
            hex = hex.replace('#','');
            if (hex.length === 3) hex = hex.split('').map(c=>c+c).join('');
            var r = parseInt(hex.substring(0,2),16);
            var g = parseInt(hex.substring(2,4),16);
            var b = parseInt(hex.substring(4,6),16);
            return {{r:r, g:g, b:b}};
        }}
        function rgbStringToObj(s) {{
            var m = s.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/);
            if (m) return {{r:parseInt(m[1]), g:parseInt(m[2]), b:parseInt(m[3])}};
            return hexToRgb(s.replace('#',''));
        }}
        function luminance(c) {{
            return 0.299*c.r + 0.587*c.g + 0.114*c.b;
        }}
        function showDetail(ticker) {{
            var d = dataMap[ticker];
            if (!d) return;
            document.getElementById('treemap-container').style.display = 'none';
            var card = document.getElementById('detail-card');
            card.style.display = 'block';
            var bgColor = d.color;
            var rgb = bgColor.startsWith('rgb') ? rgbStringToObj(bgColor) : hexToRgb(bgColor.replace('#',''));
            var lum = luminance(rgb);
            var textColor = lum > 160 ? '#1a1a1a' : '#ffffff';
            var subTextColor = lum > 160 ? '#555555' : 'rgba(255,255,255,0.75)';
            var borderColor = lum > 160 ? 'rgba(0,0,0,0.15)' : 'rgba(255,255,255,0.3)';
            var btnBg = lum > 160 ? 'rgba(0,0,0,0.06)' : 'rgba(255,255,255,0.15)';
            var radarColor = lum > 160 ? 'rgba(107,158,159,0.35)' : 'rgba(255,255,255,0.35)';
            var radarBorder = lum > 160 ? '#6B9E9F' : '#ffffff';
            card.style.background = bgColor;
            card.innerHTML = `
                <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:18px;">
                    <span style="font-size:22px; font-weight:700; color:${{textColor}};">${{d.ticker}} — ${{d.name}}</span>
                    <button onclick="hideDetail()" style="background:${{btnBg}}; border:1px solid ${{borderColor}}; border-radius:6px; padding:6px 16px; cursor:pointer; font-size:14px; color:${{textColor}}; white-space:nowrap; margin-left:12px;">← Back</button>
                </div>
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:0; height:370px;">
                    <div style="padding-right:32px; border-right:1px solid ${{borderColor}}; display:flex; flex-direction:column; justify-content:space-between;">
                        <div style="display:grid; grid-template-columns:1fr 1fr; gap:18px 24px;">
                            <div>
                                <div style="font-size:13px; color:${{subTextColor}}; margin-bottom:4px;">Ann. Return (CAGR)</div>
                                <div style="font-size:32px; font-weight:700; color:${{textColor}}; line-height:1;">${{d.cagr}}</div>
                            </div>
                            <div>
                                <div style="font-size:13px; color:${{subTextColor}}; margin-bottom:4px;">Volatility</div>
                                <div style="font-size:32px; font-weight:700; color:${{textColor}}; line-height:1;">${{d.vol}}</div>
                            </div>
                            <div>
                                <div style="font-size:13px; color:${{subTextColor}}; margin-bottom:4px;">Max Drawdown</div>
                                <div style="font-size:32px; font-weight:700; color:${{textColor}}; line-height:1;">${{d.maxdd}}</div>
                            </div>
                            <div>
                                <div style="font-size:13px; color:${{subTextColor}}; margin-bottom:4px;">Sharpe Ratio</div>
                                <div style="font-size:32px; font-weight:700; color:${{textColor}}; line-height:1;">${{d.sharpe}}</div>
                            </div>
                            <div>
                                <div style="font-size:13px; color:${{subTextColor}}; margin-bottom:4px;">Worst Year Return</div>
                                <div style="font-size:32px; font-weight:700; color:${{textColor}}; line-height:1;">${{d.worst_ret}}</div>
                            </div>
                            <div>
                                <div style="font-size:13px; color:${{subTextColor}}; margin-bottom:4px;">Worst Year</div>
                                <div style="font-size:32px; font-weight:700; color:${{textColor}}; line-height:1;">${{d.worst_yr}}</div>
                            </div>
                        </div>
                        <div style="display:flex; gap:10px;">
                            <a href="${{d.yf_url}}" target="_blank" style="flex:1; text-align:center; padding:14px 8px; border:1px solid ${{borderColor}}; border-radius:8px; text-decoration:none; color:${{textColor}}; font-size:15px; font-weight:600; background:${{btnBg}};">Yahoo Finance</a>
                            <a href="${{d.tv_url}}" target="_blank" style="flex:1; text-align:center; padding:14px 8px; border:1px solid ${{borderColor}}; border-radius:8px; text-decoration:none; color:${{textColor}}; font-size:15px; font-weight:600; background:${{btnBg}};">TradingView</a>
                        </div>
                    </div>
                    <div style="padding-left:32px; display:flex; flex-direction:column; align-items:center; justify-content:center;">
                        <div style="width:100%; flex:1; display:flex; align-items:center; justify-content:center;">
                            <canvas id="radarCanvas" style="max-width:340px; max-height:340px;"></canvas>
                        </div>
                        <div style="text-align:center; font-size:12px; color:${{subTextColor}}; margin-top:10px;">Scores relative to all assets. Higher = better.</div>
                    </div>
                </div>
            `;
            if (radarChart) {{ radarChart.destroy(); radarChart = null; }}
            var ctx = document.getElementById('radarCanvas').getContext('2d');
            radarChart = new Chart(ctx, {{
                type: 'radar',
                data: {{
                    labels: ['Ann. Return', 'Low Vol', 'DD Protection', 'Sharpe', 'Worst Year'],
                    datasets: [{{
                        data: d.radar,
                        backgroundColor: radarColor,
                        borderColor: radarBorder,
                        borderWidth: 2,
                        pointBackgroundColor: radarBorder,
                        pointRadius: 4,
                    }}]
                }},
                options: {{
                    maintainAspectRatio: true,
                    scales: {{ r: {{
                        min: 0, max: 100,
                        ticks: {{ display: false }},
                        grid: {{ color: lum > 160 ? 'rgba(0,0,0,0.1)' : 'rgba(255,255,255,0.2)' }},
                        angleLines: {{ color: lum > 160 ? 'rgba(0,0,0,0.1)' : 'rgba(255,255,255,0.2)' }},
                        pointLabels: {{ font: {{ size: 14, weight: '600' }}, color: textColor }}
                    }} }},
                    plugins: {{ legend: {{ display: false }} }},
                    animation: {{ duration: 300 }}
                }}
            }});
        }}
        function attachClickHandler(gd) {{
            gd.on('plotly_treemapclick', function(eventData) {{
                if (eventData && eventData.points && eventData.points.length > 0) {{
                    var pt = eventData.points[0];
                    var label = pt.label || '';
                    var ticker = label.split('<br>')[0].trim();
                    if (ticker && dataMap[ticker]) {{
                        showDetail(ticker);
                    }}
                }}
                return false;
            }});
        }}
        function hideDetail() {{
            document.getElementById('detail-card').style.display = 'none';
            document.getElementById('treemap-container').style.display = 'block';
            if (radarChart) {{ radarChart.destroy(); radarChart = null; }}
        }}
        function purgeRoguePathbar() {{
            var container = document.getElementById('treemap-container');
            if (!container) return;
            // Hide pathbar groups
            container.querySelectorAll('g.pathbar, .pathbar, .slice.pathbar').forEach(function(el) {{
                el.style.display = 'none';
            }});
            // Hide any text node that still shows literal %{{label}}
            container.querySelectorAll('text').forEach(function(t) {{
                if (t.textContent && t.textContent.indexOf('%{{label}}') !== -1) {{
                    t.style.display = 'none';
                    var p = t.parentElement;
                    while (p && p !== container) {{
                        if (p.tagName === 'g' || p.tagName === 'G') {{
                            p.style.display = 'none';
                            break;
                        }}
                        p = p.parentElement;
                    }}
                }}
            }});
        }}
        Plotly.newPlot('treemap-container', [trace], layout, config).then(function(gd) {{
            attachClickHandler(gd);
            purgeRoguePathbar();
            // Re-purge after every Plotly redraw (hover can re-render)
            gd.on('plotly_afterplot', purgeRoguePathbar);
            gd.on('plotly_hover', purgeRoguePathbar);
            gd.on('plotly_unhover', purgeRoguePathbar);
        }});
        </script>
        """
        components.html(html_code, height=480)

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — BACKTEST & PAIN INDEX
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("<div id='backtest' style='padding-top: 70px; margin-top: -70px;'></div>", unsafe_allow_html=True)
st.title("Backtest & Pain Index")
st.caption("How would your portfolio have performed historically — and could you have endured the downturns?")

if 'allocation' not in st.session_state or not st.session_state['allocation']:
    st.info("Complete the Risk Allocation section first.")
else:
    # ── Advanced Settings ──────────────────────────────────────────────────────
    # Set defaults first
    if 'bt_params' not in st.session_state:
        st.session_state['bt_params'] = {
            'strategy': 'LumpSum',
            'initial': 300000,
            'monthly': 15000,
        }

    with st.expander("⚙️ Advanced Settings", expanded=False):
        adv_col1, adv_col2, adv_col3 = st.columns(3)
        with adv_col1:
            strategy_bt = st.radio("Strategy", ["LumpSum", "DCA"], key="bt_strategy", index=0)
        with adv_col2:
            if strategy_bt == "LumpSum":
                initial_bt = st.number_input("Initial Investment (NT$)", min_value=1000, value=300000, step=10000, key="bt_initial")
                monthly_bt = 15000
            else:
                monthly_bt = st.number_input("Monthly Contribution (NT$)", min_value=100, value=15000, step=1000, key="bt_monthly")
                initial_bt = 300000
        with adv_col3:
            start_bt = st.date_input("Start Date", value=date(2010, 1, 1), key="bt_start")
            end_bt = st.date_input("End Date", value=date.today(), key="bt_end")

        st.session_state['bt_params'] = {
            'strategy': strategy_bt,
            'initial': initial_bt,
            'monthly': monthly_bt if strategy_bt == 'DCA' else st.session_state.get('bt_params', {}).get('monthly', 500),
        }

    strategy_bt = st.session_state['bt_params']['strategy']
    initial_bt = st.session_state['bt_params']['initial']
    monthly_bt = st.session_state['bt_params']['monthly']
    start_bt = st.session_state.get('bt_start', date(2010, 1, 1))
    end_bt = st.session_state.get('bt_end', date.today())

    # ── Run backtest automatically ─────────────────────────────────────────────
    with st.spinner("Running backtest..."):
        try:
            result_df = run_backtest(
                strategy=strategy_bt,
                start_date=str(start_bt),
                end_date=str(end_bt),
                initial_investment=initial_bt,
                monthly_amount=monthly_bt,
                tickers_weights=st.session_state['allocation'],
            )
            display_usd = st.session_state.get('display_usd', False)
            fx_rate = st.session_state.get('live_twd_usd', 32.0)

            final_val = result_df['portfolio_value'].iloc[-1]
            total_inv = result_df['total_invested'].iloc[-1]
            total_ret = result_df['total_return_pct'].iloc[-1]
            years = (pd.to_datetime(end_bt) - pd.to_datetime(start_bt)).days / 365.0
            cagr_bt = (final_val / total_inv) ** (1 / years) - 1 if years > 0 and total_inv > 0 else 0.0
            st.session_state['backtest_cagr'] = cagr_bt

            disp_final, cs = convert_display(final_val, display_usd, fx_rate)
            disp_inv, _ = convert_display(total_inv, display_usd, fx_rate)
            gain = final_val - total_inv
            disp_gain, _ = convert_display(gain, display_usd, fx_rate)

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Final Value", f"{cs}{disp_final:,.0f}")
            m2.metric("Total Invested", f"{cs}{disp_inv:,.0f}")
            m3.metric("Total Return", f"{total_ret:.1f}%")
            m4.metric(
                "CAGR",
                f"{cagr_bt:.1%}",
                help="This is the actual annualized return of your portfolio over the backtest period, "
                     "calculated in TWD. USD-denominated assets are converted using historical exchange rates, "
                     "so currency fluctuations are included. This may differ from the Weighted CAGR shown "
                     "in Risk Allocation, which uses each asset's native-currency historical average."
            )

            st.subheader("Portfolio Value Over Time")
            line_fig = go.Figure()
            chart_divisor = fx_rate if display_usd else 1.0
            chart_cs = "$" if display_usd else "NT$"
            line_fig.add_trace(go.Scatter(
                x=result_df['date'], y=result_df['portfolio_value'] / chart_divisor,
                mode='lines', name='Portfolio Value',
                line=dict(color='#2196F3', width=2)
            ))
            line_fig.add_trace(go.Scatter(
                x=result_df['date'], y=result_df['total_invested'] / chart_divisor,
                mode='lines', name='Total Invested',
                line=dict(color='#9E9E9E', width=1.5, dash='dash')
            ))
            line_fig.update_layout(
                height=320, margin=dict(t=20, b=20, l=20, r=20),
                yaxis_title=f"Value ({chart_cs})",
                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                legend=dict(orientation="h", yanchor="bottom", y=1.02)
            )
            st.plotly_chart(line_fig, use_container_width=True)
            total_gain = final_val - total_inv
            insight1 = (
                f"Starting with {cs}{disp_inv:,.0f}, "
                f"your portfolio would have grown to {cs}{disp_final:,.0f} — "
                f"a gain of {cs}{disp_gain:,.0f} "
                f"({total_ret:.1f}%) over the period, equivalent to a {cagr_bt:.1%} annualized return."
            )
            st.markdown(
                f'<div style="background-color:#e8f4f8; padding:12px 16px; border-radius:8px; '
                f'border-left:4px solid #1f77b4; font-size:14px; color:#1a1a1a;">{insight1}</div>',
                unsafe_allow_html=True
            )

            st.subheader("Max Drawdown Over Time (Pain Index)")
            rolling_max = result_df['portfolio_value'].cummax()
            drawdown = (result_df['portfolio_value'] - rolling_max) / rolling_max * 100
            dd_fig = go.Figure()
            dd_fig.add_trace(go.Scatter(
                x=result_df['date'], y=drawdown,
                mode='lines', name='Drawdown',
                fill='tozeroy',
                line=dict(color='#F44336', width=1.5)
            ))
            dd_fig.update_layout(
                height=260, margin=dict(t=20, b=20, l=20, r=20),
                yaxis_title="Drawdown (%)",
                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(dd_fig, use_container_width=True)
            max_dd_val = float(drawdown.min())
            insight2 = f"The worst drawdown during this period was {max_dd_val:.1f}%. This is the pain a buy-and-hold investor would have had to endure without selling — the key behavioral challenge of passive investing."
            st.markdown(
                f'<div style="background-color:#fdf0f0; padding:12px 16px; border-radius:8px; '
                f'border-left:4px solid #F44336; font-size:14px; color:#1a1a1a;">{insight2}</div>',
                unsafe_allow_html=True
            )

            st.subheader("Annual Returns")
            result_df['year'] = pd.to_datetime(result_df['date']).dt.year
            annual = result_df.groupby('year').apply(
                lambda x: (x['portfolio_value'].iloc[-1] / x['portfolio_value'].iloc[0] - 1) * 100
                if x['portfolio_value'].iloc[0] > 0 else float('nan')
            ).reset_index(name='annual_return')
            annual = annual[annual['annual_return'].notna() & ~annual['annual_return'].isin([float('inf'), float('-inf')])]
            colors_annual = ['#F44336' if r < 0 else '#4CAF50' for r in annual['annual_return']]
            bar_fig = go.Figure()
            bar_fig.add_trace(go.Bar(
                x=annual['year'], y=annual['annual_return'],
                marker_color=colors_annual,
                text=[f"{r:.1f}%" for r in annual['annual_return']],
                textposition='outside'
            ))
            bar_fig.update_layout(
                height=280, margin=dict(t=20, b=20, l=20, r=20),
                yaxis_title="Return (%)",
                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(bar_fig, use_container_width=True)
            neg_years = (annual['annual_return'] < 0).sum()
            best_year = annual.loc[annual['annual_return'].idxmax()]
            worst_year_row = annual.loc[annual['annual_return'].idxmin()]
            insight3 = f"Out of {len(annual)} years, {neg_years} year(s) were negative. Best year: {int(best_year['year'])} (+{best_year['annual_return']:.1f}%). Worst year: {int(worst_year_row['year'])} ({worst_year_row['annual_return']:.1f}%)."
            st.markdown(
                f'<div style="background-color:#f0f7f0; padding:12px 16px; border-radius:8px; '
                f'border-left:4px solid #4CAF50; font-size:14px; color:#1a1a1a;">{insight3}</div>',
                unsafe_allow_html=True
            )

        except Exception as e:
            st.error(f"Backtest failed: {e}")

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — FIRE CALCULATOR
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("<div id='fire-calculator' style='padding-top: 70px; margin-top: -70px;'></div>", unsafe_allow_html=True)
st.title("FIRE Calculator")
st.caption("Based on your allocation's historical CAGR, estimate when you can reach financial independence.")

portfolio_cagr = st.session_state.get('backtest_cagr', st.session_state.get('allocation_cagr', None))
bt_params = st.session_state.get('bt_params', {})
risk_from_allocation = st.session_state.get('risk_pref', 'Medium')

if st.session_state.get('backtest_cagr'):
    st.success(f"Using backtest CAGR: **{portfolio_cagr:.2%}** (from your Backtest results)")
elif portfolio_cagr:
    st.success(f"Using portfolio weighted CAGR: **{portfolio_cagr:.2%}** (from your Risk Allocation)")

# ── Advanced Settings ──────────────────────────────────────────────────────────
currency_symbol_fire = "NT$"
target_amount = 30000000
initial_capital = int(bt_params.get('initial', 300000))
monthly_contribution = int(bt_params.get('monthly', 15000))
risk_level_fire = risk_from_allocation if risk_from_allocation in ["Low", "Medium", "High", "Extreme High"] else "Medium"
inflation_rate = float(round(default_inflation, 3))
inflation_rate_pct = round(default_inflation * 100, 2)

with st.expander("⚙️ Advanced Settings", expanded=False):
    st.markdown("Adjust the parameters below. Risk Level is carried over from your Risk Allocation.")
    fire_r1c1, fire_r1c2, fire_r1c3 = st.columns(3)
    with fire_r1c1:
        target_amount = st.number_input(
            "Retirement Target (NT$)",
            min_value=100000, max_value=500000000,
            value=30000000, step=100000, key="fire_target"
        )
    with fire_r1c2:
        initial_capital = st.number_input(
            "Current Savings (NT$)",
            min_value=0, value=int(bt_params.get('initial', 300000)),
            step=10000, key="fire_capital"
        )
    with fire_r1c3:
        monthly_contribution = st.number_input(
            "Monthly Contribution (NT$)",
            min_value=0, value=int(bt_params.get('monthly', 15000)),
            step=1000, key="fire_monthly"
        )
    fire_r2c1, fire_r2c2, fire_r2c3 = st.columns(3)
    with fire_r2c1:
        inflation_rate_pct = st.number_input(
            "Annual Inflation Rate (%)",
            min_value=0.0, max_value=10.0,
            value=round(default_inflation * 100, 2),
            step=0.1, key="fire_inflation",
            help=f"Latest US CPI YoY: {default_inflation:.2%} (auto-fetched from FRED). You can override this value."
        )
        inflation_rate = inflation_rate_pct / 100
        st.caption(f"Current US CPI YoY: {default_inflation:.2%}")
    with fire_r2c2:
        st.markdown(f"**Risk Level**")
        st.markdown(f"{risk_level_fire}")
        st.caption("Carried over from Risk Allocation")
    with fire_r2c3:
        st.markdown(f"**Currency**")
        st.markdown("NT$ (TWD)")
        st.caption("All calculations in New Taiwan Dollar")

# ── Auto-run FIRE calculation ──────────────────────────────────────────────────
with st.spinner("Calculating FIRE projection..."):
    try:
        result = calculate_fire(
            target_amount=target_amount,
            monthly_contribution=monthly_contribution,
            initial_capital=initial_capital,
            weights=st.session_state.get('allocation', {}),
            max_years=50
        )
        projection_df = result['projection'].copy()
        annual_cagr = result['annual_cagr']
        years_to_fire = result['years_to_fire']

        projection_df['real_value'] = projection_df.apply(
            lambda row: row['portfolio_value'] / ((1 + inflation_rate) ** row['year']), axis=1
        )
        real_fire_year = next(
            (int(row['year']) for _, row in projection_df.iterrows() if row['real_value'] >= target_amount),
            None
        )

        display_usd = st.session_state.get('display_usd', False)
        fx_rate = st.session_state.get('live_twd_usd', 32.0)
        fire_cs = "$" if display_usd else "NT$"
        fire_divisor = fx_rate if display_usd else 1.0

        display_cagr = st.session_state.get('backtest_cagr', annual_cagr)
        f1, f2, f3, f4 = st.columns(4)
        f1.metric("CAGR Used", f"{display_cagr:.2%}")
        f2.metric("Years to FIRE (Nominal)", f"{years_to_fire} yrs" if years_to_fire else "50+ yrs")
        f3.metric("Years to FIRE (Real)", f"{real_fire_year} yrs" if real_fire_year else "50+ yrs")
        f4.metric("Inflation Applied", f"{inflation_rate:.1%}")

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=projection_df['year'], y=projection_df['portfolio_value'] / fire_divisor,
            mode='lines', name='Nominal Value',
            line=dict(color='#2196F3', width=2)
        ))
        fig.add_trace(go.Scatter(
            x=projection_df['year'], y=projection_df['real_value'] / fire_divisor,
            mode='lines', name='Real Value (Inflation-Adjusted)',
            line=dict(color='#FF9800', width=2, dash='dot')
        ))
        disp_target = target_amount / fire_divisor
        fig.add_hline(
            y=disp_target, line_dash="dash", line_color="#F44336",
            annotation_text=f"Target: {fire_cs}{disp_target:,.0f}",
            annotation_position="top left"
        )
        if years_to_fire:
            fig.add_vline(
                x=years_to_fire, line_dash="dot", line_color="#4CAF50",
                annotation_text=f"FIRE @ Year {years_to_fire}",
                annotation_position="top right"
            )
        fig.update_layout(
            height=400, xaxis_title="Years",
            yaxis_title=f"Value ({fire_cs})",
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            margin=dict(t=40, b=40, l=40, r=40)
        )
        st.plotly_chart(fig, use_container_width=True)

        display_df = projection_df.copy()
        display_df['portfolio_value'] = display_df['portfolio_value'].apply(lambda x: f"{fire_cs}{x/fire_divisor:,.0f}")
        display_df['real_value'] = display_df['real_value'].apply(lambda x: f"{fire_cs}{x/fire_divisor:,.0f}")
        display_df.columns = ['Year', 'Nominal Value', 'Real Value (Inflation-Adjusted)']
        st.dataframe(display_df, use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"Calculation failed: {e}")

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 6 — SUMMARY
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("<div id='summary' style='padding-top: 70px; margin-top: -70px;'></div>", unsafe_allow_html=True)
st.title("Summary")
st.caption("A snapshot of your portfolio based on the selections above.")

allocation = st.session_state.get('allocation', {})
risk_pref = st.session_state.get('risk_pref', None)
allocation_cagr = st.session_state.get('allocation_cagr', None)
backtest_cagr = st.session_state.get('backtest_cagr', None)
years_to_fire = st.session_state.get('fire_years', None)

if not allocation:
    st.info("Complete the Risk Allocation section to see your portfolio summary.")
else:
    # ── Pull metrics for allocated assets ─────────────────────────────────────
    alloc_df_sum = metrics_df[metrics_df['ticker'].isin(allocation.keys())].copy()
    alloc_df_sum['weight'] = alloc_df_sum['ticker'].map(allocation)
    port_dd_sum = float(np.dot(alloc_df_sum['weight'].values, alloc_df_sum['max_drawdown'].values))
    port_vol_sum = float(np.dot(alloc_df_sum['weight'].values, alloc_df_sum['volatility'].values))
    display_cagr = backtest_cagr if backtest_cagr else allocation_cagr

    # ── FIRE years (re-calculate if not in session state) ─────────────────────
    fire_result = calculate_fire(
        target_amount=st.session_state.get('fire_target', 30000000),
        monthly_contribution=st.session_state.get('fire_monthly', 15000),
        initial_capital=st.session_state.get('fire_capital', 300000),
        weights=allocation,
        max_years=50
    )
    fire_years = fire_result.get('years_to_fire', None)

    # ── Dynamic insight generation ─────────────────────────────────────────────
    worst_dd_float = port_dd_sum  # e.g. -0.359
    worst_dd_str = f"{worst_dd_float:.1%}"
    loss_per_million = abs(worst_dd_float) * 100  # e.g. 35.9 (per NT$1M)
    worst_year_row = alloc_df_sum.loc[alloc_df_sum['max_drawdown'].idxmin()]
    worst_asset = worst_year_row['ticker']

    # Map drawdown severity to historical event
    if abs(worst_dd_float) >= 0.50:
        historical_ref = "a loss comparable to the 2008 Global Financial Crisis, when the S&P 500 took over 4 years to fully recover"
    elif abs(worst_dd_float) >= 0.30:
        historical_ref = "a loss in the range of the 2020 COVID crash or the 2022 rate-hike selloff, both of which saw sharp drops within months"
    else:
        historical_ref = "a moderate drawdown — smaller than major crashes, but still a meaningful test of investor patience"

    # Insight 1: allocation structure
    category_weights = {}
    for t, w in allocation.items():
        row = alloc_df_sum[alloc_df_sum['ticker'] == t]
        if not row.empty:
            cat = row.iloc[0]['category']
            category_weights[cat] = category_weights.get(cat, 0) + w
    dominant_cat = max(category_weights, key=category_weights.get)
    dominant_pct = category_weights[dominant_cat] * 100
    top_holding = sorted(allocation.items(), key=lambda x: -x[1])[0]
    cat_descriptions = {
        'TW_ETF': f"Taiwan ETFs dominate at <strong>{dominant_pct:.0f}%</strong> of your portfolio. This gives you strong exposure to Taiwan's equity market — high historical returns, but concentrated in a single market with geopolitical risk.",
        'US_ETF': f"US ETFs make up <strong>{dominant_pct:.0f}%</strong> of your portfolio, anchored by <strong>{top_holding[0]}</strong> ({top_holding[1]*100:.1f}%). This is a broadly diversified, globally proven approach — the core of most passive strategies.",
        'DEFENSIVE': f"Defensive assets (bonds and commodities) dominate at <strong>{dominant_pct:.0f}%</strong>. This heavily dampens volatility but also caps long-term growth — suitable for investors prioritizing stability over accumulation speed.",
        'CRYPTO': f"Crypto assets represent <strong>{dominant_pct:.0f}%</strong> of your allocation. While historically high-returning, crypto introduces extreme volatility that can overwhelm the stability of other holdings.",
    }
    insight1 = "📊 <strong>Portfolio Structure:</strong> " + cat_descriptions.get(dominant_cat, f"Your largest category is {dominant_cat} at {dominant_pct:.0f}%.")

    # Insight 2: drawdown contextualized
    insight2 = (
        f"📉 <strong>What the Drawdown Really Means:</strong> "
        f"A max drawdown of <strong>{worst_dd_str}</strong> means on a NT$1,000,000 portfolio, "
        f"you would have watched NT${loss_per_million*10000:,.0f} disappear on paper — {historical_ref}. "
        f"The hardest-hit position in your mix is <strong>{worst_asset}</strong>. "
        f"The question is not whether you can accept this mathematically — it's whether you can hold without selling when it's happening in real time."
    )

    # Insight 3: behavioral or FIRE based on risk
    if risk_pref in ["Low", "Medium"]:
        if fire_years:
            years_context = "ahead of schedule" if fire_years < 25 else "a long runway that rewards consistency over urgency"
            insight3 = (
                f"🎯 <strong>FIRE Reality Check:</strong> "
                f"At this allocation's historical return rate, your target is <strong>{fire_years} years</strong> away — {years_context}. "
                f"The compounding math works in your favor as long as you stay invested and keep contributing. "
                f"Missing just 10 of the best market days in a decade can cut your returns in half — passive means passive."
            )
        else:
            insight3 = (
                f"🎯 <strong>FIRE Reality Check:</strong> "
                f"At this allocation's return rate, your FIRE target may take more than 50 years. "
                f"Consider whether increasing your monthly contribution or accepting slightly more risk could meaningfully shorten that timeline."
            )
    else:
        insight3 = (
            f"⚠️ <strong>The Behavior Gap:</strong> "
            f"Studies consistently show that most retail investors earn significantly less than the funds they invest in — "
            f"because they buy high and sell low. With a portfolio capable of dropping <strong>{worst_dd_str}</strong>, "
            f"the biggest risk is not market volatility itself, but your own reaction to it. "
            f"High-risk passive investing only works if 'passive' is absolute — no panic selling, no market timing, no exceptions."
        )

    combined = f"""
    <div style="padding:20px 24px; border-radius:10px; background:#f8f9fa; border-left:4px solid #6B9E9F;">
      <p style="font-size:16px; color:#1a1a1a; margin-bottom:18px; line-height:1.7;">{insight1}</p>
      <p style="font-size:16px; color:#1a1a1a; margin-bottom:18px; line-height:1.7;">{insight2}</p>
      <p style="font-size:16px; color:#1a1a1a; margin:0; line-height:1.7;">{insight3}</p>
    </div>
    """
    st.markdown(combined, unsafe_allow_html=True)

    # ── Methodology caveat: fat tails (only for crypto-heavy / high-risk portfolios) ──
    crypto_weight = category_weights.get('CRYPTO', 0)
    if crypto_weight >= 0.10 or risk_pref in ["High", "Extreme High"]:
        st.markdown(
            """
            <div style="padding:12px 18px; margin-top:14px; border-radius:8px;
                        background:#fff8e1; border-left:4px solid #f9a825;
                        font-size:13px; color:#5d4e00; line-height:1.6;">
              ⚠️ <strong>A note on risk metrics.</strong>
              Volatility-based measures (Sharpe ratio, annualized stdev) assume daily returns follow a normal distribution.
              Real markets &mdash; especially crypto &mdash; have "fat tails":
              extreme drops happen far more often than the model predicts. Treat the Sharpe ratios
              and volatility figures above as a <em>lower bound</em> on tail risk, not a ceiling.
            </div>
            """,
            unsafe_allow_html=True
        )

st.divider()

# ── Currency Toggle ────────────────────────────────────────────────────────────
if 'display_usd' not in st.session_state:
    st.session_state['display_usd'] = False

btn_label = "🇺🇸 Switch to USD" if not st.session_state['display_usd'] else "🇹🇼 Switch to TWD"
if st.button(btn_label, type="secondary", key="currency_toggle"):
    st.session_state['display_usd'] = not st.session_state['display_usd']
    if st.session_state['display_usd']:
        try:
            import requests
            headers = {'User-Agent': 'Mozilla/5.0'}
            url = 'https://query1.finance.yahoo.com/v8/finance/chart/TWD=X?interval=1d&range=5d'
            r = requests.get(url, headers=headers, timeout=10, verify=False)
            data = r.json()
            closes = data['chart']['result'][0]['indicators']['quote'][0]['close']
            closes = [x for x in closes if x is not None]
            st.session_state['live_twd_usd'] = closes[-1]
        except Exception:
            st.session_state['live_twd_usd'] = 32.0
    st.rerun()

if st.session_state['display_usd']:
    rate = st.session_state.get('live_twd_usd', 32.0)
    st.caption(f"Currently displaying in USD. Exchange rate: 1 USD = NT${rate:.2f} (live rate). Input fields remain in TWD.")
else:
    st.caption("Currently displaying in TWD. Input fields remain in TWD regardless of display currency.")

