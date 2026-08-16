"""Index constituent lists (the Python equivalent of tidyquant::tq_index).

Pulls the current S&P 500 members (symbol, company name, GICS sector) from
Wikipedia. Yahoo wants dashes, not dots, in class-share tickers (BRK.B -> BRK-B).
"""
from __future__ import annotations

import pandas as pd

WIKI_SP500 = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
# Wikipedia 403s the default urllib user-agent.
_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def sp500_constituents() -> pd.DataFrame:
    """Return columns: ticker, name, sector (one row per member)."""
    tbl = pd.read_html(WIKI_SP500, storage_options=_UA)[0]
    out = pd.DataFrame({
        "ticker": (tbl["Symbol"].astype(str).str.upper()
                   .str.replace(".", "-", regex=False).str.strip()),
        "name": tbl["Security"].astype(str),
        "sector": tbl["GICS Sector"].astype(str),
    })
    return out.drop_duplicates("ticker").reset_index(drop=True)
