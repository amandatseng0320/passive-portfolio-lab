"""Fetch US CPI year-over-year inflation rate from the FRED API."""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

def get_latest_cpi_yoy() -> float:
    """
    Fetch the latest US CPI year-over-year inflation rate from FRED API.
    Series: CPIAUCSL (Consumer Price Index for All Urban Consumers)
    Returns the most recent annual inflation rate as a float (e.g. 0.031 for 3.1%).
    Falls back to 0.025 if the API call fails.
    """
    api_key = os.getenv("FRED_API_KEY")
    if not api_key:
        print("FRED_API_KEY not found in .env. Using fallback inflation rate of 2.5%.")
        return 0.025

    try:
        url = (
            "https://api.stlouisfed.org/fred/series/observations"
            "?series_id=CPIAUCSL"
            "&api_key=" + api_key +
            "&sort_order=desc"
            "&limit=13"
            "&file_type=json"
        )
        response = requests.get(url, timeout=10, verify=False)
        data = response.json()
        observations = data.get("observations", [])

        # We request limit=13 (most recent month + 12 months prior) sorted descending,
        # so observations[0] = latest month, observations[12] = same month one year ago.
        REQUIRED = 13
        if not isinstance(observations, list) or len(observations) < REQUIRED:
            print("Not enough FRED data to calculate YoY. Using fallback 2.5%.")
            return 0.025

        latest_val = observations[0].get('value', '.')
        year_ago_val = observations[12].get('value', '.')
        # FRED uses '.' as a placeholder for missing/unreleased observations.
        if latest_val == '.' or year_ago_val == '.':
            print("FRED returned missing value ('.'). Using fallback 2.5%.")
            return 0.025

        latest = float(latest_val)
        year_ago = float(year_ago_val)
        yoy = (latest - year_ago) / year_ago
        return round(yoy, 4)

    except Exception as e:
        print(f"Failed to fetch CPI from FRED: {e}. Using fallback 2.5%.")
        return 0.025


if __name__ == "__main__":
    rate = get_latest_cpi_yoy()
    print(f"Latest CPI YoY Inflation Rate: {rate:.2%}")
