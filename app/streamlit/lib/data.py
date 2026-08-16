"""Streamlit-aware cached wrappers around db / fetch.

Reads are cached for 5 min so flipping between pages is instant. Call
``invalidate()`` after any write (refresh / notes) to clear the cache.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from lib import db, fetch


@st.cache_data(ttl=300, show_spinner=False)
def snapshot(tickers: tuple | None = None, table: str = db.PRICES) -> pd.DataFrame:
    return db.get_snapshot(list(tickers) if tickers else None, table=table)


@st.cache_data(ttl=300, show_spinner=False)
def history(tickers: tuple | None = None, since=None, table: str = db.PRICES) -> pd.DataFrame:
    return db.get_history(list(tickers) if tickers else None, since=since, table=table)


@st.cache_data(ttl=300, show_spinner=False)
def meta() -> pd.DataFrame:
    return db.get_meta()


@st.cache_data(ttl=300, show_spinner=False)
def sp500_meta() -> pd.DataFrame:
    return db.get_sp500_meta()


@st.cache_data(ttl=300, show_spinner=False)
def shortlist() -> pd.DataFrame:
    return db.get_shortlist()


@st.cache_data(ttl=300, show_spinner=False)
def list_tickers(table: str) -> list[str]:
    return db.list_tickers(table=table)


@st.cache_data(ttl=3600, show_spinner=False)
def live(symbol: str, period: str = "5y") -> pd.DataFrame | None:
    return fetch.fetch_ticker(symbol, period=period)


# ── view-backed reads (see db/views.sql) ─────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def freshness() -> dict | None:
    return db.get_freshness()


@st.cache_data(ttl=300, show_spinner=False)
def market() -> pd.DataFrame:
    return db.get_market()


@st.cache_data(ttl=300, show_spinner=False)
def breadth_sp500(since=None) -> pd.DataFrame:
    return db.get_breadth_sp500(since=since)


@st.cache_data(ttl=300, show_spinner=False)
def perf(tickers: tuple | None = None) -> pd.DataFrame:
    return db.get_perf(list(tickers) if tickers else None)


@st.cache_data(ttl=300, show_spinner=False)
def shortlist_snapshot() -> pd.DataFrame:
    return db.get_shortlist_snapshot()


@st.cache_data(ttl=300, show_spinner=False)
def rel_perf(sym: str, bench: str, since) -> pd.DataFrame:
    return db.get_rel_perf(sym, bench, since)


@st.cache_data(ttl=300, show_spinner=False)
def prices_all(tickers: tuple | None = None, since=None) -> pd.DataFrame:
    return db.get_prices_all(list(tickers) if tickers else None, since=since)


@st.cache_data(ttl=300, show_spinner=False)
def highlow_52w(since=None) -> pd.DataFrame:
    return db.get_highlow_52w(since=since)


@st.cache_data(ttl=300, show_spinner=False)
def sector_rs(latest_only: bool = True) -> pd.DataFrame:
    return db.get_sector_rs(latest_only=latest_only)


@st.cache_data(ttl=300, show_spinner=False)
def forming_candles(sym: str, unit: str, since) -> pd.DataFrame:
    return db.get_forming_candles(sym, unit, since)


@st.cache_data(ttl=300, show_spinner=False)
def conditional_returns(
    universe_tickers: tuple | None, where_clause: str, horizon: int, since,
) -> dict:
    return db.conditional_returns(
        list(universe_tickers) if universe_tickers else None, where_clause, horizon, since,
    )


@st.cache_data(ttl=300, show_spinner=False)
def event_study(
    universe_tickers: tuple | None, where_clause: str, since,
    horizons: tuple = (1, 2, 3, 5, 10, 21, 42, 63, 126), max_events: int = 100,
) -> dict:
    return db.event_study(
        list(universe_tickers) if universe_tickers else None, where_clause, since,
        horizons=horizons, max_events=max_events,
    )


@st.cache_data(ttl=300, show_spinner=False)
def ichimoku(sym: str, since) -> pd.DataFrame:
    return db.get_ichimoku(sym, since)


@st.cache_data(ttl=300, show_spinner=False)
def ma_matrix() -> pd.DataFrame:
    return db.get_ma_matrix()


@st.cache_data(ttl=300, show_spinner=False)
def volume_profile_monthly(sym: str, since) -> pd.DataFrame:
    return db.get_volume_profile_monthly(sym, since)


@st.cache_data(ttl=300, show_spinner=False)
def setup_checklist() -> pd.DataFrame:
    """A-setup checklist inputs for every ticker in ONE query (v_latest +
    v_rs_spy join), sliced per ticker in memory by the Single Stock Viewer —
    see db.get_setup_checklist for why per-ticker queries were pointless."""
    return db.get_setup_checklist()


def invalidate() -> None:
    st.cache_data.clear()
