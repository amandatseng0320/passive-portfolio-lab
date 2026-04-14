with open("dashboard/Passive_Portfolio_Lab.py", "r") as f:
    content = f.read()

# CHANGE 1:
target1 = """def fetch_current_prices(tickers: list) -> dict:
    \"\"\"Fetch current price for each ticker using yfinance.\"\"\"
    import yfinance as yf
    prices = {}
    for ticker in tickers:
        try:
            data = yf.Ticker(ticker).fast_info
            prices[ticker] = round(float(data.last_price), 2)
        except Exception:
            prices[ticker] = None
    return prices"""

replace1 = """def fetch_price_and_volume(tickers: list) -> dict:
    \"\"\"Fetch current price and volume for each ticker using yfinance.\"\"\"
    import yfinance as yf
    result = {}
    for ticker in tickers:
        try:
            info = yf.Ticker(ticker).fast_info
            result[ticker] = {
                'price': round(float(info.last_price), 2),
                'volume': int(info.three_month_average_volume) if hasattr(info, 'three_month_average_volume') and info.three_month_average_volume else None
            }
        except Exception:
            result[ticker] = {'price': None, 'volume': None}
    return result"""

content = content.replace(target1, replace1)

# CHANGE 2:
target2 = """if 'price_map' not in st.session_state:
    with st.spinner("Fetching current prices..."):
        st.session_state.price_map = fetch_current_prices(pool_df['ticker'].tolist())
pool_df['price'] = pool_df['ticker'].map(st.session_state.price_map)"""

replace2 = """if 'market_data' not in st.session_state:
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
)"""
content = content.replace(target2, replace2)

# CHANGE 3:
target3 = """f_col1, f_col2, f_col3, f_col4, f_col5 = st.columns(5)
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
    selected_vol = st.selectbox("Volatility", vol_options, key="pool_vol")"""

replace3 = """f_col1, f_col2, f_col3, f_col4 = st.columns(4)
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
    selected_vol = st.selectbox("Volatility", vol_options, key="pool_vol")"""
content = content.replace(target3, replace3)

# CHANGE 4:
target4 = """filtered = pool_df.copy()
if selected_category != "All":
    filtered = filtered[filtered['category'] == selected_category]
if selected_risk != "All":
    filtered = filtered[filtered['risk_level'] == selected_risk]
if selected_currency != "All":
    filtered = filtered[filtered['currency'] == selected_currency]"""

replace4 = """filtered = pool_df.copy()
if selected_category != "All":
    filtered = filtered[filtered['category'] == selected_category]
if selected_risk != "All":
    filtered = filtered[filtered['risk_level'] == selected_risk]"""
content = content.replace(target4, replace4)

# CHANGE 5:
target5 = """if 'sort_col' not in st.session_state:
    st.session_state.sort_col = 'cagr'
    st.session_state.sort_asc = False

filtered = filtered.sort_values(
    by=st.session_state.sort_col if st.session_state.sort_col in filtered.columns else 'cagr',
    ascending=st.session_state.sort_asc,
    na_position='last'
)"""

replace5 = """CATEGORY_ORDER = {'TW_ETF': 0, 'US_ETF': 1, 'DEFENSIVE': 2, 'CRYPTO': 3}
filtered['_cat_order'] = filtered['category'].map(CATEGORY_ORDER).fillna(99)
filtered = filtered.sort_values(['_cat_order', 'cagr'], ascending=[True, False]).drop(columns=['_cat_order'])"""
content = content.replace(target5, replace5)


# CHANGE 6:
start6_idx = content.find("def build_display_df(df, include_price=True):")
end6_idx = content.find("st.divider()", start6_idx) + len("st.divider()")

replace6 = """def build_display_df(df):
    d = df[['ticker', 'name', 'category', 'price_display', 'volume_display',
            'cagr', 'volatility', 'max_drawdown', 'worst_year', 'worst_year_label']].copy()
    d['cagr'] = d['cagr'].apply(lambda x: f"{x:.2%}" if pd.notnull(x) else "N/A")
    d['volatility'] = d['volatility'].apply(lambda x: f"{x:.2%}" if pd.notnull(x) else "N/A")
    d['max_drawdown'] = d['max_drawdown'].apply(lambda x: f"{x:.2%}" if pd.notnull(x) else "N/A")
    d['worst_year'] = d['worst_year'].apply(lambda x: f"{x:.2%}" if pd.notnull(x) else "N/A")
    d['worst_year_label'] = d['worst_year_label'].apply(lambda x: str(int(x)) if pd.notnull(x) else "N/A")
    d.columns = ['Ticker', 'Name', 'Category', 'Price', 'Volume',
                 'Ann. Return', 'Volatility', 'Max Drawdown', 'Worst Year Ret.', 'Worst Year']
    return d

# ── Asset Pool ─────────────────────────────────────────────────────────────────
st.markdown(f"#### Asset Pool — {len(filtered)} assets")

filtered_reset = filtered.reset_index(drop=True)
display_df = build_display_df(filtered_reset)

editor_df = display_df.copy()
editor_df.insert(0, 'Add', False)

edited = st.data_editor(
    editor_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Add": st.column_config.CheckboxColumn("＋", width="small"),
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
        st.rerun()

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

st.divider()"""

content = content[:start6_idx] + replace6 + content[end6_idx:]

with open("dashboard/Passive_Portfolio_Lab.py", "w") as f:
    f.write(content)

print("Patch applied successfully.")
