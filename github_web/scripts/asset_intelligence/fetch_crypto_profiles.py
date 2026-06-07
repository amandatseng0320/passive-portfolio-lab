#!/usr/bin/env python3
"""Fetch crypto profile source pages from approved public URLs."""

from __future__ import annotations

from fetch_etf_profiles import fetch_source_summary


def fetch_crypto_source_summary(ticker: str) -> dict[str, str]:
    """Fetch a crypto public source page and return a normalized summary snippet."""
    return fetch_source_summary(ticker, "CRYPTO")
