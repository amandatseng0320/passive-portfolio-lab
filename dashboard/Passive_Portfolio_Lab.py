import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import streamlit as st
import pandas as pd
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
<a class="nav-link" href="#risk-comparison">Risk Comparison</a>
<a class="nav-link" href="#allocation-backtest">Allocation & Backtest</a>
<a class="nav-link" href="#fire-calculator">FIRE Calculator</a>
""", unsafe_allow_html=True)



AUTO_PORTFOLIOS = {
    "Low":          {"0050.TW": 0.5, "SPY": 0.3, "GLD": 0.2},
    "Medium":       {"SPY": 0.5, "QQQ": 0.3, "0050.TW": 0.2},
    "High":         {"QQQ": 0.5, "BTC-USD": 0.3, "SPY": 0.2},
    "Extreme High": {"BTC-USD": 0.6, "ETH-USD": 0.4},
}
RISK_ORDER = ["Low", "Medium", "High", "Extreme High"]
ALL_TICKERS = sorted(set(t for p in AUTO_PORTFOLIOS.values() for t in p.keys()))

# ── Sidebar Navigation ─────────────────────────────────────────────────────────



# ── Helper: Load Data ──────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def load_candidates():
    return get_all_candidates()

@st.cache_data(ttl=3600)
def load_metrics():
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    dataset_id = os.getenv("BIGQUERY_DATASET")
    query = f"SELECT * FROM `{dataset_id}.asset_metrics` ORDER BY risk_level, cagr DESC"
    return pandas_gbq.read_gbq(query, project_id=project_id)

@st.cache_data(ttl=86400)
def fetch_inflation_default():
    return get_latest_cpi_yoy()

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — INTRODUCTION
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("<div id='introduction' style='padding-top: 70px; margin-top: -70px;'></div>", unsafe_allow_html=True)
st.title("🏠 Passive Portfolio Lab")
st.subheader("A data-driven toolkit for long-term passive investors")

st.markdown("""
> *"The stock market is a device for transferring money from the impatient to the patient."*
> — Benjamin Graham, as cited in **A Random Walk Down Wall Street** (Burton Malkiel)

The academic evidence is clear: most active managers fail to beat the market over time.
**A Random Walk Down Wall Street** (Malkiel) argues that a passive index strategy — buying and holding a diversified portfolio without stock-picking or market-timing — consistently outperforms active management after fees.
**The Simple Path to Wealth** (JL Collins) and **Your Money or Your Life** (Vicki Robin) extend this logic into the FIRE movement: by minimizing costs, maximizing savings rate, and staying invested through market cycles, financial independence becomes a matter of time, not luck.

This dashboard helps you explore that thesis with real data:
- **Asset Screening** — which assets have the best risk-adjusted historical returns?
- **Risk Comparison** — how do different risk profiles compare across key metrics?
- **Allocation & Backtest** — what would your portfolio have returned over any historical period?
- **FIRE Calculator** — given your savings rate and risk profile, when can you retire?
""")

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — ASSET SCREENING
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("<div id='asset-screening' style='padding-top: 70px; margin-top: -70px;'></div>", unsafe_allow_html=True)
st.title("🔍 Asset Screening")
st.caption("Candidate assets sourced from MoneyDJ, TradingView, and CoinGecko — enriched with historical performance metrics from BigQuery.")

candidates_df = load_candidates()
metrics_df = load_metrics()

# Controls
f_col1, f_col2 = st.columns(2)
with f_col1:
    all_categories = ["All"] + sorted(candidates_df['category'].unique().tolist())
    selected_category = st.selectbox("Asset Category", all_categories, key="screening_category")
with f_col2:
    all_risk_levels = ["All", "Low", "Medium", "High", "Extreme High"]
    selected_risk = st.selectbox("Risk Level", all_risk_levels, key="screening_risk")

st.subheader("📋 Candidate Assets")
filtered_candidates = candidates_df.copy()
if selected_category != "All":
    filtered_candidates = filtered_candidates[filtered_candidates['category'] == selected_category]
st.dataframe(
    filtered_candidates[['rank', 'ticker', 'name', 'category', 'aum_or_market_cap', 'currency', 'source']],
    use_container_width=True, hide_index=True
)

st.subheader("📊 Detailed Performance Metrics")
filtered_metrics = metrics_df.copy()
if selected_category != "All":
    filtered_metrics = filtered_metrics[filtered_metrics['ticker'].isin(filtered_candidates['ticker'].tolist())]
if selected_risk != "All":
    filtered_metrics = filtered_metrics[filtered_metrics['risk_level'] == selected_risk]

display_cols = ['ticker', 'name', 'category', 'cagr', 'volatility', 'max_drawdown',
                'sharpe_ratio', 'worst_year', 'worst_year_label',
                'recovery_status', 'recovery_period_days', 'risk_level', 'risk_consensus']
format_map = {'cagr': '{:.2%}', 'volatility': '{:.2%}', 'max_drawdown': '{:.2%}',
              'sharpe_ratio': '{:.2f}', 'worst_year': '{:.2%}'}
styled_df = filtered_metrics[display_cols].copy()
for col, fmt in format_map.items():
    if col in styled_df.columns:
        styled_df[col] = styled_df[col].apply(lambda x: fmt.format(x) if pd.notnull(x) else '')
st.dataframe(styled_df, use_container_width=True, hide_index=True)

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — RISK COMPARISON
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("<div id='risk-comparison' style='padding-top: 70px; margin-top: -70px;'></div>", unsafe_allow_html=True)
st.title("⚖️ Risk Comparison")
st.caption("Compare historical performance metrics across risk levels, and review the asset composition of each portfolio.")

selected_levels = st.multiselect("Select Risk Levels to Compare", options=RISK_ORDER, default=RISK_ORDER, key="risk_levels")

if selected_levels:
    def get_portfolio_summary(risk_level):
        weights = AUTO_PORTFOLIOS[risk_level]
        tickers = list(weights.keys())
        subset = metrics_df[metrics_df['ticker'].isin(tickers)].copy()
        if subset.empty:
            return None
        total_w = sum(weights[t] for t in tickers if t in subset['ticker'].values)
        row = {"risk_level": risk_level}
        for metric in ['cagr', 'volatility', 'max_drawdown', 'sharpe_ratio']:
            row[metric] = sum(
                subset.loc[subset['ticker'] == t, metric].values[0] * weights[t] / total_w
                for t in tickers if t in subset['ticker'].values
            )
        return row

    summary_df = pd.DataFrame([r for r in [get_portfolio_summary(l) for l in selected_levels] if r])
    colors = {"Low": "#4CAF50", "Medium": "#2196F3", "High": "#FF9800", "Extreme High": "#F44336"}
    metrics_config = {
        "cagr": ("CAGR", "{:.1%}"),
        "volatility": ("Volatility", "{:.1%}"),
        "max_drawdown": ("Max Drawdown", "{:.1%}"),
        "sharpe_ratio": ("Sharpe Ratio", "{:.2f}"),
    }

    st.subheader("📊 Portfolio Metrics by Risk Level")
    cols = st.columns(2)
    for i, (metric_key, (metric_label, fmt)) in enumerate(metrics_config.items()):
        with cols[i % 2]:
            fig = go.Figure()
            for _, row in summary_df.iterrows():
                lvl = row['risk_level']
                val = row[metric_key]
                fig.add_trace(go.Bar(
                    x=[lvl], y=[abs(val)], name=lvl,
                    marker_color=colors.get(lvl, "#999"),
                    text=[fmt.format(val)], textposition='outside', showlegend=False
                ))
            fig.update_layout(
                title=metric_label, height=300,
                margin=dict(t=40, b=20, l=20, r=20),
                yaxis=dict(showticklabels=False, showgrid=False),
                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            )
            st.plotly_chart(fig, use_container_width=True)

    st.subheader("🗂️ Portfolio Composition by Risk Level")
    for lvl in selected_levels:
        weights = AUTO_PORTFOLIOS[lvl]
        subset = metrics_df[metrics_df['ticker'].isin(weights.keys())][['ticker', 'name', 'category', 'cagr', 'volatility', 'risk_level']].copy()
        subset['weight'] = subset['ticker'].map(weights)
        subset['cagr'] = subset['cagr'].apply(lambda x: '{:.2%}'.format(x))
        subset['volatility'] = subset['volatility'].apply(lambda x: '{:.2%}'.format(x))
        subset['weight'] = subset['weight'].apply(lambda x: '{:.0%}'.format(x))
        with st.expander(f"{lvl} Risk Portfolio", expanded=True):
            st.dataframe(subset[['ticker', 'name', 'category', 'weight', 'cagr', 'volatility', 'risk_level']],
                         use_container_width=True, hide_index=True)

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — ALLOCATION & BACKTEST
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("<div id='allocation-backtest' style='padding-top: 70px; margin-top: -70px;'></div>", unsafe_allow_html=True)
st.title("📐 Allocation & Backtest")
st.caption("Configure your portfolio allocation and run a historical backtest to evaluate performance.")

# Controls in columns above charts
bt_col1, bt_col2, bt_col3, bt_col4, bt_col5 = st.columns(5)
with bt_col1:
    strategy = st.radio("Strategy", ["DCA", "LumpSum"], key="bt_strategy")
with bt_col2:
    portfolio_mode = st.radio("Portfolio Mode", ["Auto", "Custom"], key="bt_mode")
with bt_col3:
    if portfolio_mode == "Auto":
        risk_level_bt = st.selectbox("Risk Level", RISK_ORDER, key="bt_risk")
        tickers_weights_bt = AUTO_PORTFOLIOS[risk_level_bt]
    else:
        risk_level_bt = None
        selected_tickers_bt = st.multiselect("Assets", ALL_TICKERS, default=["SPY", "BTC-USD"], key="bt_tickers")
        tickers_weights_bt = {t: round(1.0 / len(selected_tickers_bt), 2) for t in selected_tickers_bt} if selected_tickers_bt else {}
with bt_col4:
    if strategy == "LumpSum":
        initial_investment_bt = st.number_input("Initial Investment", min_value=1000, value=10000, step=1000, key="bt_lump")
        monthly_amount_bt = 1000
    else:
        monthly_amount_bt = st.number_input("Monthly Contribution", min_value=100, value=1000, step=100, key="bt_dca")
        initial_investment_bt = 10000
    currency_bt = st.radio("Currency", ["USD", "TWD"], key="bt_currency")
with bt_col5:
    start_date_bt = st.date_input("Start Date", value=date(2020, 1, 1), key="bt_start")
    end_date_bt = st.date_input("End Date", value=date(2024, 12, 31), key="bt_end")
    run_bt = st.button("▶ Run Backtest", type="primary", key="bt_run")

if run_bt and tickers_weights_bt:
    with st.spinner("Running backtest..."):
        try:
            result_df = run_backtest(
                strategy=strategy,
                portfolio_mode="auto" if portfolio_mode == "Auto" else "custom",
                start_date=str(start_date_bt),
                end_date=str(end_date_bt),
                initial_investment=initial_investment_bt,
                monthly_amount=monthly_amount_bt,
                risk_level=risk_level_bt,
                tickers_weights=tickers_weights_bt if portfolio_mode != "Auto" else None,
                currency=currency_bt
            )
            currency_symbol_bt = "NT$" if currency_bt == "TWD" else "$"
            final_value = result_df['portfolio_value'].iloc[-1]
            total_invested = result_df['total_invested'].iloc[-1]
            total_return = result_df['total_return_pct'].iloc[-1]
            years = (pd.to_datetime(end_date_bt) - pd.to_datetime(start_date_bt)).days / 365.0
            cagr_bt = (final_value / total_invested) ** (1 / years) - 1 if years > 0 and total_invested > 0 else 0.0

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Final Portfolio Value", f"{currency_symbol_bt}{final_value:,.0f}")
            m2.metric("Total Invested", f"{currency_symbol_bt}{total_invested:,.0f}")
            m3.metric("Total Return", f"{total_return:.1f}%")
            m4.metric("CAGR", f"{cagr_bt:.1%}")

            chart_col1, chart_col2 = st.columns([1, 2])
            with chart_col1:
                st.subheader("🥧 Portfolio Allocation")
                pie_fig = px.pie(names=list(tickers_weights_bt.keys()), values=list(tickers_weights_bt.values()),
                                 color_discrete_sequence=px.colors.qualitative.Set2)
                pie_fig.update_layout(margin=dict(t=20, b=20, l=20, r=20), height=350)
                st.plotly_chart(pie_fig, use_container_width=True)
            with chart_col2:
                st.subheader("📉 Portfolio Value Over Time")
                line_fig = go.Figure()
                line_fig.add_trace(go.Scatter(x=result_df['date'], y=result_df['portfolio_value'],
                                              mode='lines', name='Portfolio Value',
                                              line=dict(color='#2196F3', width=2)))
                line_fig.add_trace(go.Scatter(x=result_df['date'], y=result_df['total_invested'],
                                              mode='lines', name='Total Invested',
                                              line=dict(color='#9E9E9E', width=1.5, dash='dash')))
                line_fig.update_layout(height=350, margin=dict(t=20, b=20, l=20, r=20),
                                       yaxis_title=f"Value ({currency_bt})", xaxis_title="Date",
                                       legend=dict(orientation="h", yanchor="bottom", y=1.02),
                                       plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(line_fig, use_container_width=True)
        except Exception as e:
            st.error(f"Backtest failed: {e}")

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — FIRE CALCULATOR
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("<div id='fire-calculator' style='padding-top: 70px; margin-top: -70px;'></div>", unsafe_allow_html=True)
st.title("🔥 FIRE Calculator")
st.caption("Estimate how many years it will take to reach your retirement goal, based on your risk profile and historical portfolio returns.")

default_inflation = fetch_inflation_default()

fire_col1, fire_col2, fire_col3, fire_col4, fire_col5 = st.columns(5)
with fire_col1:
    target_amount = st.number_input("Retirement Target", min_value=100000, max_value=100000000,
                                    value=10000000, step=100000, key="fire_target")
    initial_capital = st.number_input("Current Savings", min_value=0, max_value=10000000,
                                      value=500000, step=10000, key="fire_capital")
with fire_col2:
    monthly_contribution = st.number_input("Monthly Contribution", min_value=0, max_value=1000000,
                                           value=30000, step=1000, key="fire_monthly")
    risk_level_fire = st.selectbox("Risk Level", RISK_ORDER, key="fire_risk")
with fire_col3:
    st.caption(f"📡 Latest US CPI YoY: **{default_inflation:.2%}**")
    inflation_rate = st.slider("Annual Inflation Rate", min_value=0.0, max_value=0.10,
                               value=float(round(default_inflation, 3)), step=0.005,
                               format="%.1f%%", key="fire_inflation")
    currency_symbol_fire = st.radio("Currency Symbol", ["$", "NT$"], key="fire_currency")
with fire_col4:
    run_fire = st.button("▶ Calculate FIRE", type="primary", key="fire_run")

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

            projection_df['real_portfolio_value'] = projection_df.apply(
                lambda row: row['portfolio_value'] / ((1 + inflation_rate) ** row['year']), axis=1
            )
            real_fire_year = next((int(row['year']) for _, row in projection_df.iterrows()
                                   if row['real_portfolio_value'] >= target_amount), None)

            f1, f2, f3, f4 = st.columns(4)
            f1.metric("Expected Annual Return (CAGR)", f"{annual_cagr:.2%}")
            f2.metric("Years to FIRE (Nominal)", f"{years_to_fire} yrs" if years_to_fire else "50+ yrs")
            f3.metric("Years to FIRE (Inflation-Adjusted)", f"{real_fire_year} yrs" if real_fire_year else "50+ yrs")
            f4.metric("Inflation Rate Applied", f"{inflation_rate:.1%}")

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=projection_df['year'], y=projection_df['portfolio_value'],
                                     mode='lines', name='Nominal Portfolio Value',
                                     line=dict(color='#2196F3', width=2)))
            fig.add_trace(go.Scatter(x=projection_df['year'], y=projection_df['real_portfolio_value'],
                                     mode='lines', name='Real Value (Inflation-Adjusted)',
                                     line=dict(color='#FF9800', width=2, dash='dot')))
            fig.add_hline(y=target_amount, line_dash="dash", line_color="#F44336",
                          annotation_text=f"Target: {currency_symbol_fire}{target_amount:,}",
                          annotation_position="top left")
            if years_to_fire:
                fig.add_vline(x=years_to_fire, line_dash="dot", line_color="#4CAF50",
                              annotation_text=f"FIRE @ Year {years_to_fire}",
                              annotation_position="top right")
            fig.update_layout(height=420, xaxis_title="Years",
                              yaxis_title=f"Portfolio Value ({currency_symbol_fire})",
                              legend=dict(orientation="h", yanchor="bottom", y=1.02),
                              plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                              margin=dict(t=40, b=40, l=40, r=40))
            st.plotly_chart(fig, use_container_width=True)

            display_df = projection_df.copy()
            display_df['portfolio_value'] = display_df['portfolio_value'].apply(lambda x: f"{currency_symbol_fire}{x:,.0f}")
            display_df['real_portfolio_value'] = display_df['real_portfolio_value'].apply(lambda x: f"{currency_symbol_fire}{x:,.0f}")
            display_df.columns = ['Year', 'Nominal Value', 'Real Value (Inflation-Adjusted)']
            st.dataframe(display_df, use_container_width=True, hide_index=True)

        except Exception as e:
            st.error(f"Calculation failed: {e}")
