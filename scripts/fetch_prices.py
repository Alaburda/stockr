"""Pull fresh Yahoo prices for the static site and write them to site/data/.

Run from the repo root:

    python scripts/fetch_prices.py

Reuses the Streamlit app's canonical fetch + indicator code (app/streamlit/lib)
so the site and the app agree on what "RSI" or "ATR extension" mean. Writes:

    site/data/prices.csv   one row per ticker/day, trimmed to LOOKBACK_DAYS
    site/data/meta.json    fetch timestamp + which tickers succeeded/failed

Nothing here touches db/database.duckdb — the site is built from a fresh pull,
so the GitHub Action needs no database and no secrets.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app" / "streamlit"))

from lib.config import (  # noqa: E402
    DASHBOARD_GROUPS, DASHBOARD_NAMES, DASHBOARD_TICKERS,
    DEFAULT_ETFS, DEFAULT_INDICES, DEFAULT_WATCHLIST,
)
from lib.fetch import fetch_bulk, fetch_ticker  # noqa: E402

# How much history each ticker keeps. 5y so the weekly and monthly candle views
# have real depth (260 daily bars is only ~12 monthly candles). The CSV is never
# published — Quarto reads it at render time — so its size costs nothing but
# build seconds.
FETCH_PERIOD = "5y"
LOOKBACK_DAYS = 1300

# The job runs unattended at 02:00. If Yahoo is having a bad night, fail the
# build rather than publish a board with half the watchlist silently missing —
# yesterday's page staying up is more useful than a misleading fresh one.
MIN_COVERAGE = 0.8

# Tickers the page's market strip is built from. Losing one of these doesn't
# trip MIN_COVERAGE — 77/78 is 99% — it just silently deletes a tile from the
# published board, which is worse than an obvious failure. So they're required.
REQUIRED = ["SPY", "QQQ", "^VIX", "^VIX3M", "^TNX", "DX-Y.NYB", "RSP", "TLT"]

# Columns the site actually reads. Everything else is dropped from the CSV.
KEEP = [
    "ticker", "date", "open", "high", "low", "close", "volume",
    "sma10", "sma20", "sma50", "sma200", "ema8", "ema21",
    "rsi", "atr", "adr", "vol_ma20", "rel_vol",
    "sma50_atr_ext", "pct_ema8", "pct_sma200", "ret_1d",
]

OUT_DIR = ROOT / "site" / "data"


def universe() -> dict[str, list[str]]:
    """Tickers to publish, grouped so the page can section them.

    Order matters: a ticker's `group` column is its FIRST match here, so SPY
    stays an "etf" for the ETF table even though it's also a dashboard
    benchmark. The RS boards select by explicit ticker list instead.
    """
    return {
        "watchlist": DEFAULT_WATCHLIST,
        "etf": DEFAULT_ETFS,
        "index": DEFAULT_INDICES,
        "dashboard": DASHBOARD_TICKERS,
    }


def backfill(df: "pd.DataFrame", symbols: list[str], bench: str = "SPY") -> "pd.DataFrame":
    """Re-request tickers the bulk download dropped or returned short.

    Yahoo's bulk endpoint is markedly less reliable from a datacenter IP than
    from a laptop. The same call that returned 78/78 complete series locally
    came back from GitHub Actions with ^VIX3M missing entirely and 38 tickers
    gapped — which silently removed the VIX3M/VIX stress tile from the
    published page while the coverage guard still read 77/78 and passed.

    Requesting the stragglers one at a time uses a different endpoint and
    usually fills them in. Tickers with genuinely short history (recent
    listings like NBIS/RDDT) get retried too and simply come back the same
    length, which costs a request and changes nothing.
    """
    counts = df.groupby("ticker").size()
    target_len = int(counts.get(bench, counts.max() if len(counts) else 0))
    short = [s for s in symbols
             if s not in counts.index or int(counts[s]) < target_len]
    if not short:
        return df

    print(f"Backfilling {len(short)} incomplete/missing tickers "
          f"(benchmark has {target_len} bars)...", flush=True)
    fixed = 0
    for sym in short:
        one = fetch_ticker(sym, period=FETCH_PERIOD)
        if one is None or one.empty:
            continue
        if len(one) > int(counts.get(sym, 0)):
            df = pd.concat([df[df["ticker"] != sym], one], ignore_index=True)
            fixed += 1
    print(f"  backfill improved {fixed} of {len(short)}")
    return df


def main() -> int:
    groups = universe()
    symbols = sorted({t for g in groups.values() for t in g})
    print(f"Fetching {len(symbols)} tickers ({FETCH_PERIOD})...", flush=True)

    df = fetch_bulk(symbols, period=FETCH_PERIOD,
                    progress=lambda frac, label: print(f"  {frac:5.0%} {label}", flush=True))
    if df.empty:
        print("ERROR: Yahoo returned nothing for the whole universe.", file=sys.stderr)
        return 1

    df = backfill(df, symbols)

    # One row per (ticker, date), then trim to the most recent LOOKBACK_DAYS.
    # The upstream feed has been seen to return a duplicated bar, which shifts
    # every rolling window and lookback for that ticker.
    before = len(df)
    df = df.drop_duplicates(subset=["ticker", "date"], keep="last")
    if len(df) < before:
        print(f"Dropped {before - len(df)} duplicate (ticker, date) rows")

    df = (df.sort_values(["ticker", "date"])
            .groupby("ticker", group_keys=False)
            .tail(LOOKBACK_DAYS))

    group_of: dict[str, str] = {}
    for name, tickers in groups.items():
        for t in tickers:
            group_of.setdefault(t, name)  # first match wins — see universe()
    df["group"] = df["ticker"].map(group_of)
    df = df[[c for c in KEEP if c in df.columns] + ["group"]]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = OUT_DIR / "prices.csv"
    df.to_csv(csv_path, index=False, float_format="%.6g")

    got = sorted(df["ticker"].unique())
    missing = [t for t in symbols if t not in set(got)]
    # "Last bar" means the benchmark's last session, not the max across the
    # universe: DX-Y.NYB carries a Sunday bar (ICE quotes the dollar index on
    # Sunday evening), so the max would advertise the board as a day or two
    # fresher than every equity number on it actually is.
    spy_dates = df.loc[df["ticker"] == "SPY", "date"]
    last_bar = str(spy_dates.max() if not spy_dates.empty else df["date"].max())[:10]

    meta = {
        "fetched_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "last_bar": last_bar,
        "last_bar_any_ticker": str(df["date"].max())[:10],
        "requested": len(symbols),
        "ok": len(got),
        "missing": missing,
        # Bar counts and the benchmark calendar make a build reproducible after
        # the fact: if the published page ever disagrees with a local render,
        # comparing these says immediately whether the upstream feed handed the
        # two runs different history.
        "bars_per_ticker": df.groupby("ticker").size().sort_index().to_dict(),
        "calendar_len": int((df["ticker"] == "SPY").sum()),
        "groups": groups,
        # The RS boards render these sections by explicit ticker list.
        "dashboard_groups": DASHBOARD_GROUPS,
        "dashboard_names": DASHBOARD_NAMES,
    }
    (OUT_DIR / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    size_kb = csv_path.stat().st_size / 1024
    print(f"Wrote {csv_path.relative_to(ROOT)} — {len(df):,} rows, {size_kb:,.0f} KB")
    print(f"Last bar {meta['last_bar']}; {len(got)}/{len(symbols)} tickers OK")
    if missing:
        print(f"Missing: {', '.join(missing)}")

    absent = [t for t in REQUIRED if t not in set(got)]
    if absent:
        print(f"ERROR: required ticker(s) missing: {', '.join(absent)}. These build "
              f"the market strip; publishing without them would quietly drop tiles.",
              file=sys.stderr)
        return 1

    coverage = len(got) / len(symbols)
    if coverage < MIN_COVERAGE:
        print(f"ERROR: only {coverage:.0%} of tickers returned data "
              f"(need {MIN_COVERAGE:.0%}). Refusing to publish a partial board.",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
