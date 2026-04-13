import requests
import pandas as pd
from bs4 import BeautifulSoup
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
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
            if len(results) == 5:
                break
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
            aum_cell = cells[1]
            aum = aum_cell.get_text(strip=True)
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
            if len(results) == 5:
                break
        return pd.DataFrame(results)
    except Exception as e:
        print(f"Error fetching US ETF ranking: {e}")
        return pd.DataFrame(columns=["rank","ticker","name","category","source","aum_or_market_cap","currency"])


def get_crypto_ranking():
    try:
        url = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=10&page=1"
        response = requests.get(url, headers=HEADERS, verify=False)
        data = response.json()
        exclude_symbols = {'usdt','usdc','busd','dai','tusd','fdusd','usds'}
        results = []
        rank = 1
        for coin in data:
            symbol = coin.get('symbol','').lower()
            if symbol in exclude_symbols:
                continue
            results.append({
                "rank": rank,
                "ticker": f"{symbol.upper()}-USD",
                "name": coin.get('name',''),
                "category": "CRYPTO",
                "source": "CoinGecko",
                "aum_or_market_cap": coin.get('market_cap',''),
                "currency": "USD"
            })
            rank += 1
            if len(results) == 5:
                break
        return pd.DataFrame(results)
    except Exception as e:
        print(f"Error fetching Crypto ranking: {e}")
        return pd.DataFrame(columns=["rank","ticker","name","category","source","aum_or_market_cap","currency"])


def get_all_candidates():
    tw_df = get_tw_etf_ranking()
    us_df = get_us_etf_ranking()
    crypto_df = get_crypto_ranking()
    return pd.concat([tw_df, us_df, crypto_df], ignore_index=True)


if __name__ == "__main__":
    candidates = get_all_candidates()
    print(candidates.to_string())
