import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import streamlit as st
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
            r = requests.get(url, headers=headers, timeout=10)
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
""")

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — ASSET SCREENING
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("<div id='asset-screening' style='padding-top: 70px; margin-top: -70px;'></div>", unsafe_allow_html=True)
st.title("Asset Screening")
st.caption("Filter and sort assets from the pool below. Click ＋ to add an asset to your watchlist.")

# ── Merge candidates with metrics ─────────────────────────────────────────────
candidates_with_currency = candidates_df[['ticker', 'category', 'currency']].drop_duplicates(subset='ticker')

pool_df = candidates_with_currency.merge(
    metrics_df[['ticker', 'name', 'cagr', 'volatility', 'max_drawdown',
                'sharpe_ratio', 'risk_level', 'worst_year', 'worst_year_label']],
    on='ticker', how='inner'
)

# ── Fetch current prices ───────────────────────────────────────────────────────
with st.spinner("Fetching current prices and volume..."):
    st.session_state.market_data = fetch_price_and_volume(pool_df['ticker'].tolist())

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

# ── Filter bar ─────────────────────────────────────────────────────────────────
f_col1, f_col2, f_col3, f_col4 = st.columns(4)
with f_col1:
    all_categories = ["All"] + sorted(pool_df['category'].dropna().unique().tolist())
    selected_category = st.selectbox("Category", all_categories, key="pool_category")
with f_col2:
    all_risks = ["All", "Low", "Medium", "High", "Extreme High"]
    selected_risk = st.selectbox("Risk", all_risks, key="pool_risk")
with f_col3:
    cagr_options = ["All", ">30%", "10–30%", "0–10%", "<0%"]
    selected_cagr = st.selectbox("Ann. Return", cagr_options, key="pool_cagr")
with f_col4:
    vol_options = ["All", "<15%", "15–30%", "30–60%", ">60%"]
    selected_vol = st.selectbox("Volatility", vol_options, key="pool_vol")

# ── Apply filters ──────────────────────────────────────────────────────────────
filtered = pool_df.copy()
if selected_category != "All":
    filtered = filtered[filtered['category'] == selected_category]
if selected_risk != "All":
    filtered = filtered[filtered['risk_level'] == selected_risk]

cagr_filter_map = {
    ">30%":   lambda x: x >= 0.30,
    "10–30%": lambda x: (x >= 0.10) & (x < 0.30),
    "0–10%":  lambda x: (x >= 0.00) & (x < 0.10),
    "<0%":    lambda x: x < 0.00,
}
if selected_cagr != "All":
    filtered = filtered[filtered['cagr'].apply(cagr_filter_map[selected_cagr])]

vol_filter_map = {
    "<15%":   lambda x: x < 0.15,
    "15–30%": lambda x: (x >= 0.15) & (x < 0.30),
    "30–60%": lambda x: (x >= 0.30) & (x < 0.60),
    ">60%":   lambda x: x >= 0.60,
}
if selected_vol != "All":
    filtered = filtered[filtered['volatility'].apply(vol_filter_map[selected_vol])]

# ── Sort state ─────────────────────────────────────────────────────────────────
CATEGORY_ORDER = {'TW_ETF': 0, 'US_ETF': 1, 'DEFENSIVE': 2, 'CRYPTO': 3}
filtered['_cat_order'] = filtered['category'].map(CATEGORY_ORDER).fillna(99)
filtered = filtered.sort_values(['_cat_order', 'cagr'], ascending=[True, False]).drop(columns=['_cat_order'])

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
    with st.expander("📋 How assets are selected", expanded=False):
        st.markdown("""
        The **27 assets** in this pool were selected using a two-step process:

        **Step 1 — Universe by trading volume ranking:**
        Assets were sourced from four categories ranked by AUM or market cap:
        - **TW ETF** (5): Top 5 Taiwan ETFs by AUM from MoneyDJ
        - **US ETF** (10): Top 10 US ETFs by AUM from TradingView (includes GLD as a commodity ETF)
        - **Defensive** (4): Bond and commodity ETFs representing stable, low-correlation asset classes — TLT, IEF, BND, DBC
        - **Crypto** (9): Top 9 non-stablecoin cryptocurrencies by market cap from CoinGecko (stablecoins and wrapped tokens excluded)

        **Step 2 — Data quality filter:**
        Assets were retained only if sufficient historical price data was available to calculate CAGR, volatility, max drawdown, and Sharpe ratio. Assets with incomplete data were excluded.

        All metrics are calculated from the full available price history for each asset using daily closing prices from Yahoo Finance, stored in Google BigQuery.
        """)

    st.markdown("#### Asset Pool")

    CATEGORY_ORDER = {'TW_ETF': 0, 'US_ETF': 1, 'DEFENSIVE': 2, 'CRYPTO': 3}
    sorted_filtered = filtered.copy()
    sorted_filtered['_cat_order'] = sorted_filtered['category'].map(CATEGORY_ORDER).fillna(99)
    sorted_filtered = sorted_filtered.sort_values(['_cat_order', 'cagr'], ascending=[True, False]).drop(columns=['_cat_order'])

    filtered_reset = sorted_filtered.reset_index(drop=True)
    display_df = build_display_df(filtered_reset)

    editor_df = display_df.copy()
    editor_df.insert(0, 'Add', False)

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
        m1.metric("Portfolio Volatility", f"{port_vol:.1%}", delta=f"Target: {target_vol:.0%}")
        m2.metric("Weighted CAGR", f"{port_cagr:.2%}")
        m3.metric("Weighted Max Drawdown", f"{port_dd:.2%}")
        m4.metric("Weighted Sharpe", f"{port_sharpe:.2f}")

        alloc_df['weight_pct'] = (alloc_df['weight'] * 100).round(1)
        alloc_df['label'] = alloc_df.apply(
            lambda r: f"{r['ticker']}<br>{r['weight_pct']}%<br>CAGR: {r['cagr']:.1%}", axis=1
        )

        treemap_fig = go.Figure(go.Treemap(
            labels=alloc_df['label'],
            parents=[""] * len(alloc_df),
            values=alloc_df['weight_pct'],
            textinfo="label",
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "Weight: %{value:.1f}%<br>"
                "CAGR: %{customdata[1]}<br>"
                "Volatility: %{customdata[2]}<br>"
                "<extra></extra>"
            ),
            customdata=alloc_df[['ticker', 'cagr', 'volatility']].apply(
                lambda r: [r['ticker'], f"{r['cagr']:.2%}", f"{r['volatility']:.2%}"], axis=1
            ).tolist(),
            marker=dict(
                colors=alloc_df['weight_pct'],
                colorscale='Teal',
                showscale=False
            )
        ))
        treemap_fig.update_layout(
            height=420,
            margin=dict(t=20, b=20, l=20, r=20)
        )
        st.plotly_chart(treemap_fig, use_container_width=True)

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
    # Controls
    bt_col1, bt_col2, bt_col3, bt_col4 = st.columns(4)
    with bt_col1:
        strategy_bt = st.radio("Strategy", ["DCA", "LumpSum"], key="bt_strategy")
    with bt_col2:
        if strategy_bt == "DCA":
            monthly_bt = st.number_input("Monthly Contribution", min_value=100, value=1000, step=100, key="bt_monthly")
            initial_bt = 1000
        else:
            initial_bt = st.number_input("Initial Investment", min_value=1000, value=10000, step=1000, key="bt_initial")
            monthly_bt = 1000
    with bt_col3:
        start_bt = st.date_input("Start Date", value=date(2020, 1, 1), key="bt_start")
        end_bt = st.date_input("End Date", value=date(2024, 12, 31), key="bt_end")
    with bt_col4:
        currency_bt = st.radio("Currency", ["USD", "TWD"], key="bt_currency")
        run_bt = st.button("Run Backtest", type="primary", key="bt_run")

    if run_bt:
        with st.spinner("Running backtest..."):
            try:
                result_df = run_backtest(
                    strategy=strategy_bt,
                    portfolio_mode="custom",
                    start_date=str(start_bt),
                    end_date=str(end_bt),
                    initial_investment=initial_bt,
                    monthly_amount=monthly_bt,
                    tickers_weights=st.session_state['allocation'],
                    currency=currency_bt
                )
                cs = "NT$" if currency_bt == "TWD" else "$"
                final_val = result_df['portfolio_value'].iloc[-1]
                total_inv = result_df['total_invested'].iloc[-1]
                total_ret = result_df['total_return_pct'].iloc[-1]
                years = (pd.to_datetime(end_bt) - pd.to_datetime(start_bt)).days / 365.0
                cagr_bt = (final_val / total_inv) ** (1 / years) - 1 if years > 0 and total_inv > 0 else 0.0

                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Final Value", f"{cs}{final_val:,.0f}")
                m2.metric("Total Invested", f"{cs}{total_inv:,.0f}")
                m3.metric("Total Return", f"{total_ret:.1f}%")
                m4.metric("CAGR", f"{cagr_bt:.1%}")

                # Portfolio value chart
                st.subheader("Portfolio Value Over Time")
                line_fig = go.Figure()
                line_fig.add_trace(go.Scatter(x=result_df['date'], y=result_df['portfolio_value'],
                                              mode='lines', name='Portfolio Value',
                                              line=dict(color='#2196F3', width=2)))
                line_fig.add_trace(go.Scatter(x=result_df['date'], y=result_df['total_invested'],
                                              mode='lines', name='Total Invested',
                                              line=dict(color='#9E9E9E', width=1.5, dash='dash')))
                line_fig.update_layout(height=320, margin=dict(t=20, b=20, l=20, r=20),
                                       plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                                       legend=dict(orientation="h", yanchor="bottom", y=1.02))
                st.plotly_chart(line_fig, use_container_width=True)

                # Pain index: Max Drawdown over time
                st.subheader("Max Drawdown Over Time (Pain Index)")
                rolling_max = result_df['portfolio_value'].cummax()
                drawdown = (result_df['portfolio_value'] - rolling_max) / rolling_max * 100
                dd_fig = go.Figure()
                dd_fig.add_trace(go.Scatter(x=result_df['date'], y=drawdown,
                                            mode='lines', name='Drawdown',
                                            fill='tozeroy',
                                            line=dict(color='#F44336', width=1.5)))
                dd_fig.update_layout(height=260, margin=dict(t=20, b=20, l=20, r=20),
                                     yaxis_title="Drawdown (%)",
                                     plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(dd_fig, use_container_width=True)

                # Annual returns bar chart
                st.subheader("Annual Returns")
                result_df['year'] = pd.to_datetime(result_df['date']).dt.year
                annual = result_df.groupby('year').apply(
                    lambda x: (x['portfolio_value'].iloc[-1] / x['portfolio_value'].iloc[0] - 1) * 100
                ).reset_index(name='annual_return')
                colors_annual = ['#F44336' if r < 0 else '#4CAF50' for r in annual['annual_return']]
                bar_fig = go.Figure()
                bar_fig.add_trace(go.Bar(x=annual['year'], y=annual['annual_return'],
                                         marker_color=colors_annual,
                                         text=[f"{r:.1f}%" for r in annual['annual_return']],
                                         textposition='outside'))
                bar_fig.update_layout(height=280, margin=dict(t=20, b=20, l=20, r=20),
                                      yaxis_title="Return (%)",
                                      plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(bar_fig, use_container_width=True)

            except Exception as e:
                st.error(f"Backtest failed: {e}")

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — FIRE CALCULATOR
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("<div id='fire-calculator' style='padding-top: 70px; margin-top: -70px;'></div>", unsafe_allow_html=True)
st.title("FIRE Calculator")
st.caption("Based on your allocation's historical CAGR, estimate when you can reach financial independence.")

portfolio_cagr = st.session_state.get('allocation_cagr', None)

if portfolio_cagr is None:
    st.info("Complete the Risk Allocation section first to auto-load your portfolio CAGR.")
else:
    st.success(f"Using portfolio weighted CAGR: **{portfolio_cagr:.2%}** (from your Risk Allocation)")

fire_col1, fire_col2, fire_col3 = st.columns(3)
with fire_col1:
    target_amount = st.number_input("Retirement Target", min_value=100000, max_value=100000000,
                                    value=10000000, step=100000, key="fire_target")
    initial_capital = st.number_input("Current Savings", min_value=0, value=500000,
                                      step=10000, key="fire_capital")
with fire_col2:
    monthly_contribution = st.number_input("Monthly Contribution", min_value=0, value=30000,
                                           step=1000, key="fire_monthly")
    risk_level_fire = st.selectbox("Risk Level", ["Low", "Medium", "High", "Extreme High"],
                                   key="fire_risk")
with fire_col3:
    st.caption(f"Latest US CPI YoY: **{default_inflation:.2%}** (from FRED)")
    inflation_rate = st.slider("Annual Inflation Rate", min_value=0.0, max_value=0.10,
                               value=float(round(default_inflation, 3)), step=0.005,
                               format="%.1f%%", key="fire_inflation")
    currency_symbol_fire = st.radio("Currency Symbol", ["$", "NT$"], key="fire_currency")

run_fire = st.button("Calculate FIRE", type="primary", key="fire_run")

if run_fire:
    with st.spinner("Calculating..."):
        try:
            result = calculate_fire(
                target_amount=target_amount,
                monthly_contribution=monthly_contribution,
                initial_capital=initial_capital,
                risk_level=risk_level_fire,
                max_years=50
            )
            projection_df = result['projection'].copy()
            annual_cagr = result['annual_cagr']
            years_to_fire = result['years_to_fire']

            projection_df['real_value'] = projection_df.apply(
                lambda row: row['portfolio_value'] / ((1 + inflation_rate) ** row['year']), axis=1
            )
            real_fire_year = next((int(row['year']) for _, row in projection_df.iterrows()
                                   if row['real_value'] >= target_amount), None)

            f1, f2, f3, f4 = st.columns(4)
            f1.metric("CAGR Used", f"{annual_cagr:.2%}")
            f2.metric("Years to FIRE (Nominal)", f"{years_to_fire} yrs" if years_to_fire else "50+ yrs")
            f3.metric("Years to FIRE (Real)", f"{real_fire_year} yrs" if real_fire_year else "50+ yrs")
            f4.metric("Inflation Applied", f"{inflation_rate:.1%}")

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=projection_df['year'], y=projection_df['portfolio_value'],
                                     mode='lines', name='Nominal Value',
                                     line=dict(color='#2196F3', width=2)))
            fig.add_trace(go.Scatter(x=projection_df['year'], y=projection_df['real_value'],
                                     mode='lines', name='Real Value (Inflation-Adjusted)',
                                     line=dict(color='#FF9800', width=2, dash='dot')))
            fig.add_hline(y=target_amount, line_dash="dash", line_color="#F44336",
                          annotation_text=f"Target: {currency_symbol_fire}{target_amount:,}",
                          annotation_position="top left")
            if years_to_fire:
                fig.add_vline(x=years_to_fire, line_dash="dot", line_color="#4CAF50",
                              annotation_text=f"FIRE @ Year {years_to_fire}",
                              annotation_position="top right")
            fig.update_layout(height=400, xaxis_title="Years",
                              yaxis_title=f"Value ({currency_symbol_fire})",
                              legend=dict(orientation="h", yanchor="bottom", y=1.02),
                              plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                              margin=dict(t=40, b=40, l=40, r=40))
            st.plotly_chart(fig, use_container_width=True)

            display_df = projection_df.copy()
            display_df['portfolio_value'] = display_df['portfolio_value'].apply(lambda x: f"{currency_symbol_fire}{x:,.0f}")
            display_df['real_value'] = display_df['real_value'].apply(lambda x: f"{currency_symbol_fire}{x:,.0f}")
            display_df.columns = ['Year', 'Nominal Value', 'Real Value (Inflation-Adjusted)']
            st.dataframe(display_df, use_container_width=True, hide_index=True)

        except Exception as e:
            st.error(f"Calculation failed: {e}")
