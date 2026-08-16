"""Metrics for the static board — the SQL views, ported to pandas.

The Streamlit app computes its judgment-carrying columns in DuckDB
(`v_latest`, `v_perf`, `v_rs_spy`, `v_ma_matrix`). A static site has no
database, so the same definitions live here over the published CSV. Where a
number exists in both places it is computed the same way, so the page and the
app agree.

Tooltip text is imported from the app's `lib/glossary.py` rather than
re-written, keeping one source of truth for what each signal means.
"""
from __future__ import annotations

import html
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

_APP = Path(__file__).resolve().parents[1] / "app" / "streamlit"
if str(_APP) not in sys.path:
    sys.path.insert(0, str(_APP))

from lib.glossary import HELP  # noqa: E402

# Trailing windows in trading sessions, matching v_perf.
HORIZONS = {"1w": 5, "1m": 21, "3m": 63, "6m": 126}

# The MA matrix columns from v_ma_matrix. sma5/sma150 aren't in the fetched
# schema, so every window is recomputed here from close for consistency.
MA_WINDOWS = [5, 10, 20, 50, 100, 150, 200]

BENCH = "SPY"


# ── helpers ──────────────────────────────────────────────────────────────────
def _ret(s: pd.Series, cal: pd.DatetimeIndex, n: int) -> float:
    """Return over the benchmark's last `n` sessions.

    Anchored to the benchmark calendar rather than counting rows back in the
    ticker's own series. A positional lookback assumes every ticker has exactly
    one row per trading day: a duplicated or missing bar shifts the window
    silently, and — because the ticker's 22nd-back row would then be a
    different date than the benchmark's — it corrupts every RS number without
    changing close, 1D or 1W, which is exactly how this surfaced in CI.

    `s` is indexed by date. The reference is the last close on or before the
    benchmark's reference date, so a ticker that didn't trade that day still
    measures the same span.
    """
    if s.empty or len(cal) <= n:
        return np.nan
    prior = s.loc[:cal[-1 - n]]
    if prior.empty:
        return np.nan
    base = prior.iloc[-1]
    return s.iloc[-1] / base - 1 if base else np.nan


def _ytd(g: pd.DataFrame) -> float:
    """Return since the first close on or after Jan 1 of the latest year."""
    last_date = g["date"].iloc[-1]
    start = g[g["date"] >= pd.Timestamp(year=last_date.year, month=1, day=1)]
    if start.empty:
        return np.nan
    first = start["close"].iloc[0]
    return g["close"].iloc[-1] / first - 1 if first else np.nan


def _rising(g: pd.DataFrame, col: str, lookback: int = 5) -> bool | None:
    """Is `col` higher than it was `lookback` sessions ago? (v_latest flags)"""
    if col not in g.columns:
        return None
    s = g[col].dropna()
    if len(s) <= lookback:
        return None
    return bool(s.iloc[-1] > s.iloc[-1 - lookback])


def tip(label: str, key: str) -> str:
    """Column label carrying its glossary explanation as a hover tooltip.

    Hover is desktop-only — phones have no hover state — so the page also
    renders a full glossary section that works everywhere.
    """
    text = HELP.get(key)
    if not text:
        return html.escape(label)
    return f'<abbr class="gl" title="{html.escape(text)}">{html.escape(label)}</abbr>'


# ── the A-setup checklist (Single Stock Viewer's ✅/❌ panel) ─────────────────
# label, predicate, glossary key. Six conditions describing a stock that is
# trending, not over-extended, and closing strong on above-average volume.
SETUP_CHECKS: list[tuple[str, str]] = [
    ("ATR ext < 4x", "sma50_atr_ext"),
    ("LoD dist < 0.6", "lod_atr_pct"),
    ("200-MA rising", "sma200_rising"),
    ("10-MA rising", "sma10_rising"),
    ("RS 1M > 0", "rs_1m"),
    ("Rel vol >= 1", "rel_vol"),
]


def _setup_results(r: pd.Series) -> list[bool | None]:
    def lt(v, x):
        return None if pd.isna(v) else bool(v < x)

    def gt(v, x):
        return None if pd.isna(v) else bool(v > x)

    return [
        lt(r.get("atr_ext"), 4),
        lt(r.get("lod_atr"), 0.6),
        r.get("sma200_rising"),
        r.get("sma10_rising"),
        gt(r.get("rs_1m"), 0),
        None if pd.isna(r.get("rel_vol")) else bool(r.get("rel_vol") >= 1),
    ]


# ── the main table ───────────────────────────────────────────────────────────
def latest_metrics(px: pd.DataFrame, bench: str = BENCH) -> pd.DataFrame:
    """One row per ticker: latest close plus every derived signal.

    Mirrors v_latest + v_perf + v_rs_spy + v_ma_matrix in a single pass.
    """
    # One row per (ticker, date). A duplicated bar from the upstream feed would
    # otherwise shift every rolling window and lookback for that ticker.
    px = (px.drop_duplicates(subset=["ticker", "date"], keep="last")
            .sort_values(["ticker", "date"]))

    bg = px[px["ticker"] == bench]
    cal = pd.DatetimeIndex(bg["date"])  # the trading calendar everything measures against
    bench_close = bg.set_index("date")["close"]
    bench_ret = {k: _ret(bench_close, cal, n) for k, n in HORIZONS.items()}

    rows = []
    for tk, g in px.groupby("ticker", sort=False):
        g = g.dropna(subset=["close"])
        if len(g) < 2:
            continue
        c, last = g.set_index("date")["close"], g.iloc[-1]

        rec: dict = {
            "ticker": tk,
            "group": last["group"],
            "close": last["close"],
            "rsi": last.get("rsi"),
            "adr": last.get("adr"),
            "rel_vol": last.get("rel_vol"),
            "atr_ext": last.get("sma50_atr_ext"),
            "pct_ema8": last.get("pct_ema8"),
            "sma10": last.get("sma10"),
            "sma20": last.get("sma20"),
            "ret_1d": _ret(c, cal, 1),
            "ret_ytd": _ytd(g),
        }
        for k, n in HORIZONS.items():
            rec[f"ret_{k}"] = _ret(c, cal, n)

        hi52 = g["high"].tail(252).max()
        rec["pct_off_52w"] = (last["close"] / hi52 - 1) * 100 if hi52 else np.nan

        # Relative strength in percentage points vs the benchmark (v_rs_spy).
        for k in ("1m", "3m"):
            r, b = rec[f"ret_{k}"], bench_ret.get(k)
            rec[f"rs_{k}"] = (r - b) * 100 if pd.notna(r) and pd.notna(b) else np.nan

        atr = last.get("atr")
        rec["lod_atr"] = ((last["close"] - last["low"]) / atr
                          if pd.notna(atr) and atr else np.nan)
        rec["sma200_rising"] = _rising(g, "sma200")
        rec["sma10_rising"] = _rising(g, "sma10")

        for w in MA_WINDOWS:
            ma = c.rolling(w).mean().iloc[-1]
            rec[f"above_{w}"] = None if pd.isna(ma) else bool(last["close"] > ma)

        rows.append(rec)

    df = pd.DataFrame(rows).set_index("ticker")
    results = df.apply(_setup_results, axis=1)
    df["setup_results"] = results
    df["setup_n"] = results.apply(lambda xs: sum(1 for x in xs if x))
    return df


def load(data_dir: str | Path = "data"):
    """Load the published data every page starts from.

    Returns (prices, meta, metrics). Pages call this instead of repeating the
    read + latest_metrics dance.
    """
    d = Path(data_dir)
    px = pd.read_csv(d / "prices.csv", parse_dates=["date"]).sort_values(["ticker", "date"])
    meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
    return px, meta, latest_metrics(px)


def load_sp500(data_dir: str | Path = "data"):
    """S&P 500 aggregates, or None if that best-effort job didn't produce them.

    fetch_sp500.py is allowed to fail without failing the build, so every
    caller has to cope with these being absent.
    """
    d = Path(data_dir)
    meta_path = d / "sp500_meta.json"
    if not meta_path.exists():
        return None
    out = {"meta": json.loads(meta_path.read_text(encoding="utf-8"))}
    for name, parse_dates in (("breadth", ["date"]), ("highlow", ["date"]), ("sector_rs", None)):
        p = d / f"{name}.csv"
        out[name] = (pd.read_csv(p, parse_dates=parse_dates) if p.exists() else None)
    return out


def load_macro(data_dir: str | Path = "data"):
    """Macro correlation studies, or None if that best-effort job didn't run."""
    d = Path(data_dir)
    p = d / "macro_meta.json"
    if not p.exists():
        return None
    out = {"meta": json.loads(p.read_text(encoding="utf-8"))}
    for name in ("corr", "lockstep"):
        f = d / f"macro_{name}.csv"
        out[name] = pd.read_csv(f, parse_dates=["date"]) if f.exists() else None
    return out


def rs_rank(df: pd.DataFrame, tickers: list[str], col: str = "ret_1m") -> pd.DataFrame:
    """Members of one RS board, percentile-ranked within the board (lib/rs.py).

    The app ranks each section's members against each other rather than showing
    a raw return, so a sector's score is "where it sits in its own peer group".
    """
    sub = df[df.index.isin(tickers)].copy()
    if sub.empty:
        return sub
    sub["rs_pct"] = (sub[col].rank(pct=True) * 100).round(0)
    return sub.sort_values(col, ascending=False)
