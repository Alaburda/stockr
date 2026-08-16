"""Shared RS-grid rendering: the heat-mapped st.dataframe `section()` helper
and its column_config, used by both pages/1_Watchlist.py and the "RS boards"
tab on pages/0_Dashboard.py so the two never drift out of sync.
"""
from __future__ import annotations

import streamlit as st

from lib import rs
from lib import glossary

BASE_COLS = ["ticker", "name", "rs_thrust", "rs_1m", "spark",
             "pct_intraday", "pct_1d", "pct_1m", "pct_off_52w"]
# Detailed per-stock view for the Watchlist section.
WATCHLIST_COLS = ["ticker", "close", "sma10", "sma20", "ema8", "ema21", "rsi",
                  "rs_1m", "atr_ext", "spark", "adr_pct", "mom", "vol_sma20"]

COLCFG = {
    "ticker": st.column_config.TextColumn("Ticker", width="small"),
    "name": st.column_config.TextColumn("Name", width="medium"),
    "rs_thrust": st.column_config.NumberColumn("RS Thrust", format="%.0f%%", width="small"),
    "rs_1m": st.column_config.NumberColumn("1-Mth RS", format="%.0f%%", width="small"),
    "spark": st.column_config.LineChartColumn("1-Mth", width="small"),
    "pct_intraday": st.column_config.NumberColumn("% Intraday", format="%.1f%%", width="small"),
    "pct_1d": st.column_config.NumberColumn("% 1D", format="%.1f%%", width="small"),
    "pct_1m": st.column_config.NumberColumn("% 1-Mth", format="%.1f%%", width="small"),
    "pct_off_52w": st.column_config.NumberColumn("% Off 52W H", format="%.0f%%", width="small"),
    "adr_pct": st.column_config.NumberColumn("ADR %", format="%.1f%%", width="small",
                                             help="Average daily range as % of price."),
    "mom": st.column_config.TextColumn("Mom", width="small", help=glossary.HELP["mom"]),
    "vol_sma20": st.column_config.NumberColumn("Vol 20d (M)", format="%.1f", width="small",
                                               help="20-day average volume, in millions."),
    "close": st.column_config.NumberColumn("Close", format="%.2f", width="small"),
    "sma10": st.column_config.NumberColumn("10 MA", format="%.2f", width="small"),
    "sma20": st.column_config.NumberColumn("20 MA", format="%.2f", width="small"),
    "ema8": st.column_config.NumberColumn("8 EMA", format="%.2f", width="small"),
    "ema21": st.column_config.NumberColumn("21 EMA", format="%.2f", width="small"),
    "rsi": st.column_config.NumberColumn("RSI", format="%.0f", width="small"),
    "atr_ext": st.column_config.NumberColumn("ATR ext", format="%.2f", width="small",
                                             help="ATRs above/below the 50-day SMA."),
}


def section(title, hist, bench, names=None, expander=False, height=None, cols=None):
    """Render one heat-mapped RS table. `bench` is the benchmark close Series
    (indexed by date) passed to rs.compute_dashboard — same for every section
    on a page (SPY by default).
    """
    cols = cols or BASE_COLS
    if hist is None or hist.empty:
        st.caption(f"**{title}** — no data yet (use the Ticker Database tab).")
        return
    d = rs.compute_dashboard(hist, bench, names=names)
    if d.empty:
        st.caption(f"**{title}** — no data.")
        return
    d = d[cols].copy()
    if "vol_sma20" in cols:
        d["vol_sma20"] = d["vol_sma20"] / 1e6  # show volume in millions
    box = st.expander(f"{title}  ·  {len(d)} symbols", expanded=False) if expander else st.container()
    kwargs = dict(column_config=COLCFG, hide_index=True, use_container_width=True)
    if height is not None:
        kwargs["height"] = height
    with box:
        if not expander:
            st.subheader(title)
        st.dataframe(rs.style(d), **kwargs)
