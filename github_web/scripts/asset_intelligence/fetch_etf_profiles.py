#!/usr/bin/env python3
"""Fetch ETF profile source pages from approved public URLs."""

from __future__ import annotations

import re
from html.parser import HTMLParser

import requests

from blocked_pages import BLOCKED_PAGE_TERMS
from schema import sanitize_text
from sources import source_for_asset, source_for_expense_ratio, validate_source_url


REQUEST_TIMEOUT_SECONDS = 12
USER_AGENT = "PassivePortfolioLab/1.0 (+https://amandatseng0320.github.io/passive-portfolio-lab/)"
ASSET_TITLE_KEYWORDS = ("etf", "fund", "asset", "profile", "基金", "投信")


class MetaDescriptionParser(HTMLParser):
    """Small HTML parser that extracts the first meta description tag."""

    def __init__(self) -> None:
        super().__init__()
        self.description = ""

    def handle_starttag(self, tag: str, attrs) -> None:
        if self.description or tag.lower() != "meta":
            return
        attr_map = {str(k).lower(): str(v) for k, v in attrs if v is not None}
        name = attr_map.get("name", "").lower()
        prop = attr_map.get("property", "").lower()
        if name == "description" or prop == "og:description":
            self.description = attr_map.get("content", "")


class VisibleTextParser(HTMLParser):
    """Extract short visible text from a public HTML page."""

    def __init__(self) -> None:
        super().__init__()
        self._ignored_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() in {"script", "style", "noscript", "svg"}:
            self._ignored_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "noscript", "svg"} and self._ignored_depth:
            self._ignored_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._ignored_depth:
            return
        text = sanitize_text(data, max_len=500)
        if len(text) >= 24:
            self.parts.append(text)


def extract_meta_description(html_text: str) -> str:
    """Extract a sanitized meta description from HTML."""
    parser = MetaDescriptionParser()
    parser.feed(html_text)
    if parser.description:
        return sanitize_text(parser.description, max_len=360)

    title_match = re.search(r"<title[^>]*>(.*?)</title>", html_text, re.IGNORECASE | re.DOTALL)
    if title_match:
        return sanitize_text(title_match.group(1), max_len=240)
    text_parser = VisibleTextParser()
    text_parser.feed(html_text)
    if text_parser.parts:
        return sanitize_text(" ".join(text_parser.parts[:3]), max_len=360)
    return ""


def extract_title(html_text: str) -> str:
    """Extract a sanitized page title."""
    title_match = re.search(r"<title[^>]*>(.*?)</title>", html_text, re.IGNORECASE | re.DOTALL)
    if not title_match:
        return ""
    return sanitize_text(title_match.group(1), max_len=240)


def looks_like_blocked_page(html_text: str, ticker: str) -> bool:
    """Detect common WAF/block pages without rejecting one keyword in isolation."""
    text = sanitize_text(html_text, max_len=20000).lower()
    title = extract_title(html_text).lower()
    ticker_root = ticker.split(".", 1)[0].split("-", 1)[0].lower()
    has_block_keyword = any(keyword in text for keyword in BLOCKED_PAGE_TERMS)
    abnormal_length = len(text) < 2500
    title_mentions_asset = ticker_root in title or any(keyword in title for keyword in ASSET_TITLE_KEYWORDS)
    return has_block_keyword and abnormal_length and not title_mentions_asset


def extract_expense_ratio(html_text: str) -> str:
    """Extract an ETF expense ratio from static HTML when exposed by the source."""
    patterns = [
        r'fundHeader-expr-data[\s\S]{0,220}?([0-9]+(?:\.[0-9]+)?%)',
        r"(?i)gross expense ratio[^0-9]{0,80}([0-9]+(?:\.[0-9]+)?%)",
        r'"expenseRatio"\s*:\s*"([0-9]+(?:\.[0-9]+)?)"',
        r'"expenseRatio"\s*:\s*([0-9]+(?:\.[0-9]+)?)',
        r"(?i)expense ratio[^0-9]{0,80}([0-9]+(?:\.[0-9]+)?%)",
        r"(?i)total expense ratio[^0-9]{0,80}([0-9]+(?:\.[0-9]+)?%)",
        r"(?i)sponsor fee[^0-9]{0,80}([0-9]+(?:\.[0-9]+)?%)",
        r"(?i)經理費[^0-9]{0,80}([0-9]+(?:\.[0-9]+)?%)",
    ]
    for pattern in patterns:
        match = re.search(pattern, html_text, re.DOTALL)
        if not match:
            continue
        value = match.group(1)
        if value.endswith("%"):
            return value
        try:
            return f"{float(value):.2f}%"
        except ValueError:
            return sanitize_text(value, max_len=20)
    return ""


def normalize_percent_text(value: str) -> str:
    """Return a normalized percent string such as 0.30%."""
    text = sanitize_text(value, max_len=120).replace("％", "%")
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*%", text)
    if not match:
        return ""
    return f"{float(match.group(1)):g}%"


def percent_values(value: str) -> list[float]:
    """Return all percent numbers in display order."""
    return [float(v) for v in re.findall(r"([0-9]+(?:\.[0-9]+)?)\s*[％%]", value)]


def format_fee_range(values: list[float]) -> str:
    """Format fixed or tiered fee values from scraped percentages."""
    if not values:
        return ""
    lo = min(values)
    hi = max(values)
    if abs(lo - hi) < 1e-9:
        return f"{lo:g}%"
    return f"{lo:g}%~{hi:g}%"


def fee_bounds(value: str) -> tuple[float, float] | None:
    values = percent_values(value)
    if not values:
        return None
    return min(values), max(values)


def format_expense_ratio(management_fee: str, custodian_fee: str) -> str:
    """Compute basic annual expense ratio as management fee + custodian fee."""
    management = fee_bounds(management_fee)
    custodian = fee_bounds(custodian_fee)
    if not management or not custodian:
        return ""
    lo = management[0] + custodian[0]
    hi = management[1] + custodian[1]
    if abs(lo - hi) < 1e-9:
        return f"{lo:g}%"
    return f"{lo:g}%~{hi:g}%"


def extract_next_value(html_text: str, labels: tuple[str, ...]) -> str:
    """Extract the table/div value immediately following any label."""
    label_group = "|".join(re.escape(label) for label in labels)
    patterns = [
        rf"(?:{label_group})</td>\s*<td[^>]*>(.*?)</td>",
        rf'<div[^>]*>\s*(?:{label_group})\s*</div>\s*<div[^>]*>(.*?)</div>',
    ]
    for pattern in patterns:
        match = re.search(pattern, html_text, flags=re.DOTALL | re.IGNORECASE)
        if match:
            return sanitize_text(match.group(1), max_len=240)
    return ""


def extract_section_fee(html_text: str, start_label: str, end_labels: tuple[str, ...]) -> str:
    """Extract tiered fee percentages from a label-delimited HTML section."""
    start = html_text.find(start_label)
    if start < 0:
        return ""
    end_positions = [html_text.find(label, start + len(start_label)) for label in end_labels]
    end_positions = [pos for pos in end_positions if pos > start]
    end = min(end_positions) if end_positions else start + 1600
    return format_fee_range(percent_values(html_text[start:end]))


def extract_gugu_00955_fees(html_text: str) -> tuple[str, str]:
    """Extract 00955 fees from a public article sentence."""
    text = sanitize_text(html_text, max_len=40000)
    custodian_match = re.search(r"管理費為\s*([0-9]+(?:\.[0-9]+)?%)", text)
    management_match = re.search(r"經理費為\s*([0-9]+(?:\.[0-9]+)?%)", text)
    return (
        normalize_percent_text(management_match.group(1) if management_match else ""),
        normalize_percent_text(custodian_match.group(1) if custodian_match else ""),
    )


def extract_fee_components(html_text: str, ticker: str) -> dict[str, str]:
    """Extract management fee, custodian fee, and computed expense ratio."""
    if ticker == "00955.TWO":
        management_fee, custodian_fee = extract_gugu_00955_fees(html_text)
    else:
        management_fee = extract_next_value(html_text, ("經理費", "管理費"))
        custodian_fee = extract_next_value(html_text, ("保管費",))
        if not management_fee:
            management_fee = extract_section_fee(html_text, "經理費", ("保管費",))
        if not custodian_fee:
            custodian_fee = extract_section_fee(html_text, "保管費", ("保管銀行", "指數介紹"))
        management_fee = format_fee_range(percent_values(management_fee))
        custodian_fee = format_fee_range(percent_values(custodian_fee))

    expense_ratio = format_expense_ratio(management_fee, custodian_fee)
    return {
        "managementFee": management_fee,
        "custodianFee": custodian_fee,
        "expenseRatio": expense_ratio,
        "expenseRatioFormula": "managementFee + custodianFee",
    }


def request_public_page(url: str) -> requests.Response:
    """Fetch an allowlisted public page with default TLS verification."""
    response = requests.get(
        url,
        headers={"User-Agent": USER_AGENT},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response


def fetch_source_summary(ticker: str, category: str) -> dict[str, str]:
    """Fetch a public source page and return a normalized summary snippet."""
    source = source_for_asset(ticker, category)
    validate_source_url(source.source_url)
    response = request_public_page(source.source_url)
    if looks_like_blocked_page(response.text, ticker):
        raise RuntimeError(f"{ticker} source page appears blocked by WAF")
    return {
        "ticker": ticker,
        "sourceName": source.source_name,
        "sourceUrl": source.source_url,
        "sourceSummary": extract_meta_description(response.text),
        "expenseRatio": extract_expense_ratio(response.text),
    }


def fetch_expense_ratio_components(ticker: str, category: str) -> dict[str, str]:
    """Fetch ETF fee components from an approved public source page."""
    source = source_for_expense_ratio(ticker, category)
    validate_source_url(source.source_url)
    response = request_public_page(source.source_url)
    if looks_like_blocked_page(response.text, ticker):
        raise RuntimeError(f"{ticker} expense source page appears blocked by WAF")
    fees = extract_fee_components(response.text, ticker)
    fees.update({
        "expenseRatioSourceName": source.source_name,
        "expenseRatioSourceUrl": source.source_url,
        "expenseRatioCollectionMethod": "web_scraping",
    })
    return fees
