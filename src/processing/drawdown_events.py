"""
Drawdown event analysis: identify the Top-N independent drawdown episodes from a
portfolio value series, and attach a human-readable historical-event label to each.

A drawdown "episode" is defined as a contiguous stretch during which the portfolio
trades below its prior all-time high. An episode begins on the day after a peak is
broken, reaches its trough on the day of the maximum percentage decline, and ends
on the day the portfolio first recovers to (or above) the peak. Episodes that are
still underwater at the end of the series are reported with recovery_date=None.

Events are sorted by depth (most severe first) and the top N are returned.

Historical context labels are attached via MARKET_EVENTS — a curated list of notable
macro / crypto events. Any event whose date range overlaps an episode's peak-to-recovery
window is attached to that episode. Labels are purely editorial; a missing label just
means no curated event matched (the episode is still a real drawdown).
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

import numpy as np
import pandas as pd

# ────────────────────────────────────────────────────────────────────────────────
# Curated market-event lookup. Each entry:
#   (start_date, end_date, label, short_tag)
#
# - Cover both equity and crypto-relevant events so the labelling works across all
#   portfolio compositions supported by the dashboard.
# - Date ranges are loose on purpose: they capture the period during which the event
#   was the dominant market narrative, not just the exact peak-to-trough window.
# - "label" is the sentence users see; "short_tag" is reserved for chart annotations
#   where horizontal space is tight.
# ────────────────────────────────────────────────────────────────────────────────
MARKET_EVENTS: List[tuple] = [
    # --- Equity / macro ---
    ("2007-10-01", "2009-06-30", "Global Financial Crisis (subprime / Lehman)", "GFC"),
    ("2010-04-15", "2010-07-31", "Flash Crash & early Greek debt crisis", "EU-Debt-I"),
    ("2011-07-01", "2011-10-31", "US credit downgrade & eurozone debt crisis", "EU-Debt-II"),
    ("2015-08-01", "2016-02-29", "China slowdown & oil price collapse", "China-Oil"),
    ("2018-01-22", "2018-04-10", "Volmageddon & early Trump tariffs", "Volmageddon"),
    ("2018-10-01", "2018-12-31", "Q4 2018 Fed tightening & trade war escalation", "Q4-2018"),
    ("2020-02-15", "2020-04-30", "COVID-19 pandemic crash", "COVID"),
    ("2022-01-01", "2022-10-31", "Fed rate hikes & inflation shock (2022 bear)", "2022-Bear"),
    ("2023-03-08", "2023-04-15", "US regional banking crisis (SVB, Signature, First Republic)", "SVB"),
    ("2024-08-01", "2024-08-15", "Japan carry-trade unwind / August 2024 selloff", "Carry-Unwind"),
    ("2025-02-01", "2025-05-31", "Trump tariff shock & trade tensions", "2025-Tariffs"),
    ("2025-10-01", "2026-03-31", "AI bubble scare & SaaSpocalypse (tech-heavy selloff)", "AI-Scare"),

    # --- Crypto-specific ---
    ("2018-01-01", "2018-12-31", "Crypto winter (post-2017 peak)", "Crypto-Winter"),
    ("2021-05-01", "2021-07-31", "China crypto mining ban & May 2021 flash crash", "May-2021"),
    ("2022-05-01", "2022-12-31", "Terra/Luna collapse & FTX implosion", "Terra-FTX"),
]


def _to_ts(d: str | pd.Timestamp | datetime) -> pd.Timestamp:
    """Coerce to a timezone-naive Timestamp."""
    ts = pd.Timestamp(d)
    if ts.tzinfo is not None:
        ts = ts.tz_localize(None)
    return ts


def match_event_label(
    peak_date: pd.Timestamp,
    recovery_date: Optional[pd.Timestamp],
    trough_date: pd.Timestamp,
) -> str:
    """
    Return a '/' -joined label of all curated events whose date range overlaps the
    drawdown window [peak_date, recovery_date or trough_date]. Returns an em-dash if
    nothing matches.
    """
    peak = _to_ts(peak_date)
    # NOTE: when this function is called via DataFrame.apply, an original None
    # recovery_date has already been coerced to pd.NaT. Using `is not None`
    # alone lets NaT slip through, and _to_ts(NaT) stays NaT, which poisons
    # every subsequent `ev_start <= end` comparison (NaT comparisons are False),
    # making ongoing drawdowns never match any curated event. Treat NaT like
    # None and fall back to trough_date as the episode end.
    if recovery_date is None or pd.isna(recovery_date):
        end = _to_ts(trough_date)
    else:
        end = _to_ts(recovery_date)

    matches: List[str] = []
    for start_s, end_s, label, _tag in MARKET_EVENTS:
        ev_start = _to_ts(start_s)
        ev_end = _to_ts(end_s)
        if ev_start <= end and ev_end >= peak:
            matches.append(label)

    return " / ".join(matches) if matches else "—"


def identify_drawdown_events(
    dates: pd.Series | pd.DatetimeIndex,
    values: pd.Series | np.ndarray,
    top_n: int = 5,
    min_depth_pct: float = 0.02,
) -> pd.DataFrame:
    """
    Detect the Top-N most severe independent drawdown episodes from a portfolio
    value series.

    Parameters
    ----------
    dates : array-like of datetime
        Date index aligned with `values`. Must be sorted ascending.
    values : array-like of float
        Portfolio value on each date. Must be strictly positive.
    top_n : int
        Number of deepest episodes to return.
    min_depth_pct : float
        Minimum depth (as a positive fraction, e.g. 0.02 = 2%) for an episode to be
        reported. Filters out microscopic noise oscillations.

    Returns
    -------
    DataFrame with columns:
        rank, peak_date, trough_date, recovery_date, drawdown_pct,
        duration_days, recovery_days, event_label
        (recovery_date / recovery_days are None/NaN if the episode is still
        underwater at the end of the series.)
    """
    dates = pd.to_datetime(pd.Series(dates).reset_index(drop=True))
    values = pd.Series(values).reset_index(drop=True).astype(float)

    if len(dates) != len(values):
        raise ValueError("dates and values must have the same length.")
    if len(values) == 0:
        return _empty_drawdown_frame()

    # Running max up to each point: the prior peak we might still be underwater from.
    running_max = values.cummax()

    # Walk through the series and carve it into episodes.
    # peak_i: index of the peak that started the current episode (the last new high).
    # trough_i: index within the current episode where max drawdown occurred so far.
    # We open a new episode the first time values[i] < running_max[i].
    episodes = []
    in_episode = False
    peak_i = 0
    trough_i = 0

    for i in range(len(values)):
        # While still making new highs, just advance the "potential peak" pointer.
        if values.iloc[i] >= running_max.iloc[i]:
            if in_episode:
                # Current episode just recovered — close it.
                episodes.append(_finalize_episode(
                    dates=dates,
                    values=values,
                    peak_i=peak_i,
                    trough_i=trough_i,
                    recovery_i=i,
                ))
                in_episode = False
            # Update the candidate peak to the current bar.
            peak_i = i
            trough_i = i
            continue

        # values[i] < running_max[i]  — we are underwater relative to some prior peak.
        if not in_episode:
            # Episode starts: the prior peak was the last bar where running_max jumped,
            # which is simply the index where running_max equals its value at i-1.
            # Because running_max is non-decreasing, the last occurrence of that value
            # before i is the peak. Approximate by walking back from i-1 while
            # running_max is flat, which is cheap in practice.
            j = i - 1
            while j > 0 and running_max.iloc[j - 1] == running_max.iloc[j]:
                j -= 1
            peak_i = j
            trough_i = i
            in_episode = True
        else:
            # Deepen the trough if we've set a new low within this episode.
            if values.iloc[i] < values.iloc[trough_i]:
                trough_i = i

    # Tail case: series ended while still underwater.
    if in_episode:
        episodes.append(_finalize_episode(
            dates=dates,
            values=values,
            peak_i=peak_i,
            trough_i=trough_i,
            recovery_i=None,
        ))

    if not episodes:
        return _empty_drawdown_frame()

    df = pd.DataFrame(episodes)
    # Filter out trivial episodes.
    df = df[df["drawdown_pct"] <= -min_depth_pct].copy()
    if df.empty:
        return _empty_drawdown_frame()

    # Rank and take top N by depth (most negative first).
    df = df.sort_values("drawdown_pct", ascending=True).head(top_n).reset_index(drop=True)
    df.insert(0, "rank", range(1, len(df) + 1))

    # Attach historical event labels.
    df["event_label"] = df.apply(
        lambda r: match_event_label(r["peak_date"], r["recovery_date"], r["trough_date"]),
        axis=1,
    )

    return df


# ────────────────────────────────────────────────────────────────────────────────
# Internals
# ────────────────────────────────────────────────────────────────────────────────
def _finalize_episode(
    dates: pd.Series,
    values: pd.Series,
    peak_i: int,
    trough_i: int,
    recovery_i: Optional[int],
) -> dict:
    peak_val = float(values.iloc[peak_i])
    trough_val = float(values.iloc[trough_i])
    drawdown_pct = (trough_val / peak_val) - 1.0 if peak_val > 0 else 0.0
    peak_date = dates.iloc[peak_i]
    trough_date = dates.iloc[trough_i]
    recovery_date = dates.iloc[recovery_i] if recovery_i is not None else None

    duration_days = (trough_date - peak_date).days
    if recovery_date is not None:
        recovery_days = (recovery_date - trough_date).days
    else:
        recovery_days = None

    return {
        "peak_date": peak_date,
        "trough_date": trough_date,
        "recovery_date": recovery_date,
        "drawdown_pct": drawdown_pct,
        "duration_days": duration_days,
        "recovery_days": recovery_days,
    }


def _empty_drawdown_frame() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "rank",
            "peak_date",
            "trough_date",
            "recovery_date",
            "drawdown_pct",
            "duration_days",
            "recovery_days",
            "event_label",
        ]
    )


if __name__ == "__main__":
    # Quick smoke test with a synthetic series: up, crash, recover, crash harder, partially recover.
    idx = pd.date_range("2020-01-01", periods=400, freq="D")
    vals = np.concatenate([
        np.linspace(100, 150, 60),       # up
        np.linspace(150, 90, 40),        # -40% crash (the COVID crash)
        np.linspace(90, 160, 100),       # recover & make new highs
        np.linspace(160, 120, 50),       # -25% pullback
        np.linspace(120, 170, 80),       # recover & new highs
        np.linspace(170, 130, 70),       # -24% ongoing
    ])
    events = identify_drawdown_events(idx, vals, top_n=5)
    print(events.to_string(index=False))
