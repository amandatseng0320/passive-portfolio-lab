"""
screening.py
Asset pool for Passive Portfolio Lab.

Asset Pool Overview
-------------------
This pool contains 37 assets across three categories:
  - Taiwan ETF  (TW_ETF)   : 14 funds, selected by AUM rank among Taiwan ETFs; includes 00646.TW and 00955.TWO as owner additions (source: Yahoo TW, 2026/04/27)
  - US ETF      (US_ETF)   : 15 funds, selected by AUM rank among US ETFs (source: TipRanks / InvestLane, 2026/03–04)
  - Crypto      (CRYPTO)   :  8 coins, top 10 by market cap excluding stablecoins and assets with insufficient history (source: CoinMarketCap, 2026/04)

The asset pool is a static list; no web scraping occurs at runtime.
Historical metrics (CAGR, volatility, max drawdown, Sharpe) are read from the BigQuery asset_metrics table.
Current prices and volumes are fetched in real time at page load via the Yahoo Finance v8 REST API.

How to Update
-------------
To modify the asset pool, edit the ASSET_POOL list below directly,
then re-run fetch_prices.py and metrics.py to backfill historical data for any new tickers.
"""

from __future__ import annotations
from typing import TypedDict
import pandas as pd


class AssetInfo(TypedDict):
    ticker: str          # Yahoo Finance ticker (TW stocks include .TW / .TWO suffix; crypto includes -USD suffix)
    name: str            # Display name
    category: str        # Top-level category: TW_ETF | US_ETF | CRYPTO
    subcategory: str     # Sub-category (for display purposes)
    aum_rank: int        # AUM / market-cap rank at time of selection
    aum_note: str        # Human-readable AUM / market-cap description (UI display only)
    description: str     # One-sentence summary


ASSET_POOL: list[AssetInfo] = [

    # ── Taiwan ETFs (ranked by AUM, data as of 2026/04/27) ───────────────────
    {
        "ticker": "0050.TW",
        "name": "Yuanta Taiwan 50 ETF",
        "category": "TW_ETF",
        "subcategory": "Market-Cap",
        "aum_rank": 1,
        "aum_note": "approx. TWD 1,661.5B",
        "description": "Tracks the top 50 Taiwan companies by market cap; the core passive investment vehicle for the Taiwan stock market.",
    },
    {
        "ticker": "0056.TW",
        "name": "Yuanta High Dividend ETF",
        "category": "TW_ETF",
        "subcategory": "High Dividend",
        "aum_rank": 2,
        "aum_note": "approx. TWD 584.1B",
        "description": "Selects the 30 Taiwan stocks with the highest forecast cash dividend yield; the flagship high-dividend ETF in Taiwan.",
    },
    {
        "ticker": "00878.TW",
        "name": "Cathay Sustainable High Dividend ETF",
        "category": "TW_ETF",
        "subcategory": "High Dividend / ESG",
        "aum_rank": 3,
        "aum_note": "approx. TWD 485.4B",
        "description": "Combines ESG screening with a high-dividend strategy; pays quarterly dividends.",
    },
    {
        "ticker": "00919.TW",
        "name": "Group Benefits Taiwan Select High Yield ETF",
        "category": "TW_ETF",
        "subcategory": "High Dividend",
        "aum_rank": 4,
        "aum_note": "approx. TWD 451.8B",
        "description": "High-dividend plus multi-factor stock selection; monthly distributions; fast-growing AUM.",
    },
    {
        "ticker": "006208.TW",
        "name": "Fubon Taiwan 50 ETF",
        "category": "TW_ETF",
        "subcategory": "Market-Cap",
        "aum_rank": 5,
        "aum_note": "approx. TWD 389.4B",
        "description": "Also tracks the Taiwan 50 index; a competitor to 0050 with a lower expense ratio.",
    },
    {
        "ticker": "00937B.TWO",
        "name": "Group Benefits ESG IG Bond 20+ ETF",
        "category": "TW_ETF",
        "subcategory": "Bond",
        "aum_rank": 6,
        "aum_note": "approx. TWD 267.9B",
        "description": "Invests in ESG investment-grade corporate bonds with 20+ year maturities; monthly distributions.",
    },
    {
        "ticker": "00679B.TWO",
        "name": "Yuanta US Treasury 20+ Year ETF",
        "category": "TW_ETF",
        "subcategory": "Bond",
        "aum_rank": 8,
        "aum_note": "approx. TWD 203.7B",
        "description": "Tracks 20-year US Treasuries; the primary tool for holding long-duration US bonds in TWD.",
    },
    {
        "ticker": "00751B.TWO",
        "name": "Yuanta AAA-A Corporate Bond ETF",
        "category": "TW_ETF",
        "subcategory": "Bond",
        "aum_rank": 9,
        "aum_note": "approx. TWD 180.0B",
        "description": "Invests in highly-rated US corporate bonds, balancing yield with credit quality.",
    },
    {
        "ticker": "0052.TW",
        "name": "Fubon Technology ETF",
        "category": "TW_ETF",
        "subcategory": "Technology Theme",
        "aum_rank": 10,
        "aum_note": "approx. TWD 132.0B",
        "description": "Tracks the Taiwan Technology Index; top holdings include TSMC and MediaTek.",
    },
    {
        "ticker": "00929.TW",
        "name": "Fuh Hwa Taiwan Tech High Yield ETF",
        "category": "TW_ETF",
        "subcategory": "Tech High Dividend",
        "aum_rank": 11,
        "aum_note": "approx. TWD 115.2B",
        "description": "Technology stocks combined with a high-dividend strategy; Taiwan's first monthly-dividend ETF.",
    },
    {
        "ticker": "00713.TW",
        "name": "Yuanta Taiwan High Dividend Low Volatility ETF",
        "category": "TW_ETF",
        "subcategory": "High Dividend Low Vol",
        "aum_rank": 12,
        "aum_note": "approx. TWD 113.0B",
        "description": "Combines high dividend and low-volatility factors; suited for conservative investors.",
    },
    {
        "ticker": "00952.TW",
        "name": "KGI Taiwan AI 50 ETF",
        "category": "TW_ETF",
        "subcategory": "AI Theme",
        "aum_rank": 14,
        "aum_note": "approx. TWD 60.0B",
        "description": "Top 50 companies in Taiwan's AI supply chain; high-purity AI theme with monthly distributions.",
    },
    {
        "ticker": "00646.TW",
        "name": "Yuanta S&P 500 ETF",
        "category": "TW_ETF",
        "subcategory": "S&P 500 Exposure",
        "aum_rank": 99,
        "aum_note": "approx. TWD 25.0B",
        "description": "Tracks the S&P 500 index in TWD; provides US large-cap exposure without currency conversion. Owner addition.",
    },
    {
        "ticker": "00955.TWO",
        "name": "CTBC Japan Sogo Shosha ETF",
        "category": "TW_ETF",
        "subcategory": "Japan Sogo Shosha",
        "aum_rank": 99,
        "aum_note": "approx. TWD 5.0B",
        "description": "Tracks Japan's five major trading conglomerates (sogo shosha). Limited history since 2023 — metrics are indicative. Owner addition.",
    },

    # ── US ETFs (ranked by AUM, data as of 2026/03–04) ───────────────────────
    {
        "ticker": "VOO",
        "name": "Vanguard S&P 500 ETF",
        "category": "US_ETF",
        "subcategory": "US Large-Cap Blend",
        "aum_rank": 1,
        "aum_note": "approx. USD 827.0B",
        "description": "The world's largest ETF; tracks the S&P 500 with a 0.03% expense ratio.",
    },
    {
        "ticker": "IVV",
        "name": "iShares Core S&P 500 ETF",
        "category": "US_ETF",
        "subcategory": "US Large-Cap Blend",
        "aum_rank": 2,
        "aum_note": "approx. USD 766.0B",
        "description": "Also tracks the S&P 500; managed by BlackRock and preferred by institutional investors.",
    },
    {
        "ticker": "SPY",
        "name": "SPDR S&P 500 ETF Trust",
        "category": "US_ETF",
        "subcategory": "US Large-Cap Blend",
        "aum_rank": 3,
        "aum_note": "approx. USD 672.0B",
        "description": "The oldest S&P 500 ETF; highest liquidity in the options market.",
    },
    {
        "ticker": "VTI",
        "name": "Vanguard Total Stock Market ETF",
        "category": "US_ETF",
        "subcategory": "US Total Market",
        "aum_rank": 4,
        "aum_note": "approx. USD 586.0B",
        "description": "Covers ~3,700 US large-, mid-, and small-cap stocks; expense ratio 0.03%.",
    },
    {
        "ticker": "QQQ",
        "name": "Invesco QQQ Trust",
        "category": "US_ETF",
        "subcategory": "US Technology Growth",
        "aum_rank": 5,
        "aum_note": "approx. USD 400.0B",
        "description": "Tracks the NASDAQ-100; tech-concentrated with 10-year annualized returns above 18%.",
    },
    {
        "ticker": "VUG",
        "name": "Vanguard Growth ETF",
        "category": "US_ETF",
        "subcategory": "US Growth",
        "aum_rank": 6,
        "aum_note": "approx. USD 207.4B",
        "description": "Large-cap growth stocks with high tech exposure; expense ratio 0.04%.",
    },
    {
        "ticker": "VEA",
        "name": "Vanguard FTSE Developed Markets ETF",
        "category": "US_ETF",
        "subcategory": "Developed International",
        "aum_rank": 7,
        "aum_note": "approx. USD 219.9B",
        "description": "Covers developed markets outside the US, including Europe, Japan, and Canada.",
    },
    {
        "ticker": "IEFA",
        "name": "iShares Core MSCI EAFE ETF",
        "category": "US_ETF",
        "subcategory": "Developed International",
        "aum_rank": 8,
        "aum_note": "approx. USD 180.9B",
        "description": "Tracks the MSCI EAFE index (excluding Canada); primarily Europe and Japan.",
    },
    {
        "ticker": "VTV",
        "name": "Vanguard Value ETF",
        "category": "US_ETF",
        "subcategory": "US Value",
        "aum_rank": 9,
        "aum_note": "approx. USD 169.3B",
        "description": "Large-cap value stocks with low P/E and high dividend yield; a natural pair with VUG.",
    },
    {
        "ticker": "GLD",
        "name": "SPDR Gold Shares",
        "category": "US_ETF",
        "subcategory": "Gold / Commodities",
        "aum_rank": 10,
        "aum_note": "approx. USD 163.4B",
        "description": "The world's largest physically-backed gold ETF; hedges inflation and systemic risk.",
    },
    {
        "ticker": "BND",
        "name": "Vanguard Total Bond Market ETF",
        "category": "US_ETF",
        "subcategory": "US Total Bond",
        "aum_rank": 11,
        "aum_note": "approx. USD 152.6B",
        "description": "Covers US investment-grade government and corporate bonds; expense ratio 0.03%.",
    },
    {
        "ticker": "IEMG",
        "name": "iShares Core MSCI Emerging Markets ETF",
        "category": "US_ETF",
        "subcategory": "Emerging Markets",
        "aum_rank": 12,
        "aum_note": "approx. USD 148.9B",
        "description": "Tracks the MSCI Emerging Markets index; top three exposures are China, India, and Brazil.",
    },
    {
        "ticker": "VXUS",
        "name": "Vanguard Total International Stock ETF",
        "category": "US_ETF",
        "subcategory": "Global ex-US",
        "aum_rank": 13,
        "aum_note": "approx. USD 144.0B",
        "description": "Covers both developed and emerging markets outside the US in a single fund.",
    },
    {
        "ticker": "AGG",
        "name": "iShares Core U.S. Aggregate Bond ETF",
        "category": "US_ETF",
        "subcategory": "US Total Bond",
        "aum_rank": 14,
        "aum_note": "approx. USD 135.9B",
        "description": "Tracks the Bloomberg US Aggregate Bond Index; highly similar to BND.",
    },
    {
        "ticker": "IEF",
        "name": "iShares 7-10 Year Treasury Bond ETF",
        "category": "US_ETF",
        "subcategory": "Intermediate US Treasury",
        "aum_rank": 15,
        "aum_note": "approx. USD 45.0B",
        "description": "Moderate interest-rate sensitivity; commonly used as an equity hedge.",
    },

    # ── Crypto (top 10 by market cap, excluding stablecoins, data as of 2026/04) ──
    {
        "ticker": "BTC-USD",
        "name": "Bitcoin",
        "category": "CRYPTO",
        "subcategory": "Store of Value",
        "aum_rank": 1,
        "aum_note": "approx. USD 1,300.0B",
        "description": "~58% market dominance; digital gold and the preferred crypto asset for institutional holdings.",
    },
    {
        "ticker": "ETH-USD",
        "name": "Ethereum",
        "category": "CRYPTO",
        "subcategory": "Smart Contract Platform",
        "aum_rank": 2,
        "aum_note": "approx. USD 280.0B",
        "description": "Core infrastructure for DeFi, NFTs, and Layer 2; the world's second-largest cryptocurrency.",
    },
    {
        "ticker": "BNB-USD",
        "name": "BNB",
        "category": "CRYPTO",
        "subcategory": "Exchange Platform Token",
        "aum_rank": 3,
        "aum_note": "approx. USD 85.0B",
        "description": "Native token of the Binance ecosystem and BNB Chain; features a periodic token-burn mechanism.",
    },
    {
        "ticker": "XRP-USD",
        "name": "XRP",
        "category": "CRYPTO",
        "subcategory": "Cross-Border Payments",
        "aum_rank": 4,
        "aum_note": "approx. USD 65.0B",
        "description": "Led by Ripple; focused on institutional cross-border settlement with 3–5 second finality.",
    },
    {
        "ticker": "SOL-USD",
        "name": "Solana",
        "category": "CRYPTO",
        "subcategory": "High-Performance L1",
        "aum_rank": 5,
        "aum_note": "approx. USD 65.0B",
        "description": "High throughput and low fees; one of the most active chains for DeFi and meme coins.",
    },
    {
        "ticker": "TRX-USD",
        "name": "TRON",
        "category": "CRYPTO",
        "subcategory": "Stablecoin Settlement Chain",
        "aum_rank": 6,
        "aum_note": "approx. USD 25.0B",
        "description": "The largest chain for USDT on-chain activity; low-fee stablecoin ecosystem.",
    },
    {
        "ticker": "DOGE-USD",
        "name": "Dogecoin",
        "category": "CRYPTO",
        "subcategory": "Meme Coin",
        "aum_rank": 7,
        "aum_note": "approx. USD 25.0B",
        "description": "The most liquid meme coin; PoW consensus mechanism with a strong community following.",
    },
    {
        "ticker": "ADA-USD",
        "name": "Cardano",
        "category": "CRYPTO",
        "subcategory": "Academic L1",
        "aum_rank": 8,
        "aum_note": "approx. USD 20.0B",
        "description": "Research-driven development; PoS consensus with regulatory compliance focus and mature governance.",
    },
]


# ── Utility Functions ─────────────────────────────────────────────────────────

def validate_tickers(tickers: list[str]) -> None:
    """Raise ValueError if any ticker is not in ASSET_POOL.

    Call this before interpolating tickers into SQL to prevent injection.
    """
    allowed = {a["ticker"] for a in ASSET_POOL}
    invalid = [t for t in tickers if t not in allowed]
    if invalid:
        raise ValueError(f"Ticker(s) not in ASSET_POOL: {invalid}")


def get_asset_info(ticker: str) -> AssetInfo | None:
    """Return full asset info for a given ticker, or None if not found."""
    for a in ASSET_POOL:
        if a["ticker"] == ticker:
            return a
    return None


_CATEGORY_CURRENCY: dict[str, str] = {
    "TW_ETF": "TWD",
    "US_ETF": "USD",
    "CRYPTO": "USD",
}


def get_all_candidates() -> pd.DataFrame:
    """
    Return the full asset pool as a DataFrame compatible with the schema
    previously produced by the dynamic screening functions.

    Columns: ticker, name, category, currency, rank, source, aum_or_market_cap
    """
    rows = [
        {
            "ticker":           a["ticker"],
            "name":             a["name"],
            "category":         a["category"],
            "currency":         _CATEGORY_CURRENCY.get(a["category"], "USD"),
            "rank":             a["aum_rank"],
            "source":           "Static",
            "aum_or_market_cap": a["aum_note"],
        }
        for a in ASSET_POOL
    ]
    return pd.DataFrame(rows)


if __name__ == "__main__":
    tw  = [a["ticker"] for a in ASSET_POOL if a["category"] == "TW_ETF"]
    us  = [a["ticker"] for a in ASSET_POOL if a["category"] == "US_ETF"]
    cry = [a["ticker"] for a in ASSET_POOL if a["category"] == "CRYPTO"]
    print(f"Taiwan ETF  ({len(tw)}):  {tw}")
    print(f"US ETF      ({len(us)}):  {us}")
    print(f"Crypto      ({len(cry)}): {cry}")
    print(f"Total: {len(ASSET_POOL)} assets")
