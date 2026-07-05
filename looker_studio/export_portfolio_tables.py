#!/usr/bin/env python3
"""
Build Looker Studio portfolio tables for Passive Portfolio Lab.

This script reads existing BigQuery raw_prices and asset_metrics, converts
foreign-currency assets to TWD using historical TWD/USD rates, then uploads
portfolio-level tables for Looker Studio.

Usage:
    python3 looker_studio/export_portfolio_tables.py

Preview CSVs without uploading:
    python3 looker_studio/export_portfolio_tables.py --no-upload
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import pandas_gbq
from dotenv import load_dotenv

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = Path(__file__).resolve().parent / "generated"
sys.path.append(str(REPO_ROOT / "streamlit_dashboard"))

from src.processing.backtest import load_fx_rate  # noqa: E402
from src.processing.drawdown_events import identify_drawdown_events  # noqa: E402
from src.processing.utils import validate_bq_identifier  # noqa: E402


@dataclass(frozen=True)
class Portfolio:
    portfolio_id: str
    name_zh: str
    name_en: str
    portfolio_type: str
    risk_level: str
    initial_investment: float
    monthly_contribution: float
    annual_expenses: float
    withdrawal_rate: float
    inflation_rate: float
    weights: dict[str, float]
    description_zh: str
    description_en: str


PORTFOLIOS: list[Portfolio] = [
    Portfolio(
        portfolio_id="young_professional",
        name_zh="年輕上班族",
        name_en="Young Professional",
        portfolio_type="Persona",
        risk_level="Medium",
        initial_investment=100_000,
        monthly_contribution=10_000,
        annual_expenses=600_000,
        withdrawal_rate=0.04,
        inflation_rate=0.025,
        weights={
            "0050.TW": 0.25,
            "VTI": 0.25,
            "VEA": 0.15,
            "BND": 0.20,
            "GLD": 0.10,
            "BTC-USD": 0.05,
        },
        description_zh="中風險累積型：台股、美股、已開發市場、債券、黃金、比特幣全面配置。",
        description_en="Medium-risk accumulation across Taiwan, US, developed markets, bonds, gold, and Bitcoin.",
    ),
    Portfolio(
        portfolio_id="pre_retirement",
        name_zh="準退休族",
        name_en="Pre-Retirement",
        portfolio_type="Persona",
        risk_level="Low",
        initial_investment=5_000_000,
        monthly_contribution=50_000,
        annual_expenses=1_200_000,
        withdrawal_rate=0.04,
        inflation_rate=0.025,
        weights={
            "0050.TW": 0.20,
            "00878.TW": 0.20,
            "VEA": 0.15,
            "BND": 0.25,
            "GLD": 0.15,
            "VTI": 0.05,
        },
        description_zh="低風險退休衝刺型：多元股票、債券與黃金，降低波動保護本金。",
        description_en="Lower-risk retirement sprint with diversified equity, bond, and gold exposure.",
    ),
    Portfolio(
        portfolio_id="aggressive_growth",
        name_zh="積極成長型",
        name_en="Aggressive Growth",
        portfolio_type="Persona",
        risk_level="High",
        initial_investment=800_000,
        monthly_contribution=30_000,
        annual_expenses=800_000,
        withdrawal_rate=0.04,
        inflation_rate=0.025,
        weights={
            "VTI": 0.35,
            "QQQ": 0.20,
            "0050.TW": 0.15,
            "VEA": 0.10,
            "BTC-USD": 0.15,
            "GLD": 0.05,
        },
        description_zh="高風險積極成長型：VTI、QQQ、台股、已開發市場、比特幣與黃金組合。",
        description_en="High-risk growth portfolio with broad US equity, QQQ, Taiwan equity, Bitcoin, and gold.",
    ),
    Portfolio(
        portfolio_id="taiwan_core",
        name_zh="台股核心",
        name_en="Taiwan Core",
        portfolio_type="Core",
        risk_level="Medium",
        initial_investment=300_000,
        monthly_contribution=15_000,
        annual_expenses=800_000,
        withdrawal_rate=0.04,
        inflation_rate=0.025,
        weights={
            "0050.TW": 0.25 / 0.90,
            "0056.TW": 0.20 / 0.90,
            "00679B.TWO": 0.15 / 0.90,
            "0052.TW": 0.15 / 0.90,
            "00646.TW": 0.15 / 0.90,
        },
        description_zh="台幣可交易核心配置：台股大型、高股息、科技、美股與長天期美債。",
        description_en="Taiwan-listed core allocation across Taiwan large cap, dividends, technology, S&P 500, and long Treasuries.",
    ),
    Portfolio(
        portfolio_id="us_core",
        name_zh="美股核心",
        name_en="US Core",
        portfolio_type="Core",
        risk_level="Medium",
        initial_investment=300_000,
        monthly_contribution=15_000,
        annual_expenses=800_000,
        withdrawal_rate=0.04,
        inflation_rate=0.025,
        weights={
            "VOO": 0.30,
            "QQQ": 0.20,
            "VEA": 0.15,
            "VTV": 0.15,
            "GLD": 0.10,
            "BND": 0.10,
        },
        description_zh="美股核心配置：標普 500、科技成長、價值股、已開發市場、黃金與債券。",
        description_en="US-oriented core allocation across S&P 500, Nasdaq growth, value, developed markets, gold, and bonds.",
    ),
    Portfolio(
        portfolio_id="crypto_core",
        name_zh="加密貨幣核心",
        name_en="Crypto Core",
        portfolio_type="Core",
        risk_level="Extreme High",
        initial_investment=300_000,
        monthly_contribution=15_000,
        annual_expenses=800_000,
        withdrawal_rate=0.04,
        inflation_rate=0.025,
        weights={
            "BTC-USD": 0.45,
            "ETH-USD": 0.25,
            "BNB-USD": 0.10,
            "XRP-USD": 0.08,
            "SOL-USD": 0.08,
            "TRX-USD": 0.04,
        },
        description_zh="加密貨幣大型市值核心配置：以比特幣與以太坊為主，搭配主要公鏈與支付代幣。",
        description_en="Large-cap crypto allocation led by Bitcoin and Ethereum, with major chain and payment tokens.",
    ),
]


def env() -> tuple[str, str]:
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    dataset_id = os.getenv("BIGQUERY_DATASET")
    if not project_id or not dataset_id:
        raise SystemExit("Missing GOOGLE_CLOUD_PROJECT or BIGQUERY_DATASET.")
    return (
        validate_bq_identifier(project_id, "project id"),
        validate_bq_identifier(dataset_id, "dataset id"),
    )


def sql_string(value: str) -> str:
    return "'" + str(value).replace("\\", "\\\\").replace("'", "\\'") + "'"


def load_bigquery_inputs(project_id: str, dataset_id: str, tickers: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    tickers_sql = ", ".join(sql_string(t) for t in tickers)
    # dataset_id is validated by get_bq_config(); tickers come from fixed portfolio presets.
    prices_query = f"SELECT date, ticker, category, close FROM `{dataset_id}.raw_prices` WHERE ticker IN ({tickers_sql}) ORDER BY ticker, date"  # nosec B608
    # dataset_id is validated by get_bq_config(); tickers come from fixed portfolio presets.
    metrics_query = f"SELECT * FROM `{dataset_id}.asset_metrics` WHERE ticker IN ({tickers_sql})"  # nosec B608
    prices = pandas_gbq.read_gbq(prices_query, project_id=project_id)
    metrics = pandas_gbq.read_gbq(metrics_query, project_id=project_id)
    prices["date"] = pd.to_datetime(prices["date"]).dt.normalize()
    prices["close"] = pd.to_numeric(prices["close"], errors="coerce")
    return prices.dropna(subset=["date", "ticker", "close"]), metrics


def convert_prices_to_twd(prices: pd.DataFrame) -> pd.DataFrame:
    start_date = prices["date"].min().strftime("%Y-%m-%d")
    end_date = prices["date"].max().strftime("%Y-%m-%d")
    fx = load_fx_rate(start_date, end_date).sort_index()

    converted = prices.copy()
    converted["close_twd"] = converted["close"].astype(float)
    usd_mask = converted["category"] != "TW_ETF"
    if usd_mask.any():
        fx_aligned = fx.reindex(converted.loc[usd_mask, "date"]).ffill().bfill()
        converted.loc[usd_mask, "close_twd"] = (
            converted.loc[usd_mask, "close"].to_numpy(dtype=float)
            * fx_aligned.to_numpy(dtype=float)
        )

    return converted


def build_allocations(metrics: pd.DataFrame) -> pd.DataFrame:
    rows = []
    metric_cols = [
        "ticker",
        "name",
        "category",
        "cagr",
        "volatility",
        "max_drawdown",
        "sharpe_ratio",
    ]
    metric_map = metrics[[c for c in metric_cols if c in metrics.columns]].drop_duplicates("ticker")

    for portfolio in PORTFOLIOS:
        for ticker, weight in portfolio.weights.items():
            rows.append({
                "portfolio_id": portfolio.portfolio_id,
                "portfolio_name_zh": portfolio.name_zh,
                "portfolio_name_en": portfolio.name_en,
                "portfolio_type": portfolio.portfolio_type,
                "risk_level": portfolio.risk_level,
                "ticker": ticker,
                "weight": weight,
                "weight_pct": weight * 100,
            })

    allocations = pd.DataFrame(rows)
    return allocations.merge(metric_map, on="ticker", how="left")


def simulate_portfolio_history(prices_twd: pd.DataFrame, portfolio: Portfolio) -> pd.DataFrame:
    tickers = list(portfolio.weights)
    pivot = (
        prices_twd[prices_twd["ticker"].isin(tickers)]
        .pivot_table(index="date", columns="ticker", values="close_twd", aggfunc="last")
        .sort_index()
    )

    pivot = pivot.dropna(subset=tickers)
    if pivot.empty:
        raise ValueError(f"No common price window for {portfolio.portfolio_id}")

    weights = pd.Series(portfolio.weights, dtype=float)
    weights = weights / weights.sum()
    shares = pd.Series(0.0, index=tickers)
    total_invested = 0.0
    first_day = pivot.index[0]
    monthly_dates = set(pivot.groupby(pd.Grouper(freq="MS")).head(1).index)

    records = []
    previous_value: float | None = None
    portfolio_index = 1.0
    for dt, price_row in pivot.iterrows():
        contribution = 0.0
        if dt == first_day:
            contribution = portfolio.initial_investment
        elif dt in monthly_dates:
            contribution = portfolio.monthly_contribution

        if contribution:
            shares += (contribution * weights) / price_row[tickers]
            total_invested += contribution

        value = float((shares * price_row[tickers]).sum())
        if previous_value is None or previous_value == 0:
            daily_return = 0.0
        else:
            # Time-weighted return: neutralize scheduled contributions so
            # return/risk fields measure the portfolio, not cashflow timing.
            daily_return = (value - contribution) / previous_value - 1
        portfolio_index *= 1 + daily_return
        previous_value = value

        records.append({
            "portfolio_id": portfolio.portfolio_id,
            "portfolio_name_zh": portfolio.name_zh,
            "portfolio_name_en": portfolio.name_en,
            "portfolio_type": portfolio.portfolio_type,
            "risk_level": portfolio.risk_level,
            "date": dt,
            "contribution_twd": contribution,
            "portfolio_value_twd": value,
            "total_invested_twd": total_invested,
            "total_return": (value / total_invested - 1) if total_invested else 0.0,
            "total_return_pct": (value / total_invested - 1) * 100 if total_invested else 0.0,
            "daily_return": daily_return,
            "daily_return_pct": daily_return * 100,
            "portfolio_index": portfolio_index,
        })

    history = pd.DataFrame(records)
    history["running_max_twd"] = history["portfolio_value_twd"].cummax()
    history["running_max_index"] = history["portfolio_index"].cummax()
    history["drawdown"] = history["portfolio_index"] / history["running_max_index"] - 1
    history["drawdown_pct"] = history["drawdown"] * 100
    return history


def build_metrics(history: pd.DataFrame, allocations: pd.DataFrame) -> pd.DataFrame:
    rows = []
    grouped_alloc = allocations.groupby("portfolio_id")
    for portfolio in PORTFOLIOS:
        h = history[history["portfolio_id"] == portfolio.portfolio_id].sort_values("date")
        if h.empty:
            continue

        years = max((h["date"].iloc[-1] - h["date"].iloc[0]).days / 365.0, 1 / 365)
        final_value = float(h["portfolio_value_twd"].iloc[-1])
        total_invested = float(h["total_invested_twd"].iloc[-1])
        daily_returns = h["daily_return"].dropna()
        total_growth = float(h["portfolio_index"].iloc[-1] / h["portfolio_index"].iloc[0])
        cagr = total_growth ** (1 / years) - 1 if total_growth > 0 else np.nan
        volatility = float(daily_returns.std() * np.sqrt(252)) if len(daily_returns) else np.nan
        max_drawdown = float(h["drawdown"].min())
        sharpe = (cagr - 0.02) / volatility if volatility and volatility > 0 else np.nan

        annual = (
            h.assign(year=h["date"].dt.year)
            .groupby("year")["daily_return"]
            .apply(lambda s: (1 + s).prod() - 1)
        )
        worst_year_label = int(annual.idxmin()) if not annual.empty else None
        worst_year = float(annual.min()) if not annual.empty else np.nan

        asset_count = len(portfolio.weights)
        top_holding = max(portfolio.weights, key=portfolio.weights.get)
        top_weight = portfolio.weights[top_holding]
        category_mix = (
            grouped_alloc.get_group(portfolio.portfolio_id)
            .groupby("category")["weight"]
            .sum()
            .to_dict()
        )

        rows.append({
            "portfolio_id": portfolio.portfolio_id,
            "portfolio_name_zh": portfolio.name_zh,
            "portfolio_name_en": portfolio.name_en,
            "portfolio_type": portfolio.portfolio_type,
            "risk_level": portfolio.risk_level,
            "description_zh": portfolio.description_zh,
            "description_en": portfolio.description_en,
            "data_start": h["date"].iloc[0],
            "data_end": h["date"].iloc[-1],
            "asset_count": asset_count,
            "top_holding": top_holding,
            "top_weight": top_weight,
            "top_weight_pct": top_weight * 100,
            "tw_etf_weight": category_mix.get("TW_ETF", 0.0),
            "us_etf_weight": category_mix.get("US_ETF", 0.0),
            "crypto_weight": category_mix.get("CRYPTO", 0.0),
            "initial_investment_twd": portfolio.initial_investment,
            "monthly_contribution_twd": portfolio.monthly_contribution,
            "annual_expenses_twd": portfolio.annual_expenses,
            "withdrawal_rate": portfolio.withdrawal_rate,
            "inflation_rate": portfolio.inflation_rate,
            "fire_target_twd": portfolio.annual_expenses / portfolio.withdrawal_rate,
            "final_value_twd": final_value,
            "total_invested_twd": total_invested,
            "total_return": float(h["total_return"].iloc[-1]),
            "total_return_pct": float(h["total_return_pct"].iloc[-1]),
            "cagr": cagr,
            "cagr_pct": cagr * 100,
            "volatility": volatility,
            "volatility_pct": volatility * 100 if pd.notna(volatility) else np.nan,
            "max_drawdown": max_drawdown,
            "max_drawdown_pct": max_drawdown * 100,
            "sharpe_ratio": sharpe,
            "worst_year": worst_year,
            "worst_year_pct": worst_year * 100 if pd.notna(worst_year) else np.nan,
            "worst_year_label": worst_year_label,
        })
    return pd.DataFrame(rows)


def build_annual_returns(history: pd.DataFrame) -> pd.DataFrame:
    annual = (
        history.assign(year=history["date"].dt.year)
        .groupby(["portfolio_id", "portfolio_name_zh", "portfolio_name_en", "year"], as_index=False)
        .agg(
            first_value_twd=("portfolio_value_twd", "first"),
            last_value_twd=("portfolio_value_twd", "last"),
            total_contribution_twd=("contribution_twd", "sum"),
            account_growth_return=("portfolio_value_twd", lambda s: s.iloc[-1] / s.iloc[0] - 1),
            annual_return=("daily_return", lambda s: (1 + s).prod() - 1),
        )
    )
    annual["annual_return_pct"] = annual["annual_return"] * 100
    annual["account_growth_return_pct"] = annual["account_growth_return"] * 100
    return annual


def build_drawdown_events(history: pd.DataFrame) -> pd.DataFrame:
    frames = []
    for portfolio in PORTFOLIOS:
        h = history[history["portfolio_id"] == portfolio.portfolio_id].sort_values("date")
        if h.empty:
            continue
        events = identify_drawdown_events(
            h["date"],
            h["portfolio_index"],
            top_n=5,
            min_depth_pct=0.02,
        )
        if events.empty:
            continue
        events.insert(0, "portfolio_name_en", portfolio.name_en)
        events.insert(0, "portfolio_name_zh", portfolio.name_zh)
        events.insert(0, "portfolio_id", portfolio.portfolio_id)
        frames.append(events)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def build_fire_tables(metrics: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    scenario_rows = []
    projection_rows = []
    metric_map = metrics.set_index("portfolio_id").to_dict("index")

    for portfolio in PORTFOLIOS:
        m = metric_map.get(portfolio.portfolio_id)
        if not m:
            continue

        annual_return = float(m["cagr"])
        monthly_rate = (1 + annual_return) ** (1 / 12) - 1
        target = portfolio.annual_expenses / portfolio.withdrawal_rate
        value = float(portfolio.initial_investment)
        years_nominal = None
        years_real = None

        for month in range(1, 50 * 12 + 1):
            value = value * (1 + monthly_rate) + portfolio.monthly_contribution
            if month % 12 != 0:
                continue

            year = month // 12
            real_value = value / ((1 + portfolio.inflation_rate) ** year)
            projection_rows.append({
                "portfolio_id": portfolio.portfolio_id,
                "portfolio_name_zh": portfolio.name_zh,
                "portfolio_name_en": portfolio.name_en,
                "year": year,
                "nominal_value_twd": value,
                "real_value_twd": real_value,
                "fire_target_twd": target,
            })
            if years_nominal is None and value >= target:
                years_nominal = year
            if years_real is None and real_value >= target:
                years_real = year

        scenario_rows.append({
            "portfolio_id": portfolio.portfolio_id,
            "portfolio_name_zh": portfolio.name_zh,
            "portfolio_name_en": portfolio.name_en,
            "portfolio_type": portfolio.portfolio_type,
            "risk_level": portfolio.risk_level,
            "annual_expenses_twd": portfolio.annual_expenses,
            "withdrawal_rate": portfolio.withdrawal_rate,
            "withdrawal_rate_pct": portfolio.withdrawal_rate * 100,
            "inflation_rate": portfolio.inflation_rate,
            "inflation_rate_pct": portfolio.inflation_rate * 100,
            "initial_investment_twd": portfolio.initial_investment,
            "monthly_contribution_twd": portfolio.monthly_contribution,
            "expected_return": annual_return,
            "expected_return_pct": annual_return * 100,
            "fire_target_twd": target,
            "years_to_fire_nominal": years_nominal,
            "years_to_fire_real": years_real,
        })

    return pd.DataFrame(scenario_rows), pd.DataFrame(projection_rows)


def write_outputs(tables: dict[str, pd.DataFrame], upload: bool, project_id: str, dataset_id: str) -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    for name, df in tables.items():
        csv_path = OUTPUT_DIR / f"{name}.csv"
        df.to_csv(csv_path, index=False)
        print(f"Wrote {len(df):,} rows -> {csv_path}")
        if upload:
            destination = f"{dataset_id}.{name}"
            pandas_gbq.to_gbq(df, destination_table=destination, project_id=project_id, if_exists="replace")
            print(f"Uploaded -> {project_id}.{destination}")


def build_tables(project_id: str, dataset_id: str) -> dict[str, pd.DataFrame]:
    tickers = sorted({ticker for p in PORTFOLIOS for ticker in p.weights})
    prices, metrics_input = load_bigquery_inputs(project_id, dataset_id, tickers)
    missing = sorted(set(tickers) - set(prices["ticker"]))
    if missing:
        raise RuntimeError(f"Missing raw_prices for ticker(s): {', '.join(missing)}")

    prices_twd = convert_prices_to_twd(prices)
    allocations = build_allocations(metrics_input)
    history = pd.concat(
        [simulate_portfolio_history(prices_twd, portfolio) for portfolio in PORTFOLIOS],
        ignore_index=True,
    )
    metrics = build_metrics(history, allocations)
    annual_returns = build_annual_returns(history)
    drawdown_events = build_drawdown_events(history)
    fire_scenarios, fire_projection = build_fire_tables(metrics)

    return {
        "looker_portfolio_allocations": allocations,
        "looker_portfolio_history": history,
        "looker_portfolio_metrics": metrics,
        "looker_portfolio_annual_returns": annual_returns,
        "looker_portfolio_drawdown_events": drawdown_events,
        "looker_fire_scenarios": fire_scenarios,
        "looker_fire_projection": fire_projection,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-upload", action="store_true", help="Write CSV previews only; do not upload to BigQuery.")
    args = parser.parse_args()

    project_id, dataset_id = env()
    tables = build_tables(project_id, dataset_id)
    write_outputs(tables, upload=not args.no_upload, project_id=project_id, dataset_id=dataset_id)


if __name__ == "__main__":
    main()
