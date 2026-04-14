def run_patch():
    with open("dashboard/Passive_Portfolio_Lab.py", "r") as f:
        content = f.read()

    new_func = """def fetch_current_prices(tickers: list) -> dict:
    \"\"\"Fetch current price for each ticker using yfinance.\"\"\"
    import yfinance as yf
    prices = {}
    for ticker in tickers:
        try:
            data = yf.Ticker(ticker).fast_info
            prices[ticker] = round(float(data.last_price), 2)
        except Exception:
            prices[ticker] = None
    return prices
"""

    # Insert after load_metrics
    target_1 = '    return pandas_gbq.read_gbq(query, project_id=project_id)\n'
    content = content.replace(target_1, target_1 + '\n' + new_func + '\n')

    section_2_new = """st.markdown("<div id='asset-screening' style='padding-top: 70px; margin-top: -70px;'></div>", unsafe_allow_html=True)
st.title("Asset Screening")
st.caption("Filter and sort assets from the pool below. Click ＋ to add an asset to your watchlist.")

# ── Merge candidates with metrics ─────────────────────────────────────────────
pool_df = candidates_df.drop_duplicates(subset='ticker').merge(
    metrics_df[['ticker', 'name', 'category', 'cagr', 'volatility', 'max_drawdown',
                'sharpe_ratio', 'risk_level', 'worst_year', 'worst_year_label']],
    on='ticker', how='inner'
).merge(
    candidates_df[['ticker', 'currency']].drop_duplicates(subset='ticker'),
    on='ticker', how='left'
)

# ── Fetch current prices ───────────────────────────────────────────────────────
with st.spinner("Fetching current prices..."):
    price_map = fetch_current_prices(pool_df['ticker'].tolist())
pool_df['price'] = pool_df['ticker'].map(price_map)

# ── Filter bar ─────────────────────────────────────────────────────────────────
f_col1, f_col2, f_col3, f_col4, f_col5 = st.columns(5)
with f_col1:
    all_categories = ["All"] + sorted(pool_df['category'].dropna().unique().tolist())
    selected_category = st.selectbox("Category", all_categories, key="pool_category")
with f_col2:
    all_risks = ["All", "Low", "Medium", "High", "Extreme High"]
    selected_risk = st.selectbox("Risk", all_risks, key="pool_risk")
with f_col3:
    all_currencies = ["All"] + sorted(pool_df['currency'].dropna().unique().tolist())
    selected_currency = st.selectbox("Currency", all_currencies, key="pool_currency")
with f_col4:
    cagr_options = ["All", ">30%", "10–30%", "0–10%", "<0%"]
    selected_cagr = st.selectbox("Ann. Return", cagr_options, key="pool_cagr")
with f_col5:
    vol_options = ["All", "<15%", "15–30%", "30–60%", ">60%"]
    selected_vol = st.selectbox("Volatility", vol_options, key="pool_vol")

# ── Apply filters ──────────────────────────────────────────────────────────────
filtered = pool_df.copy()
if selected_category != "All":
    filtered = filtered[filtered['category'] == selected_category]
if selected_risk != "All":
    filtered = filtered[filtered['risk_level'] == selected_risk]
if selected_currency != "All":
    filtered = filtered[filtered['currency'] == selected_currency]

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
if 'sort_col' not in st.session_state:
    st.session_state.sort_col = 'cagr'
    st.session_state.sort_asc = False

filtered = filtered.sort_values(
    by=st.session_state.sort_col if st.session_state.sort_col in filtered.columns else 'cagr',
    ascending=st.session_state.sort_asc,
    na_position='last'
)

# ── Helper: build display dataframe ───────────────────────────────────────────
def build_display_df(df, include_price=True):
    d = df[['ticker', 'name', 'category', 'cagr', 'volatility',
            'max_drawdown', 'worst_year', 'worst_year_label']].copy()
    if include_price:
        d['price'] = df['price'].apply(lambda x: f"{x:,.2f}" if pd.notnull(x) else "N/A")
    d['cagr'] = d['cagr'].apply(lambda x: f"{x:.2%}" if pd.notnull(x) else "N/A")
    d['volatility'] = d['volatility'].apply(lambda x: f"{x:.2%}" if pd.notnull(x) else "N/A")
    d['max_drawdown'] = d['max_drawdown'].apply(lambda x: f"{x:.2%}" if pd.notnull(x) else "N/A")
    d['worst_year'] = d['worst_year'].apply(lambda x: f"{x:.2%}" if pd.notnull(x) else "N/A")
    d['worst_year_label'] = d['worst_year_label'].apply(lambda x: str(int(x)) if pd.notnull(x) else "N/A")
    if include_price:
        d = d[['ticker', 'name', 'category', 'price', 'cagr', 'volatility',
               'max_drawdown', 'worst_year', 'worst_year_label']]
        d.columns = ['Ticker', 'Name', 'Category', 'Price', 'Ann. Return',
                     'Volatility', 'Max Drawdown', 'Worst Year Ret.', 'Worst Year']
    else:
        d.columns = ['Ticker', 'Name', 'Category', 'Ann. Return',
                     'Volatility', 'Max Drawdown', 'Worst Year Ret.', 'Worst Year']
    return d

# ── Asset Pool ─────────────────────────────────────────────────────────────────
st.markdown(f"#### Asset Pool — {len(filtered)} assets")

filtered_reset = filtered.reset_index(drop=True)
display_df = build_display_df(filtered_reset, include_price=True)

for i, row in filtered_reset.iterrows():
    ticker = row['ticker']
    in_watchlist = ticker in st.session_state.watchlist
    btn_col, table_col = st.columns([0.3, 9.7])
    with btn_col:
        btn_label = "－" if in_watchlist else "＋"
        btn_type = "primary" if in_watchlist else "secondary"
        if st.button(btn_label, key=f"add_{ticker}", type=btn_type):
            if in_watchlist:
                st.session_state.watchlist.remove(ticker)
            else:
                st.session_state.watchlist.append(ticker)
            st.rerun()
    with table_col:
        st.dataframe(
            display_df.iloc[[i]],
            use_container_width=True,
            hide_index=True
        )

# ── Watchlist ──────────────────────────────────────────────────────────────────
st.markdown("#### Watchlist")
if not st.session_state.watchlist:
    st.info("No assets selected yet. Click ＋ to add assets to your watchlist.")
else:
    wl_raw = pool_df[pool_df['ticker'].isin(st.session_state.watchlist)].copy()
    wl_display = build_display_df(wl_raw, include_price=True)
    st.dataframe(wl_display, use_container_width=True, hide_index=True)

    if st.button("Clear Watchlist", type="secondary", key="clear_watchlist"):
        st.session_state.watchlist = []
        st.rerun()

st.divider()"""

    start_idx = content.find("st.markdown(\"<div id='asset-screening'")
    end_idx = content.find("st.divider()", start_idx) + len("st.divider()")
    
    content = content[:start_idx] + section_2_new + content[end_idx:]
    
    with open("dashboard/Passive_Portfolio_Lab.py", "w") as f:
        f.write(content)

run_patch()
