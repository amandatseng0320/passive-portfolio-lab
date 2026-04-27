# Passive Portfolio Lab

A Buy-and-Hold backtesting platform for everyday investors. It explores the historical performance of passive portfolios across various risk profiles, quantifies the "pain" of drawdowns, and estimates the timeline to financial independence (FIRE).

The central question the dashboard tries to answer: **When a portfolio's backtested return looks attractive, what is the accompanying cost?**

---

The Streamlit dashboard is organized into six main modules, guiding you from quick setup to deep-dive projections.

### 0. Quick Start: Investor Personas

Select a preset investor profile (e.g., **Young Professional**, **Pre-Retirement**, **Aggressive Growth**) to instantly populate the dashboard with expert-curated asset allocations, risk levels, and financial parameters. This bypasses the manual screening process and allows for immediate visualization and backtesting of proven strategies.

### 1. Asset Screening & Watchlist

Explore and filter a curated universe of assets including Taiwan ETFs (MoneyDJ), US ETFs (TradingView), Defensive assets (Gold, Bonds), and major Cryptocurrencies.

*   **AgGrid Integration**: A high-performance table interface with built-in sorting and filtering.
*   **Multi-Market Intelligence**: Displays prices in their native currency (TWD, USD) while maintaining mathematically correct sorting based on real-time USD-equivalent value.
*   **Advanced Risk Filters**: Filter assets by CAGR, Sharpe Ratio, or **Maximum Drawdown** (e.g., show only assets with < 20% historic DD).
*   **Dynamic Watchlist**: Check any asset to add it to your local watchlist for downstream backtesting.

### 2. Correlation Analysis

Located directly below the screening table, this module helps you avoid redundant exposure.

*   **Correlation Matrix**: Computes a Pearson correlation heatmap based on 3-year daily returns for all selected assets.
*   **Redundancy Engine**: Automatically identifies pairs with high correlation (> 0.85) and suggests which asset to keep based on scale and volume, helping you build a truly diversified portfolio.

### 3. Risk Allocation & Portfolio Visualization

Allocate your watchlist into a diversified portfolio based on four risk tiers: **Low, Medium, High, and Extreme High**.

*   **Interactive Treemap**: Visualize weights and volatility across your portfolio.
*   **Asset Detail Cards**: Click any asset to see deep-dive metrics (Sharpe, Volatility, Max DD) and a Radar chart comparing it to the market average.

### 4. Backtest & FIRE Projection

Simulate holding your portfolio through history and project your future.

*   **Pain Index & Drawdowns**: Beyond CAGR, we visualize "Pain" by highlighting the top 5 historic drawdown episodes, tagged with macro events (e.g., 2008 GFC, COVID-19).
*   **FIRE Calculator**: Derives your retirement target from annual expenses and withdrawal rates. It projects years-to-FIRE using weighted historical CAGRs, with both nominal and inflation-adjusted (Real) horizons.

### 5. Summary & AI Insights

Receive an instant, holistic review of your portfolio structure, risk trade-offs, and FIRE timeline. Powered by **Gemini 2.5 Flash**, the AI provides **Strategic Next Steps** — actionable, practical advice on how to optimize your allocation and adjust your savings rate to reach your financial goals faster.


---

## Tech Stack

| Layer | Tools |
|---|---|
| Dashboard | Streamlit, **Streamlit-AgGrid** |
| Visualization | Plotly (Treemap, Time Series), Chart.js (Radar) |
| Data Processing | Pandas, NumPy, Scipy |
| Data Collection | Yahoo Finance v8 API (Direct REST), FRED API, BeautifulSoup |
| Storage | Google BigQuery |
| AI Engine | **Google Gemini 2.5 Flash** |

---

## Project Structure

```
passive-portfolio-lab/
├── dashboard/
│   └── Passive_Portfolio_Lab.py      # Main Streamlit Dashboard
├── src/
│   ├── data_collection/
│   │   ├── fetch_prices.py           # Multi-market price fetching
│   │   └── fetch_macro.py            # FRED CPI fetching
│   └── processing/
│       ├── screening.py              # Asset pool & scrapers
│       ├── metrics.py                # Financial metric calculations
│       ├── backtest.py               # Portfolio backtesting engine
│       ├── drawdown_events.py        # Drawdown analysis & tagging
│       └── fire_calculator.py        # FIRE projection logic
├── requirements.txt                  # Dependency list (AgGrid included)
└── README.md                         # Project documentation
```

---

## Methodology & Risk

**Sorting Logic**: The dashboard handles mixed currencies (TWD/USD) by calculating a USD-equivalent value for each asset based on current exchange rates. This value is used for sorting in the AgGrid interface, ensuring that a "100 USD" asset correctly ranks higher than a "150 TWD" asset, even while displaying native units.

**Risk Tiers**:
| Risk Tier | Target Volatility | Typical Composition |
|---|---|---|
| Low | 12% | Bond-heavy / Conservative |
| Medium | 20% | Broad-market Equity |
| High | 35% | Growth / Tech-concentrated |
| Extreme High | 65% | High Crypto exposure |

**Limitations**: 
*   Historical performance is not a guarantee of future results.
*   Crypto metrics should be treated with caution due to the limited historical window and extreme volatility.
*   The 4% withdrawal rule is a baseline; conservative investors should aim for 3-3.5%.
