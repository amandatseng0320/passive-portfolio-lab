import requests
import pandas as pd
from bs4 import BeautifulSoup
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# Tickers that appear in the upstream rankings (MoneyDJ / CoinGecko) but do NOT
# have a usable daily-price feed on Yahoo Finance, so they would just spam the
# fetch log and never produce metrics. We filter them at the end of
# get_all_candidates() so they also never show up in the dashboard watchlist.
#
# If Yahoo later starts carrying one of these, just remove it from the set.
YAHOO_UNAVAILABLE_TICKERS = {
    # TW bond ETFs — MoneyDJ market-cap top-10 often includes these but
    # Yahoo doesn't price them (different data provider).
    "00937B.TW",
    "00679B.TW",
    "00687B.TW",
    "00687C.TW",
    "00751B.TW",
    # Bitfinex exchange token — appears in CoinGecko top-20 by market cap
    # but Yahoo Finance has no LEO-USD feed.
    "LEO-USD",
}

def get_tw_etf_ranking():
    try:
        url = "https://www.moneydj.com/ETF/X/Rank/Rank0004.xdjhtm?eRank=mkt&eOrd=t800074&eMid=TW&eArea=0&eTarget=0&eCoin=0&eTab=5&ePeriod=1Y"
        response = requests.get(url, headers=HEADERS, verify=False)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        tables = soup.find_all('table')
        table = max(tables, key=lambda t: len(t.find_all('tr')))
        results = []
        for row in table.find_all('tr'):
            col00 = row.find('td', class_='col00')
            col01 = row.find('td', class_='col01')
            col02 = row.find('td', class_='col02')
            col04 = row.find('td', class_='col04')
            if not all([col00, col01, col02, col04]):
                continue
            rank_text = col00.get_text(strip=True)
            if not rank_text.isdigit():
                continue
            a_tag = col01.find('a')
            if not a_tag:
                continue
            etfid = a_tag.get('etfid', '')
            ticker = etfid if etfid.endswith('.TW') else etfid + '.TW'
            name = col02.get_text(strip=True)
            aum = col04.get_text(strip=True)
            results.append({
                "rank": int(rank_text),
                "ticker": ticker,
                "name": name,
                "category": "TW_ETF",
                "source": "MoneyDJ",
                "aum_or_market_cap": aum,
                "currency": "TWD"
            })
            if len(results) == 10:
                break

        # Manually include specific ETFs that may not appear in top-10 by market cap
        # but are considered important reference assets for the dashboard.
        # - 00646.TW: TW-listed S&P 500 tracker, useful for "SPY in TWD" comparison.
        # - 00955.TW: Newly-launched (2024) Japan trading-house ETF, offers Japan exposure.
        # Dedupe happens downstream via get_all_candidates(); if MoneyDJ already returned
        # one of these in its top-10, the manual entry is skipped here.
        manual_additions = [
            {"ticker": "00646.TW", "name": "元大 S&P 500"},
            # 00955 is listed on TPEx (Taipei Exchange, OTC board), so on Yahoo
            # Finance it carries the .TWO suffix rather than .TW. Using .TW
            # returns HTTP 404 from the v8 chart endpoint.
            {"ticker": "00955.TWO", "name": "中信日本商社"},
        ]
        existing_tickers = {r["ticker"] for r in results}
        for add in manual_additions:
            if add["ticker"] not in existing_tickers:
                results.append({
                    "rank": len(results) + 1,
                    "ticker": add["ticker"],
                    "name": add["name"],
                    "category": "TW_ETF",
                    "source": "Manual",
                    "aum_or_market_cap": "N/A",
                    "currency": "TWD",
                })

        return pd.DataFrame(results)
    except Exception as e:
        print(f"Error fetching TW ETF ranking: {e}")
        return pd.DataFrame(columns=["rank","ticker","name","category","source","aum_or_market_cap","currency"])


def get_us_etf_ranking():
    try:
        url = "https://www.tradingview.com/markets/etfs/funds-usa/"
        response = requests.get(url, headers=HEADERS, verify=False)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table')
        if not table:
            raise ValueError("No table found on TradingView page")
        results = []
        rank = 1
        for row in table.find_all('tr'):
            cells = row.find_all('td')
            if len(cells) < 3:
                continue
            first_cell = cells[0]
            a_tags = first_cell.find_all('a')
            if len(a_tags) < 2:
                continue
            ticker = a_tags[0].get_text(strip=True)
            name = a_tags[1].get_text(strip=True)
            if not ticker:
                continue
            aum = cells[1].get_text(strip=True)
            results.append({
                "rank": rank,
                "ticker": ticker,
                "name": name,
                "category": "US_ETF",
                "source": "TradingView",
                "aum_or_market_cap": aum,
                "currency": "USD"
            })
            rank += 1
            if len(results) == 10:
                break
        return pd.DataFrame(results)
    except Exception as e:
        print(f"Error fetching US ETF ranking: {e}")
        return pd.DataFrame(columns=["rank","ticker","name","category","source","aum_or_market_cap","currency"])


def get_defensive_etf_list():
    """
    Returns a fixed list of defensive ETFs (bonds, gold, commodities).
    These are manually curated as they require domain knowledge to identify.
    """
    defensive_assets = [
        {"rank": 1, "ticker": "TLT",  "name": "iShares 20+ Year Treasury Bond ETF", "category": "DEFENSIVE", "source": "Manual", "aum_or_market_cap": "N/A", "currency": "USD"},
        {"rank": 2, "ticker": "IEF",  "name": "iShares 7-10 Year Treasury Bond ETF","category": "DEFENSIVE", "source": "Manual", "aum_or_market_cap": "N/A", "currency": "USD"},
        {"rank": 3, "ticker": "BND",  "name": "Vanguard Total Bond Market ETF",      "category": "DEFENSIVE", "source": "Manual", "aum_or_market_cap": "N/A", "currency": "USD"},
        {"rank": 4, "ticker": "GLD",  "name": "SPDR Gold Shares",                    "category": "DEFENSIVE", "source": "Manual", "aum_or_market_cap": "N/A", "currency": "USD"},
        {"rank": 5, "ticker": "DBC",  "name": "Invesco DB Commodity Index ETF",      "category": "DEFENSIVE", "source": "Manual", "aum_or_market_cap": "N/A", "currency": "USD"},
    ]
    return pd.DataFrame(defensive_assets)


def get_crypto_ranking():
    """
    Return a fixed list of the top-5 cryptocurrencies by market cap (as of
    2025): BTC, ETH, XRP, BNB, SOL.

    This is intentionally hardcoded rather than scraped from CoinGecko for
    three reasons:
      1. Market-cap rankings shift daily — a scraped list would make the
         watchlist and the dashboard copy ("Crypto (5): BTC, ETH, XRP, BNB,
         SOL …") drift out of sync over time.
      2. It removes a runtime dependency on CoinGecko's rate-limited public
         API, which intermittently throttles unauthenticated requests.
      3. Stablecoins (USDT, USDC, DAI, …), wrapped variants (WBTC, wstETH),
         exchange-specific tokens (LEO, WBT), and memecoins (DOGE, SHIB) are
         deliberately excluded because they don't fit the passive-portfolio
         investment thesis this dashboard is built around. BNB is retained
         because it also functions as the native gas token of BNB Chain, not
         purely an exchange token.
    """
    coins = [
        {"rank": 1, "ticker": "BTC-USD", "name": "Bitcoin"},
        {"rank": 2, "ticker": "ETH-USD", "name": "Ethereum"},
        {"rank": 3, "ticker": "XRP-USD", "name": "XRP"},
        {"rank": 4, "ticker": "BNB-USD", "name": "BNB"},
        {"rank": 5, "ticker": "SOL-USD", "name": "Solana"},
    ]
    results = [
        {
            **c,
            "category": "CRYPTO",
            "source": "Manual",
            "aum_or_market_cap": "N/A",
            "currency": "USD",
        }
        for c in coins
    ]
    return pd.DataFrame(results)


def get_all_candidates():
    tw_df = get_tw_etf_ranking()
    us_df = get_us_etf_ranking()
    defensive_df = get_defensive_etf_list()
    crypto_df = get_crypto_ranking()
    combined = pd.concat([tw_df, us_df, defensive_df, crypto_df], ignore_index=True)
    combined = combined.drop_duplicates(subset='ticker', keep='first').reset_index(drop=True)
    # Drop tickers that Yahoo Finance doesn't actually price — they would just
    # fail to fetch, never appear in asset_metrics, and add no value to the
    # watchlist UI. See YAHOO_UNAVAILABLE_TICKERS above for rationale.
    combined = combined[~combined['ticker'].isin(YAHOO_UNAVAILABLE_TICKERS)].reset_index(drop=True)
    return combined


if __name__ == "__main__":
    candidates = get_all_candidates()
    print(candidates.to_string())
    print(f"\nTotal candidates: {len(candidates)}")
    print(f"By category:\n{candidates['category'].value_counts()}")
