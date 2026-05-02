#!/usr/bin/env python3
"""
export_web_data.py
------------------
Reads asset metrics and price history from BigQuery and regenerates
github_web/src/ppl-data.js so the static React SPA has accurate data.

The script replaces the generated PPL_ASSETS and PPL_PRICE_HISTORY blocks.
Persona presets, calculation functions, and everything else in ppl-data.js are
untouched.

Usage (local):
    python github_web/scripts/export_web_data.py

Usage (CI — set env vars via GitHub Secrets):
    GOOGLE_CLOUD_PROJECT=... BIGQUERY_DATASET=... python github_web/scripts/export_web_data.py
"""

import os
import re
import sys
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pandas_gbq
from dotenv import load_dotenv

load_dotenv()

# ── Paths ──────────────────────────────────────────────────────────────────────
REPO_ROOT  = Path(__file__).resolve().parents[2]
WEB_ROOT   = Path(__file__).resolve().parents[1]
OUTPUT     = WEB_ROOT / "src" / "ppl-data.js"
sys.path.append(str(REPO_ROOT / "streamlit_dashboard"))

from src.processing.screening import ASSET_POOL
from src.processing.backtest import load_fx_rate

# ── Chinese names (TW ETFs only — US/Crypto keep English) ─────────────────────
ZH_NAMES = {
    "0050.TW":    "元大台灣50",
    "0056.TW":    "元大高股息",
    "00878.TW":   "國泰永續高股息",
    "00919.TW":   "群益台灣精選高息",
    "006208.TW":  "富邦台50",
    "00937B.TWO": "群益ESG投等債20+",
    "00679B.TWO": "元大美債20年",
    "00751B.TWO": "元大AAA至A公司債",
    "0052.TW":    "富邦科技",
    "00929.TW":   "復華台灣科技優息",
    "00713.TW":   "元大台灣高息低波",
    "00952.TW":   "凱基台灣AI 50",
    "00646.TW":   "元大S&P500",
    "00955.TWO":  "中信日本商社",
}

# ── AUM note overrides (for display notes not in BigQuery) ─────────────────────
AUM_OVERRIDES = {
    "00955.TWO": "approx. TWD 5.0B ⚠️",   # limited history since 2023
}

METRIC_FALLBACKS = {
    "00646.TW": {
        "cagr": 0.135, "volatility": 0.185, "max_drawdown": -0.350,
        "sharpe_ratio": 0.73, "worst_year": -0.195, "worst_year_label": 2022,
    },
    "00955.TWO": {
        "cagr": 0.150, "volatility": 0.220, "max_drawdown": -0.280,
        "sharpe_ratio": 0.68, "worst_year": -0.200, "worst_year_label": 2023,
    },
}

# ── Build lookup from ASSET_POOL ───────────────────────────────────────────────
POOL_MAP = {a["ticker"]: a for a in ASSET_POOL}


def js_string(value: str) -> str:
    """Return a JavaScript-safe string literal."""
    return json.dumps(str(value), ensure_ascii=False)


def sql_string(value: str) -> str:
    """Return a BigQuery SQL string literal."""
    return "'" + str(value).replace("\\", "\\\\").replace("'", "\\'") + "'"


def load_metrics() -> pd.DataFrame:
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    dataset_id = os.getenv("BIGQUERY_DATASET")
    if not project_id or not dataset_id:
        raise ValueError(
            "Missing GOOGLE_CLOUD_PROJECT or BIGQUERY_DATASET. "
            "Set them in .env or as environment variables."
        )
    query = f"SELECT * FROM `{dataset_id}.asset_metrics`"
    print(f"Querying {project_id}.{dataset_id}.asset_metrics ...")
    df = pandas_gbq.read_gbq(query, project_id=project_id)
    print(f"  → {len(df)} rows loaded")
    return df


def load_raw_prices(tickers: list[str]) -> pd.DataFrame:
    """Load raw daily close prices for the web asset universe."""
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    dataset_id = os.getenv("BIGQUERY_DATASET")
    tickers_sql = ", ".join(sql_string(t) for t in tickers)
    query = f"""
        SELECT date, ticker, close
        FROM `{dataset_id}.raw_prices`
        WHERE ticker IN ({tickers_sql})
        ORDER BY ticker, date
    """
    print(f"Querying {project_id}.{dataset_id}.raw_prices ...")
    df = pandas_gbq.read_gbq(query, project_id=project_id)
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df = df.dropna(subset=["date", "ticker", "close"])
    print(f"  → {len(df)} price rows loaded")
    return df


def build_js_line(ticker: str, row: pd.Series, pool: dict) -> str:
    """Format one asset entry as a JS object literal (single line)."""
    category = pool["category"]
    aum_note = AUM_OVERRIDES.get(ticker, pool["aum_note"])
    currency  = "TWD" if category == "TW_ETF" else "USD"

    cagr      = round(float(row["cagr"])         * 100, 1)
    vol       = round(float(row["volatility"])   * 100, 1)
    max_dd    = round(float(row["max_drawdown"]) * 100, 1)
    sharpe    = round(float(row["sharpe_ratio"]),       2)
    worst_yr  = round(float(row["worst_year"])   * 100, 1)
    worst_lbl = int(row["worst_year_label"])

    parts = [
        f"ticker:{js_string(ticker)}",
        f"name:{js_string(pool['name'])}",
    ]
    if ticker in ZH_NAMES:
        parts.append(f"nameZh:{js_string(ZH_NAMES[ticker])}")
    parts += [
        f"category:{js_string(category)}",
        f"subcategory:{js_string(pool['subcategory'])}",
        f"currency:{js_string(currency)}",
        f"aumNote:{js_string(aum_note)}",
        f"cagr:{cagr}",
        f"vol:{vol}",
        f"maxDD:{max_dd}",
        f"sharpe:{sharpe}",
        f"worstYear:{worst_yr}",
        f"worstYearLabel:{worst_lbl}",
    ]
    return "  { " + ", ".join(parts) + " },"


def build_assets_block(metrics_df: pd.DataFrame, updated_at: str) -> str:
    """Build the full PPL_ASSETS replacement block."""
    tw     = [a for a in ASSET_POOL if a["category"] == "TW_ETF"]
    us     = [a for a in ASSET_POOL if a["category"] == "US_ETF"]
    crypto = [a for a in ASSET_POOL if a["category"] == "CRYPTO"]

    total   = len(ASSET_POOL)
    skipped = 0
    lines   = []
    lines.append(f"// ── Asset Universe ({total} assets — matches screening.py ASSET_POOL) ──────────────")
    lines.append(f"// Last updated: {updated_at}")
    lines.append("const PPL_ASSETS = [")

    for label, group in [("Taiwan ETFs", tw), ("US ETFs", us), ("Crypto", crypto)]:
        lines.append(f"  // {label}")
        for pool in group:
            ticker = pool["ticker"]
            row    = metrics_df[metrics_df["ticker"] == ticker]
            if row.empty:
                fallback = METRIC_FALLBACKS.get(ticker)
                if not fallback:
                    print(f"  ⚠️  {ticker}: not found in asset_metrics — skipped")
                    skipped += 1
                    continue
                print(f"  ⚠️  {ticker}: not found in asset_metrics — using fallback metrics")
                row_data = pd.Series(fallback)
            else:
                row_data = row.iloc[0]
            lines.append(build_js_line(ticker, row_data, pool))

    lines.append("];")
    if skipped:
        print(f"\n  ⚠️  {skipped} asset(s) skipped (missing from BigQuery). "
              "Run fetch_prices.py + metrics.py to backfill them.")
    return "\n".join(lines)


def build_price_history_block(prices_df: pd.DataFrame, updated_at: str) -> str:
    """Build daily TWD price history for true static-web backtests."""
    if prices_df.empty:
        raise ValueError("raw_prices is empty; cannot build PPL_PRICE_HISTORY")

    pool_by_ticker = {a["ticker"]: a for a in ASSET_POOL}
    start_date = prices_df["date"].min().strftime("%Y-%m-%d")
    end_date = prices_df["date"].max().strftime("%Y-%m-%d")
    fx = load_fx_rate(start_date, end_date).sort_index()
    latest_fx = float(fx.iloc[-1])

    history: dict[str, list[list[object]]] = {}
    missing = []

    for ticker in [a["ticker"] for a in ASSET_POOL]:
        t_df = prices_df[prices_df["ticker"] == ticker].sort_values("date")
        if t_df.empty:
            missing.append(ticker)
            continue

        category = pool_by_ticker[ticker]["category"]
        converted = t_df[["date", "close"]].copy()
        if category != "TW_ETF":
            fx_aligned = fx.reindex(converted["date"]).ffill().bfill()
            converted["close"] = converted["close"].to_numpy(dtype=float) * fx_aligned.to_numpy(dtype=float)

        converted["date"] = converted["date"].dt.strftime("%Y-%m-%d")
        converted["close"] = converted["close"].astype(float).round(4)
        history[ticker] = converted[["date", "close"]].values.tolist()

    if missing:
        print(f"  ⚠️  {len(missing)} ticker(s) missing from raw_prices: {', '.join(missing)}")

    encoded_history = json.dumps(history, ensure_ascii=False, separators=(",", ":"))
    lines = [
        "// ── Daily Price History in TWD (from BigQuery raw_prices) ────────────────",
        f"// Last updated: {updated_at}",
        f"const PPL_HISTORY_UPDATED_AT = {js_string(updated_at)};",
        f"const PPL_FX_RATE = {round(latest_fx, 4)};",
        f"const PPL_PRICE_HISTORY = {encoded_history};",
    ]
    return "\n".join(lines)


def replace_assets_block(original: str, new_block: str) -> str:
    """
    Replace the PPL_ASSETS section in the existing ppl-data.js.
    Keeps the header (PPL_BLUE6 etc.) and everything after PPL_ASSETS (personas, functions).
    """
    # Match from the Asset Universe comment to the closing ]; of PPL_ASSETS
    pattern = re.compile(
        r"// ── Asset Universe.*?^const PPL_ASSETS = \[.*?^\];",
        re.DOTALL | re.MULTILINE,
    )
    if not pattern.search(original):
        raise RuntimeError(
            "Could not locate the PPL_ASSETS block in ppl-data.js. "
            "Make sure the file contains '// ── Asset Universe' and 'const PPL_ASSETS = ['."
        )
    return pattern.sub(new_block, original)


def replace_price_history_block(original: str, new_block: str) -> str:
    pattern = re.compile(
        r"// ── Daily Price History.*?^const PPL_PRICE_HISTORY = .*?;",
        re.DOTALL | re.MULTILINE,
    )
    if pattern.search(original):
        return pattern.sub(new_block, original)

    marker = "// ── Persona Presets"
    if marker not in original:
        raise RuntimeError("Could not locate insertion point for PPL_PRICE_HISTORY.")
    return original.replace(marker, new_block + "\n\n" + marker, 1)


def main():
    print("=== export_web_data.py ===")

    metrics_df = load_metrics()
    prices_df = load_raw_prices([a["ticker"] for a in ASSET_POOL])
    updated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    new_block = build_assets_block(metrics_df, updated_at)
    history_block = build_price_history_block(prices_df, updated_at)

    original = OUTPUT.read_text(encoding="utf-8")
    updated  = replace_assets_block(original, new_block)
    updated  = replace_price_history_block(updated, history_block)

    OUTPUT.write_text(updated, encoding="utf-8")

    tw_count     = sum(1 for a in ASSET_POOL if a["category"] == "TW_ETF")
    us_count     = sum(1 for a in ASSET_POOL if a["category"] == "US_ETF")
    crypto_count = sum(1 for a in ASSET_POOL if a["category"] == "CRYPTO")

    print(f"\n✅ ppl-data.js updated successfully")
    print(f"   Assets: {len(ASSET_POOL)} total "
          f"({tw_count} TW ETF · {us_count} US ETF · {crypto_count} Crypto)")
    print(f"   Updated at: {updated_at}")
    print(f"   Output: {OUTPUT}")


if __name__ == "__main__":
    main()
