with open("dashboard/Passive_Portfolio_Lab.py", "r") as f:
    content = f.read()

# CHANGE 1
target1 = """selected_tickers = filtered_reset.loc[edited['Add'] == True, 'ticker'].tolist()
if selected_tickers:
    if st.button(f"Add {len(selected_tickers)} asset(s) to Watchlist", type="primary", key="add_to_watchlist"):
        for t in selected_tickers:
            if t not in st.session_state.watchlist:
                st.session_state.watchlist.append(t)
        st.rerun()"""

replace1 = """selected_tickers = filtered_reset.loc[edited['Add'] == True, 'ticker'].tolist()
if selected_tickers:
    if st.button(f"Add {len(selected_tickers)} asset(s) to Watchlist", type="primary", key="add_to_watchlist"):
        for t in selected_tickers:
            if t not in st.session_state.watchlist:
                st.session_state.watchlist.append(t)
        st.session_state.watchlist = list(dict.fromkeys(st.session_state.watchlist))
        st.rerun(scope="app")"""

if target1 in content:
    content = content.replace(target1, replace1)
else:
    print("Warning: Target1 not found")

# CHANGE 2
target2 = """        alloc_col1, alloc_col2 = st.columns([1, 2])

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
            st.plotly_chart(pie_fig, use_container_width=True)"""

replace2 = """        alloc_df['weight_pct'] = (alloc_df['weight'] * 100).round(1)
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
        st.plotly_chart(treemap_fig, use_container_width=True)"""

if target2 in content:
    content = content.replace(target2, replace2)
else:
    print("Warning: Target2 not found")

with open("dashboard/Passive_Portfolio_Lab.py", "w") as f:
    f.write(content)

print("Patch 4 applied.")
