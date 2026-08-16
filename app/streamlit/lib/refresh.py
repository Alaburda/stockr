"""Shared data-refresh routines used by both Ticker Database and the Dashboard
quick-refresh button. Keeping the fetch+upsert logic here means both pages call
the exact same code path instead of duplicating it.
"""
from __future__ import annotations

from typing import Callable

import pandas as pd

from lib import db, data, fetch
from lib.config import DEFAULT_INDICES, DEFAULT_ETFS, DASHBOARD_TICKERS


def refresh_symbols(symbols: list[str], period: str, table: str = db.PRICES,
                    progress: Callable[[float, str], None] | None = None,
                    rebuild: bool = True) -> pd.DataFrame:
    """Fetch `symbols` via yfinance and upsert into `table`. Returns the fetched df.

    Raises db.DBLocked if the write fails because the DB is held elsewhere.
    Caller is responsible for calling data.invalidate() afterwards.

    `rebuild=True` re-materializes `prices_all_mat` (db.rebuild_prices_all) after
    the upsert so v_prices_all reflects the new rows. Callers doing several
    upserts back-to-back (quick_refresh) pass rebuild=False and rebuild once at
    the end instead of after every table.
    """
    df = fetch.fetch_many(symbols, period=period, progress=progress)
    if df.empty:
        return df
    db.upsert_prices(df, table=table)
    if rebuild:
        db.rebuild_prices_all()
    return df


def quick_refresh(period: str = "5y", progress: Callable[[float, str], None] | None = None) -> dict:
    """The Dashboard's "🔄 Refresh data" quick set: watchlist (tracked) prices +
    indices & ETFs + dashboard ETFs. Deliberately excludes the slow ~500-ticker
    S&P 500 bulk pull (that lives in Ticker Database only).

    Returns a dict of {label: n_tickers_written} for a short summary. Raises
    db.DBLocked if any write fails because the DB is locked.
    """
    results: dict[str, int] = {}

    tracked = data.meta()["ticker"].tolist() if not data.meta().empty else []
    if tracked:
        df = refresh_symbols(tracked, period, table=db.PRICES, rebuild=False,
                             progress=progress and (lambda p, s: progress(p * 0.34, f"watchlist: {s}")))
        results["watchlist prices"] = df["ticker"].nunique() if not df.empty else 0

    extras = DEFAULT_INDICES + DEFAULT_ETFS
    df = refresh_symbols(extras, period, table=db.PRICES, rebuild=False,
                         progress=progress and (lambda p, s: progress(0.34 + p * 0.33, f"indices & ETFs: {s}")))
    results["indices & ETFs"] = df["ticker"].nunique() if not df.empty else 0

    df = refresh_symbols(DASHBOARD_TICKERS, period, table=db.DASHBOARD, rebuild=False,
                         progress=progress and (lambda p, s: progress(0.67 + p * 0.33, f"dashboard ETFs: {s}")))
    results["dashboard ETFs"] = df["ticker"].nunique() if not df.empty else 0

    # One materialization pass for all three upserts above.
    if progress is not None:
        progress(0.99, "rebuilding v_prices_all…")
    db.rebuild_prices_all()

    if progress is not None:
        progress(1.0, "done")

    data.invalidate()
    return results
