"""Relative-strength dashboard metrics + heat-map styling.

Reproduces the columns from the TradingView-style RS grid:
  RS Thrust %, 1-Mth RS %, a 1-month sparkline, % intraday / 1D / 1-month,
  and % off the 52-week high. RS is measured against a benchmark (SPY by default).

The two RS columns are *percentile ranks within the section* (0–100), matching how
the screenshot ranks members against each other:
  - 1-Mth RS  = rank of 1-month return relative to the benchmark
  - RS Thrust = rank of the 5-day relative-strength move (recent thrust)
These are approximations of the proprietary metric, but capture the same idea.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

DISPLAY_COLS = ["ticker", "name", "rs_thrust", "rs_1m", "spark",
                "pct_intraday", "pct_1d", "pct_1m", "pct_off_52w",
                "adr_pct", "mom", "vol_sma20",
                "close", "sma10", "sma20", "ema8", "ema21", "rsi", "atr_ext"]


def _v(row, col):
    return row[col] if col in row.index else np.nan


def _ret(arr: np.ndarray, n: int) -> float:
    return arr[-1] / arr[-1 - n] - 1 if len(arr) > n else np.nan


def compute_dashboard(hist: pd.DataFrame, bench_close: pd.Series,
                      names: dict | None = None, spark_n: int = 21) -> pd.DataFrame:
    names = names or {}
    b = bench_close.dropna().to_numpy() if bench_close is not None else np.array([])
    b1m, b5 = _ret(b, 21), _ret(b, 5)

    rows = []
    for tk, g in hist.sort_values("date").groupby("ticker"):
        g = g.dropna(subset=["close"])
        if len(g) < 2:
            continue
        c = g["close"].to_numpy()
        last = g.iloc[-1]
        r1m, r5 = _ret(c, 21), _ret(c, 5)
        rs1 = (1 + r1m) / (1 + b1m) - 1 if pd.notna(r1m) and pd.notna(b1m) else np.nan
        rs5 = (1 + r5) / (1 + b5) - 1 if pd.notna(r5) and pd.notna(b5) else np.nan
        hi52 = g["high"].tail(252).max()
        op = last["open"]
        ret_1d = last["ret_1d"] if "ret_1d" in g.columns else np.nan
        rows.append({
            "ticker": tk,
            "name": names.get(tk, ""),
            "_rs1": rs1, "_rs5": rs5,
            "spark": [float(x) for x in c[-spark_n:]],
            "pct_intraday": (last["close"] / op - 1) * 100 if op else np.nan,
            "pct_1d": (ret_1d * 100) if pd.notna(ret_1d) else np.nan,
            "pct_1m": (r1m * 100) if pd.notna(r1m) else np.nan,
            "pct_off_52w": (last["close"] / hi52 - 1) * 100 if hi52 else np.nan,
            "adr_pct": (last["adr"] * 100) if "adr" in g.columns and pd.notna(last["adr"]) else np.nan,
            "vol_sma20": last["vol_ma20"] if "vol_ma20" in g.columns else np.nan,
            "close": _v(last, "close"), "sma10": _v(last, "sma10"), "sma20": _v(last, "sma20"),
            "ema8": _v(last, "ema8"), "ema21": _v(last, "ema21"), "rsi": _v(last, "rsi"),
            "atr_ext": _v(last, "sma50_atr_ext"),
        })

    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["rs_1m"] = (df["_rs1"].rank(pct=True) * 100).round(0)
    df["rs_thrust"] = (df["_rs5"].rank(pct=True) * 100).round(0)
    df["mom"] = np.where(df["adr_pct"] >= 9, "🔥", "")  # high-momentum: ADR ≥ 9%
    return df.drop(columns=["_rs1", "_rs5"])[DISPLAY_COLS].sort_values("rs_1m", ascending=False)


# ── heat-map styling (no matplotlib dependency) ──────────────────────────────
_RED, _WHITE, _GREEN = (231, 76, 60), (255, 255, 255), (24, 188, 156)


def _lerp(a, b, f):
    return tuple(int(round(a[i] + (b[i] - a[i]) * f)) for i in range(3))


def _heat(t: float) -> str:
    if pd.isna(t):
        return ""
    t = max(0.0, min(1.0, t))
    rgb = _lerp(_RED, _WHITE, t / 0.5) if t < 0.5 else _lerp(_WHITE, _GREEN, (t - 0.5) / 0.5)
    return f"background-color: rgb{rgb}; color: #1a1a1a"


def _col_heat(s: pd.Series, lo: float, hi: float):
    return [_heat((v - lo) / (hi - lo)) if pd.notna(v) else "" for v in s]


_HEAT_SPEC = {
    "rs_thrust": (0, 100), "rs_1m": (0, 100),
    "pct_intraday": (-2, 2), "pct_1d": (-2, 2), "pct_1m": (-8, 8),
    "pct_off_52w": (-15, 0), "adr_pct": (0, 10),
}


def style(df: pd.DataFrame):
    """Return a pandas Styler with green/red heat on whatever numeric columns are present."""
    sty = df.style
    for col, (lo, hi) in _HEAT_SPEC.items():
        if col in df.columns:
            sty = sty.apply(_col_heat, lo=lo, hi=hi, subset=[col])
    return sty
