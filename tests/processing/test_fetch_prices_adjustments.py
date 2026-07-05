"""
Tests for manual price adjustments in fetch_prices.py.
"""

import pandas as pd

from src.data_collection.fetch_prices import apply_manual_adjustments


def test_0052_split_adjusts_pre_split_prices_and_volume():
    prices = pd.DataFrame({
        "date": ["2025-11-14", "2025-11-17"],
        "open": [700.0, 100.0],
        "high": [714.0, 102.0],
        "low": [686.0, 98.0],
        "close": [707.0, 101.0],
        "volume": [10, 20],
    })

    adjusted = apply_manual_adjustments(prices.copy(), "0052.TW")

    assert adjusted.loc[0, "open"] == 100.0
    assert adjusted.loc[0, "high"] == 102.0
    assert adjusted.loc[0, "low"] == 98.0
    assert adjusted.loc[0, "close"] == 101.0
    assert adjusted.loc[0, "volume"] == 70
    assert adjusted.loc[1, "close"] == 101.0
    assert str(adjusted["volume"].dtype) == "int64"


def test_0050_existing_split_adjustment_is_preserved():
    prices = pd.DataFrame({
        "date": ["2013-12-31", "2014-01-02"],
        "open": [40.0, 10.0],
        "high": [40.0, 10.0],
        "low": [36.0, 9.0],
        "close": [37.2, 9.3],
        "volume": [100, 200],
    })

    adjusted = apply_manual_adjustments(prices.copy(), "0050.TW")

    assert adjusted.loc[0, "open"] == 10.0
    assert adjusted.loc[0, "close"] == 9.3
    assert adjusted.loc[0, "volume"] == 400
    assert adjusted.loc[1, "close"] == 9.3
