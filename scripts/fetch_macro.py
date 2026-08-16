"""Macro correlation studies: SPX vs housing, and the SPX / 30Y / dollar trio.

Run from the repo root (order doesn't matter — this reads nothing the other
fetch scripts write):

    python scripts/fetch_macro.py

Two things live here, both of which are *claims* as much as indicators, so this
script measures them rather than only plotting them.

1. SPX vs HGX (PHLX Housing) rolling correlation. The claim being tracked is
   that the correlation is normally positive, and that stretches where it turns
   negative tend to be followed by market volatility.

2. The SPX / 30-year yield / dollar "lockstep". The claim is that the biggest
   moves of a macro cycle — up and down alike — happen when all three move
   together. That is a statement about a common factor dominating the three
   series, which is exactly what the first principal component's share of
   variance measures (the "absorption ratio" idea from systemic-risk work).

Both are written with an event study attached, so the page can show what the
history actually says instead of asserting it.

Outputs (all small; the raw price history is never published):

    site/data/macro_corr.csv      date, spx, hgx, corr10, corr20
    site/data/macro_lockstep.csv  date, pc1_share, pairwise corrs, tyx level
    site/data/macro_meta.json     event-study results + yield-level context
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "site" / "data"

TICKERS = {"spx": "^GSPC", "hgx": "^HGX", "tyx": "^TYX", "dxy": "DX-Y.NYB"}

CORR_FAST, CORR_SLOW = 10, 20   # the tweet's indicator is the 10-day
LOCKSTEP_WINDOW = 60            # ~a quarter: long enough for a 3x3 corr to mean something
FORWARD = 21                    # ~1 month forward window for the event studies


def load_closes() -> pd.DataFrame:
    """Wide frame of closes, one column per key. Full available history."""
    out = {}
    for key, sym in TICKERS.items():
        h = yf.Ticker(sym).history(period="max", auto_adjust=True)
        if h is None or h.empty:
            print(f"  {sym}: no data", flush=True)
            continue
        h = h.reset_index()
        dates = pd.to_datetime(h.iloc[:, 0])
        if getattr(dates.dt, "tz", None) is not None:
            dates = dates.dt.tz_localize(None)
        s = pd.Series(h["Close"].astype(float).values, index=dates.dt.normalize())
        out[key] = s[~s.index.duplicated(keep="last")]
        print(f"  {sym}: {len(s):,} bars from {s.index.min().date()}", flush=True)
    return pd.DataFrame(out).sort_index()


def innovations(df: pd.DataFrame) -> pd.DataFrame:
    """Daily innovations, using the right transform per asset class.

    Prices get log returns. The 30-year *yield* gets a first difference in
    percentage points: a "return" on a yield level is close to meaningless
    (a move from 1% to 1.1% is +10%, the same move from 5% to 5.1% is +2%),
    and would make correlations depend on the level rather than the move.
    """
    out = pd.DataFrame(index=df.index)
    for col in ("spx", "hgx", "dxy"):
        if col in df:
            out[col] = np.log(df[col]).diff()
    if "tyx" in df:
        out["tyx"] = df["tyx"].diff()
    return out


def pc1_share(window: np.ndarray) -> float:
    """Share of variance explained by the first principal component.

    Computed on the correlation matrix so the three series are comparable
    despite wildly different units. 1/3 = no common factor at all (perfectly
    independent), 1.0 = the three are one thing wearing three hats.
    """
    if np.isnan(window).any():
        return np.nan
    c = np.corrcoef(window, rowvar=False)
    if np.isnan(c).any():
        return np.nan
    vals = np.linalg.eigvalsh(c)
    return float(vals[-1] / vals.sum())


def rolling_pc1(inn: pd.DataFrame, cols: list[str], window: int) -> pd.Series:
    arr = inn[cols].to_numpy()
    out = np.full(len(arr), np.nan)
    for i in range(window, len(arr) + 1):
        out[i - 1] = pc1_share(arr[i - window:i])
    return pd.Series(out, index=inn.index)


def forward_vol(ret: pd.Series, n: int) -> pd.Series:
    """Annualized realized vol over the NEXT n sessions, aligned to today."""
    return ret.rolling(n).std().shift(-n) * np.sqrt(252) * 100


def forward_abs_move(close: pd.Series, n: int) -> pd.Series:
    """Absolute % change over the next n sessions — size of move, either way."""
    return (close.shift(-n) / close - 1).abs() * 100


def episodes(flag: pd.Series) -> pd.Series:
    """First day of each run of True — so one regime counts once, not 30 times."""
    f = flag.fillna(False)
    return f & ~f.shift(1, fill_value=False)


def study(cond: pd.Series, outcome: pd.Series, label: str) -> dict:
    """Compare an outcome on condition days against the unconditional baseline.

    Deliberately descriptive: forward windows of consecutive events overlap, so
    these are not independent samples and no p-value would be honest. The
    useful question is whether the conditional distribution looks different at
    all, and by how much.
    """
    joined = pd.concat([cond.rename("c"), outcome.rename("y")], axis=1).dropna()
    hit = joined[joined["c"]]["y"]
    base = joined["y"]
    if hit.empty:
        return {"label": label, "n": 0}
    return {
        "label": label,
        "n": int(len(hit)),
        "median": round(float(hit.median()), 2),
        "mean": round(float(hit.mean()), 2),
        "baseline_median": round(float(base.median()), 2),
        "baseline_mean": round(float(base.mean()), 2),
        "ratio_median": round(float(hit.median() / base.median()), 2) if base.median() else None,
        "pct_above_baseline_median": round(float((hit > base.median()).mean() * 100), 1),
    }


def main() -> int:
    print("Fetching macro series (full history)...", flush=True)
    closes = load_closes()
    missing = [k for k in TICKERS if k not in closes.columns]
    if missing:
        print(f"::warning::macro series missing: {', '.join(missing)}", flush=True)
    if "spx" not in closes.columns:
        print("::warning::no SPX data; macro studies skipped", flush=True)
        return 1

    inn = innovations(closes)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    meta: dict = {
        "fetched_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "last_bar": str(closes.index.max())[:10],
    }

    # ── 1. SPX vs HGX rolling correlation ────────────────────────────────────
    if "hgx" in inn.columns:
        pair = inn[["spx", "hgx"]].dropna()
        px_pair = closes[["spx", "hgx"]].dropna()
        # Two definitions, because they disagree and the source chart's is
        # ambiguous. StockCharts' correlation indicator runs on closing prices;
        # correlating *returns* is the statistically sounder read, since over a
        # 10-bar window a price correlation mostly measures shared trend.
        corr = pd.DataFrame({
            "corr10": pair["spx"].rolling(CORR_FAST).corr(pair["hgx"]),
            "corr20": pair["spx"].rolling(CORR_SLOW).corr(pair["hgx"]),
            "corr10_px": px_pair["spx"].rolling(CORR_FAST).corr(px_pair["hgx"]),
            "corr20_px": px_pair["spx"].rolling(CORR_SLOW).corr(px_pair["hgx"]),
        })
        corr["spx"] = closes["spx"].reindex(corr.index)
        corr["hgx"] = closes["hgx"].reindex(corr.index)
        corr = corr.dropna(subset=["corr10", "corr10_px"])
        corr.index.name = "date"
        corr[["spx", "hgx", "corr10", "corr20", "corr10_px", "corr20_px"]] \
            .round(4).to_csv(OUT_DIR / "macro_corr.csv")

        spx_ret = inn["spx"].reindex(corr.index)
        fvol = forward_vol(spx_ret, FORWARD)
        meta["hgx"] = {
            "start": str(corr.index.min())[:10],
            "sessions": int(len(corr)),
            "forward_days": FORWARD,
            "current": {
                "corr10_returns": round(float(corr["corr10"].iloc[-1]), 3),
                "corr10_price": round(float(corr["corr10_px"].iloc[-1]), 3),
                "negative_returns": bool(corr["corr10"].iloc[-1] < 0),
                "negative_price": bool(corr["corr10_px"].iloc[-1] < 0),
                "corr10_price_5d_ago": round(float(corr["corr10_px"].iloc[-6]), 3),
            },
        }
        for key, col in (("returns", "corr10"), ("price", "corr10_px")):
            neg = corr[col] < 0
            meta["hgx"][key] = {
                "pct_days_negative": round(float(neg.mean() * 100), 1),
                "episodes": int(episodes(neg).sum()),
                "all_negative_days": study(neg, fvol, f"{key}: any day corr10 < 0"),
                "episode_starts": study(episodes(neg), fvol,
                                        f"{key}: first day corr10 turns negative"),
            }
        c = meta["hgx"]
        print(f"HGX corr ({len(corr):,} sessions): returns {c['current']['corr10_returns']:+.2f} "
              f"({c['returns']['pct_days_negative']}% neg) · "
              f"price {c['current']['corr10_price']:+.2f} "
              f"({c['price']['pct_days_negative']}% neg)")
        for key in ("returns", "price"):
            s = c[key]["episode_starts"]
            if s.get("n"):
                print(f"  {key}: {s['n']} episodes · fwd {FORWARD}d vol median "
                      f"{s['median']}% vs baseline {s['baseline_median']}% "
                      f"(x{s['ratio_median']})")

    # ── 2. SPX / 30Y / dollar lockstep ───────────────────────────────────────
    trio = [c for c in ("spx", "tyx", "dxy") if c in inn.columns]
    if len(trio) == 3:
        sub = inn[trio].dropna()
        pc1 = rolling_pc1(sub, trio, LOCKSTEP_WINDOW)
        lock = pd.DataFrame({"pc1_share": pc1})
        lock["c_spx_tyx"] = sub["spx"].rolling(LOCKSTEP_WINDOW).corr(sub["tyx"])
        lock["c_spx_dxy"] = sub["spx"].rolling(LOCKSTEP_WINDOW).corr(sub["dxy"])
        lock["c_tyx_dxy"] = sub["tyx"].rolling(LOCKSTEP_WINDOW).corr(sub["dxy"])
        lock["tyx"] = closes["tyx"].reindex(lock.index)
        lock["spx"] = closes["spx"].reindex(lock.index)
        lock = lock.dropna(subset=["pc1_share"])
        lock.index.name = "date"
        lock.round(4).to_csv(OUT_DIR / "macro_lockstep.csv")

        spx_ret = inn["spx"].reindex(lock.index)
        spx_close = closes["spx"].reindex(lock.index)
        fmove = forward_abs_move(spx_close, FORWARD)
        fvol = forward_vol(spx_ret, FORWARD)

        hi = lock["pc1_share"].quantile(0.9)
        lo = lock["pc1_share"].quantile(0.1)
        aligned = lock["pc1_share"] >= hi

        # Which way the common factor points right now: loading signs say
        # whether stocks rise with yields and the dollar, or against them.
        recent = sub.tail(LOCKSTEP_WINDOW)
        c = np.corrcoef(recent.to_numpy(), rowvar=False)
        vals, vecs = np.linalg.eigh(c)
        load = vecs[:, -1]
        if load[0] < 0:            # orient so SPX loads positive, for readability
            load = -load
        meta["lockstep"] = {
            "start": str(lock.index.min())[:10],
            "sessions": int(len(lock)),
            "window": LOCKSTEP_WINDOW,
            "current_pc1": round(float(lock["pc1_share"].iloc[-1]), 3),
            "decile_hi": round(float(hi), 3),
            "decile_lo": round(float(lo), 3),
            "current_pct_rank": round(float((lock["pc1_share"] <= lock["pc1_share"].iloc[-1]).mean() * 100), 1),
            "loadings": {k: round(float(v), 3) for k, v in zip(trio, load)},
            "pairwise_now": {
                "spx_tyx": round(float(lock["c_spx_tyx"].iloc[-1]), 3),
                "spx_dxy": round(float(lock["c_spx_dxy"].iloc[-1]), 3),
                "tyx_dxy": round(float(lock["c_tyx_dxy"].iloc[-1]), 3),
            },
            "abs_move_when_aligned": study(aligned, fmove, "PC1 in top decile"),
            "vol_when_aligned": study(aligned, fvol, "PC1 in top decile"),
            "abs_move_when_dispersed": study(lock["pc1_share"] <= lo, fmove, "PC1 in bottom decile"),
            "forward_days": FORWARD,
        }
        print(f"Lockstep: PC1 now {meta['lockstep']['current_pc1']:.2f} "
              f"({meta['lockstep']['current_pct_rank']:.0f}th pct), "
              f"top decile >= {hi:.2f}")

    # ── 30-year yield level context ──────────────────────────────────────────
    if "tyx" in closes.columns:
        t = closes["tyx"].dropna()
        meta["tyx"] = {
            "start": str(t.index.min())[:10],
            "current": round(float(t.iloc[-1]), 3),
            "all_time_high": round(float(t.max()), 3),
            "all_time_high_date": str(t.idxmax())[:10],
            "pct_of_all_time_high": round(float(t.iloc[-1] / t.max() * 100), 1),
            "high_5y": round(float(t[t.index >= t.index.max() - pd.Timedelta(days=1825)].max()), 3),
            "high_10y": round(float(t[t.index >= t.index.max() - pd.Timedelta(days=3650)].max()), 3),
            "pct_off_5y_high": round(float(
                (t.iloc[-1] / t[t.index >= t.index.max() - pd.Timedelta(days=1825)].max() - 1) * 100), 2),
        }
        print(f"30Y yield {meta['tyx']['current']:.2f}% · 5y high "
              f"{meta['tyx']['high_5y']:.2f}% · all-time high "
              f"{meta['tyx']['all_time_high']:.2f}% ({meta['tyx']['all_time_high_date']})")

    (OUT_DIR / "macro_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    try:
        code = main()
        if code:
            print("::warning::macro studies unavailable this run.", flush=True)
        raise SystemExit(code)
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 — re-raised after reporting
        print(f"::warning::fetch_macro crashed: {type(exc).__name__}: {exc}", flush=True)
        raise
