#!/usr/bin/env python3
"""Allowed source registry for asset profile collection."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse


ALLOWED_DOMAINS = {
    "bitcoin.org",
    "cardano.org",
    "dogecoin.com",
    "ethereum.org",
    "investor.vanguard.com",
    "solana.com",
    "tron.network",
    "trondao.org",
    "www.bnbchain.org",
    "www.invesco.com",
    "www.ishares.com",
    "www.etfinfo.tw",
    "www.capitalfund.com.tw",
    "www.spdrgoldshares.com",
    "www.ssga.com",
    "www.twse.com.tw",
    "www.yuantaetf.com",
    "school.gugu.fund",
    "xrpl.org",
}


CURATED_EXPENSE_RATIO_FALLBACKS = {
    "00679B.TWO": {
        "managementFee": "0.1%~0.12%",
        "custodianFee": "0.04%~0.1%",
        "expenseRatio": "0.14%~0.22%",
        "expenseRatioFormula": "managementFee + custodianFee",
        "expenseRatioSourceName": "Yuanta official ETF profile",
        "expenseRatioSourceUrl": "https://www.yuantaetf.com/product/detail/00679B/Basic_information",
        "expenseRatioCollectionMethod": "curated_fallback",
    },
    "00751B.TWO": {
        "managementFee": "0.18%~0.4%",
        "custodianFee": "0.05%~0.1%",
        "expenseRatio": "0.23%~0.5%",
        "expenseRatioFormula": "managementFee + custodianFee",
        "expenseRatioSourceName": "Yuanta official ETF profile",
        "expenseRatioSourceUrl": "https://www.yuantaetf.com/product/detail/00751B/Basic_information",
        "expenseRatioCollectionMethod": "curated_fallback",
    },
    "00955.TWO": {
        "managementFee": "0.6%",
        "custodianFee": "0.15%",
        "expenseRatio": "0.75%",
        "expenseRatioFormula": "managementFee + custodianFee",
        "expenseRatioSourceName": "Gugu public ETF fee profile",
        "expenseRatioSourceUrl": "https://school.gugu.fund/ai/answer/00955%E4%B8%AD-5-655118",
        "expenseRatioCollectionMethod": "curated_fallback",
    },
}


@dataclass(frozen=True)
class AssetSource:
    ticker: str
    source_name: str
    source_url: str


US_ETF_SOURCE_OVERRIDES = {
    "VOO": AssetSource("VOO", "Vanguard official ETF profile", "https://investor.vanguard.com/investment-products/etfs/profile/voo"),
    "VTI": AssetSource("VTI", "Vanguard official ETF profile", "https://investor.vanguard.com/investment-products/etfs/profile/vti"),
    "VUG": AssetSource("VUG", "Vanguard official ETF profile", "https://investor.vanguard.com/investment-products/etfs/profile/vug"),
    "VTV": AssetSource("VTV", "Vanguard official ETF profile", "https://investor.vanguard.com/investment-products/etfs/profile/vtv"),
    "VEA": AssetSource("VEA", "Vanguard official ETF profile", "https://investor.vanguard.com/investment-products/etfs/profile/vea"),
    "VXUS": AssetSource("VXUS", "Vanguard official ETF profile", "https://investor.vanguard.com/investment-products/etfs/profile/vxus"),
    "BND": AssetSource("BND", "Vanguard official ETF profile", "https://investor.vanguard.com/investment-products/etfs/profile/bnd"),
    "IVV": AssetSource("IVV", "iShares official ETF profile", "https://www.ishares.com/us/products/239726/ishares-core-sp-500-etf"),
    "IEFA": AssetSource("IEFA", "iShares official ETF profile", "https://www.ishares.com/us/products/244049/ishares-core-msci-eafe-etf"),
    "IEMG": AssetSource("IEMG", "iShares official ETF profile", "https://www.ishares.com/us/products/244050/ishares-core-msci-emerging-markets-etf"),
    "AGG": AssetSource("AGG", "iShares official ETF profile", "https://www.ishares.com/us/products/239458/ishares-core-us-aggregate-bond-etf"),
    "IEF": AssetSource("IEF", "iShares official ETF profile", "https://www.ishares.com/us/products/239456/ishares-7-10-year-treasury-bond-etf"),
    "SPY": AssetSource("SPY", "SPDR official ETF profile", "https://www.ssga.com/us/en/intermediary/etfs/spdr-sp-500-etf-trust-spy"),
    "GLD": AssetSource("GLD", "SPDR official ETF profile", "https://www.ssga.com/us/en/intermediary/etfs/spdr-gold-shares-gld"),
    "QQQ": AssetSource("QQQ", "Invesco official ETF profile", "https://www.invesco.com/qqq-etf/en/home.html"),
}


CRYPTO_SOURCE_OVERRIDES = {
    "BTC-USD": AssetSource("BTC-USD", "Bitcoin official website", "https://bitcoin.org/en/"),
    "ETH-USD": AssetSource("ETH-USD", "Ethereum official website", "https://ethereum.org/en/"),
    "BNB-USD": AssetSource("BNB-USD", "BNB Chain official website", "https://www.bnbchain.org/en"),
    "XRP-USD": AssetSource("XRP-USD", "XRP Ledger official website", "https://xrpl.org/"),
    "SOL-USD": AssetSource("SOL-USD", "Solana official website", "https://solana.com/"),
    "TRX-USD": AssetSource("TRX-USD", "TRON DAO official website", "https://trondao.org/"),
    "DOGE-USD": AssetSource("DOGE-USD", "Dogecoin official website", "https://dogecoin.com/"),
    "ADA-USD": AssetSource("ADA-USD", "Cardano official website", "https://cardano.org/"),
}


TW_EXPENSE_SOURCE_OVERRIDES = {
    "00679B.TWO": AssetSource(
        "00679B.TWO",
        "Yuanta official ETF profile",
        "https://www.yuantaetf.com/product/detail/00679B/Basic_information",
    ),
    "00751B.TWO": AssetSource(
        "00751B.TWO",
        "Yuanta official ETF profile",
        "https://www.yuantaetf.com/product/detail/00751B/Basic_information",
    ),
    "00919.TW": AssetSource(
        "00919.TW",
        "Capital official ETF profile",
        "https://www.capitalfund.com.tw/etf/product/detail/195/basic",
    ),
    "00937B.TWO": AssetSource(
        "00937B.TWO",
        "Capital official ETF profile",
        "https://www.capitalfund.com.tw/etf/product/detail/378/basic",
    ),
    "00955.TWO": AssetSource(
        "00955.TWO",
        "Gugu public ETF fee profile",
        "https://school.gugu.fund/ai/answer/00955%E4%B8%AD-5-655118",
    ),
}


def is_allowed_url(url: str) -> bool:
    """Return True when a URL belongs to an approved profile data source."""
    parsed = urlparse(url)
    if parsed.scheme != "https":
        return False
    hostname = parsed.hostname or ""
    return hostname in ALLOWED_DOMAINS


def source_for_asset(ticker: str, category: str) -> AssetSource:
    """Return the primary public source for a ticker."""
    if category == "CRYPTO":
        if ticker not in CRYPTO_SOURCE_OVERRIDES:
            raise ValueError(f"No crypto source configured for {ticker}")
        return CRYPTO_SOURCE_OVERRIDES[ticker]

    if ticker.endswith(".TW") or ticker.endswith(".TWO"):
        code = ticker.split(".", 1)[0]
        url = f"https://www.twse.com.tw/en/ETFortune-institute/etfInfo/{code}"
        return AssetSource(ticker=ticker, source_name="TWSE public ETF information page", source_url=url)

    if ticker not in US_ETF_SOURCE_OVERRIDES:
        raise ValueError(f"No US ETF source configured for {ticker}")
    return US_ETF_SOURCE_OVERRIDES[ticker]


def source_for_expense_ratio(ticker: str, category: str) -> AssetSource:
    """Return the public page used to scrape management and custodian fees."""
    if category == "CRYPTO":
        raise ValueError(f"Crypto assets do not have ETF expense ratios: {ticker}")
    if ticker.endswith(".TW") or ticker.endswith(".TWO"):
        if ticker in TW_EXPENSE_SOURCE_OVERRIDES:
            return TW_EXPENSE_SOURCE_OVERRIDES[ticker]
        code = ticker.split(".", 1)[0]
        return AssetSource(
            ticker=ticker,
            source_name="ETFInfo public ETF fee profile",
            source_url=f"https://www.etfinfo.tw/etf/{code}",
        )
    return source_for_asset(ticker, category)


def validate_source_url(url: str) -> None:
    """Raise ValueError when a profile source URL is not explicitly allowed."""
    if not is_allowed_url(url):
        raise ValueError(f"Source URL is not allowed: {url}")
