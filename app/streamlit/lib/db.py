"""All DuckDB access lives here.

Design notes:
- The app owns two tables: ``prices`` (OHLCV + indicators) and ``watchlist_meta``
  (your tracked tickers + setup/notes). It never touches the older tables that
  app/database.R writes, so nothing collides.
- Every call opens a short-lived connection and closes it. DuckDB allows only one
  writer process at a time, so holding a connection open would block RStudio (and
  vice-versa). Per-call connect keeps the lock window tiny.
"""
from __future__ import annotations

from pathlib import Path
import duckdb
import pandas as pd

# app/streamlit/lib/db.py -> parents[3] is the repo root.
DB_PATH = str(Path(__file__).resolve().parents[3] / "db" / "database.duckdb")

PRICES = "prices"            # watchlist OHLCV + indicators
META = "watchlist_meta"      # tracked tickers + notes
SP500 = "sp500"              # S&P 500 OHLCV + indicators (same schema as prices)
SP500_META = "sp500_meta"    # S&P 500 constituents: ticker, name, sector
TV_WATCHLIST = "tv_watchlist"  # imported TradingView watchlist (OHLCV + indicators)
DASHBOARD = "dashboard"        # RS-dashboard ETF groups (index/segment/sector)
SHORTLIST = "shortlist"        # user's shortlist (ticker, ord, note, added)

# db/views.sql -> the user's SQL extension point (views + table macros only).
VIEWS_SQL_PATH = Path(__file__).resolve().parents[3] / "db" / "views.sql"

_views_applied = False  # module-level "applied at most once per process" flag


class DBLocked(Exception):
    """Raised when the DuckDB file is held by another process."""


def _is_lock_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return "another process" in msg or "could not set lock" in msg or "being used" in msg


# ── low-level helpers ────────────────────────────────────────────────────────
def query(sql: str, params: list | None = None) -> pd.DataFrame:
    try:
        with duckdb.connect(DB_PATH, read_only=True) as con:
            return con.execute(sql, params or []).fetchdf()
    except Exception as e:  # noqa: BLE001
        if _is_lock_error(e):
            raise DBLocked(str(e)) from e
        raise


def execute(sql: str, params: list | None = None) -> None:
    try:
        with duckdb.connect(DB_PATH, read_only=False) as con:
            con.execute(sql, params or [])
    except Exception as e:  # noqa: BLE001
        if _is_lock_error(e):
            raise DBLocked(str(e)) from e
        raise


def has_table(name: str) -> bool:
    try:
        tbls = query("SELECT table_name FROM information_schema.tables")
        return name in tbls["table_name"].tolist()
    except Exception:  # noqa: BLE001
        return False


def _query_or_empty(sql: str, params: list | None = None) -> pd.DataFrame:
    """Like query(), but a missing view/macro/table returns an empty frame
    instead of raising. Used by hot read paths (Single Stock Viewer) so they
    don't pay a separate has_table() round-trip — each connection open costs
    ~50ms, so guard-query-then-real-query doubled the latency of every
    cache-miss. DBLocked still propagates (query() raises it first).
    """
    try:
        return query(sql, params)
    except DBLocked:
        raise
    except duckdb.CatalogException:
        return pd.DataFrame()


def status() -> dict:
    """Summary used by the Refresh tab / Home banner."""
    try:
        with duckdb.connect(DB_PATH, read_only=False):
            pass
        writable = True
    except Exception as e:  # noqa: BLE001
        if _is_lock_error(e):
            return {"ok": False, "writable": False,
                    "msg": "DuckDB is locked by another process (RStudio?). "
                           "Close that connection to enable refresh."}
        writable = False
    if not has_table(PRICES):
        return {"ok": True, "writable": writable,
                "msg": "Connected. No `prices` table yet — use Refresh to build it."}
    info = query(
        f"SELECT COUNT(*) n_rows, COUNT(DISTINCT ticker) n_tickers, MAX(date) last_date FROM {PRICES}"
    ).iloc[0]
    return {"ok": True, "writable": writable, "info": info.to_dict(),
            "msg": f"{int(info['n_rows']):,} rows · {int(info['n_tickers'])} tickers · latest {info['last_date']}"}


# ── prices (works for any OHLCV table: `prices` or `sp500`) ──────────────────
def _ensure_columns(con, table: str, df: pd.DataFrame) -> None:
    """Schema evolution: ALTER TABLE ADD COLUMN for any df column the table
    doesn't have yet. Lets fetch.py::compute_indicators grow new indicator
    columns (e.g. stoch_k, macd) and have them land in already-created tables
    on the next refresh, instead of `INSERT ... BY NAME` failing outright.
    """
    existing = {c.lower() for c in con.execute(f"DESCRIBE {table}").fetchdf()["column_name"]}
    for col in df.columns:
        if col.lower() in existing:
            continue
        dtype = df[col].dtype
        if pd.api.types.is_bool_dtype(dtype):
            sql_type = "BOOLEAN"
        elif pd.api.types.is_integer_dtype(dtype):
            sql_type = "BIGINT"
        elif pd.api.types.is_float_dtype(dtype):
            sql_type = "DOUBLE"
        elif pd.api.types.is_datetime64_any_dtype(dtype):
            sql_type = "TIMESTAMP"
        else:
            sql_type = "VARCHAR"
        con.execute(f'ALTER TABLE {table} ADD COLUMN "{col}" {sql_type}')


def upsert_prices(df: pd.DataFrame, table: str = PRICES) -> None:
    """Insert/replace rows for the tickers present in ``df`` (delete-then-insert)."""
    if df is None or df.empty:
        return
    tickers = df["ticker"].unique().tolist()
    placeholders = ", ".join(["?"] * len(tickers))
    with duckdb.connect(DB_PATH, read_only=False) as con:
        con.register("df_tmp", df)
        if table not in con.execute("SHOW TABLES").fetchdf()["name"].tolist():
            con.execute(f"CREATE TABLE {table} AS SELECT * FROM df_tmp")
        else:
            _ensure_columns(con, table, df)
            con.execute(f"DELETE FROM {table} WHERE ticker IN ({placeholders})", tickers)
            con.execute(f"INSERT INTO {table} BY NAME SELECT * FROM df_tmp")
        con.unregister("df_tmp")


def get_history(tickers: list | None = None, since=None, table: str = PRICES) -> pd.DataFrame:
    if not has_table(table):
        return pd.DataFrame()
    clauses, params = [], []
    if tickers:
        clauses.append(f"ticker IN ({', '.join(['?'] * len(tickers))})")
        params += [t.upper() for t in tickers]
    if since is not None:
        clauses.append("date >= ?")
        params.append(pd.to_datetime(since).date())
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    df = query(f"SELECT * FROM {table}{where} ORDER BY ticker, date", params)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
    return df


def get_snapshot(tickers: list | None = None, table: str = PRICES) -> pd.DataFrame:
    if not has_table(table):
        return pd.DataFrame()
    clause, params = "", []
    if tickers:
        clause = f"WHERE ticker IN ({', '.join(['?'] * len(tickers))})"
        params = [t.upper() for t in tickers]
    df = query(
        f"""
        SELECT p.* FROM {table} p
        JOIN (SELECT ticker, MAX(date) md FROM {table} {clause} GROUP BY ticker) m
          ON p.ticker = m.ticker AND p.date = m.md
        """,
        params,
    )
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
    return df


def list_tickers(table: str = PRICES) -> list[str]:
    if not has_table(table):
        return []
    return query(f"SELECT DISTINCT ticker FROM {table} ORDER BY ticker")["ticker"].tolist()


def get_freshness() -> dict | None:
    """MAX(date) across every OHLCV table (prices/sp500/tv_watchlist/dashboard).

    Cheap: uses v_prices_all if present (already deduped), else falls back to
    scanning `prices` alone so the Dashboard freshness stamp still works before
    views have been applied. Returns None if there's no data at all.
    """
    table = "v_prices_all" if has_table("v_prices_all") else (PRICES if has_table(PRICES) else None)
    if table is None:
        return None
    row = query(f"SELECT MAX(date) AS last_date FROM {table}").iloc[0]
    if pd.isna(row["last_date"]):
        return None
    last_date = pd.to_datetime(row["last_date"]).date()
    days_old = (pd.Timestamp.today().normalize().date() - last_date).days
    return {"last_date": last_date, "days_old": days_old}


def table_info(table: str) -> dict | None:
    """Row/ticker/last-date summary for any OHLCV table, or None if absent/empty."""
    if not has_table(table):
        return None
    info = query(
        f"SELECT COUNT(*) n_rows, COUNT(DISTINCT ticker) n_tickers, MAX(date) last_date FROM {table}"
    ).iloc[0]
    if int(info["n_rows"]) == 0:
        return None
    return {"rows": int(info["n_rows"]), "tickers": int(info["n_tickers"]),
            "last_date": info["last_date"]}


# ── views (see db/views.sql — call ensure_views() before using these) ────────
def get_market() -> pd.DataFrame:
    """Latest row of v_market (SPY/VIX/VIX3M/TNX), forward-filling sparser series.

    VIX3M/TNX don't always land on the same trading day as SPY, so a plain
    "last row" can show NaN ratios. Take the latest SPY row, then backfill any
    null column from the most recent prior date where it was populated.
    """
    if not has_table("v_market"):
        return pd.DataFrame()
    df = query("SELECT * FROM v_market ORDER BY date DESC LIMIT 30")
    if df.empty:
        return df
    df["date"] = pd.to_datetime(df["date"])
    latest = df.iloc[0].copy()
    for col in df.columns:
        if col != "date" and pd.isna(latest[col]):
            non_null = df[col].dropna()
            if not non_null.empty:
                latest[col] = non_null.iloc[0]
    return latest.to_frame().T


def get_breadth_sp500(since=None) -> pd.DataFrame:
    if not has_table("v_breadth_sp500"):
        return pd.DataFrame()
    clause, params = "", []
    if since is not None:
        clause = "WHERE date >= ?"
        params = [pd.to_datetime(since).date()]
    df = query(f"SELECT * FROM v_breadth_sp500 {clause} ORDER BY date", params)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
    return df


def get_perf(tickers: list | None = None) -> pd.DataFrame:
    if not has_table("v_perf"):
        return pd.DataFrame()
    clause, params = "", []
    if tickers:
        clause = f"WHERE ticker IN ({', '.join(['?'] * len(tickers))})"
        params = [t.upper() for t in tickers]
    return query(f"SELECT * FROM v_perf {clause}", params)


def get_shortlist_snapshot() -> pd.DataFrame:
    """v_shortlist: shortlist joined to latest snapshot, RS-vs-SPY, and trailing perf."""
    if not has_table("v_shortlist"):
        return pd.DataFrame()
    return query("SELECT * FROM v_shortlist ORDER BY ord")


def get_rel_perf(sym: str, bench: str, since) -> pd.DataFrame:
    """Normalized ticker vs. benchmark + RS line, via the rel_perf() table macro."""
    df = _query_or_empty(
        "SELECT * FROM rel_perf(?, ?, ?)",
        [sym.upper().strip(), bench.upper().strip(), pd.to_datetime(since).date()],
    )
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
    return df


def get_highlow_52w(since=None) -> pd.DataFrame:
    """v_highlow_52w: per-date new-52w-high/low counts across the S&P 500."""
    if not has_table("v_highlow_52w"):
        return pd.DataFrame()
    clause, params = "", []
    if since is not None:
        clause = "WHERE date >= ?"
        params = [pd.to_datetime(since).date()]
    df = query(f"SELECT * FROM v_highlow_52w {clause} ORDER BY date", params)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
    return df


def get_sector_rs(latest_only: bool = True) -> pd.DataFrame:
    """v_sector_rs: equal-weighted sector RS vs. SPY (21d/63d), one row per sector/date.

    latest_only=True filters to the most recent date server-side (cheap: the
    view is already ordered/small — 11 sectors × trading days).
    """
    if not has_table("v_sector_rs"):
        return pd.DataFrame()
    clause = "WHERE date = (SELECT max(date) FROM v_sector_rs)" if latest_only else ""
    df = query(f"SELECT * FROM v_sector_rs {clause} ORDER BY rs_1m DESC")
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
    return df


def get_forming_candles(sym: str, unit: str, since) -> pd.DataFrame:
    """forming_candles(sym, unit, since) — cumulative MTD/WTD candle per day.

    `unit` is 'month' or 'week'.
    """
    df = _query_or_empty(
        "SELECT * FROM forming_candles(?, ?, ?)",
        [sym.upper().strip(), unit, pd.to_datetime(since).date()],
    )
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
        df["period_start"] = pd.to_datetime(df["period_start"])
    return df


def conditional_returns(
    universe_tickers: list[str] | None,
    where_clause: str,
    horizon: int,
    since,
    baseline_sample: int = 50_000,
) -> dict:
    """SQL-first conditional forward-return backtest (Returns Lab).

    Builds one query over v_prices_all filtered to `universe_tickers` (None =
    every ticker) and `since`, LEFT JOINed to v_market by date (so conditions
    can reference market-state columns — vix_ratio, vix_close, tnx_close —
    alongside per-ticker ones), computes the forward return over `horizon`
    trading days via LEAD, then splits into "matched" (rows where
    `where_clause` — a raw user-typed SQL WHERE fragment — is true) vs. the
    full "baseline". Returns a dict with:
        stats        1-row DataFrame: n/win_rate/avg/median/stdev for both
        matched      matched rows (date, ticker, close, fwd_ret, + a fixed
                     set of indicator columns) for the table + histogram
        baseline_ret fwd_ret Series for the baseline histogram (sampled down
                     to `baseline_sample` rows if larger)
        sql          the exact SQL executed, so it can be shown/copied
    Raises whatever duckdb raises on a bad where_clause (caller should catch
    and show the error + the SQL).
    """
    clauses, params = [], []
    if universe_tickers:
        clauses.append(f"p.ticker IN ({', '.join(['?'] * len(universe_tickers))})")
        params += [t.upper() for t in universe_tickers]
    if since is not None:
        clauses.append("p.date >= ?")
        params.append(pd.to_datetime(since).date())
    where_universe = (" WHERE " + " AND ".join(clauses)) if clauses else ""

    sql = f"""
    WITH base AS (
        SELECT p.* EXCLUDE (date), p.date AS date, m.vix_close, m.vix3m_close, m.vix_ratio, m.tnx_close,
               LEAD(p.close, {int(horizon)}) OVER (
                   PARTITION BY p.ticker ORDER BY p.date
               ) / NULLIF(p.close, 0) - 1 AS fwd_ret
        FROM v_prices_all p
        LEFT JOIN v_market m ON m.date = p.date
        {where_universe}
    ),
    scored AS (
        SELECT *, ({where_clause}) AS is_match
        FROM base
        WHERE fwd_ret IS NOT NULL
    )
    SELECT
        count(*) FILTER (WHERE is_match)                       AS n_matched,
        avg(CASE WHEN fwd_ret > 0 THEN 1.0 ELSE 0.0 END) FILTER (WHERE is_match) AS win_rate_matched,
        avg(fwd_ret) FILTER (WHERE is_match)                    AS avg_matched,
        median(fwd_ret) FILTER (WHERE is_match)                 AS median_matched,
        stddev(fwd_ret) FILTER (WHERE is_match)                 AS stdev_matched,
        count(*)                                                AS n_baseline,
        avg(CASE WHEN fwd_ret > 0 THEN 1.0 ELSE 0.0 END)        AS win_rate_baseline,
        avg(fwd_ret)                                            AS avg_baseline,
        median(fwd_ret)                                         AS median_baseline,
        stddev(fwd_ret)                                         AS stdev_baseline
    FROM scored
    """
    stats = query(sql, params)

    matched_sql = f"""
    WITH base AS (
        SELECT p.* EXCLUDE (date), p.date AS date, m.vix_close, m.vix3m_close, m.vix_ratio, m.tnx_close,
               LEAD(p.close, {int(horizon)}) OVER (
                   PARTITION BY p.ticker ORDER BY p.date
               ) / NULLIF(p.close, 0) - 1 AS fwd_ret
        FROM v_prices_all p
        LEFT JOIN v_market m ON m.date = p.date
        {where_universe}
    )
    SELECT ticker, date, close, fwd_ret, rsi, sma50_atr_ext, pct_sma200, rel_vol, adr
    FROM base
    WHERE fwd_ret IS NOT NULL AND ({where_clause})
    ORDER BY date DESC
    """
    matched = query(matched_sql, params)
    if not matched.empty:
        matched["date"] = pd.to_datetime(matched["date"])

    baseline_sql = f"""
    WITH base AS (
        SELECT p.*,
               LEAD(p.close, {int(horizon)}) OVER (
                   PARTITION BY p.ticker ORDER BY p.date
               ) / NULLIF(p.close, 0) - 1 AS fwd_ret
        FROM v_prices_all p
        {where_universe}
    )
    SELECT fwd_ret
    FROM base
    WHERE fwd_ret IS NOT NULL
    USING SAMPLE {int(baseline_sample)} ROWS
    """
    baseline = query(baseline_sql, params)
    baseline_ret = baseline["fwd_ret"] if not baseline.empty else pd.Series(dtype=float)

    return {"stats": stats, "matched": matched, "baseline_ret": baseline_ret, "sql": sql}


def get_ichimoku(sym: str, since) -> pd.DataFrame:
    """ichimoku(sym, since) — Tenkan/Kijun/Senkou A&B (forward-shifted via plot_date)/Chikou."""
    df = _query_or_empty("SELECT * FROM ichimoku(?, ?)",
                         [sym.upper().strip(), pd.to_datetime(since).date()])
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
        df["plot_date"] = pd.to_datetime(df["plot_date"])
    return df


def get_ma_matrix() -> pd.DataFrame:
    """v_ma_matrix: latest above/below-MA snapshot for the benchmark list."""
    if not has_table("v_ma_matrix"):
        return pd.DataFrame()
    return query("SELECT * FROM v_ma_matrix ORDER BY ticker")


def get_volume_profile_monthly(sym: str, since) -> pd.DataFrame:
    """volume_profile_monthly(sym, since) — per-month VPOC + 70% value area."""
    df = _query_or_empty(
        "SELECT * FROM volume_profile_monthly(?, ?)",
        [sym.upper().strip(), pd.to_datetime(since).date()],
    )
    if not df.empty:
        df["month_start"] = pd.to_datetime(df["month_start"])
        df["month_end"] = pd.to_datetime(df["month_end"])
    return df


def event_study(
    universe_tickers: list[str] | None,
    where_clause: str,
    since,
    horizons: tuple[int, ...] = (1, 2, 3, 5, 10, 21, 42, 63, 126),
    max_events: int = 100,
) -> dict:
    """Per-event forward % change at multiple horizons (Returns Lab "Event study").

    One query computes LEAD(close, h) for every horizon in `horizons`, then
    filters to rows where `where_clause` is true. Returns the most recent
    `max_events` matched rows (date desc) plus the total match count so the
    caller can show a "showing N of M" caption when truncated.
    """
    clauses, params = [], []
    if universe_tickers:
        clauses.append(f"p.ticker IN ({', '.join(['?'] * len(universe_tickers))})")
        params += [t.upper() for t in universe_tickers]
    if since is not None:
        clauses.append("p.date >= ?")
        params.append(pd.to_datetime(since).date())
    where_universe = (" WHERE " + " AND ".join(clauses)) if clauses else ""

    horizon_cols = ",\n           ".join(
        f"(LEAD(p.close, {int(h)}) OVER (PARTITION BY p.ticker ORDER BY p.date) / NULLIF(p.close, 0) - 1) * 100 AS h{h}"
        for h in horizons
    )
    sql = f"""
    WITH base AS (
        SELECT p.* EXCLUDE (date), p.date AS date, m.vix_close, m.vix3m_close, m.vix_ratio, m.tnx_close,
               {horizon_cols}
        FROM v_prices_all p
        LEFT JOIN v_market m ON m.date = p.date
        {where_universe}
    )
    SELECT ticker, date, close, {', '.join(f'h{h}' for h in horizons)}
    FROM base
    WHERE ({where_clause})
    ORDER BY date DESC
    """
    all_matched = query(sql, params)
    n_total = len(all_matched)
    events = all_matched.head(max_events).copy()
    if not events.empty:
        events["date"] = pd.to_datetime(events["date"])
    return {"events": events, "n_total": n_total, "horizons": horizons, "sql": sql}


def get_setup_checklist() -> pd.DataFrame:
    """A-setup checklist inputs for EVERY ticker in one query: the v_latest
    columns the checklist needs joined to v_rs_spy's rs_1m. One row per ticker.

    The Single Stock Viewer used to run two per-ticker queries (v_latest +
    v_rs_spy) on every rerun — both views recompute window functions over the
    whole universe regardless of the ticker filter, so per-ticker queries buy
    nothing. Fetch all tickers once (cached in data.setup_checklist, ttl 300)
    and slice per ticker in memory instead.
    """
    return _query_or_empty(
        """
        SELECT l.ticker, l.sma50_atr_ext, l.lod_atr_pct, l.sma200_rising,
               l.sma10_rising, l.rel_vol, r.rs_1m
        FROM v_latest l
        LEFT JOIN v_rs_spy r ON r.ticker = l.ticker
        """
    )


def get_prices_all(tickers: list | None = None, since=None) -> pd.DataFrame:
    """Read from v_prices_all (the deduplicated union of all OHLCV tables)."""
    clauses, params = [], []
    if tickers:
        clauses.append(f"ticker IN ({', '.join(['?'] * len(tickers))})")
        params += [t.upper() for t in tickers]
    if since is not None:
        clauses.append("date >= ?")
        params.append(pd.to_datetime(since).date())
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    df = _query_or_empty(f"SELECT * FROM v_prices_all{where} ORDER BY ticker, date", params)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
    return df


# ── watchlist_meta (tracked tickers + notes) ─────────────────────────────────
def ensure_meta() -> None:
    execute(
        f"""CREATE TABLE IF NOT EXISTS {META} (
                ticker VARCHAR PRIMARY KEY,
                note   VARCHAR,
                added  DATE
            )"""
    )
    # Migrate away the legacy `setup` column if an older table still has it.
    try:
        if "setup" in query(f"SELECT * FROM {META} LIMIT 0").columns.tolist():
            execute(f"ALTER TABLE {META} DROP COLUMN setup")
    except Exception:  # noqa: BLE001
        pass


def seed_meta(tickers: list[str]) -> None:
    ensure_meta()
    if query(f"SELECT COUNT(*) n FROM {META}").iloc[0]["n"] > 0:
        return
    rows = pd.DataFrame({
        "ticker": [t.upper() for t in tickers],
        "note": "", "added": pd.Timestamp.today().date(),
    })
    with duckdb.connect(DB_PATH, read_only=False) as con:
        con.register("seed_tmp", rows)
        con.execute(f"INSERT INTO {META} BY NAME SELECT * FROM seed_tmp")
        con.unregister("seed_tmp")


def get_meta() -> pd.DataFrame:
    if not has_table(META):
        return pd.DataFrame(columns=["ticker", "setup", "note", "added"])
    return query(f"SELECT * FROM {META} ORDER BY ticker")


def upsert_meta(ticker: str, note: str = "") -> None:
    ensure_meta()
    execute(
        f"""INSERT INTO {META} (ticker, note, added)
            VALUES (?, ?, ?)
            ON CONFLICT (ticker) DO UPDATE SET note = excluded.note""",
        [ticker.upper().strip(), note, pd.Timestamp.today().date()],
    )


def delete_meta(ticker: str) -> None:
    execute(f"DELETE FROM {META} WHERE ticker = ?", [ticker.upper().strip()])


# ── S&P 500 constituents ─────────────────────────────────────────────────────
def save_sp500_meta(df: pd.DataFrame) -> None:
    """Replace the constituents table (ticker, name, sector)."""
    clean = df[["ticker", "name", "sector"]].copy()
    clean["ticker"] = clean["ticker"].astype(str).str.upper().str.strip()
    with duckdb.connect(DB_PATH, read_only=False) as con:
        con.register("sp_tmp", clean)
        con.execute(f"CREATE OR REPLACE TABLE {SP500_META} AS SELECT * FROM sp_tmp")
        con.unregister("sp_tmp")


def get_sp500_meta() -> pd.DataFrame:
    if not has_table(SP500_META):
        return pd.DataFrame(columns=["ticker", "name", "sector"])
    return query(f"SELECT * FROM {SP500_META} ORDER BY ticker")


PRICES_ALL_MAT = "prices_all_mat"  # materialized v_prices_all_raw — see rebuild_prices_all()


def rebuild_prices_all(con: "duckdb.DuckDBPyConnection | None" = None) -> None:
    """(Re-)materialize `prices_all_mat` from the `v_prices_all_raw` view.

    `v_prices_all_raw` (db/views.sql) is the expensive UNION ALL BY NAME +
    QUALIFY row_number() dedup of prices/dashboard/sp500/tv_watchlist —
    ~750k+ rows recomputed from scratch on every read if left as a plain view.
    `v_prices_all` is a thin view over this table instead, so every downstream
    reader (v_latest, v_rs_spy, ichimoku, rel_perf, volume_profile_monthly,
    forming_candles, the Single Stock Viewer, ...) gets a fast table scan.

    Call this after any write that touches prices/dashboard/sp500/tv_watchlist
    (quick_refresh, Ticker Database pulls, the Dashboard shortlist add-ticker
    fetch) so `prices_all_mat` doesn't go stale. Pass an existing connection to
    reuse it (e.g. from inside apply_views' own connection); otherwise a
    short-lived write connection is opened and closed here.

    DBLocked-safe: if the write can't get the lock, the old `prices_all_mat`
    is simply left in place (stale-but-correct beats no data) and DBLocked
    propagates so the caller can show its usual "locked" message.
    """
    # ORDER BY ticker, date so DuckDB's per-row-group zone maps can prune
    # single-ticker scans (the app's hottest access pattern) instead of
    # scanning all ~750k rows every time.
    sql = ("CREATE OR REPLACE TABLE prices_all_mat AS "
           "SELECT * FROM v_prices_all_raw ORDER BY ticker, date")
    try:
        if con is not None:
            con.execute(sql)
            return
        with duckdb.connect(DB_PATH, read_only=False) as con2:
            con2.execute(sql)
    except Exception as e:  # noqa: BLE001
        if _is_lock_error(e):
            raise DBLocked(str(e)) from e
        raise


def apply_views() -> None:
    """(Re-)run db/views.sql — CREATE OR REPLACE VIEW / MACRO statements only.

    Safe to call any time: every statement in the file is idempotent. Executes
    the whole file as one script on a single short-lived write connection.
    `v_shortlist` depends on the `shortlist` table, so make sure that exists
    first (views.sql itself stays view/macro-only, per the file's own rule).

    Ordering for `v_prices_all` (see db/views.sql): the file defines
    `v_prices_all_raw` (the union/dedup SQL) then `v_prices_all AS SELECT *
    FROM prices_all_mat`. DuckDB views are late-binding for *existing* tables
    but a CREATE VIEW that references a table that has NEVER existed fails
    immediately (verified: unlike Postgres, DuckDB validates the referenced
    catalog entry exists at creation time, not just at query time) — so on a
    completely fresh DB the script would fail on the `v_prices_all` statement.
    We guarantee `prices_all_mat` exists first with a cheap `LIMIT 0` schema-only
    create (no-op if it already exists — doesn't touch real data), then run the
    file, then do the real (possibly slow) rebuild.
    """
    sql = VIEWS_SQL_PATH.read_text(encoding="utf-8")
    try:
        with duckdb.connect(DB_PATH, read_only=False) as con:
            con.execute(
                f"""CREATE TABLE IF NOT EXISTS {SHORTLIST} (
                        ticker VARCHAR PRIMARY KEY,
                        ord    INTEGER,
                        note   VARCHAR,
                        added  DATE
                    )"""
            )
            # v_prices_all_raw must exist before we can even probe its schema,
            # and v_prices_all (later in the same script) needs prices_all_mat
            # to already exist — so create the raw view first, stub the mat
            # table's schema (cheap, LIMIT 0, no-op if already there), then run
            # the whole file (which re-creates v_prices_all_raw harmlessly and
            # adds v_prices_all + everything downstream).
            con.execute(_extract_statement(sql, "v_prices_all_raw"))
            con.execute(f"CREATE TABLE IF NOT EXISTS {PRICES_ALL_MAT} AS "
                        f"SELECT * FROM v_prices_all_raw LIMIT 0")
            con.execute(sql)
        # Real rebuild (can be slower — full union/dedup scan) after the
        # script has committed, on its own short-lived connection. If this
        # raises DBLocked, the stub/previous prices_all_mat stays in place.
        rebuild_prices_all()
    except Exception as e:  # noqa: BLE001
        if _is_lock_error(e):
            raise DBLocked(str(e)) from e
        raise


def _extract_statement(sql: str, view_or_macro_name: str) -> str:
    """Pull out a single `CREATE OR REPLACE VIEW/MACRO <name> AS ...;` statement
    from views.sql by name, so apply_views() can create `v_prices_all_raw`
    before running the rest of the file (see apply_views' docstring).
    """
    marker = f"VIEW {view_or_macro_name} AS"
    idx = sql.index(marker)
    end = sql.index(";", idx) + 1
    start = sql.rindex("CREATE", 0, idx)
    return sql[start:end]


def ensure_views() -> None:
    """Apply views.sql at most once per process.

    If the DB is locked, views may already exist from a previous run — check
    for one of them (v_latest) and proceed read-only without complaint. Only
    re-raise DBLocked when the views are missing entirely (nothing to read).
    """
    global _views_applied
    if _views_applied:
        return
    try:
        apply_views()
        _views_applied = True
    except DBLocked:
        if has_table("v_latest"):
            _views_applied = True  # views already exist; read-only is fine
            return
        raise


# ── shortlist ─────────────────────────────────────────────────────────────────
def ensure_shortlist() -> None:
    execute(
        f"""CREATE TABLE IF NOT EXISTS {SHORTLIST} (
                ticker VARCHAR PRIMARY KEY,
                ord    INTEGER,
                note   VARCHAR,
                added  DATE
            )"""
    )


def get_shortlist() -> pd.DataFrame:
    if not has_table(SHORTLIST):
        return pd.DataFrame(columns=["ticker", "ord", "note", "added"])
    return query(f"SELECT * FROM {SHORTLIST} ORDER BY ord")


def add_to_shortlist(ticker: str, note: str = "") -> None:
    ensure_shortlist()
    ticker = ticker.upper().strip()
    if not ticker:
        return
    next_ord = query(f"SELECT COALESCE(MAX(ord), -1) + 1 AS n FROM {SHORTLIST}").iloc[0]["n"]
    execute(
        f"""INSERT INTO {SHORTLIST} (ticker, ord, note, added)
            VALUES (?, ?, ?, ?)
            ON CONFLICT (ticker) DO NOTHING""",
        [ticker, int(next_ord), note, pd.Timestamp.today().date()],
    )


def remove_from_shortlist(ticker: str) -> None:
    execute(f"DELETE FROM {SHORTLIST} WHERE ticker = ?", [ticker.upper().strip()])


def move_in_shortlist(ticker: str, direction: int) -> None:
    """Swap `ticker`'s ord with its neighbor. direction: -1 = up, +1 = down."""
    df = get_shortlist()
    if df.empty or ticker not in df["ticker"].tolist():
        return
    df = df.sort_values("ord").reset_index(drop=True)
    idx = df.index[df["ticker"] == ticker][0]
    swap_idx = idx + direction
    if swap_idx < 0 or swap_idx >= len(df):
        return
    ord_a, ord_b = df.loc[idx, "ord"], df.loc[swap_idx, "ord"]
    tk_a, tk_b = df.loc[idx, "ticker"], df.loc[swap_idx, "ticker"]
    with duckdb.connect(DB_PATH, read_only=False) as con:
        con.execute(f"UPDATE {SHORTLIST} SET ord = ? WHERE ticker = ?", [int(ord_b), tk_a])
        con.execute(f"UPDATE {SHORTLIST} SET ord = ? WHERE ticker = ?", [int(ord_a), tk_b])


def save_meta(df: pd.DataFrame) -> None:
    """Replace the whole watchlist_meta table (used by the editable notes grid)."""
    clean = df.copy()
    clean["ticker"] = clean["ticker"].astype(str).str.upper().str.strip()
    clean = clean[clean["ticker"] != ""].drop_duplicates(subset="ticker", keep="last")
    if "note" not in clean.columns:
        clean["note"] = ""
    clean["note"] = clean["note"].fillna("").astype(str)
    if "added" not in clean.columns or clean["added"].isna().all():
        clean["added"] = pd.Timestamp.today().date()
    clean = clean[["ticker", "note", "added"]]
    ensure_meta()
    with duckdb.connect(DB_PATH, read_only=False) as con:
        con.register("meta_tmp", clean)
        con.execute(f"CREATE OR REPLACE TABLE {META} AS SELECT * FROM meta_tmp")
        con.unregister("meta_tmp")
