"""S&P 500 aggregates: breadth, 52-week new highs/lows, sector RS.

Run from the repo root, AFTER scripts/fetch_prices.py (it reads SPY's calendar
from the board's own CSV):

    python scripts/fetch_sp500.py

This pulls ~500 tickers, which is slow and the most failure-prone thing in the
build, so it is deliberately **best-effort and separate**: it writes its own
small aggregate files and never touches prices.csv. The workflow runs it with
continue-on-error, and the Indicators page renders these sections only if the
files are present. A bad S&P night costs you the breadth panels, not the board.

Only aggregates are written — never the ~500 x 500 price matrix, which would
be a ~100 MB CSV for numbers no page ever reads individually.

    site/data/breadth.csv    date, % above 20/50/200d SMA, % up on the day
    site/data/highlow.csv    date, new 52w highs, new lows, net
    site/data/sector_rs.csv  sector, member count, 1m/3m return and RS vs SPY
    site/data/sp500_meta.json
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app" / "streamlit"))

from lib.fetch import fetch_bulk  # noqa: E402
from lib.universe import sp500_constituents  # noqa: E402

FETCH_PERIOD = "2y"      # enough to warm the 200-day SMA and a 252-day high
PUBLISH_SESSIONS = 378   # ~18 months of breadth history on the chart
HIGH_LOW_WINDOW = 252

# Below this share of constituents the aggregates stop being meaningful —
# "42% above the 50-day" means nothing if it's 42% of a third of the index.
MIN_MEMBERS = 0.7

OUT_DIR = ROOT / "site" / "data"


def _ret_asof(s: pd.Series, ref: pd.Timestamp) -> float:
    """Return from the last close on or before `ref` to the latest close.

    Date-anchored for the same reason board.py is: constituents don't all share
    one trading calendar, so counting rows back would compare different spans.
    """
    prior = s.loc[:ref]
    if prior.empty or not prior.iloc[-1]:
        return np.nan
    return s.iloc[-1] / prior.iloc[-1] - 1


def main() -> int:
    try:
        members = sp500_constituents()
    except Exception as exc:  # noqa: BLE001 — Wikipedia scrape is fragile by nature
        print(f"ERROR: could not fetch constituent list: {exc}", file=sys.stderr)
        return 1
    print(f"S&P 500 constituents: {len(members)}", flush=True)

    symbols = members["ticker"].tolist()
    px = fetch_bulk(symbols, period=FETCH_PERIOD,
                    progress=lambda frac, label: print(f"  {frac:5.0%} {label}", flush=True))
    if px.empty:
        print("ERROR: no S&P 500 prices returned.", file=sys.stderr)
        return 1

    px = (px.drop_duplicates(subset=["ticker", "date"], keep="last")
            .sort_values(["ticker", "date"]))
    got = px["ticker"].nunique()
    coverage = got / len(symbols)
    print(f"Got {got}/{len(symbols)} tickers ({coverage:.0%})")
    if coverage < MIN_MEMBERS:
        print(f"ERROR: only {coverage:.0%} of constituents returned data "
              f"(need {MIN_MEMBERS:.0%}); aggregates would be misleading.",
              file=sys.stderr)
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # ── breadth: % of members above their own 20/50/200-day SMA, per date ────
    px["above_20"] = px["close"] > px["sma20"]
    px["above_50"] = px["close"] > px["sma50"]
    px["above_200"] = px["close"] > px["sma200"]
    px["up_day"] = px["ret_1d"] > 0

    # Only count a ticker on a date where the SMA actually exists, otherwise
    # early dates read as artificially bearish (NaN > x is False).
    def pct_true(flag: str, need: str) -> pd.Series:
        valid = px[px[need].notna()]
        return valid.groupby("date")[flag].mean() * 100

    breadth = pd.DataFrame({
        "pct_above_20": pct_true("above_20", "sma20"),
        "pct_above_50": pct_true("above_50", "sma50"),
        "pct_above_200": pct_true("above_200", "sma200"),
        "pct_up": pct_true("up_day", "ret_1d"),
        "n": px[px["sma200"].notna()].groupby("date")["ticker"].nunique(),
    }).dropna(subset=["pct_above_200"]).tail(PUBLISH_SESSIONS)
    breadth.index.name = "date"
    breadth.round(3).to_csv(OUT_DIR / "breadth.csv")

    # ── 52-week new highs / new lows ─────────────────────────────────────────
    g = px.groupby("ticker")
    px["hi252"] = g["high"].transform(lambda s: s.rolling(HIGH_LOW_WINDOW).max())
    px["lo252"] = g["low"].transform(lambda s: s.rolling(HIGH_LOW_WINDOW).min())
    px["is_nh"] = px["high"] >= px["hi252"]
    px["is_nl"] = px["low"] <= px["lo252"]
    valid = px[px["hi252"].notna()]
    hl = pd.DataFrame({
        "new_highs": valid.groupby("date")["is_nh"].sum(),
        "new_lows": valid.groupby("date")["is_nl"].sum(),
    }).tail(PUBLISH_SESSIONS)
    hl["net"] = hl["new_highs"] - hl["new_lows"]
    hl.index.name = "date"
    hl.to_csv(OUT_DIR / "highlow.csv")

    # ── sector RS: equal-weighted sector return vs SPY ───────────────────────
    board_csv = OUT_DIR / "prices.csv"
    if not board_csv.exists():
        print("ERROR: site/data/prices.csv missing — run fetch_prices.py first.",
              file=sys.stderr)
        return 1
    board = pd.read_csv(board_csv, parse_dates=["date"])
    spy = board[board["ticker"] == "SPY"].sort_values("date")
    cal = pd.DatetimeIndex(spy["date"])
    spy_close = spy.set_index("date")["close"]

    sector_of = dict(zip(members["ticker"], members["sector"]))
    rows = []
    for tk, gg in px.groupby("ticker"):
        s = gg.set_index("date")["close"].dropna()
        if len(s) < 2:
            continue
        rows.append({"ticker": tk, "sector": sector_of.get(tk, "Unknown"),
                     "ret_21": _ret_asof(s, cal[-22]) if len(cal) > 21 else np.nan,
                     "ret_63": _ret_asof(s, cal[-64]) if len(cal) > 63 else np.nan})
    per_ticker = pd.DataFrame(rows)

    spy_21 = _ret_asof(spy_close, cal[-22]) if len(cal) > 21 else np.nan
    spy_63 = _ret_asof(spy_close, cal[-64]) if len(cal) > 63 else np.nan

    sector = (per_ticker.groupby("sector")
              .agg(n=("ticker", "size"), ret_21=("ret_21", "mean"), ret_63=("ret_63", "mean"))
              .reset_index())
    sector["rs_21"] = (sector["ret_21"] - spy_21) * 100
    sector["rs_63"] = (sector["ret_63"] - spy_63) * 100
    sector = sector.sort_values("rs_21", ascending=False)
    sector.round(6).to_csv(OUT_DIR / "sector_rs.csv", index=False)

    meta = {
        "fetched_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "last_bar": str(px["date"].max())[:10],
        "constituents": len(symbols),
        "ok": int(got),
        "coverage": round(coverage, 4),
        "spy_ret_21": None if pd.isna(spy_21) else round(float(spy_21), 6),
        "spy_ret_63": None if pd.isna(spy_63) else round(float(spy_63), 6),
    }
    (OUT_DIR / "sp500_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    latest = breadth.iloc[-1]
    print(f"Breadth {breadth.index[-1].date()}: "
          f"20d {latest['pct_above_20']:.0f}% · 50d {latest['pct_above_50']:.0f}% · "
          f"200d {latest['pct_above_200']:.0f}% (n={int(latest['n'])})")
    print(f"New highs {int(hl['new_highs'].iloc[-1])} / lows {int(hl['new_lows'].iloc[-1])} "
          f"→ net {int(hl['net'].iloc[-1])}")
    print(f"Sectors: {len(sector)} · leader {sector.iloc[0]['sector']} "
          f"({sector.iloc[0]['rs_21']:+.1f}pp 1M RS)")
    return 0


if __name__ == "__main__":
    # This step is continue-on-error, so a warning (not an error) annotation:
    # it explains why the breadth panels are absent without implying the build
    # broke.
    try:
        code = main()
        if code:
            print("::warning::S&P 500 aggregates unavailable this run; "
                  "Indicators will render without the breadth panels.", flush=True)
        raise SystemExit(code)
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 — re-raised after reporting
        print(f"::warning::fetch_sp500 crashed: {type(exc).__name__}: {exc}", flush=True)
        raise
