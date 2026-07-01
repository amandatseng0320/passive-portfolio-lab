import sys
import os
import json
import tempfile
sys.path.append(os.path.dirname(__file__))

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import pandas_gbq
import plotly.graph_objects as go
import plotly.express as px
import requests
from datetime import date
from collections import defaultdict
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode
from dotenv import load_dotenv
from src.processing.screening import get_all_candidates
from src.processing.backtest import run_backtest, load_prices_for_tickers
from src.processing.fire_calculator import calculate_fire
from src.processing.drawdown_events import identify_drawdown_events, MARKET_EVENTS
from src.asset_profiles.loader import get_asset_profile
from src.data_collection.fetch_macro import get_latest_cpi_yoy
from src.processing.utils import YAHOO_HEADERS, RISK_FREE_RATE, get_bq_config
from google import genai
import warnings

# Suppress annoying warnings from libraries
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.simplefilter(action='ignore', category=DeprecationWarning)


load_dotenv()
# The new google-genai SDK uses a Client object for configuration.
# Top-level configuration is no longer needed.

# ── Streamlit Cloud setup: materialize GCP credentials from st.secrets ──────
# Locally, auth goes through .env + credentials.json (GOOGLE_APPLICATION_CREDENTIALS).
# On Streamlit Cloud, credentials.json doesn't exist — so if st.secrets has the
# service-account table, dump it to a temp JSON file and point the env var there,
# so every existing pandas_gbq call keeps working with no further changes.
_app_password = None
try:
    if "gcp_service_account" in st.secrets:
        _creds_path = os.path.join(tempfile.gettempdir(), "gcp_credentials.json")
        with open(_creds_path, "w") as _f:
            json.dump(dict(st.secrets["gcp_service_account"]), _f)
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = _creds_path
    # Top-level TOML keys are auto-injected as env vars on Streamlit Cloud,
    # so os.getenv("GOOGLE_CLOUD_PROJECT") etc. still work. We only need to
    # read APP_PASSWORD explicitly for the password gate below.
    _app_password = st.secrets.get("APP_PASSWORD")
except FileNotFoundError:
    # Local dev: no secrets.toml; production secrets live in Streamlit Cloud.
    pass
except Exception as exc:
    print(f"Warning: Streamlit secrets could not be initialized: {exc}")

st.set_page_config(page_title="Passive Portfolio Lab", page_icon="🚀", layout="wide", initial_sidebar_state="expanded")

# ── Language / i18n ───────────────────────────────────────────────────────────
if 'lang' not in st.session_state:
    st.session_state['lang'] = st.query_params.get("lang", "zh-TW")

LANG_OPTIONS = {
    "English": "en",
    "繁體中文": "zh-TW",
}

ZH_TW = {
    "This dashboard is currently shared for project review. Please enter the access password.": "此儀表板目前供專案審閱使用，請輸入存取密碼。",
    "Password": "密碼",  # nosec B105
    "Incorrect password.": "密碼不正確。",
    "Introduction": "介紹",
    "Asset Screening": "資產篩選",
    "Correlation Analysis": "相關性分析",
    "Risk Allocation": "風險配置",
    "Backtest & Pain Index": "回測與痛苦指數",
    "FIRE Calculator": "財務自由試算",
    "Summary": "總結",
    "A data-driven toolkit for long-term passive investors": "為長期被動投資者打造的資料化工具箱",
    "Passive Portfolio Lab": "被動投資組合實驗室",
    "Filter and sort assets from the pool below. Click ＋ to add an asset to your watchlist.": "從下方資產池篩選與排序。點選 ＋ 將資產加入你的觀察清單。",
    "📋 How assets are selected": "📋 資產如何被選入",
    "Fetching current prices and volume...": "正在取得最新價格與成交量...",
    "Asset Pool": "資產池",
    "Search": "搜尋",
    "Search assets...": "搜尋資產...",
    "Category": "類別",
    "All": "全部",
    "Crypto": "加密貨幣",
    "Max DD": "最大回撤",
    "CAGR ≥": "CAGR ≥",
    "Sharpe ≥": "Sharpe ≥",
    "Select All": "全選",
    "Clear": "清除",
    "Review Portfolio →": "檢視投資組合 →",
    "Preset applied": "已套用預設",
    "Diagnostic only": "僅供參考",
    "Review overlaps": "檢視重疊",
    "Suggested Removals Action: keep only ONE asset from each group.": "建議移除操作：每個群組只保留 1 個資產。",
    "Recommendation": "建議保留",
    "Reason": "原因",
    "highest AUM / liquidity in this correlated group.": "在此高相關群組中 AUM / 流動性最高。",
    "Select ONE asset to keep": "選擇要保留的 1 個資產",
    "Keep Selected Assets": "保留所選資產",
    "Portfolio updated. Correlation analysis has been refreshed.": "投資組合已更新，相關性分析已重新整理。",
    "Not sure where to start?": "不知道從哪裡開始？",
    "Try a preset investor persona:": "試試預設投資人情境：",
    "Select a persona...": "選擇投資人情境...",
    "Choose a Persona": "選擇投資人情境",
    "🐣 Young Professional": "🐣 年輕上班族",
    "🕊️ Pre-Retirement": "🕊️ 準退休族",
    "🚀 Aggressive Growth": "🚀 積極成長型",
    "Confirm your portfolio is genuinely diversified before running risk and FIRE calculations.": "在進行風險與財務自由試算前，先確認你的投資組合真的足夠分散。",
    "The preset has been applied. Assets are auto-confirmed for the calculations below.": "已套用預設情境，系統已自動確認資產並進入下方計算。",
    "Based on your watchlist, the system automatically allocates weights to match your target risk level.": "系統會根據你的觀察清單，自動配置權重以符合目標風險等級。",
    "Add assets to your watchlist in Asset Screening first.": "請先在資產篩選中加入資產到觀察清單。",
    "Confirm your portfolio in **Correlation Analysis** above to unlock this section.": "請先在上方的 **相關性分析** 確認投資組合，才能解鎖此區塊。",
    "No metric data found for your selected assets.": "找不到你所選資產的指標資料。",
    "How is the achievable risk range determined?": "可達成風險範圍如何判定？",
    "Target Risk Level": "目標風險等級",
    "Weighted CAGR": "加權 CAGR",
    "Portfolio Volatility": "投資組合波動率",
    "Weighted Max Drawdown": "加權最大回撤",
    "Weighted Sharpe": "加權 Sharpe",
    "Portfolio Composition": "投資組合組成",
    "Complete the Risk Allocation section first.": "請先完成風險配置區塊。",
    "How would your portfolio have performed historically — and could you have endured the downturns?": "你的投資組合在歷史上表現如何？而你是否撐得過下跌？",
    "Advanced Settings": "進階設定",
    "Initial Investment (NT$)": "初始投資金額 (NT$)",
    "Monthly Contribution (NT$)": "每月投入 (NT$)",
    "Start Date": "開始日期",
    "End Date": "結束日期",
    "Running backtest...": "正在執行回測...",
    "Final Value": "最終資產",
    "Total Invested": "總投入",
    "Total Return": "總報酬",
    "Portfolio Value Over Time": "投資組合價值走勢",
    "Portfolio Value": "投資組合價值",
    "Max Drawdown Over Time (Pain Index)": "最大回撤走勢（痛苦指數）",
    "Drawdown": "回撤",
    "Drawdown (%)": "回撤 (%)",
    "View Top 5 Drawdown Episodes": "查看前 5 大回撤區間",
    "Ongoing": "尚未恢復",
    "Annual Returns": "年度報酬",
    "Return (%)": "報酬率 (%)",
    "Ticker": "代號",
    "Name": "名稱",
    "Price": "價格",
    "Volume": "成交量",
    "Ann. Return": "年化報酬",
    "Volatility": "波動率",
    "Max Drawdown": "最大回撤",
    "Worst Year Ret.": "最差年度報酬",
    "Worst Year": "最差年度",
    "Rank": "排名",
    "Peak": "高點",
    "Trough": "低點",
    "Recovery": "恢復",
    "Fall Time": "下跌時間",
    "Recovery Time": "恢復時間",
    "Historical Context": "歷史背景",
    "Based on your allocation's historical CAGR, estimate when you can reach financial independence.": "根據配置的歷史 CAGR，估算你何時能達成財務自由。",
    "Using backtest CAGR:": "使用回測 CAGR：",
    "Using portfolio weighted CAGR:": "使用投資組合加權 CAGR：",
    "Adjust the parameters below. Risk Level is carried over from your Risk Allocation.": "調整下方參數。風險等級會沿用風險配置區塊的設定。",
    "Annual Expenses (NT$)": "年度支出 (NT$)",
    "Withdrawal Rate (%)": "提領率 (%)",
    "Implied FIRE Target": "推算 FIRE 目標",
    "= Expenses ÷ Withdrawal Rate": "= 支出 ÷ 提領率",
    "Current Savings (NT$)": "目前存款 (NT$)",
    "Annual Inflation Rate (%)": "年通膨率 (%)",
    "Risk Level": "風險等級",
    "Currency": "幣別",
    "All calculations in New Taiwan Dollar": "所有計算皆以新台幣進行",
    "About the 4% Rule (Trinity Study)": "關於 4% 法則（Trinity Study）",
    "Calculating FIRE projection...": "正在計算 FIRE 預測...",
    "CAGR Used": "採用 CAGR",
    "Years to FIRE (Nominal)": "距離 FIRE 年數（名目）",
    "Years to FIRE (Real)": "距離 FIRE 年數（實質）",
    "Inflation Applied": "套用通膨率",
    "Nominal Value": "名目價值",
    "Real Value (Inflation-Adjusted)": "實質價值（通膨調整後）",
    "Years": "年數",
    "A snapshot of your portfolio based on the selections above.": "根據上方選擇產生的投資組合快照。",
    "Complete the Risk Allocation section to see your portfolio summary.": "完成風險配置後即可查看投資組合總結。",
    "AI Insights": "AI 洞察",
    "Strategic review generated by Gemini 2.5 Flash": "由 Gemini 2.5 Flash 產生的策略檢視",
    "Generating AI insights...": "正在產生 AI 洞察...",
    "AI Insights will be available once the backtest calculation is complete.": "完成回測計算後即可查看 AI 洞察。",
    "Switch to USD": "切換為 USD",
    "Switch to TWD": "切換為 TWD",
    "Currently displaying in TWD. Input fields remain in TWD regardless of display currency.": "目前以 TWD 顯示。無論顯示幣別為何，輸入欄位皆維持 TWD。",
    "Low": "低",
    "Medium": "中",
    "High": "高",
    "Extreme High": "極高",
}

def tr(text: str, zh_tw: str = None) -> str:
    if st.session_state.get('lang') == "zh-TW":
        return zh_tw or ZH_TW.get(text, text)
    return text

def risk_label(value: str) -> str:
    return tr(value)

def fmt_years(value) -> str:
    if st.session_state.get('lang') == "zh-TW":
        return f"{value} 年" if value is not None else "50+ 年"
    return f"{value} yrs" if value is not None else "50+ yrs"

COST_SCENARIO_RATES: tuple[float, float] = (0.005, 0.01)

def cost_adjusted_cagr(cagr: float, annual_cost: float) -> float:
    """Return a conservative reference CAGR after a generic annual cost scenario."""
    return max(cagr - annual_cost, -0.99)

def estimate_fire_years_for_cagr(
    cagr: float,
    current_savings: float,
    monthly_contribution: float,
    target_amount: float,
    inflation_rate: float,
    max_years: int = 50,
) -> tuple[int | None, int | None]:
    """Estimate nominal and inflation-adjusted FIRE years for a supplied CAGR."""
    if target_amount <= 0:
        return None, None

    monthly_rate = (1 + cagr) ** (1 / 12) - 1
    value = float(current_savings)
    nominal_year = None
    real_year = None

    for month in range(1, max_years * 12 + 1):
        value = value * (1 + monthly_rate) + monthly_contribution
        if month % 12 == 0:
            year = month // 12
            real_value = value / ((1 + inflation_rate) ** year)
            if nominal_year is None and value >= target_amount:
                nominal_year = year
            if real_year is None and real_value >= target_amount:
                real_year = year
            if nominal_year is not None and real_year is not None:
                break

    return nominal_year, real_year

def format_cost_cagr_reference(cagr: float) -> str:
    parts = [
        f"{rate * 100:.1f}% → {cost_adjusted_cagr(cagr, rate):.2%}"
        for rate in COST_SCENARIO_RATES
    ]
    return " / ".join(parts)

def cost_scope_note() -> str:
    return tr(
        "Note: Backtests use adjusted close prices and historical TWD/USD exchange rates. "
        "They do not model individual trading costs, taxes, brokerage fees, FX spreads, "
        "or other personal account-level costs.",
        "備註：回測使用調整後收盤價與歷史 TWD/USD 匯率計算，未逐筆模擬個人交易、稅務、券商手續費、換匯價差或其他帳戶層級成本。",
    )

# ── Portfolio risk constants ───────────────────────────────────────────────────
# Maps risk tier names to a sort order and to the allocation optimizer's target
# annual volatility. Adjust RISK_VOL_TARGET if the acceptable risk bounds change.
RISK_ORDER: dict[str, int] = {"Low": 1, "Medium": 2, "High": 3, "Extreme High": 4}
RISK_VOL_TARGET: dict[str, float] = {
    "Low": 0.12,
    "Medium": 0.20,
    "High": 0.35,
    "Extreme High": 0.65,
}
def vol_to_risk_label(v: float) -> str:
    """Map an annualized volatility to the nearest risk tier label."""
    if v < 0.16:
        return "Low"
    elif v < 0.27:
        return "Medium"
    elif v < 0.50:
        return "High"
    return "Extreme High"


_ALLOC_MAX_ITER  = 200
_ALLOC_TOLERANCE = 0.001
_ALLOC_NUDGE     = 0.05


def compute_allocation(df: pd.DataFrame, target_vol: float) -> pd.DataFrame:
    """
    Return *df* with a ``weight`` column fitted to *target_vol*.

    Uses inverse-volatility weights as a starting point, then iteratively
    nudges weights toward the target portfolio volatility (_ALLOC_MAX_ITER max).
    Weights are clamped to ≥ 0.01 and renormalized each step.
    """
    df = df.copy()
    vols = df['volatility'].values.astype(float)

    # Step 1: inverse volatility weights as starting point
    inv_vol = 1.0 / np.where(vols == 0, 0.001, vols)
    weights = inv_vol / inv_vol.sum()

    # Step 2: iteratively nudge weights toward target volatility
    for _ in range(_ALLOC_MAX_ITER):
        port_vol = float(np.dot(weights, vols))
        if abs(port_vol - target_vol) < _ALLOC_TOLERANCE:
            break
        if port_vol > target_vol:
            adj = weights * (1 - _ALLOC_NUDGE * (vols / vols.max()))
        else:
            adj = weights * (1 + _ALLOC_NUDGE * (vols / vols.max()))
        weights = np.clip(adj, 0.01, None)
        weights = weights / weights.sum()

    df['weight'] = weights
    df['weight'] = df['weight'] / df['weight'].sum()
    return df


# ── Password gate (activated only when APP_PASSWORD is configured in secrets) ──
if _app_password:
    def _check_password():
        if st.session_state.get("authenticated", False):
            return
        st.markdown("### 🔒 Passive Portfolio Lab")
        st.caption(tr("This dashboard is currently shared for project review. Please enter the access password."))
        pw = st.text_input(tr("Password"), type="password", key="pw_input")
        if pw:
            if pw == _app_password:
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error(tr("Incorrect password."))
        st.stop()
    _check_password()

st.markdown("""
<style>
[data-testid="metric-container"] {
    font-size: 14px !important;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    font-size: 1.4rem !important;
}
iframe[title="st_aggrid.agGrid"] {
    position: relative !important;
    z-index: 0 !important;
}
.st-key-persona_quick_start_container {
    position: relative !important;
    z-index: 1000 !important;
    isolation: isolate !important;
    background: var(--background-color);
}
.st-key-persona_quick_start_container button {
    pointer-events: auto !important;
}
</style>
""", unsafe_allow_html=True)

# ── Sidebar ────────────────────────────────────────────────────────────────────

with st.sidebar:
    current_lang = st.session_state.get("lang", "en")
    selected_lang_label = st.radio(
        "Language / 語言",
        options=list(LANG_OPTIONS.keys()),
        index=list(LANG_OPTIONS.values()).index(current_lang) if current_lang in LANG_OPTIONS.values() else 0,
        horizontal=True,
        key="language_toggle",
    )
    selected_lang = LANG_OPTIONS[selected_lang_label]
    if selected_lang != current_lang:
        st.session_state["lang"] = selected_lang
        st.query_params["lang"] = selected_lang
        st.rerun()

    st.markdown(f"""
<style>
.nav-link {{
    display: block;
    padding: 6px 12px;
    margin: 2px 0;
    color: #555 !important;
    text-decoration: none !important;
    font-size: 14px;
    font-weight: 400;
    border-radius: 6px;
}}
.nav-link:hover {{
    background-color: #f0f2f6;
    color: #111 !important;
}}
</style>
<a class="nav-link" href="#introduction">{tr("Introduction")}</a>
<a class="nav-link" href="#asset-screening">{tr("Asset Screening")}</a>
<a class="nav-link" href="#correlation-analysis">{tr("Correlation Analysis")}</a>
<a class="nav-link" href="#risk-allocation">{tr("Risk Allocation")}</a>
<a class="nav-link" href="#backtest">{tr("Backtest & Pain Index")}</a>
<a class="nav-link" href="#fire-calculator">{tr("FIRE Calculator")}</a>
<a class="nav-link" href="#summary">{tr("Summary")}</a>
""", unsafe_allow_html=True)

# ── Session State ──────────────────────────────────────────────────────────────

if 'watchlist' not in st.session_state:
    st.session_state.watchlist = []
if 'portfolio_confirmed' not in st.session_state:
    st.session_state['portfolio_confirmed'] = False
if 'active_persona' not in st.session_state:
    st.session_state['active_persona'] = None

# ── Load Data ──────────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def load_candidates():
    return get_all_candidates()

@st.cache_data(ttl=3600)
def load_metrics():
    project_id, dataset_id = get_bq_config()
    # dataset_id is validated by get_bq_config() before SQL assembly.
    query = f"SELECT * FROM `{dataset_id}.asset_metrics`"  # nosec B608
    return pandas_gbq.read_gbq(query, project_id=project_id)

def fetch_price_and_volume(tickers: list) -> dict:
    """
    Fetch current price and volume directly from Yahoo Finance REST API.
    More stable than yfinance library which breaks when Yahoo changes their backend.
    """
    result = {}
    for ticker in tickers:
        try:
            url = f'https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=5d'
            r = requests.get(url, headers=YAHOO_HEADERS, timeout=10)
            data = r.json()
            close = data['chart']['result'][0]['indicators']['quote'][0]['close']
            volume = data['chart']['result'][0]['indicators']['quote'][0]['volume']
            close = [x for x in close if x is not None]
            volume = [x for x in volume if x is not None]
            result[ticker] = {
                'price': round(close[-1], 2),
                'volume': int(volume[-1]) if volume else None
            }
        except Exception:
            result[ticker] = {'price': None, 'volume': None}
    return result


@st.cache_data(ttl=86400)
def fetch_inflation_default():
    return get_latest_cpi_yoy()


# ── Correlation check (Phase 2) ────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def load_prices_wide(tickers_tuple: tuple) -> pd.DataFrame:
    """
    Load daily close prices for the given tickers from BigQuery and return as a
    wide DataFrame (index=date, columns=ticker). Cached for 1 hour so repeated
    watchlist edits don't re-query BigQuery.
    """
    if not tickers_tuple:
        return pd.DataFrame()
    df = load_prices_for_tickers(list(tickers_tuple))
    if df.empty:
        return pd.DataFrame()
    pivot = df.pivot(index='date', columns='ticker', values='close').sort_index()
    return pivot


REDUNDANCY_THRESHOLD = 0.90  # ρ ≥ this → suggest removing duplicates


def _avg_pairwise_corr(corr: pd.DataFrame, tickers: list) -> float:
    """Return the mean upper-triangle pairwise correlation for *tickers* in *corr*.

    Returns 0.0 when fewer than 2 tickers are available.
    """
    if len(tickers) < 2:
        return 0.0
    valid = [t for t in tickers if t in corr.index]
    if len(valid) < 2:
        return 0.0
    c_sub = corr.loc[valid, valid]
    mask_ut = np.triu(np.ones_like(c_sub, dtype=bool), k=1)
    pair_vals = c_sub.where(mask_ut).stack().dropna()
    return float(pair_vals.mean()) if not pair_vals.empty else 0.0


def _compute_redundant_groups(corr: pd.DataFrame, pool_df: pd.DataFrame, threshold: float):
    """
    Identify near-duplicate groups using union-find on pairs with ρ ≥ threshold.
    For each group, suggest keeping the asset with the highest trading volume
    (proxy for liquidity / popularity) and removing the rest.
    Returns a list of dicts: {keep, remove, max_corr, group}.
    """
    mask = np.triu(np.ones_like(corr, dtype=bool), k=1)
    pair_vals = corr.where(mask).stack().dropna()
    high_pairs = pair_vals[pair_vals >= threshold].sort_values(ascending=False)
    if high_pairs.empty:
        return []

    parent = {}
    def find(x):
        if x not in parent:
            parent[x] = x
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]
    def union(x, y):
        parent[find(x)] = find(y)
    for (t1, t2), _ in high_pairs.items():
        union(t1, t2)

    members = defaultdict(list)
    for t in set(t for pair in high_pairs.index for t in pair):
        members[find(t)].append(t)

    suggestions = []
    rank_lookup = pool_df.set_index('ticker')['rank'].fillna(999)
    for group in members.values():
        if len(group) < 2:
            continue
        ranks = {t: float(rank_lookup.get(t, 999)) for t in group}
        # Keep the one with the lowest rank number (highest AUM)
        keep = min(ranks, key=ranks.get)
        remove = sorted([t for t in group if t != keep])
        # Max correlation involving the keep asset within the group
        max_corr_in_group = float(max(corr.loc[keep, t] for t in remove))
        group_id = f"sug_{keep}_{'_'.join(remove)}"
        suggestions.append({
            'id': group_id,
            'keep': keep,
            'remove': remove,
            'max_corr': max_corr_in_group,
            'group': sorted(group),
        })
    return suggestions


def render_correlation_analysis(tickers: list, pool_df: pd.DataFrame) -> None:
    if not tickers:
        st.info(tr("Select assets in **Asset Screening** above and click **Review Portfolio →**.",
                   "請先在上方 **資產篩選** 選擇資產，並點選 **檢視投資組合 →**。"))
        return

    # ── Load price data (session_state cache) ─────────────────────────────
    tickers_key = tuple(sorted(tickers))
    cached_ok = (st.session_state.get('corr_tickers') == tickers_key and
                 'corr_data' in st.session_state)
    if not cached_ok:
        with st.spinner(tr(f"Loading 3-year price data for {len(tickers)} assets...",
                           f"正在載入 {len(tickers)} 個資產的 3 年價格資料...")):
            try:
                prices = load_prices_wide(tickers_key)
                st.session_state['corr_data'] = prices
                st.session_state['corr_tickers'] = tickers_key
            except Exception as e:
                st.error(tr(f"Failed to load correlation data: {e}", f"相關性資料載入失敗：{e}"))
                return

    prices = st.session_state['corr_data']
    if prices.empty or prices.shape[1] < 2:
        st.warning(tr("Not enough price data available in BigQuery to compute correlations.",
                      "BigQuery 中可用價格資料不足，無法計算相關性。"))
        return

    # ── Pairwise correlation on last 3 years ──────────────────────────────
    end_ts = prices.index.max()
    start_ts = end_ts - pd.DateOffset(years=3)
    window = prices.loc[prices.index >= start_ts].copy()
    returns = window.pct_change(fill_method=None)
    corr = returns.corr(min_periods=60)

    if corr.isna().all().all():
        st.warning(tr("Not enough overlapping history to compute correlations. "
                      "Consider removing very newly-listed assets.",
                      "重疊歷史資料不足，無法計算相關性。可考慮移除非常新上市的資產。"))
        return

    # Redundancy detection
    suggestions = _compute_redundant_groups(corr, pool_df, REDUNDANCY_THRESHOLD)
    active_persona = st.session_state.get('active_persona')
    persona_mode = active_persona in PERSONAS
    
    rm_set = set()
    final_tickers = list(tickers)

    avg_corr_before = _avg_pairwise_corr(corr, tickers)
    # Compute "after" by simulating accepting all suggested removals, so the
    # metric is meaningful before the user actually clicks "Keep Selected Assets".
    suggested_removes = {t for s in suggestions for t in s['group'] if t != s['keep']}
    avg_corr_after = _avg_pairwise_corr(corr, [t for t in tickers if t not in suggested_removes])

    # ── UI: Insight Strip ──────────────────────────────────────────────────
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.container(border=True).metric(
            tr("Selected Assets", "已選資產"),
            f"{len(tickers)}", 
            delta=tr("Preset applied") if persona_mode else (tr("Review overlaps") if suggestions else tr("No reductions", "無需刪減")),
            delta_color="normal" if len(final_tickers) == len(tickers) else "inverse"
        )
    with col2:
        issues_count = len(suggestions)
        removable_count = sum(len(s['remove']) for s in suggestions)
        st.container(border=True).metric(
            tr("Overlaps Found", "發現重疊"),
            f"{issues_count}", 
            delta=tr("Diagnostic only") if persona_mode else (tr(f"Can remove {removable_count}", f"可移除 {removable_count} 個") if removable_count else tr("No issues", "無問題")),
            delta_color="inverse" if removable_count else "off"
        )
    with col3:
        st.container(border=True).metric(
            tr("Avg Correlation (After)", "平均相關性（調整後）"),
            f"{avg_corr_after:.2f}", 
            delta=tr(f"Was {avg_corr_before:.2f}", f"原為 {avg_corr_before:.2f}") if avg_corr_before != avg_corr_after else None,
            delta_color="inverse"
        )

    if persona_mode:
        st.info(
            tr(
                f"The “{active_persona}” preset has been applied. Assets are auto-confirmed for the calculations below.",
                f"已套用「{tr(active_persona)}」預設情境，系統已自動確認資產並進入下方計算。"
            )
        )
        st.session_state['final_tickers'] = final_tickers
        st.session_state['portfolio_confirmed'] = True
        return

    # ── UI: Suggestions Engine ──────────────────────────────────────────────
    if suggestions:
        st.markdown(f"##### 🔴 {tr('Suggested Removals Action: keep only ONE asset from each group.')}")
        selected_keeps = {}
        for s in suggestions:
            group_str = ", ".join(s['group'])
            with st.container(border=True):
                st.markdown(
                    f"""
                    <div style="padding:12px 14px; margin:-4px 0 12px 0; border-radius:6px;
                                background:#f6fbff; border-left:4px solid #4182b9;">
                      <div style="font-weight:700; margin-bottom:8px;">
                        {tr(
                            f"{group_str} have high historical correlation (≥ {REDUNDANCY_THRESHOLD:.2f}).",
                            f"{group_str} 的歷史相關性偏高（≥ {REDUNDANCY_THRESHOLD:.2f}）。"
                        )}
                      </div>
                      <div style="display:flex; flex-wrap:wrap; gap:8px 18px; font-size:14px;">
                        <span><strong>{tr("Recommendation")}:</strong> {s['keep']}</span>
                        <span><strong>{tr("Reason")}:</strong> {tr("highest AUM / liquidity in this correlated group.")}</span>
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.markdown(f"**{tr('Select ONE asset to keep')}:**")
                keep_choice = st.radio(
                    f"{tr('Select ONE asset to keep')} - {group_str}",
                    options=s['group'],
                    index=s['group'].index(s['keep']) if s['keep'] in s['group'] else 0,
                    horizontal=True,
                    label_visibility="collapsed",
                    key=f"keep_{s['id']}",
                )
                selected_keeps[s['id']] = keep_choice

        keep_col, _ = st.columns([1, 3])
        if keep_col.button(tr("Keep Selected Assets"), type="primary", width="stretch"):
            selected_for_remove = set()
            for s in suggestions:
                keep_choice = selected_keeps.get(s['id'], s['keep'])
                selected_for_remove.update(t for t in s['group'] if t != keep_choice)

            new_watchlist = [t for t in tickers if t not in selected_for_remove]
            st.session_state.watchlist = new_watchlist
            st.session_state['pending_tickers'] = new_watchlist
            st.session_state['final_tickers'] = new_watchlist
            st.session_state['portfolio_confirmed'] = False
            st.session_state['active_persona'] = None
            st.session_state.pop('corr_data', None)
            st.session_state.pop('corr_tickers', None)
            st.success(tr("Portfolio updated. Correlation analysis has been refreshed."))
            st.rerun()
    else:
        st.success(tr("✅ Your portfolio has no major overlaps (all correlations < 0.85).",
                      "✅ 你的投資組合沒有明顯重疊（所有相關性 < 0.85）。"))

    # ── UI: Confirmation Bar ────────────────────────────────────────────────
    st.markdown("---")
    st.session_state['final_tickers'] = final_tickers
    
    conf_col1, conf_col2 = st.columns([3, 1])
    with conf_col1:
        st.markdown(tr(f"**Confirm {len(final_tickers)} assets to enter Risk Allocation**",
                       f"**確認 {len(final_tickers)} 個資產並進入風險配置**"))
        if len(rm_set) > 0:
            st.caption(tr(f"Removed {len(rm_set)} redundant assets.", f"已移除 {len(rm_set)} 個重複性較高的資產。"))
        st.markdown(" ".join([f"`{t}`" for t in final_tickers]), unsafe_allow_html=True)
        
    with conf_col2:
        if st.button(tr("Confirm Assets →", "確認資產 →"), type="primary", width="stretch"):
            st.session_state['portfolio_confirmed'] = True
            st.rerun()

    if st.session_state.get('portfolio_confirmed', False):
        st.success(tr("✅ Portfolio Confirmed! Scroll down to Risk Allocation.",
                      "✅ 投資組合已確認！請往下到風險配置區塊。"))

@st.cache_data(ttl=300, show_spinner=False)
def get_gemini_insights(
    watchlist: tuple,
    allocation: tuple,
    cagr_bt: float,
    max_drawdown: float,
    total_return: float,
    fire_years: float,
    fire_target: int,
    risk_level: str,
    initial_cap: float,
    monthly_cont: float,
    annual_exp: float,
    existing_summaries: list = None
) -> str:
    """Call Gemini API to generate structured, actionable portfolio insights."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return ""
    try:
        client = genai.Client(api_key=api_key)
        allocation_str = ", ".join([f"{t} ({w*100:.0f}%)" for t, w in allocation])
        summary_context = "\n".join([f"- {s}" for s in existing_summaries]) if existing_summaries else ""
        
        prompt = f"""You are a professional financial advisor helping a Taiwan-based passive investor. 
Analyze the following portfolio and provide exactly 3-5 concise bullet points of Strategic Next Steps.

Financial Context:
- Current Portfolio: {allocation_str}
- Risk Level: {risk_level}
- Historical Performance: {cagr_bt*100:.1f}% CAGR, {max_drawdown*100:.1f}% Max Drawdown, {total_return:.1f}x Total Return
- FIRE Target: NT${fire_target:,}
- Years to FIRE (Real): {fire_years:.1f}
- Current Stats: Initial NT${initial_cap:,.0f}, Monthly Contribution NT${monthly_cont:,.0f}, Annual Expenses NT${annual_exp:,.0f}

Base Insights:
{summary_context}

Please provide your response in the following format:

🚀 **Strategic Next Steps**
- (Concise point 1)
- (Concise point 2)
- (Concise point 3)
- (Up to 2 more points)

Rules:
1. MAX 5 bullet points total.
2. Each bullet should be 1-2 sentences.
3. DO NOT use bold (**) or italics (*) inside the bullet points.
4. Focus on high-impact actions to reach FIRE faster.
5. Write in Traditional Chinese if the dashboard language is zh-TW; otherwise write in English.

Dashboard language: {st.session_state.get('lang', 'en')}"""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        return response.text.strip()
    except Exception:
        return ""

def convert_display(amount, display_usd, rate):
    """Convert TWD amount to USD for display if needed."""
    if display_usd and rate:
        return amount / rate, "$"
    return amount, "NT$"

candidates_df = load_candidates()
metrics_df = load_metrics()
default_inflation = fetch_inflation_default()

# ── Demo Preset Personas ───────────────────────────────────────────────────────
PERSONAS = {
    "🐣 Young Professional": {
        "watchlist": ["0050.TW", "VTI", "VEA", "BND", "GLD", "BTC-USD"],
        "weights": {"0050.TW": 0.25, "VTI": 0.25, "VEA": 0.15, "BND": 0.20, "GLD": 0.10, "BTC-USD": 0.05},
        "risk": "Medium",
        "initial": 100000,
        "monthly": 10000,
        "annual_expenses": 600000,
    },
    "🕊️ Pre-Retirement": {
        "watchlist": ["0050.TW", "00878.TW", "VEA", "BND", "GLD", "VTI"],
        "weights": {"0050.TW": 0.20, "00878.TW": 0.20, "VEA": 0.15, "BND": 0.25, "GLD": 0.15, "VTI": 0.05},
        "risk": "Low",
        "initial": 5000000,
        "monthly": 50000,
        "annual_expenses": 1200000,
    },
    "🚀 Aggressive Growth": {
        "watchlist": ["VTI", "QQQ", "0050.TW", "VEA", "BTC-USD", "GLD"],
        "weights": {"VTI": 0.35, "QQQ": 0.20, "0050.TW": 0.15, "VEA": 0.10, "BTC-USD": 0.15, "GLD": 0.05},
        "risk": "High",
        "initial": 800000,
        "monthly": 30000,
        "annual_expenses": 800000,
    },
}

def apply_persona(p_name, rerun=False):
    p = PERSONAS[p_name]
    st.session_state['watchlist'] = p['watchlist']
    st.session_state['pending_tickers'] = p['watchlist']
    st.session_state['final_tickers'] = p['watchlist']
    st.session_state['risk_pref'] = p['risk']
    st.session_state['bt_params'] = {
        'initial': p['initial'],
        'monthly': p['monthly'],
        'start': st.session_state.get('bt_params', {}).get('start', date(2010, 1, 1)),
        'end': st.session_state.get('bt_params', {}).get('end', date.today()),
    }
    st.session_state['fire_annual_expenses'] = p['annual_expenses']
    # Auto-confirm to bypass Correlation Analysis
    st.session_state['portfolio_confirmed'] = True
    # Clear old correlation cache to force a reload of the new persona's data
    st.session_state.pop('corr_data', None)
    st.session_state.pop('corr_tickers', None)
    # Reset backtest result to force refresh
    st.session_state.pop('backtest_cagr', None)
    st.session_state['active_persona'] = p_name
    st.session_state['skip_aggrid_sync_once'] = True
    if rerun:
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — INTRODUCTION
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("<div id='introduction' style='padding-top: 70px; margin-top: -70px; pointer-events: none;'></div>", unsafe_allow_html=True)
st.title(tr("Passive Portfolio Lab"))
st.subheader(tr("A data-driven toolkit for long-term passive investors"))
st.markdown(tr("""
> *"The stock market is a device for transferring money from the impatient to the patient."*
> — Benjamin Graham, as cited in **A Random Walk Down Wall Street** (Burton Malkiel)

The academic evidence is clear: most active managers fail to beat the market over time.
**A Random Walk Down Wall Street** (Malkiel) argues that a passive index strategy — buying and holding
a diversified portfolio without stock-picking or market-timing — consistently outperforms active management after fees.
**The Simple Path to Wealth** (JL Collins) and **Your Money or Your Life** (Vicki Robin) extend this logic
into the FIRE movement: by minimizing costs, maximizing savings rate, and staying invested through market cycles,
financial independence becomes a matter of time, not luck.

This dashboard helps you explore that thesis with real data:
- **Asset Screening** — browse and select assets into your watchlist
- **Risk Allocation** — auto-allocate weights based on each asset's risk profile
- **Backtest & Pain Index** — see historical returns and the drawdowns you'd have to endure
- **FIRE Calculator** — estimate when you can retire based on your allocation

> *All portfolio calculations are performed in New Taiwan Dollar (TWD). For USD-denominated assets (US ETFs, bonds, commodities, and crypto), daily prices are converted to TWD using historical exchange rates — meaning currency fluctuations are factored into the returns. This reflects the real experience of a Taiwan-based investor holding foreign assets. All input amounts should be entered in TWD.*
""", """
> *「股市是一個把金錢從沒有耐心的人手中，轉移到有耐心的人手中的裝置。」*
> — Benjamin Graham，引自 Burton Malkiel 的 **A Random Walk Down Wall Street**

學術證據相當清楚：多數主動型經理人長期難以打敗市場。
**A Random Walk Down Wall Street** 主張，被動指數策略，也就是買進並持有分散化投資組合、不選股、不擇時，在扣除費用後通常能勝過主動管理。
**The Simple Path to Wealth**（JL Collins）與 **Your Money or Your Life**（Vicki Robin）則把這套邏輯延伸到 FIRE 運動：降低成本、提高儲蓄率，並在市場循環中持續投入，財務自由就更像是時間問題，而不是運氣問題。

這個儀表板用真實資料協助你探索這個命題：
- **資產篩選** — 瀏覽並選擇資產到觀察清單
- **風險配置** — 依各資產風險特性自動配置權重
- **回測與痛苦指數** — 查看歷史報酬，以及你需要承受的回撤
- **財務自由試算** — 依照配置估算何時能退休

> *所有投資組合計算皆以新台幣（TWD）進行。對於以美元計價的資產（美股 ETF、債券、商品與加密貨幣），每日價格會使用歷史匯率轉換為 TWD，因此匯率波動也會反映在報酬中。這更貼近台灣投資人持有海外資產的真實經驗。所有輸入金額都應以 TWD 填寫。*
"""))

st.divider()


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — ASSET SCREENING
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("<div id='asset-screening' style='padding-top: 70px; margin-top: -70px; pointer-events: none;'></div>", unsafe_allow_html=True)
st.title(tr("Asset Screening"))
st.caption(tr("Filter and sort assets from the pool below. Click ＋ to add an asset to your watchlist."))
with st.expander(tr("📋 How assets are selected"), expanded=False):
    st.markdown(tr("""
    The **37 assets** in this pool come from three categories. The list is static and curated by AUM / market-cap rank — no live scraping occurs at runtime.

    **Asset universe:**
    - **TW ETF** (14): Top Taiwan ETFs by AUM as of 2026/04/27 (source: Yahoo Finance TW). Covers market-cap, high-dividend, ESG, bond, and AI-theme strategies. Includes 00646.TW and 00955.TWO as owner additions. Assets with insufficient price history are excluded.
    - **US ETF** (15): Top 15 US ETFs by AUM as of 2026/03–04 (source: TipRanks / InvestLane). Includes broad market, growth, value, international, bond, and gold ETFs.
    - **Crypto** (8): Top 10 cryptocurrencies by market cap as of 2026/04, excluding stablecoins and assets with insufficient trading history (source: CoinMarketCap).

    **Data quality filter:**
    Assets with insufficient historical price data to calculate CAGR, volatility, max drawdown, and Sharpe ratio are excluded from the metrics view.

    All metrics are calculated from the full available price history for each asset using daily closing prices from Yahoo Finance, stored in Google BigQuery.
    """, """
    這個資產池共有 **37 個資產**，來自三個類別。清單是依 AUM / 市值排名靜態整理而成，執行時不會即時爬取資料。

    **資產 universe：**
    - **台股 ETF**（14）：截至 2026/04/27 依 AUM 排名的台灣主要 ETF（來源：Yahoo Finance TW），涵蓋市值型、高股息、ESG、債券與 AI 主題策略；另含持有人私人加入的 00646.TW 與 00955.TWO。價格歷史不足的資產會被排除。
    - **美股 ETF**（15）：截至 2026/03–04 依 AUM 排名的前 15 大美國 ETF（來源：TipRanks / InvestLane），包含大盤、成長、價值、國際、債券與黃金 ETF。
    - **加密貨幣**（8）：截至 2026/04 依市值排名的前 10 大加密貨幣，排除穩定幣與交易歷史不足的資產（來源：CoinMarketCap）。

    **資料品質篩選：**
    若資產歷史價格不足以計算 CAGR、波動率、最大回撤與 Sharpe ratio，將不會出現在指標檢視中。

    所有指標皆使用 Yahoo Finance 的每日收盤價完整歷史資料計算，並儲存在 Google BigQuery。
    """))

# ── Merge candidates with metrics ─────────────────────────────────────────────
candidates_subset = candidates_df[['ticker', 'category', 'currency', 'rank', 'aum_or_market_cap']].drop_duplicates(subset='ticker')

pool_df = candidates_subset.merge(
    metrics_df[['ticker', 'name', 'cagr', 'volatility', 'max_drawdown',
                'sharpe_ratio', 'worst_year', 'worst_year_label']],
    on='ticker', how='inner'
)

# ── Fetch current prices ───────────────────────────────────────────────────────
if 'market_data' not in st.session_state:
    with st.spinner(tr("Fetching current prices and volume...")):
        price_data = fetch_price_and_volume(pool_df['ticker'].tolist())
        # Only update session state if we got valid data
        has_valid = any(v.get('price') is not None for v in price_data.values())
        if has_valid:
            st.session_state.market_data = price_data
        else:
            st.session_state.market_data = {}

pool_df['price'] = pool_df['ticker'].map(lambda t: st.session_state.market_data.get(t, {}).get('price'))
pool_df['volume'] = pool_df['ticker'].map(lambda t: st.session_state.market_data.get(t, {}).get('volume'))

CURRENCY_MAP = {
    'TW_ETF': 'TWD',
    'US_ETF': 'USD',
    'CRYPTO': 'USD',
}
pool_df['price_display'] = pool_df.apply(
    lambda row: f"{row['price']:,.2f} {CURRENCY_MAP.get(row['category'], 'USD')}"
    if pd.notnull(row['price']) else "N/A", axis=1
)
pool_df['volume_display'] = pool_df['volume'].apply(
    lambda x: f"{x/1e6:.2f}M" if pd.notnull(x) and x >= 1e6
    else (f"{x/1e3:.1f}K" if pd.notnull(x) and x >= 1e3 else (str(x) if pd.notnull(x) else "N/A"))
)

# ── Helper: build display dataframe ───────────────────────────────────────────
def build_display_df(df):
    d = df.copy()
    
    # Get current FX rate
    fx_rate = st.session_state.get('live_twd_usd', 32.0)
    
    # 1. Price calculation: USD-equivalent for sorting, Native for display
    d['price_usd'] = d.apply(lambda r: r['price'] / fx_rate if r['currency'] == 'TWD' else r['price'], axis=1)
    d['Price_Display'] = d.apply(lambda r: f"{r['price']:,.2f} {r['currency']}" if pd.notnull(r['price']) else "N/A", axis=1)
    
    # 2. Volume formatting: Keep raw for sorting, format for display
    d['volume_raw'] = d['volume']
    def format_vol(v):
        if pd.isnull(v): return "N/A"
        if v >= 1e6: return f"{v/1e6:.1f}M"
        if v >= 1e3: return f"{v/1e3:.1f}K"
        return str(int(v))
    d['Volume_Display'] = d['volume'].apply(format_vol)
    
    # 3. Select columns
    d = d[['ticker', 'name', 'category', 'price_usd', 'Price_Display', 'volume_raw', 'Volume_Display',
            'cagr', 'volatility', 'max_drawdown', 'worst_year', 'worst_year_label']].copy()
            
    # Multiply metrics by 100
    for col in ['cagr', 'volatility', 'max_drawdown', 'worst_year']:
        d[col] = d[col].apply(lambda x: round(x * 100, 4) if pd.notnull(x) else None)
    d['worst_year_label'] = d['worst_year_label'].apply(lambda x: str(int(x)) if pd.notnull(x) else "N/A")
    
    d.columns = ['Ticker', 'Name', 'Category', 'price_usd', 'Price', 'volume_raw', 'Volume',
                 'Ann. Return', 'Volatility', 'Max Drawdown', 'Worst Year Ret.', 'Worst Year']
    return d

# ── Asset Pool ─────────────────────────────────────────────────────────────────
def render_asset_pool():
    st.markdown(f"#### {tr('Asset Pool')}")
    
    # ── Toolbar ──────────────────────────────────────────────────────────────────
    fc1, fc2, fc3, fc4, fc5 = st.columns(5)
    with fc1:
        search_query = st.text_input(tr("Search"), placeholder=tr("Search assets..."), label_visibility="collapsed")
    with fc2:
        selected_type = st.selectbox(tr("Category"), ["All", "TW ETF", "US ETF", "Crypto"], label_visibility="collapsed", format_func=lambda x: tr(x))
    with fc3:
        selected_cagr = st.selectbox(tr("CAGR ≥"), ["CAGR ≥ 0", "CAGR ≥ 5%", "CAGR ≥ 10%", "CAGR ≥ 15%", "CAGR ≥ 20%"], label_visibility="collapsed")
    with fc4:
        selected_sharpe = st.selectbox(tr("Sharpe ≥"), ["Sharpe ≥ 0", "Sharpe ≥ 0.5", "Sharpe ≥ 1.0", "Sharpe ≥ 1.5"], label_visibility="collapsed")
    with fc5:
        selected_mdd = st.selectbox(tr("Max DD"), ["Max DD All", "Max DD ≤ 20%", "Max DD ≤ 30%", "Max DD ≤ 50%"], label_visibility="collapsed", format_func=lambda x: tr(x, x.replace("Max DD", "最大回撤") if x.startswith("Max DD") else x))

    filtered = pool_df.copy()

    # Apply Search Filter
    if search_query:
        sq = search_query.lower()
        filtered = filtered[filtered['ticker'].str.lower().str.contains(sq) | filtered['name'].str.lower().str.contains(sq)]
        
    # Apply Type Filter
    type_map = {"TW ETF": "TW_ETF", "US ETF": "US_ETF", "Crypto": "CRYPTO"}
    if selected_type != "All":
        filtered = filtered[filtered['category'] == type_map[selected_type]]
        
    # Apply CAGR Filter
    if selected_cagr != "CAGR ≥ 0":
        c_val = float(selected_cagr.replace("CAGR ≥ ", "").replace("%", "")) / 100.0
        filtered = filtered[filtered['cagr'] >= c_val]
        
    # Apply Sharpe Filter
    if selected_sharpe != "Sharpe ≥ 0":
        s_val = float(selected_sharpe.replace("Sharpe ≥ ", ""))
        filtered = filtered[filtered['sharpe_ratio'] >= s_val]

    # Apply Max DD Filter
    if selected_mdd != "Max DD All":
        mdd_threshold = -float(selected_mdd.replace("Max DD ≤ ", "").replace("%", "")) / 100.0
        filtered = filtered[filtered['max_drawdown'] >= mdd_threshold]

    filtered_reset = filtered.reset_index(drop=True)

    # ── Selected Bar / Batch Actions ───────────────────────────────────────────────
    pending = st.session_state.get('pending_tickers', list(st.session_state.watchlist))
    
    def handle_review_click():
        p_list = st.session_state.get('pending_tickers', [])
        st.session_state.watchlist = list(p_list)
        st.session_state['portfolio_confirmed'] = False
        st.session_state['active_persona'] = None
        tickers_key = tuple(sorted(p_list))
        if st.session_state.get('corr_tickers') != tickers_key:
            st.session_state.pop('corr_data', None)
            st.session_state.pop('corr_tickers', None)

    bar_container = st.container(border=True)
    bc1, bc2, bc3, bc4 = bar_container.columns([3, 1, 1, 2])
    
    bc1.markdown(tr(
        f"**{len(pending)} asset{'s' if len(pending) != 1 else ''} selected** (Showing {len(filtered_reset)} total)",
        f"**已選 {len(pending)} 個資產**（目前顯示 {len(filtered_reset)} 個）"
    ))
    
    # Render select/deselect buttons in the second column
    if bc2.button(f"☑ {tr('Select All')}", width="stretch"):
        st.session_state['pending_tickers'] = filtered_reset['ticker'].tolist()
        st.session_state.pop('asset_pool_editor', None)
        st.rerun()
        
    if bc3.button(f"☐ {tr('Clear')}", key="clear_selected", width="stretch"):
        st.session_state['pending_tickers'] = []
        st.session_state.pop('asset_pool_aggrid', None) # Update key to match AgGrid
        st.rerun()
        
    bc4.button(tr("Review Portfolio →"), type="primary", key="review_portfolio_btn",
               width="stretch", disabled=len(pending) == 0, on_click=handle_review_click)

    # ── AG Grid ──────────────────────────────────────────────────────────────────
    display_df = build_display_df(filtered_reset)
    editor_df = display_df.copy()
    editor_df.insert(0, 'Add', [t in pending for t in filtered_reset['ticker']])

    gb = GridOptionsBuilder.from_dataframe(editor_df)
    gb.configure_default_column(sortable=True, resizable=True, filter=False, floatingFilter=False, suppressMenu=True)

    gb.configure_column("Add", headerName="＋", width=60, editable=True,
                        cellRenderer="agCheckboxCellRenderer",
                        cellEditor="agCheckboxCellEditor",
                        pinned="left") # Pin checkbox to left
    
    gb.configure_column("Ticker", headerName=tr("Ticker"), pinned="left", width=100) # Pin Ticker next to checkbox
    gb.configure_column("Name", headerName=tr("Name"))
    gb.configure_column("Category", headerName=tr("Category"))

    # Decouple value from display for Price and Volume
    gb.configure_column("Price", 
                        valueGetter="data.price_usd", 
                        valueFormatter="data.Price",
                        headerName=tr("Price"),
                        sortable=True)
    
    gb.configure_column("Volume",
                        valueGetter="data.volume_raw",
                        valueFormatter="data.Volume",
                        headerName=tr("Volume"),
                        sortable=True)
    
    gb.configure_column("price_usd", hide=True)
    gb.configure_column("volume_raw", hide=True)

    for col in ['Ann. Return', 'Volatility', 'Max Drawdown', 'Worst Year Ret.']:
        gb.configure_column(col, headerName=tr(col), valueFormatter="value != null ? value.toFixed(2) + '%' : 'N/A'")
    gb.configure_column("Worst Year", headerName=tr("Worst Year"))
    gb.configure_grid_options(
        suppressMovableColumns=True,
        suppressMenuHide=True,
        suppressFieldDotNotation=True,
        sideBar=False,
    )

    grid_response = AgGrid(
        editor_df,
        gridOptions=gb.build(),
        update_mode=GridUpdateMode.VALUE_CHANGED,
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        width="stretch",
        height=450,
        theme="streamlit",
        key="asset_pool_aggrid"
    )

    result_df = grid_response["data"]
    
    # AgGrid returns all-False on first render before JS initializes.
    # Only sync back if at least one checkbox is True, or if we need to
    # clear a previously-set pending list.
    skip_aggrid_sync = st.session_state.pop('skip_aggrid_sync_once', False)
    if result_df is not None and not result_df.empty and not skip_aggrid_sync:
        checked_tickers = filtered_reset.loc[result_df['Add'] == True, 'ticker'].tolist()
        visible_tickers = filtered_reset['ticker'].tolist()
        hidden_confirmed = [t for t in st.session_state.watchlist if t not in visible_tickers]
        new_pending = list(dict.fromkeys(hidden_confirmed + checked_tickers))

        has_any_checked = result_df['Add'].any()
        pending_was_set = 'pending_tickers' in st.session_state

        if (has_any_checked or pending_was_set) and set(new_pending) != set(pending):
            st.session_state['pending_tickers'] = new_pending
            st.rerun()



def render_persona_quick_start():
    st.markdown("<div style='height:72px;'></div>", unsafe_allow_html=True)
    with st.container(border=True, key="persona_quick_start_container"):
        st.markdown(f"💡 **{tr('Not sure where to start?')}** {tr('Try a preset investor persona:')}")
        cols = st.columns(len(PERSONAS))
        active_persona = st.session_state.get('active_persona')
        for col, p_name in zip(cols, PERSONAS.keys()):
            button_type = "primary" if p_name == active_persona else "secondary"
            col.button(
                tr(p_name),
                key=f"persona_quick_start_{p_name}",
                type=button_type,
                width="stretch",
                on_click=apply_persona,
                args=(p_name,),
            )

render_asset_pool()
render_persona_quick_start()




# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — CORRELATION ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("<div id='correlation-analysis' style='padding-top: 70px; margin-top: -70px; pointer-events: none;'></div>",
            unsafe_allow_html=True)
st.title(tr("Correlation Analysis"))
st.caption(tr("Confirm your portfolio is genuinely diversified before running risk and FIRE calculations."))

render_correlation_analysis(st.session_state.watchlist, pool_df)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — RISK ALLOCATION
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("<div id='risk-allocation' style='padding-top: 70px; margin-top: -70px; pointer-events: none;'></div>", unsafe_allow_html=True)
st.title(tr("Risk Allocation"))
st.caption(tr("Based on your watchlist, the system automatically allocates weights to match your target risk level."))

if not st.session_state.watchlist:
    st.info(tr("Add assets to your watchlist in Asset Screening first."))
elif not st.session_state.get('portfolio_confirmed', False):
    st.info("ℹ️ " + tr("Confirm your portfolio in **Correlation Analysis** above to unlock this section."))
else:
    final_tickers = st.session_state.get('final_tickers', st.session_state.watchlist)
    selected_metrics = metrics_df[metrics_df['ticker'].isin(final_tickers)].copy()

    if selected_metrics.empty:
        st.warning(tr("No metric data found for your selected assets."))
    else:
        # ── Calculate achievable risk range ────────────────────────────────────
        vols = selected_metrics.set_index('ticker')['volatility']
        min_vol = float(vols.min())
        max_vol = float(vols.max())

        min_risk = vol_to_risk_label(min_vol)
        max_risk = vol_to_risk_label(max_vol)
        min_risk_num = RISK_ORDER[min_risk]
        max_risk_num = RISK_ORDER[max_risk]

        achievable = [k for k, v in RISK_ORDER.items() if min_risk_num <= v <= max_risk_num]

        st.info(tr(
            f"Based on your selected assets, achievable risk range: **{min_risk}** to **{max_risk}**",
            f"根據你選擇的資產，可達成的風險範圍為：**{risk_label(min_risk)}** 到 **{risk_label(max_risk)}**"
        ))

        with st.expander("ℹ️ " + tr("How is the achievable risk range determined?")):
            st.markdown(
                tr(f"""
The achievable risk range is derived from the **annualized volatility** of the assets in your watchlist:

1. Compute each asset's annualized volatility (stdev of daily returns × √N).
2. Find the **lowest** and **highest** volatility across your watchlist.
3. Map each to a risk tier using these fixed thresholds:

| Annualized Volatility | Risk Tier |
|---|---|
| &lt; 16% | Low |
| 16% &ndash; 27% | Medium |
| 27% &ndash; 50% | High |
| &ge; 50% | Extreme High |

4. The achievable range spans from the tier of the **least volatile** asset to the tier of the **most volatile** asset.

**Why this is the full achievable range.** The allocation algorithm combines assets by a weighted average of their volatilities (ignoring cross-asset correlations), so the resulting portfolio volatility is always bounded between the minimum and maximum single-asset volatility in your watchlist &mdash; you cannot reach a tier below the lowest-vol asset or above the highest-vol asset.

**Your watchlist right now:** lowest volatility = **{min_vol:.1%}** ({min_risk}), highest volatility = **{max_vol:.1%}** ({max_risk}).
                """, f"""
可達成的風險範圍是由觀察清單中資產的 **年化波動率** 推導而來：

1. 計算每個資產的年化波動率（日報酬標準差 × √N）。
2. 找出觀察清單中 **最低** 與 **最高** 的波動率。
3. 依照固定門檻映射到風險等級：

| 年化波動率 | 風險等級 |
|---|---|
| &lt; 16% | 低 |
| 16% &ndash; 27% | 中 |
| 27% &ndash; 50% | 高 |
| &ge; 50% | 極高 |

4. 可達成範圍會從 **最低波動資產** 的等級延伸到 **最高波動資產** 的等級。

**為什麼這是完整範圍。** 配置演算法以各資產波動率的加權平均來組合（未納入跨資產相關性），因此投資組合波動率會落在單一資產最低與最高波動率之間，無法低於最低波動資產，也無法高於最高波動資產。

**你目前的觀察清單：** 最低波動率 = **{min_vol:.1%}**（{risk_label(min_risk)}），最高波動率 = **{max_vol:.1%}**（{risk_label(max_risk)}）。
                """)
            )

        # ── Risk preference selector (only show achievable levels) ─────────────
        persona_risk = st.session_state.get('persona_risk')
        default_risk_idx = achievable.index(persona_risk) if persona_risk in achievable else 0
        
        risk_pref = st.radio(
            tr("Target Risk Level"),
            options=achievable,
            horizontal=True,
            index=default_risk_idx,
            key="risk_pref",
            format_func=risk_label
        )

        target_vol = RISK_VOL_TARGET[risk_pref]

        # ── Weight assignment ──────────────────────────────────────────────────
        # If a persona is active and the watchlist matches, use its preset weights
        p_weights = st.session_state.get('persona_weights')
        p_name = st.session_state.get('active_persona')
        use_persona_weights = (p_weights and p_name and
                               set(p_weights.keys()) == set(selected_metrics['ticker']))

        # Cache key: skip the 200-iteration optimizer if inputs haven't changed.
        alloc_key = (tuple(sorted(selected_metrics['ticker'])), target_vol,
                     use_persona_weights, p_name if use_persona_weights else None)
        if alloc_key == st.session_state.get('_alloc_cache_key') and \
                st.session_state.get('_alloc_cache_df') is not None:
            alloc_df = st.session_state['_alloc_cache_df']
        elif use_persona_weights:
            alloc_df = selected_metrics.copy()
            alloc_df['weight'] = alloc_df['ticker'].map(p_weights)
            st.session_state['_alloc_cache_key'] = alloc_key
            st.session_state['_alloc_cache_df'] = alloc_df
        else:
            alloc_df = compute_allocation(selected_metrics, target_vol)
            st.session_state['_alloc_cache_key'] = alloc_key
            st.session_state['_alloc_cache_df'] = alloc_df

        # Final portfolio metrics
        port_vol = float(np.dot(alloc_df['weight'].values, alloc_df['volatility'].values))
        port_cagr = float(np.dot(alloc_df['weight'].values, alloc_df['cagr'].values))
        port_dd = float(np.dot(alloc_df['weight'].values, alloc_df['max_drawdown'].values))
        port_sharpe = float(np.dot(alloc_df['weight'].values, alloc_df['sharpe_ratio'].values))

        # Store in session state for downstream use
        st.session_state['allocation'] = dict(zip(alloc_df['ticker'], alloc_df['weight']))
        st.session_state['allocation_cagr'] = port_cagr

        # ── Display ────────────────────────────────────────────────────────────
        m1, m2, m3, m4 = st.columns(4)
        m1.metric(
            tr("Weighted CAGR"),
            f"{port_cagr:.2%}",
            help="This is the weighted average of each asset's historical CAGR based on original currency. "
                 "It may differ from the Backtest CAGR below, which reflects actual TWD-converted portfolio "
                 "performance including currency fluctuation effects over the selected backtest period."
        )
        m2.metric(tr("Portfolio Volatility"), f"{port_vol:.1%}", delta=tr(f"Target: {target_vol:.0%}", f"目標：{target_vol:.0%}"))
        m3.metric(tr("Weighted Max Drawdown"), f"{port_dd:.2%}")
        m4.metric(tr("Weighted Sharpe"), f"{port_sharpe:.2f}")

        alloc_df['weight_pct'] = (alloc_df['weight'] * 100).round(1)

        # ── Treemap via HTML component with click support ──────────────────────
        BLUE_6 = [
            'rgb(210, 228, 245)',
            'rgb(168, 202, 232)',
            'rgb(114, 168, 212)',
            'rgb(65, 130, 185)',
            'rgb(30, 90, 150)',
            'rgb(10, 50, 110)',
        ]
        all_vols = metrics_df[['ticker', 'volatility']].copy()
        all_vols = all_vols.sort_values('volatility').reset_index(drop=True)
        all_vols['vol_rank'] = range(1, len(all_vols) + 1)
        all_vols['tier'] = ((all_vols['vol_rank'] - 1) // 4).clip(upper=5)
        vol_tier_map = dict(zip(all_vols['ticker'], all_vols['tier']))
        alloc_df['tier'] = alloc_df['ticker'].map(vol_tier_map).fillna(2).astype(int)
        alloc_df['color'] = alloc_df['tier'].apply(lambda t: BLUE_6[t])
        alloc_df['label'] = alloc_df.apply(
            lambda r: f"{r['ticker']}<br>{r['weight_pct']}%<br>CAGR: {r['cagr']:.1%}", axis=1
        )
        # Pre-calculate radar scores in Python
        pool_cagr_max = float(metrics_df['cagr'].max())
        pool_vol_max = float(metrics_df['volatility'].max())
        pool_dd_min = float(metrics_df['max_drawdown'].min())
        pool_sharpe_max = float(metrics_df['sharpe_ratio'].max())
        def calc_radar(r):
            cagr_score = round(min(100, max(0, (r['cagr'] / pool_cagr_max) * 100)) if pool_cagr_max else 0, 1)
            vol_score = round(min(100, max(0, (1 - r['volatility'] / pool_vol_max) * 100)) if pool_vol_max else 0, 1)
            dd_score = round(min(100, max(0, (1 - abs(r['max_drawdown']) / abs(pool_dd_min)) * 100)) if pool_dd_min else 0, 1)
            sharpe_score = round(min(100, max(0, (r['sharpe_ratio'] / pool_sharpe_max) * 100)) if pool_sharpe_max else 0, 1)
            worst_score = round(min(100, max(0, (1 - abs(r['worst_year']) / 1.0) * 100)), 1)
            return [cagr_score, vol_score, dd_score, sharpe_score, worst_score]
        metrics_by_ticker = {row['ticker']: row for _, row in metrics_df.iterrows()}
        treemap_data_list = []
        for _, row in alloc_df.iterrows():
            mr = metrics_by_ticker.get(row['ticker'])
            if mr is not None:
                radar = calc_radar(mr)
                yf_ticker = row['ticker']
                tv_ticker = row['ticker'].replace('-USD', 'USD').replace('.TW', '')
                treemap_data_list.append({
                    'label': row['label'],
                    'value': row['weight_pct'],
                    'color': row['color'],
                    'ticker': row['ticker'],
                    'name': str(mr['name']),
                    'cagr': f"{mr['cagr']:.2%}",
                    'vol': f"{mr['volatility']:.2%}",
                    'maxdd': f"{mr['max_drawdown']:.2%}",
                    'sharpe': f"{mr['sharpe_ratio']:.2f}",
                    'worst_ret': f"{mr['worst_year']:.2%}",
                    'worst_yr': str(int(mr['worst_year_label'])),
                    'radar': radar,
                    'yf_url': f"https://finance.yahoo.com/quote/{yf_ticker}",
                    'tv_url': f"https://www.tradingview.com/symbols/{tv_ticker}/",
                    'profile': get_asset_profile(row['ticker']),
                })
        treemap_data = json.dumps(treemap_data_list)
        st.markdown(f"### {tr('Portfolio Composition')}")
        st.markdown(
            f"""
            <div style="padding:10px 16px; margin:6px 0 14px 0; border-radius:6px;
                        background:#eff5fb; border-left:3px solid #4182b9;
                        font-size:14.5px; color:#1f3b5c; line-height:1.55;">
              Weights automatically fitted to your target risk level
              (<strong>{risk_pref}</strong>). Click any tile for details.
            </div>
            """,
            unsafe_allow_html=True,
        )
        html_code = f"""
        <style>
            g.pathbar, .pathbar, .slice.pathbar {{ display: none !important; }}
        </style>
        <div id="main-container" style="width:100%; min-height:720px; position:relative;">
            <div id="treemap-container" style="width:100%; height:560px;"></div>
            <div id="detail-card" style="display:none; width:100%; min-height:700px; box-sizing:border-box; padding:24px 28px; font-family:sans-serif; border-radius:8px; position:absolute; top:0; left:0;"></div>
        </div>
        <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
        <script>
        var allData = {treemap_data};
        var dataMap = {{}};
        allData.forEach(function(d) {{ dataMap[d.ticker] = d; }});
        var labels = allData.map(d => d.label);
        var values = allData.map(d => d.value);
        var colors = allData.map(d => d.color);
        var trace = {{
            type: 'treemap',
            labels: labels,
            parents: labels.map(() => ''),
            values: values,
            textinfo: 'label',
            hovertemplate: '<b>%{{label}}</b><extra></extra>',
            marker: {{ colors: colors }},
            pathbar: {{ visible: false }},
        }};
        var layout = {{
            margin: {{t:10, b:10, l:10, r:10}},
            paper_bgcolor: 'rgba(0,0,0,0)',
        }};
        var config = {{displayModeBar: false}};
        var radarChart = null;
        function hexToRgb(hex) {{
            hex = hex.replace('#','');
            if (hex.length === 3) hex = hex.split('').map(c=>c+c).join('');
            var r = parseInt(hex.substring(0,2),16);
            var g = parseInt(hex.substring(2,4),16);
            var b = parseInt(hex.substring(4,6),16);
            return {{r:r, g:g, b:b}};
        }}
        function rgbStringToObj(s) {{
            var m = s.match(/rgb\\((\\d+),\\s*(\\d+),\\s*(\\d+)\\)/);
            if (m) return {{r:parseInt(m[1]), g:parseInt(m[2]), b:parseInt(m[3])}};
            return hexToRgb(s.replace('#',''));
        }}
        function luminance(c) {{
            return 0.299*c.r + 0.587*c.g + 0.114*c.b;
        }}
        function escapeHtml(value) {{
            return String(value || '').replace(/[&<>"']/g, function(ch) {{
                return ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}})[ch];
            }});
        }}
        function profileRows(profile) {{
            if (!profile) return '';
            var isCrypto = profile.assetType === 'Crypto';
            var expenseText = profile.managementFee && profile.custodianFee
                ? `${{profile.expenseRatio}}（包含經理費 ${{profile.managementFee}} 及保管費 ${{profile.custodianFee}}）`
                : profile.expenseRatio;
            var rows = isCrypto ? [
                ['類型', profile.assetType],
                ['類別', profile.cryptoCategory || profile.category],
                ['區塊鏈', profile.blockchain],
                ['發行商', profile.issuer],
                ['共識機制', profile.consensus]
            ] : [
                ['類型', profile.assetType],
                ['類別', profile.category],
                ['發行商', profile.issuer],
                ['費用率', expenseText],
                ['配息政策', profile.dividendPolicy]
            ];
            return rows.filter(function(row) {{ return row[1]; }}).map(function(row) {{
                return `<div style="background:rgba(255,255,255,0.12); border:1px solid rgba(255,255,255,0.24); border-radius:7px; padding:8px 10px;">
                    <div style="font-size:11px; font-weight:700; opacity:0.75; margin-bottom:3px;">${{escapeHtml(row[0])}}</div>
                    <div style="font-size:13px; font-weight:600;">${{escapeHtml(row[1])}}</div>
                </div>`;
            }}).join('');
        }}
        function profileBlock(d, textColor, subTextColor, borderColor, btnBg) {{
            var profile = d.profile || null;
            if (!profile) {{
            return `<div style="color:${{textColor}};">目前尚無補充資訊。</div>`;
            }}
            var sourceLabel = profile.collectionMethod === 'web_scraping'
                ? `網頁爬蟲來源：${{escapeHtml(profile.sourceName || '公開資料頁')}}`
                : `補充來源：${{escapeHtml(profile.sourceName || '公開資料頁')}}`;
            var source = profile.sourceUrl ? `<a href="${{escapeHtml(profile.sourceUrl)}}" target="_blank" style="color:${{textColor}}; font-weight:700; text-decoration:none;">${{sourceLabel}}</a>` : '';
            var expenseSource = profile.expenseRatioSourceUrl && profile.expenseRatioSourceUrl !== profile.sourceUrl
                ? `<a href="${{escapeHtml(profile.expenseRatioSourceUrl)}}" target="_blank" style="color:${{textColor}}; font-weight:700; text-decoration:none;">費率來源：${{escapeHtml(profile.expenseRatioSourceName || '公開資料頁')}}</a>`
                : '';
            return `<div style="color:${{textColor}}; display:flex; flex-direction:column;">
                <div style="font-size:15px; font-weight:700; margin-bottom:6px;">資產補充資訊</div>
                <div style="font-size:13px; line-height:1.55; color:${{subTextColor}}; margin-bottom:10px;">${{escapeHtml(profile.summary)}}</div>
                <div style="display:grid; grid-template-columns:1fr; gap:8px; margin-bottom:10px;">${{profileRows(profile)}}</div>
                <div style="display:flex; justify-content:space-between; gap:10px; flex-wrap:wrap; font-size:12px; color:${{subTextColor}};">
                    <span>更新時間：${{escapeHtml(profile.fetchedAt || 'N/A')}}</span>
                    ${{source}}
                    ${{expenseSource}}
                </div>
            </div>`;
        }}
        function showDetail(ticker) {{
            var d = dataMap[ticker];
            if (!d) return;
            document.getElementById('treemap-container').style.display = 'none';
            var card = document.getElementById('detail-card');
            card.style.display = 'block';
            var bgColor = d.color;
            var rgb = bgColor.startsWith('rgb') ? rgbStringToObj(bgColor) : hexToRgb(bgColor.replace('#',''));
            var lum = luminance(rgb);
            var textColor = lum > 160 ? '#1a1a1a' : '#ffffff';
            var subTextColor = lum > 160 ? '#555555' : 'rgba(255,255,255,0.75)';
            var borderColor = lum > 160 ? 'rgba(0,0,0,0.15)' : 'rgba(255,255,255,0.3)';
            var btnBg = lum > 160 ? 'rgba(0,0,0,0.06)' : 'rgba(255,255,255,0.15)';
            var radarColor = lum > 160 ? 'rgba(107,158,159,0.35)' : 'rgba(255,255,255,0.35)';
            var radarBorder = lum > 160 ? '#6B9E9F' : '#ffffff';
            var panelStyle = `min-height:560px; min-width:0; padding:16px; border:1px solid ${{borderColor}}; border-radius:8px; background:${{btnBg}}; box-sizing:border-box; overflow:visible;`;
            card.style.background = bgColor;
            card.innerHTML = `
                <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:18px;">
                    <span style="font-size:22px; font-weight:700; color:${{textColor}};">${{d.ticker}} — ${{d.name}}</span>
                    <button onclick="hideDetail()" style="background:${{btnBg}}; border:1px solid ${{borderColor}}; border-radius:6px; padding:6px 16px; cursor:pointer; font-size:14px; color:${{textColor}}; white-space:nowrap; margin-left:12px;">← Back</button>
                </div>
                <div style="display:grid; grid-template-columns:minmax(280px, 0.95fr) minmax(260px, 0.9fr) minmax(300px, 1.15fr); gap:24px; align-items:stretch;">
                    <div style="${{panelStyle}} display:flex; flex-direction:column; justify-content:flex-start;">
                        <div>
                            <div style="display:grid; grid-template-columns:1fr 1fr; gap:18px 22px;">
                                <div>
                                    <div style="font-size:13px; color:${{subTextColor}}; margin-bottom:4px;">Ann. Return (CAGR)</div>
                                    <div style="font-size:32px; font-weight:700; color:${{textColor}}; line-height:1;">${{d.cagr}}</div>
                                </div>
                                <div>
                                    <div style="font-size:13px; color:${{subTextColor}}; margin-bottom:4px;">Volatility</div>
                                    <div style="font-size:32px; font-weight:700; color:${{textColor}}; line-height:1;">${{d.vol}}</div>
                                </div>
                                <div>
                                    <div style="font-size:13px; color:${{subTextColor}}; margin-bottom:4px;">Max Drawdown</div>
                                    <div style="font-size:32px; font-weight:700; color:${{textColor}}; line-height:1;">${{d.maxdd}}</div>
                                </div>
                                <div>
                                    <div style="font-size:13px; color:${{subTextColor}}; margin-bottom:4px;">Sharpe Ratio</div>
                                    <div style="font-size:32px; font-weight:700; color:${{textColor}}; line-height:1;">${{d.sharpe}}</div>
                                </div>
                                <div>
                                    <div style="font-size:13px; color:${{subTextColor}}; margin-bottom:4px;">Worst Year Return</div>
                                    <div style="font-size:32px; font-weight:700; color:${{textColor}}; line-height:1;">${{d.worst_ret}}</div>
                                </div>
                                <div>
                                    <div style="font-size:13px; color:${{subTextColor}}; margin-bottom:4px;">Worst Year</div>
                                    <div style="font-size:32px; font-weight:700; color:${{textColor}}; line-height:1;">${{d.worst_yr}}</div>
                                </div>
                            </div>
                        </div>
                        <div style="display:flex; gap:10px; margin-top:24px;">
                            <a href="${{d.yf_url}}" target="_blank" style="flex:1; text-align:center; padding:14px 8px; border:1px solid ${{borderColor}}; border-radius:8px; text-decoration:none; color:${{textColor}}; font-size:15px; font-weight:600; background:${{btnBg}};">Yahoo Finance</a>
                            <a href="${{d.tv_url}}" target="_blank" style="flex:1; text-align:center; padding:14px 8px; border:1px solid ${{borderColor}}; border-radius:8px; text-decoration:none; color:${{textColor}}; font-size:15px; font-weight:600; background:${{btnBg}};">TradingView</a>
                        </div>
                    </div>
                    <div style="${{panelStyle}}">
                        ${{profileBlock(d, textColor, subTextColor, borderColor, btnBg)}}
                    </div>
                    <div style="${{panelStyle}} display:flex; flex-direction:column; align-items:center; justify-content:center; text-align:center;">
                        <div style="width:100%; flex:1; min-height:410px; display:flex; align-items:center; justify-content:center;">
                            <canvas id="radarCanvas" style="max-width:340px; max-height:340px;"></canvas>
                        </div>
                        <div style="text-align:center; font-size:12px; color:${{subTextColor}}; margin-top:10px;">Scores relative to all assets. Higher = better.</div>
                    </div>
                </div>
            `;
            if (radarChart) {{ radarChart.destroy(); radarChart = null; }}
            var ctx = document.getElementById('radarCanvas').getContext('2d');
            radarChart = new Chart(ctx, {{
                type: 'radar',
                data: {{
                    labels: ['Ann. Return', 'Low Vol', 'DD Protection', 'Sharpe', 'Worst Year'],
                    datasets: [{{
                        data: d.radar,
                        backgroundColor: radarColor,
                        borderColor: radarBorder,
                        borderWidth: 2,
                        pointBackgroundColor: radarBorder,
                        pointRadius: 4,
                    }}]
                }},
                options: {{
                    maintainAspectRatio: true,
                    scales: {{ r: {{
                        min: 0, max: 100,
                        ticks: {{ display: false }},
                        grid: {{ color: lum > 160 ? 'rgba(0,0,0,0.1)' : 'rgba(255,255,255,0.2)' }},
                        angleLines: {{ color: lum > 160 ? 'rgba(0,0,0,0.1)' : 'rgba(255,255,255,0.2)' }},
                        pointLabels: {{ font: {{ size: 14, weight: '600' }}, color: textColor }}
                    }} }},
                    plugins: {{ legend: {{ display: false }} }},
                    animation: {{ duration: 300 }}
                }}
            }});
        }}
        function attachClickHandler(gd) {{
            gd.on('plotly_treemapclick', function(eventData) {{
                if (eventData && eventData.points && eventData.points.length > 0) {{
                    var pt = eventData.points[0];
                    var label = pt.label || '';
                    var ticker = label.split('<br>')[0].trim();
                    if (ticker && dataMap[ticker]) {{
                        showDetail(ticker);
                    }}
                }}
                return false;
            }});
        }}
        function hideDetail() {{
            document.getElementById('detail-card').style.display = 'none';
            document.getElementById('treemap-container').style.display = 'block';
            if (radarChart) {{ radarChart.destroy(); radarChart = null; }}
        }}
        function purgeRoguePathbar() {{
            var container = document.getElementById('treemap-container');
            if (!container) return;
            // Hide pathbar groups
            container.querySelectorAll('g.pathbar, .pathbar, .slice.pathbar').forEach(function(el) {{
                el.style.display = 'none';
            }});
            // Hide any text node that still shows literal %{{label}}
            container.querySelectorAll('text').forEach(function(t) {{
                if (t.textContent && t.textContent.indexOf('%{{label}}') !== -1) {{
                    t.style.display = 'none';
                    var p = t.parentElement;
                    while (p && p !== container) {{
                        if (p.tagName === 'g' || p.tagName === 'G') {{
                            p.style.display = 'none';
                            break;
                        }}
                        p = p.parentElement;
                    }}
                }}
            }});
        }}
        Plotly.newPlot('treemap-container', [trace], layout, config).then(function(gd) {{
            attachClickHandler(gd);
            purgeRoguePathbar();
            // Re-purge after every Plotly redraw (hover can re-render)
            gd.on('plotly_afterplot', purgeRoguePathbar);
            gd.on('plotly_hover', purgeRoguePathbar);
            gd.on('plotly_unhover', purgeRoguePathbar);
        }});
        </script>
        """
        components.html(html_code, height=780)

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — BACKTEST & PAIN INDEX
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("<div id='backtest' style='padding-top: 70px; margin-top: -70px; pointer-events: none;'></div>", unsafe_allow_html=True)
st.title(tr("Backtest & Pain Index"))
st.caption(tr("How would your portfolio have performed historically — and could you have endured the downturns?"))

if not st.session_state.get('portfolio_confirmed', False):
    st.info("ℹ️ " + tr("Confirm your portfolio in **Correlation Analysis** above to unlock this section."))
elif 'allocation' not in st.session_state or not st.session_state['allocation']:
    st.info(tr("Complete the Risk Allocation section first."))
else:
    # ── Advanced Settings ────────────────────────────────────────────
    # Set defaults first
    if 'bt_params' not in st.session_state:
        st.session_state['bt_params'] = {
            'initial': 300000,
            'monthly': 15000,
            'start': date(2010, 1, 1),
            'end': date.today(),
        }

    with st.expander("⚙️ " + tr("Advanced Settings"), expanded=False):
        row1_col1, row1_col2 = st.columns(2)
        with row1_col1:
            initial_bt = st.number_input(tr("Initial Investment (NT$)"), min_value=0, value=st.session_state['bt_params'].get('initial', 300000), step=10000, key="bt_initial")
        with row1_col2:
            monthly_bt = st.number_input(tr("Monthly Contribution (NT$)"), min_value=0, value=st.session_state['bt_params'].get('monthly', 15000), step=1000, key="bt_monthly")
        row2_col1, row2_col2 = st.columns(2)
        with row2_col1:
            start_bt = st.date_input(tr("Start Date"), value=st.session_state['bt_params'].get('start', date(2010, 1, 1)), key="bt_start")
        with row2_col2:
            end_bt = st.date_input(tr("End Date"), value=st.session_state['bt_params'].get('end', date.today()), key="bt_end")

        st.session_state['bt_params'] = {
            'initial': initial_bt,
            'monthly': monthly_bt,
            'start': start_bt,
            'end': end_bt,
        }

    initial_bt = st.session_state['bt_params']['initial']
    monthly_bt = st.session_state['bt_params']['monthly']
    start_bt = st.session_state['bt_params']['start']
    end_bt = st.session_state['bt_params']['end']

    # ── Run backtest automatically ─────────────────────────────────────────────
    with st.spinner(tr("Running backtest...")):
        try:
            result_df = run_backtest(
                start_date=str(start_bt),
                end_date=str(end_bt),
                initial_investment=initial_bt,
                monthly_contribution=monthly_bt,
                tickers_weights=st.session_state['allocation'],
            )
            display_usd = st.session_state.get('display_usd', False)
            fx_rate = st.session_state.get('live_twd_usd', 32.0)

            final_val = result_df['portfolio_value'].iloc[-1]
            total_inv = result_df['total_invested'].iloc[-1]
            total_ret = result_df['total_return_pct'].iloc[-1]
            years = (pd.to_datetime(end_bt) - pd.to_datetime(start_bt)).days / 365.0
            cagr_bt = (final_val / total_inv) ** (1 / years) - 1 if years > 0 and total_inv > 0 else 0.0
            st.session_state['backtest_cagr'] = cagr_bt
            st.session_state['backtest_total_return'] = total_ret

            disp_final, cs = convert_display(final_val, display_usd, fx_rate)
            disp_inv, _ = convert_display(total_inv, display_usd, fx_rate)
            gain = final_val - total_inv
            disp_gain, _ = convert_display(gain, display_usd, fx_rate)

            m1, m2, m3, m4 = st.columns(4)
            m1.metric(tr("Final Value"), f"{cs}{disp_final:,.0f}")
            m2.metric(tr("Total Invested"), f"{cs}{disp_inv:,.0f}")
            m3.metric(tr("Total Return"), f"{total_ret:.1f}%")
            m4.metric(
                "CAGR",
                f"{cagr_bt:.1%}",
                help="This is the actual annualized return of your portfolio over the backtest period, "
                     "calculated in TWD. USD-denominated assets are converted using historical exchange rates, "
                     "so currency fluctuations are included. This may differ from the Weighted CAGR shown "
                     "in Risk Allocation, which uses each asset's native-currency historical average."
            )
            st.caption(
                tr(
                    f"Cost scenario reference: if trading, tax, and FX-related costs are estimated at "
                    f"0.5% / 1.0% per year, reference CAGR would be approximately "
                    f"{format_cost_cagr_reference(cagr_bt)}.",
                    f"成本情境參考：若交易、稅務與換匯等成本以年化 0.5% / 1.0% 估算，"
                    f"參考 CAGR 約為 {format_cost_cagr_reference(cagr_bt)}。",
                )
            )
            st.caption(cost_scope_note())

            # ── Top-5 drawdown episodes (shared by both charts + table below) ───
            dd_events_df = identify_drawdown_events(
                result_df['date'], result_df['portfolio_value'], top_n=5
            )

            def _add_drawdown_shading(fig, events_df):
                """Overlay semi-transparent shading for each Top-N drawdown episode."""
                for _, ev in events_df.iterrows():
                    x0 = pd.Timestamp(ev['peak_date'])
                    x1 = pd.Timestamp(
                        ev['recovery_date']
                        if pd.notna(ev['recovery_date'])
                        else result_df['date'].iloc[-1]
                    )
                    fig.add_vrect(
                        x0=x0, x1=x1,
                        fillcolor="rgba(244, 67, 54, 0.10)",
                        line_width=0,
                        layer="below",
                        annotation_text=f"#{int(ev['rank'])}",
                        annotation_position="top left",
                        annotation_font_size=11,
                        annotation_font_color="#b71c1c",
                    )

            st.subheader(tr("Portfolio Value Over Time"))
            line_fig = go.Figure()
            chart_divisor = fx_rate if display_usd else 1.0
            chart_cs = "$" if display_usd else "NT$"
            line_fig.add_trace(go.Scatter(
                x=result_df['date'], y=result_df['portfolio_value'] / chart_divisor,
                mode='lines', name=tr('Portfolio Value'),
                line=dict(color='#2196F3', width=2)
            ))
            line_fig.add_trace(go.Scatter(
                x=result_df['date'], y=result_df['total_invested'] / chart_divisor,
                mode='lines', name=tr('Total Invested'),
                line=dict(color='#9E9E9E', width=1.5, dash='dash')
            ))
            if not dd_events_df.empty:
                _add_drawdown_shading(line_fig, dd_events_df)
            line_fig.update_layout(
                height=320, margin=dict(t=20, b=20, l=20, r=20),
                yaxis_title=tr(f"Value ({chart_cs})", f"價值 ({chart_cs})"),
                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                legend=dict(orientation="h", yanchor="bottom", y=1.02)
            )
            st.plotly_chart(line_fig, use_container_width=True)
            total_gain = final_val - total_inv
            insight1 = tr(
                (
                f"Starting with {cs}{disp_inv:,.0f}, "
                f"your portfolio would have grown to {cs}{disp_final:,.0f} — "
                f"a gain of {cs}{disp_gain:,.0f} "
                f"({total_ret:.1f}%) over the period, equivalent to a {cagr_bt:.1%} annualized return."
                ),
                f"從 {cs}{disp_inv:,.0f} 開始，你的投資組合會成長到 {cs}{disp_final:,.0f}，"
                f"期間增加 {cs}{disp_gain:,.0f}（{total_ret:.1f}%），約等於 {cagr_bt:.1%} 的年化報酬率。"
            )
            st.markdown(
                f'<div style="background-color:#e8f4f8; padding:12px 16px; border-radius:8px; '
                f'border-left:4px solid #1f77b4; font-size:14px; color:#1a1a1a;">{insight1}</div>',
                unsafe_allow_html=True
            )

            st.subheader(tr("Max Drawdown Over Time (Pain Index)"))
            rolling_max = result_df['portfolio_value'].cummax()
            drawdown = (result_df['portfolio_value'] - rolling_max) / rolling_max * 100
            dd_fig = go.Figure()
            dd_fig.add_trace(go.Scatter(
                x=result_df['date'], y=drawdown,
                mode='lines', name=tr('Drawdown'),
                fill='tozeroy',
                line=dict(color='#F44336', width=1.5)
            ))
            if not dd_events_df.empty:
                _add_drawdown_shading(dd_fig, dd_events_df)
            dd_fig.update_layout(
                height=260, margin=dict(t=20, b=20, l=20, r=20),
                yaxis_title=tr("Drawdown (%)"),
                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(dd_fig, use_container_width=True)
            max_dd_val = float(drawdown.min())
            st.session_state['backtest_max_drawdown'] = max_dd_val / 100.0
            insight2 = tr(
                f"The worst drawdown during this period was {max_dd_val:.1f}%. This is the pain a buy-and-hold investor would have had to endure without selling — the key behavioral challenge of passive investing.",
                f"這段期間最嚴重的回撤為 {max_dd_val:.1f}%。這就是買進持有投資人必須承受且不能賣出的痛苦，也是被動投資最大的行為挑戰。"
            )
            st.markdown(
                f'<div style="background-color:#fdf0f0; padding:12px 16px; border-radius:8px; '
                f'border-left:4px solid #F44336; font-size:14px; color:#1a1a1a;">{insight2}</div>',
                unsafe_allow_html=True
            )

            # ── Top-5 drawdowns table (collapsible) ───────────────────────────
            if not dd_events_df.empty:
                with st.expander("📉 " + tr("View Top 5 Drawdown Episodes")):
                    st.caption(
                        "The five most severe independent drawdowns during this backtest, "
                        "ranked by depth. Shaded bands on the charts above correspond to "
                        "these periods (labelled #1–#5). Historical context is matched from "
                        "a curated list of notable market events."
                    )
                    dd_table = dd_events_df.copy()
                    dd_table['Rank'] = dd_table['rank'].astype(int)
                    dd_table['Peak'] = pd.to_datetime(dd_table['peak_date']).dt.strftime('%Y-%m-%d')
                    dd_table['Trough'] = pd.to_datetime(dd_table['trough_date']).dt.strftime('%Y-%m-%d')
                    dd_table['Recovery'] = dd_table['recovery_date'].apply(
                        lambda d: pd.to_datetime(d).strftime('%Y-%m-%d') if pd.notna(d) else tr('Ongoing')
                    )
                    dd_table['Drawdown'] = (dd_table['drawdown_pct'] * 100).round(2).astype(str) + '%'

                    def _fmt_days(n):
                        if pd.isna(n):
                            return '—'
                        n = int(n)
                        if n >= 30:
                            months = n / 30.44
                            return f"{n}d ({months:.1f}mo)"
                        return f"{n}d"
                    dd_table['Fall Time'] = dd_table['duration_days'].apply(_fmt_days)
                    dd_table['Recovery Time'] = dd_table['recovery_days'].apply(
                        lambda n: _fmt_days(n) if pd.notna(n) else tr('Ongoing')
                    )
                    dd_table['Historical Context'] = dd_table['event_label']

                    display_cols = ['Rank', 'Peak', 'Trough', 'Recovery',
                                    'Drawdown', 'Fall Time', 'Recovery Time', 'Historical Context']
                    dd_display = dd_table[display_cols].copy()
                    dd_display.columns = [tr(c) for c in display_cols]
                    st.dataframe(
                        dd_display,
                        width="stretch",
                        hide_index=True,
                    )

            st.subheader(tr("Annual Returns"))
            result_df['year'] = pd.to_datetime(result_df['date']).dt.year
            annual = result_df.groupby('year').apply(
                lambda x: (x['portfolio_value'].iloc[-1] / x['portfolio_value'].iloc[0] - 1) * 100
                if x['portfolio_value'].iloc[0] > 0 else float('nan'), include_groups=False
            ).reset_index(name='annual_return')
            annual = annual[annual['annual_return'].notna() & ~annual['annual_return'].isin([float('inf'), float('-inf')])]
            colors_annual = ['#F44336' if r < 0 else '#4CAF50' for r in annual['annual_return']]
            bar_fig = go.Figure()
            bar_fig.add_trace(go.Bar(
                x=annual['year'], y=annual['annual_return'],
                marker_color=colors_annual,
                text=[f"{r:.1f}%" for r in annual['annual_return']],
                textposition='outside'
            ))
            bar_fig.update_layout(
                height=280, margin=dict(t=20, b=20, l=20, r=20),
                yaxis_title=tr("Return (%)"),
                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(bar_fig, use_container_width=True)
            neg_years = (annual['annual_return'] < 0).sum()
            best_year = annual.loc[annual['annual_return'].idxmax()]
            worst_year_row = annual.loc[annual['annual_return'].idxmin()]
            insight3 = tr(
                f"Out of {len(annual)} years, {neg_years} year(s) were negative. Best year: {int(best_year['year'])} (+{best_year['annual_return']:.1f}%). Worst year: {int(worst_year_row['year'])} ({worst_year_row['annual_return']:.1f}%).",
                f"在 {len(annual)} 年中，有 {neg_years} 年為負報酬。最佳年度：{int(best_year['year'])}（+{best_year['annual_return']:.1f}%）。最差年度：{int(worst_year_row['year'])}（{worst_year_row['annual_return']:.1f}%）。"
            )
            st.markdown(
                f'<div style="background-color:#f0f7f0; padding:12px 16px; border-radius:8px; '
                f'border-left:4px solid #4CAF50; font-size:14px; color:#1a1a1a;">{insight3}</div>',
                unsafe_allow_html=True
            )

        except Exception as e:
            st.error(tr(f"Backtest failed: {e}", f"回測失敗：{e}"))

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — FIRE CALCULATOR
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("<div id='fire-calculator' style='padding-top: 70px; margin-top: -70px; pointer-events: none;'></div>", unsafe_allow_html=True)
st.title(tr("FIRE Calculator"))
st.caption(tr("Based on your allocation's historical CAGR, estimate when you can reach financial independence."))

if not st.session_state.get('portfolio_confirmed', False):
    st.info("ℹ️ " + tr("Confirm your portfolio in **Correlation Analysis** above to unlock this section."))
    st.divider()
    # Render Summary section's locked stub then halt; avoids leaving the page with
    # an unrendered FIRE body and a missing Summary anchor in the sidebar.
    st.markdown("<div id='summary' style='padding-top: 70px; margin-top: -70px; pointer-events: none;'></div>",
                unsafe_allow_html=True)
    st.title(tr("Summary"))
    st.info("ℹ️ " + tr("Confirm your portfolio in **Correlation Analysis** above to unlock this section."))
    st.stop()

portfolio_cagr = st.session_state.get('backtest_cagr', st.session_state.get('allocation_cagr', None))
bt_params = st.session_state.get('bt_params', {})
risk_from_allocation = st.session_state.get('risk_pref', 'Medium')

if st.session_state.get('backtest_cagr') is not None:
    st.success(tr(f"Using backtest CAGR: **{portfolio_cagr:.2%}** (from your Backtest results)",
                  f"使用回測 CAGR：**{portfolio_cagr:.2%}**（來自你的回測結果）"))
elif portfolio_cagr:
    st.success(tr(f"Using portfolio weighted CAGR: **{portfolio_cagr:.2%}** (from your Risk Allocation)",
                  f"使用投資組合加權 CAGR：**{portfolio_cagr:.2%}**（來自風險配置）"))

# ── Advanced Settings ──────────────────────────────────────────────────────────
# The FIRE target is now DERIVED from (Annual Expenses ÷ Withdrawal Rate) rather
# than being a directly-entered number. This aligns with the canonical FIRE /
# Trinity-Study framing and lets the demo-preset personas describe retirement
# in lifestyle terms ("NT$ 800k/yr at 3.5% withdrawal") instead of opaque
# targets. Downstream code (Summary section, calculate_fire call site below)
# reads st.session_state['fire_target'], which we populate with the computed
# value so no other callers need to know about expenses/rate.
currency_symbol_fire = "NT$"
annual_expenses = 1200000          # NT$ 1.2M/yr ⇒ implies NT$ 30M target at 4%
withdrawal_rate = 0.04
target_amount = int(annual_expenses / withdrawal_rate)
initial_capital = int(bt_params.get('initial', 300000))
monthly_contribution = int(bt_params.get('monthly', 15000))
risk_level_fire = risk_from_allocation if risk_from_allocation in ["Low", "Medium", "High", "Extreme High"] else "Medium"
inflation_rate = float(round(default_inflation, 3))
inflation_rate_pct = round(default_inflation * 100, 2)

with st.expander("⚙️ " + tr("Advanced Settings"), expanded=False):
    st.markdown(tr("Adjust the parameters below. Risk Level is carried over from your Risk Allocation."))

    # Row 1 — FIRE math: Annual Expenses ÷ Withdrawal Rate = Implied Target
    fire_r1c1, fire_r1c2, fire_r1c3 = st.columns(3)
    with fire_r1c1:
        annual_expenses = st.number_input(
            tr("Annual Expenses (NT$)"),
            min_value=100000, max_value=50000000,
            value=st.session_state.get('fire_annual_expenses', 1200000), step=10000, key="fire_annual_expenses",
            help="How much you expect to spend per year in retirement (in TWD). "
                 "Drives the implied FIRE target via the withdrawal rate."
        )
    with fire_r1c2:
        withdrawal_rate_pct = st.number_input(
            tr("Withdrawal Rate (%)"),
            min_value=1.0, max_value=10.0,
            value=4.0, step=0.1, key="fire_withdrawal_rate",
            help="The fraction of the portfolio withdrawn in year 1. "
                 "See \"About the 4% Rule\" below for guidance."
        )
        withdrawal_rate = withdrawal_rate_pct / 100
    with fire_r1c3:
        target_amount = int(annual_expenses / withdrawal_rate) if withdrawal_rate > 0 else 0
        st.markdown(f"**{tr('Implied FIRE Target')}**")
        st.markdown(f"NT$ {target_amount:,.0f}")
        st.caption(tr("= Expenses ÷ Withdrawal Rate"))

    # Keep downstream readers (Summary section, etc.) working without having to
    # know about the new expenses/rate inputs. The old fire_target widget key is
    # gone, so writing this session_state key directly is safe (no widget conflict).
    st.session_state['fire_target'] = target_amount

    # Row 2 — capital + contribution + inflation
    fire_r2c1, fire_r2c2, fire_r2c3 = st.columns(3)
    with fire_r2c1:
        initial_capital = st.number_input(
            tr("Current Savings (NT$)"),
            min_value=0, value=int(bt_params.get('initial', 300000)),
            step=10000, key="fire_capital"
        )
        st.caption(tr("Carried over from Backtest & Pain Index", "沿用回測與痛苦指數的設定"))
    with fire_r2c2:
        monthly_contribution = st.number_input(
            tr("Monthly Contribution (NT$)"),
            min_value=0, value=int(bt_params.get('monthly', 15000)),
            step=1000, key="fire_monthly"
        )
        st.caption(tr("Carried over from Backtest & Pain Index", "沿用回測與痛苦指數的設定"))
    with fire_r2c3:
        inflation_rate_pct = st.number_input(
            tr("Annual Inflation Rate (%)"),
            min_value=0.0, max_value=10.0,
            value=round(default_inflation * 100, 2),
            step=0.1, key="fire_inflation",
            help=f"Latest US CPI YoY: {default_inflation:.2%} (auto-fetched from FRED). You can override this value."
        )
        inflation_rate = inflation_rate_pct / 100
        st.caption(tr(f"Current US CPI YoY: {default_inflation:.2%}", f"目前美國 CPI 年增率：{default_inflation:.2%}"))

    # Row 3 — read-only Risk Level + Currency
    fire_r3c1, fire_r3c2 = st.columns(2)
    with fire_r3c1:
        st.markdown(f"**{tr('Risk Level')}**")
        st.markdown(f"{risk_label(risk_level_fire)}")
        st.caption(tr("Carried over from Risk Allocation", "沿用風險配置的設定"))
    with fire_r3c2:
        st.markdown(f"**{tr('Currency')}**")
        st.markdown("NT$ (TWD)")
        st.caption(tr("All calculations in New Taiwan Dollar"))

# ── Educational note: 4% Rule / Trinity Study ─────────────────────────────────
# Kept as a sibling expander (NOT nested inside Advanced Settings) because
# Streamlit disallows nested expanders. Sitting right below the parameter
# block, it's still in plain sight for users wondering where the 4% comes from.
with st.expander("📖 " + tr("About the 4% Rule (Trinity Study)")):
    st.markdown(tr("""
The default **4% withdrawal rate** comes from the **Trinity Study**
(Cooley, Hubbard & Walz, 1998), which backtested US equity + bond
portfolios from 1926–1995. Withdrawing 4% of the initial balance in
year 1 (adjusted for inflation thereafter) had roughly a **95% success
rate** of lasting a full 30-year retirement without running out.

The shortcut form is the **Rule of 25**:

> **FIRE target ≈ 25 × annual expenses**

**How to adjust the rate to your situation:**
- **3.0 – 3.5%** — more conservative, suitable for 40+ year
  retirement horizons, lower expected returns, or higher risk aversion.
- **4.0%** — the classic baseline for a 30-year retirement.
- **4.5 – 5.0%** — more aggressive, suitable if you have other income
  sources (part-time work, rental income, social security) that reduce
  how much you need to pull from the portfolio.

_Reference: Cooley, P., Hubbard, C., & Walz, D. (1998).
"Retirement Savings: Choosing a Withdrawal Rate That Is Sustainable."
AAII Journal._
""", """
預設的 **4% 提領率** 來自 **Trinity Study**
（Cooley, Hubbard & Walz, 1998）。該研究回測 1926–1995 年間的美國股票與債券投資組合，若退休第 1 年提領初始資產的 4%，之後每年依通膨調整，約有 **95% 成功率** 能支撐完整 30 年退休期間而不耗盡資產。

簡化版就是 **25 倍法則**：

> **FIRE 目標 ≈ 年度支出 × 25**

**如何依自身情況調整提領率：**
- **3.0 – 3.5%** — 較保守，適合 40 年以上退休期間、較低預期報酬或較高風險趨避者。
- **4.0%** — 30 年退休期間的經典基準。
- **4.5 – 5.0%** — 較積極，適合有其他收入來源（兼職、租金、社會保險等）可降低投資組合提領壓力的人。

_參考：Cooley, P., Hubbard, C., & Walz, D. (1998).
"Retirement Savings: Choosing a Withdrawal Rate That Is Sustainable."
AAII Journal._
"""))

# ── Auto-run FIRE calculation ──────────────────────────────────────────────────
with st.spinner(tr("Calculating FIRE projection...")):
    try:
        result = calculate_fire(
            target_amount=target_amount,
            monthly_contribution=monthly_contribution,
            initial_capital=initial_capital,
            weights=st.session_state.get('allocation', {}),
            max_years=50
        )
        projection_df = result['projection'].copy()
        annual_cagr = result['annual_cagr']
        years_to_fire = result['years_to_fire']

        projection_df['real_value'] = projection_df.apply(
            lambda row: row['portfolio_value'] / ((1 + inflation_rate) ** row['year']), axis=1
        )
        real_fire_year = next(
            (int(row['year']) for _, row in projection_df.iterrows() if row['real_value'] >= target_amount),
            None
        )
        st.session_state['fire_years_real'] = real_fire_year
        st.session_state['fire_result_cache'] = result

        display_usd = st.session_state.get('display_usd', False)
        fx_rate = st.session_state.get('live_twd_usd', 32.0)
        fire_cs = "$" if display_usd else "NT$"
        fire_divisor = fx_rate if display_usd else 1.0

        display_cagr = st.session_state.get('backtest_cagr', annual_cagr)
        f1, f2, f3, f4 = st.columns(4)
        f1.metric(tr("CAGR Used"), f"{display_cagr:.2%}")
        f2.metric(tr("Years to FIRE (Nominal)"), fmt_years(years_to_fire))
        f3.metric(tr("Years to FIRE (Real)"), fmt_years(real_fire_year))
        f4.metric(tr("Inflation Applied"), f"{inflation_rate:.1%}")
        fire_cost_rows = []
        for rate in COST_SCENARIO_RATES:
            adjusted_cagr = cost_adjusted_cagr(display_cagr, rate)
            nominal_year, real_year = estimate_fire_years_for_cagr(
                adjusted_cagr,
                current_savings=initial_capital,
                monthly_contribution=monthly_contribution,
                target_amount=target_amount,
                inflation_rate=inflation_rate,
            )
            fire_cost_rows.append(
                tr(
                    f"{rate * 100:.1f}% scenario: CAGR {adjusted_cagr:.2%}, "
                    f"nominal {fmt_years(nominal_year)}, real {fmt_years(real_year)}",
                    f"{rate * 100:.1f}% 情境：CAGR {adjusted_cagr:.2%}，"
                    f"名目 {fmt_years(nominal_year)}，實質 {fmt_years(real_year)}",
                )
            )
        st.caption(
            tr(
                "Cost scenario reference: " + " / ".join(fire_cost_rows),
                "成本情境參考：" + " / ".join(fire_cost_rows),
            )
        )
        st.caption(cost_scope_note())

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=projection_df['year'], y=projection_df['portfolio_value'] / fire_divisor,
            mode='lines', name=tr('Nominal Value'),
            line=dict(color='#2196F3', width=2)
        ))
        fig.add_trace(go.Scatter(
            x=projection_df['year'], y=projection_df['real_value'] / fire_divisor,
            mode='lines', name=tr('Real Value (Inflation-Adjusted)'),
            line=dict(color='#FF9800', width=2, dash='dot')
        ))
        disp_target = target_amount / fire_divisor
        fig.add_hline(
            y=disp_target, line_dash="dash", line_color="#F44336",
            annotation_text=tr(f"Target: {fire_cs}{disp_target:,.0f}", f"目標：{fire_cs}{disp_target:,.0f}"),
            annotation_position="top left"
        )
        if years_to_fire:
            fig.add_vline(
                x=years_to_fire, line_dash="dot", line_color="#4CAF50",
                annotation_text=tr(f"FIRE @ Year {years_to_fire}", f"FIRE @ 第 {years_to_fire} 年"),
                annotation_position="top right"
            )
        fig.update_layout(
            height=400, xaxis_title=tr("Years"),
            yaxis_title=tr(f"Value ({fire_cs})", f"價值 ({fire_cs})"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            margin=dict(t=40, b=40, l=40, r=40)
        )
        st.plotly_chart(fig, use_container_width=True)

        display_df = projection_df.copy()
        display_df['portfolio_value'] = display_df['portfolio_value'].apply(lambda x: f"{fire_cs}{x/fire_divisor:,.0f}")
        display_df['real_value'] = display_df['real_value'].apply(lambda x: f"{fire_cs}{x/fire_divisor:,.0f}")
        display_df.columns = [tr('Year', '年份'), tr('Nominal Value'), tr('Real Value (Inflation-Adjusted)')]
        st.dataframe(display_df, width="stretch", hide_index=True)

    except Exception as e:
        st.error(tr(f"Calculation failed: {e}", f"計算失敗：{e}"))

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 6 — SUMMARY
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("<div id='summary' style='padding-top: 70px; margin-top: -70px; pointer-events: none;'></div>", unsafe_allow_html=True)
st.title(tr("Summary"))
st.caption(tr("A snapshot of your portfolio based on the selections above."))
st.caption(tr("📌 Backtest returns are calculated using adjusted close prices, which reflect dividend distributions and stock splits. Dividend reinvestment is implicitly assumed.",
              "📌 回測報酬使用調整後收盤價計算，已反映股利分配與股票分割，並隱含假設股利再投入。"))

allocation = st.session_state.get('allocation', {})
risk_pref = st.session_state.get('risk_pref', None)
allocation_cagr = st.session_state.get('allocation_cagr', None)
backtest_cagr = st.session_state.get('backtest_cagr', None)
years_to_fire = st.session_state.get('fire_years', None)

if not allocation:
    st.info(tr("Complete the Risk Allocation section to see your portfolio summary."))
else:
    # ── Pull metrics for allocated assets ─────────────────────────────────────
    alloc_df_sum = metrics_df[metrics_df['ticker'].isin(allocation.keys())].copy()
    alloc_df_sum['weight'] = alloc_df_sum['ticker'].map(allocation)
    port_dd_sum = float(np.dot(alloc_df_sum['weight'].values, alloc_df_sum['max_drawdown'].values))
    port_vol_sum = float(np.dot(alloc_df_sum['weight'].values, alloc_df_sum['volatility'].values))
    display_cagr = backtest_cagr if backtest_cagr else allocation_cagr

    # ── FIRE years (reuse cached result from FIRE section when available) ────────
    fire_result = st.session_state.get('fire_result_cache') or calculate_fire(
        target_amount=st.session_state.get('fire_target', 30000000),
        monthly_contribution=st.session_state.get('fire_monthly', 15000),
        initial_capital=st.session_state.get('fire_capital', 300000),
        weights=allocation,
        max_years=50,
    )
    fire_years = fire_result.get('years_to_fire', None)

    # ── Dynamic insight generation ─────────────────────────────────────────────
    worst_dd_float = port_dd_sum  # e.g. -0.359
    worst_dd_str = f"{worst_dd_float:.1%}"
    loss_per_million = abs(worst_dd_float) * 100  # e.g. 35.9 (per NT$1M)
    worst_year_row = alloc_df_sum.loc[alloc_df_sum['max_drawdown'].idxmin()]
    worst_asset = worst_year_row['ticker']

    # Map drawdown severity to historical event
    if abs(worst_dd_float) >= 0.50:
        historical_ref = "a loss comparable to the 2008 Global Financial Crisis, when the S&P 500 took over 4 years to fully recover"
    elif abs(worst_dd_float) >= 0.30:
        historical_ref = "a loss in the range of the 2020 COVID crash or the 2022 rate-hike selloff, both of which saw sharp drops within months"
    else:
        historical_ref = "a moderate drawdown — smaller than major crashes, but still a meaningful test of investor patience"

    # Insight 1: allocation structure
    category_weights = {}
    for t, w in allocation.items():
        row = alloc_df_sum[alloc_df_sum['ticker'] == t]
        if not row.empty:
            cat = row.iloc[0]['category']
            category_weights[cat] = category_weights.get(cat, 0) + w
    dominant_cat = max(category_weights, key=category_weights.get)
    dominant_pct = category_weights[dominant_cat] * 100
    top_holding = sorted(allocation.items(), key=lambda x: -x[1])[0]
    if st.session_state.get('lang') == "zh-TW":
        cat_descriptions = {
            'TW_ETF': f"台股 ETF 佔投資組合 <strong>{dominant_pct:.0f}%</strong>，是目前最大類別。這帶來台灣股票市場的高度曝險，歷史報酬具吸引力，但也集中於單一市場並帶有地緣政治風險。",
            'US_ETF': f"美股 ETF 佔投資組合 <strong>{dominant_pct:.0f}%</strong>，由 <strong>{top_holding[0]}</strong>（{top_holding[1]*100:.1f}%）作為核心。這是廣泛分散且經過長期驗證的被動投資方式。",
            'DEFENSIVE': f"防禦型資產（債券與商品）佔 <strong>{dominant_pct:.0f}%</strong>。這會大幅降低波動，但也可能限制長期成長，較適合重視穩定性的投資人。",
            'CRYPTO': f"加密貨幣佔投資組合 <strong>{dominant_pct:.0f}%</strong>。雖然歷史報酬高，但波動極端，可能壓過其他資產帶來的穩定效果。",
        }
        insight1 = "📊 <strong>投資組合結構：</strong> " + cat_descriptions.get(dominant_cat, f"你最大的類別是 {dominant_cat}，佔 {dominant_pct:.0f}%。")
    else:
        cat_descriptions = {
            'TW_ETF': f"Taiwan ETFs dominate at <strong>{dominant_pct:.0f}%</strong> of your portfolio. This gives you strong exposure to Taiwan's equity market — high historical returns, but concentrated in a single market with geopolitical risk.",
            'US_ETF': f"US ETFs make up <strong>{dominant_pct:.0f}%</strong> of your portfolio, anchored by <strong>{top_holding[0]}</strong> ({top_holding[1]*100:.1f}%). This is a broadly diversified, globally proven approach — the core of most passive strategies.",
            'DEFENSIVE': f"Defensive assets (bonds and commodities) dominate at <strong>{dominant_pct:.0f}%</strong>. This heavily dampens volatility but also caps long-term growth — suitable for investors prioritizing stability over accumulation speed.",
            'CRYPTO': f"Crypto assets represent <strong>{dominant_pct:.0f}%</strong> of your allocation. While historically high-returning, crypto introduces extreme volatility that can overwhelm the stability of other holdings.",
        }
        insight1 = "📊 <strong>Portfolio Structure:</strong> " + cat_descriptions.get(dominant_cat, f"Your largest category is {dominant_cat} at {dominant_pct:.0f}%.")

    # Insight 2: drawdown contextualized
    if st.session_state.get('lang') == "zh-TW":
        insight2 = (
            f"📉 <strong>回撤真正代表什麼：</strong> "
            f"最大回撤 <strong>{worst_dd_str}</strong> 代表若投資組合為 NT$1,000,000，"
            f"你會看到帳面上約 NT${loss_per_million*10000:,.0f} 蒸發。"
            f"組合中受傷最深的位置是 <strong>{worst_asset}</strong>。"
            f"問題不只是你能否在數學上接受，而是當它真實發生時，你能否不賣出。"
        )
    else:
        insight2 = (
            f"📉 <strong>What the Drawdown Really Means:</strong> "
            f"A max drawdown of <strong>{worst_dd_str}</strong> means on a NT$1,000,000 portfolio, "
            f"you would have watched NT${loss_per_million*10000:,.0f} disappear on paper — {historical_ref}. "
            f"The hardest-hit position in your mix is <strong>{worst_asset}</strong>. "
            f"The question is not whether you can accept this mathematically — it's whether you can hold without selling when it's happening in real time."
        )

    # Insight 3: behavioral or FIRE based on risk
    if risk_pref in ["Low", "Medium"]:
        if fire_years:
            years_context = "ahead of schedule" if fire_years < 25 else "a long runway that rewards consistency over urgency"
            insight3 = tr(
                (
                    f"🎯 <strong>FIRE Reality Check:</strong> "
                    f"At this allocation's historical return rate, your target is <strong>{fire_years} years</strong> away — {years_context}. "
                    f"The compounding math works in your favor as long as you stay invested and keep contributing. "
                    f"Missing just 10 of the best market days in a decade can cut your returns in half — passive means passive."
                ),
                f"🎯 <strong>FIRE 現實檢查：</strong> 依此配置的歷史報酬率，你距離目標約 <strong>{fire_years} 年</strong>。只要持續投入並留在市場中，複利會站在你這邊。被動投資的重點就是足夠被動，不因短期波動退出。"
            )
        else:
            insight3 = tr(
                (
                    f"🎯 <strong>FIRE Reality Check:</strong> "
                    f"At this allocation's return rate, your FIRE target may take more than 50 years. "
                    f"Consider whether increasing your monthly contribution or accepting slightly more risk could meaningfully shorten that timeline."
                ),
                "🎯 <strong>FIRE 現實檢查：</strong> 依此配置的報酬率，你可能需要超過 50 年才能達成 FIRE。可以評估提高每月投入，或接受稍高風險，是否能明顯縮短時間。"
            )
    else:
        insight3 = tr(
            (
                f"⚠️ <strong>The Behavior Gap:</strong> "
                f"Studies consistently show that most retail investors earn significantly less than the funds they invest in — "
                f"because they buy high and sell low. With a portfolio capable of dropping <strong>{worst_dd_str}</strong>, "
                f"the biggest risk is not market volatility itself, but your own reaction to it. "
                f"High-risk passive investing only works if 'passive' is absolute — no panic selling, no market timing, no exceptions."
            ),
            f"⚠️ <strong>行為落差：</strong> 研究一再顯示，多數散戶實際賺到的報酬低於他們投資的基金，原因常是追高殺低。當投資組合可能下跌 <strong>{worst_dd_str}</strong> 時，最大的風險不是市場波動本身，而是你面對波動時的反應。高風險被動投資只有在你真的不恐慌賣出、不擇時、不破例時才有效。"
        )

    combined = f"""
    <div style="padding:20px 24px; border-radius:10px; background:#f8f9fa; border-left:4px solid #6B9E9F;">
      <p style="font-size:16px; color:#1a1a1a; margin-bottom:18px; line-height:1.7;">{insight1}</p>
      <p style="font-size:16px; color:#1a1a1a; margin-bottom:18px; line-height:1.7;">{insight2}</p>
      <p style="font-size:16px; color:#1a1a1a; margin:0; line-height:1.7;">{insight3}</p>
    </div>
    """
    st.markdown(combined, unsafe_allow_html=True)

    # ── AI Insights ───────────────────────────────────────────────────────────────
    from dotenv import load_dotenv
    load_dotenv(override=True)  # Force reload to pick up key if added while app is running
    gemini_key = os.getenv("GEMINI_API_KEY")
    
    if gemini_key and st.session_state.get('allocation'):
        # Dynamic configuration is handled by initializing genai.Client inside get_gemini_insights
        if st.session_state.get('backtest_cagr') is not None:
            allocation_tuple = tuple(sorted(st.session_state['allocation'].items()))
            watchlist_tuple = tuple(sorted(st.session_state.get('watchlist', [])))
            fire_years_val = st.session_state.get('fire_years_real', 0)
            fire_target_val = st.session_state.get('fire_target', 0)
            max_dd_val = st.session_state.get('backtest_max_drawdown', 0)
            total_ret_val = st.session_state.get('backtest_total_return', 0)
            risk_val = st.session_state.get('risk_pref', 'Medium')

            with st.spinner(tr("Generating AI insights...")):
                # Strip HTML tags from existing summaries for cleaner AI prompt
                import re
                clean_summaries = [re.sub('<[^<]+?>', '', s) for s in [insight1, insight2, insight3]]
                
                # Fetch parameters from bt_params dict
                bt_p = st.session_state.get('bt_params', {})
                
                insight_text = get_gemini_insights(
                    watchlist=watchlist_tuple,
                    allocation=allocation_tuple,
                    cagr_bt=st.session_state['backtest_cagr'],
                    max_drawdown=max_dd_val,
                    total_return=total_ret_val,
                    fire_years=fire_years_val if fire_years_val is not None else 0,
                    fire_target=fire_target_val,
                    risk_level=risk_val,
                    initial_cap=bt_p.get('initial', 0),
                    monthly_cont=bt_p.get('monthly', 0),
                    annual_exp=st.session_state.get('fire_annual_expenses', 0),
                    existing_summaries=clean_summaries
                )

            if insight_text:
                st.markdown(f"#### ✨ {tr('AI Insights')}")
                st.caption(tr("Strategic review generated by Gemini 2.5 Flash"))
                
                # Escape $ to prevent LaTeX parsing issues in Streamlit markdown
                safe_text = insight_text.replace("$", r"\$")
                
                with st.container(border=True):
                    st.markdown(
                        '<div style="border-left: 5px solid #008080; padding-left: 16px; margin-bottom: 4px;">'
                        '<strong>🚀 Strategic Next Steps</strong></div>',
                        unsafe_allow_html=True
                    )
                    # Strip the header line from insight_text if the model includes it
                    body = safe_text.replace("🚀 **Strategic Next Steps**", "").strip()
                    st.markdown(body)
        else:
            st.caption("✨ " + tr("AI Insights will be available once the backtest calculation is complete."))

    # ── Methodology caveat: fat tails (only for crypto-heavy / high-risk portfolios) ──
    crypto_weight = category_weights.get('CRYPTO', 0)
    if crypto_weight >= 0.10 or risk_pref in ["High", "Extreme High"]:
        st.markdown(
            """
            <div style="padding:12px 18px; margin-top:14px; border-radius:8px;
                        background:#fff8e1; border-left:4px solid #f9a825;
                        font-size:13px; color:#5d4e00; line-height:1.6;">
              ⚠️ <strong>A note on risk metrics.</strong>
              Volatility-based measures (Sharpe ratio, annualized stdev) assume daily returns follow a normal distribution.
              Real markets &mdash; especially crypto &mdash; have "fat tails":
              extreme drops happen far more often than the model predicts. Treat the Sharpe ratios
              and volatility figures above as a <em>lower bound</em> on tail risk, not a ceiling.
            </div>
            """,
            unsafe_allow_html=True
        )



st.divider()

# ── Currency Toggle ────────────────────────────────────────────────────────────
if 'display_usd' not in st.session_state:
    st.session_state['display_usd'] = False

btn_label = f"🇺🇸 {tr('Switch to USD')}" if not st.session_state['display_usd'] else f"🇹🇼 {tr('Switch to TWD')}"
if st.button(btn_label, type="secondary", key="currency_toggle"):
    st.session_state['display_usd'] = not st.session_state['display_usd']
    if st.session_state['display_usd']:
        try:
            url = 'https://query1.finance.yahoo.com/v8/finance/chart/TWD=X?interval=1d&range=5d'
            r = requests.get(url, headers=YAHOO_HEADERS, timeout=10)
            data = r.json()
            closes = data['chart']['result'][0]['indicators']['quote'][0]['close']
            closes = [x for x in closes if x is not None]
            st.session_state['live_twd_usd'] = closes[-1]
        except Exception:
            st.session_state['live_twd_usd'] = 32.0
    st.rerun()

if st.session_state['display_usd']:
    rate = st.session_state.get('live_twd_usd', 32.0)
    st.caption(tr(
        f"Currently displaying in USD. Exchange rate: 1 USD = NT${rate:.2f} (live rate). Input fields remain in TWD.",
        f"目前以 USD 顯示。匯率：1 USD = NT${rate:.2f}（即時匯率）。輸入欄位仍維持 TWD。"
    ))
else:
    st.caption(tr("Currently displaying in TWD. Input fields remain in TWD regardless of display currency."))
