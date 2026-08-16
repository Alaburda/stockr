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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app" / "streamlit"))

from lib.config import DEFAULT_ETFS, DEFAULT_INDICES, DEFAULT_WATCHLIST  # noqa: E402
from lib.fetch import fetch_bulk  # noqa: E402

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

# Columns the site actually reads. Everything else is dropped from the CSV.
KEEP = [
    "ticker", "date", "open", "high", "low", "close", "volume",
    "sma10", "sma20", "sma50", "sma200", "ema8", "ema21",
    "rsi", "atr", "adr", "vol_ma20", "rel_vol",
    "sma50_atr_ext", "pct_ema8", "pct_sma200", "ret_1d",
]

OUT_DIR = ROOT / "site" / "data"


def universe() -> dict[str, list[str]]:
    """Tickers to publish, grouped so the page can section them."""
    return {
        "watchlist": DEFAULT_WATCHLIST,
        "etf": DEFAULT_ETFS,
        "index": DEFAULT_INDICES,
    }


def main() -> int:
    groups = universe()
    symbols = sorted({t for g in groups.values() for t in g})
    print(f"Fetching {len(symbols)} tickers ({FETCH_PERIOD})...", flush=True)

    df = fetch_bulk(symbols, period=FETCH_PERIOD,
                    progress=lambda frac, label: print(f"  {frac:5.0%} {label}", flush=True))
    if df.empty:
        print("ERROR: Yahoo returned nothing for the whole universe.", file=sys.stderr)
        return 1

    # Trim each ticker to its most recent LOOKBACK_DAYS bars.
    df = (df.sort_values(["ticker", "date"])
            .groupby("ticker", group_keys=False)
            .tail(LOOKBACK_DAYS))

    group_of = {t: name for name, tickers in groups.items() for t in tickers}
    df["group"] = df["ticker"].map(group_of)
    df = df[[c for c in KEEP if c in df.columns] + ["group"]]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = OUT_DIR / "prices.csv"
    df.to_csv(csv_path, index=False, float_format="%.6g")

    got = sorted(df["ticker"].unique())
    missing = [t for t in symbols if t not in set(got)]
    meta = {
        "fetched_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "last_bar": str(df["date"].max())[:10],
        "requested": len(symbols),
        "ok": len(got),
        "missing": missing,
        "groups": groups,
    }
    (OUT_DIR / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    size_kb = csv_path.stat().st_size / 1024
    print(f"Wrote {csv_path.relative_to(ROOT)} — {len(df):,} rows, {size_kb:,.0f} KB")
    print(f"Last bar {meta['last_bar']}; {len(got)}/{len(symbols)} tickers OK")
    if missing:
        print(f"Missing: {', '.join(missing)}")

    coverage = len(got) / len(symbols)
    if coverage < MIN_COVERAGE:
        print(f"ERROR: only {coverage:.0%} of tickers returned data "
              f"(need {MIN_COVERAGE:.0%}). Refusing to publish a partial board.",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
