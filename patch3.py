with open("dashboard/Passive_Portfolio_Lab.py", "r") as f:
    content = f.read()

# Injec numpy import
if "import numpy as np" not in content:
    content = content.replace("import pandas as pd", "import pandas as pd\nimport numpy as np")

# NEW BLOCK
new_block = """st.markdown("<div id='risk-allocation' style='padding-top: 70px; margin-top: -70px;'></div>", unsafe_allow_html=True)
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

        alloc_col1, alloc_col2 = st.columns([1, 2])

        with alloc_col1:
            display_alloc = alloc_df[['ticker', 'name', 'risk_level', 'weight', 'cagr', 'volatility']].copy()
            display_alloc['weight'] = display_alloc['weight'].apply(lambda x: f"{x:.1%}")
            display_alloc['cagr'] = display_alloc['cagr'].apply(lambda x: f"{x:.2%}")
            display_alloc['volatility'] = display_alloc['volatility'].apply(lambda x: f"{x:.2%}")
            display_alloc.columns = ['Ticker', 'Name', 'Risk', 'Weight', 'Ann. Return', 'Volatility']
            st.dataframe(display_alloc, use_container_width=True, hide_index=True)

        with alloc_col2:
            pie_fig = px.pie(
                alloc_df,
                names='ticker',
                values='weight',
                color_discrete_sequence=px.colors.qualitative.Set2
            )
            pie_fig.update_layout(margin=dict(t=20, b=20, l=20, r=20), height=320)
            st.plotly_chart(pie_fig, use_container_width=True)

st.divider()"""

start_idx = content.find("st.markdown(\"<div id='risk-allocation'")
end_idx = content.find("st.divider()", start_idx) + len("st.divider()")

if start_idx != -1 and end_idx != -1:
    content = content[:start_idx] + new_block + content[end_idx:]
    with open("dashboard/Passive_Portfolio_Lab.py", "w") as f:
        f.write(content)
    print("Patch applied successfully.")
else:
    print("Could not find start or end markers!")
