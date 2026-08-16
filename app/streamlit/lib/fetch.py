"""Yahoo fetch + indicator computation — THE canonical data shape.

fetch_ticker("AAPL") returns a DataFrame whose columns are exactly what the
``prices`` table stores and what the charts expect. Add an indicator here and it
flows through the whole app.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import yfinance as yf


def _naive_dates(series: pd.Series) -> pd.Series:
    """Coerce a date/datetime column to tz-naive, normalized days.

    yf.Ticker().history() returns tz-aware dates; yf.download() returns tz-naive.
    """
    d = pd.to_datetime(series)
    if getattr(d.dt, "tz", None) is not None:
        d = d.dt.tz_localize(None)
    return d.dt.normalize()


def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values("date").reset_index(drop=True)
    c, h, l, v = df["close"], df["high"], df["low"], df["volume"]

    df["sma10"] = c.rolling(10).mean()
    df["sma20"] = c.rolling(20).mean()
    df["sma50"] = c.rolling(50).mean()
    df["sma100"] = c.rolling(100).mean()
    df["sma200"] = c.rolling(200).mean()
    df["ema8"] = c.ewm(span=8, adjust=False).mean()
    df["ema21"] = c.ewm(span=21, adjust=False).mean()

    # ATR (Wilder smoothing)
    prev_c = c.shift(1)
    tr = pd.concat([(h - l), (h - prev_c).abs(), (l - prev_c).abs()], axis=1).max(axis=1)
    df["atr"] = tr.ewm(alpha=1 / 14, adjust=False).mean()

    # RSI (Wilder)
    delta = c.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / 14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / 14, adjust=False).mean()
    rs = avg_gain / avg_loss
    df["rsi"] = 100 - 100 / (1 + rs)

    # Bollinger (20, 2)
    mid = c.rolling(20).mean()
    sd = c.rolling(20).std()
    df["bb_mid"], df["bb_upper"], df["bb_lower"] = mid, mid + 2 * sd, mid - 2 * sd

    df["vol_ma20"] = v.rolling(20).mean()
    df["roc12"] = (c / c.shift(12) - 1) * 100
    df["roc2"] = (c / c.shift(2) - 1) * 100

    # Stochastic oscillator (14, 3): %K from the 14-day high/low range, %D is
    # its 3-day SMA. Guard the denominator (flat 14-day range) with NaN-safe
    # division so a div-by-zero doesn't blow up into +/-inf.
    low14 = l.rolling(14).min()
    high14 = h.rolling(14).max()
    denom14 = (high14 - low14).replace(0, np.nan)
    df["stoch_k"] = (c - low14) / denom14 * 100
    df["stoch_d"] = df["stoch_k"].rolling(3).mean()

    # StochRSI (14, 14, 3, 3): the stochastic formula applied to RSI itself
    # instead of price, then smoothed the same way (%K = 3-SMA of the raw
    # stochastic-of-RSI, %D = 3-SMA of %K — the common charting convention).
    rsi_series = df["rsi"]
    rsi_low14 = rsi_series.rolling(14).min()
    rsi_high14 = rsi_series.rolling(14).max()
    rsi_denom14 = (rsi_high14 - rsi_low14).replace(0, np.nan)
    stochrsi_raw = (rsi_series - rsi_low14) / rsi_denom14 * 100
    df["stochrsi_k"] = stochrsi_raw.rolling(3).mean()
    df["stochrsi_d"] = df["stochrsi_k"].rolling(3).mean()

    # MACD (12, 26, 9): EMA12 - EMA26, its 9-EMA signal line, and the
    # histogram (macd - signal).
    ema12 = c.ewm(span=12, adjust=False).mean()
    ema26 = c.ewm(span=26, adjust=False).mean()
    df["macd"] = ema12 - ema26
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"] = df["macd"] - df["macd_signal"]

    df["adr"] = (h - l) / c
    df["rel_vol"] = v / df["vol_ma20"]
    df["pct_ema8"] = (c - df["ema8"]) / df["ema8"] * 100
    df["pct_sma200"] = (c - df["sma200"]) / df["sma200"] * 100
    df["sma50_atr_ext"] = ((c - df["sma50"]) / c) / (df["atr"] / c)
    df["above_ema8"] = c > df["ema8"]
    df["above_ema21"] = c > df["ema21"]

    df["ret_1d"] = c.pct_change().round(4)              # trailing daily change
    df["change_1d"] = (c.shift(-1) / c - 1).round(4)    # forward returns
    df["change_1w"] = (c.shift(-5) / c - 1).round(4)
    df["change_1m"] = (c.shift(-21) / c - 1).round(4)

    df = df.replace([np.inf, -np.inf], np.nan)
    return df


def fetch_ticker(symbol: str, period: str = "5y") -> pd.DataFrame | None:
    sym = symbol.upper().strip()
    try:
        raw = yf.Ticker(sym).history(period=period, auto_adjust=True)
    except Exception:  # noqa: BLE001
        return None
    if raw is None or raw.empty:
        return None

    raw = raw.reset_index()
    # The datetime column is "Date" for daily data; normalize whatever it is.
    date_col = "Date" if "Date" in raw.columns else raw.columns[0]
    out = pd.DataFrame({
        "ticker": sym,
        "date": _naive_dates(raw[date_col]),
        "open": raw["Open"].astype(float),
        "high": raw["High"].astype(float),
        "low": raw["Low"].astype(float),
        "close": raw["Close"].astype(float),
        "volume": raw["Volume"].astype(float),
    })
    out = out.dropna(subset=["close"])
    if len(out) < 2:
        return None
    return compute_indicators(out)


def fetch_many(symbols: list[str], period: str = "5y", progress=None) -> pd.DataFrame:
    frames, n = [], len(symbols)
    for i, sym in enumerate(symbols):
        if progress is not None:
            progress(i / max(n, 1), sym)
        df = fetch_ticker(sym, period=period)
        if df is not None and not df.empty:
            frames.append(df)
    if progress is not None:
        progress(1.0, "done")
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def _one_ticker_from_bulk(sym: str, sub: pd.DataFrame) -> pd.DataFrame | None:
    sub = sub.dropna(how="all")
    if sub.empty:
        return None
    raw = sub.reset_index()
    date_col = "Date" if "Date" in raw.columns else raw.columns[0]
    try:
        out = pd.DataFrame({
            "ticker": sym,
            "date": _naive_dates(raw[date_col]),
            "open": raw["Open"].astype(float),
            "high": raw["High"].astype(float),
            "low": raw["Low"].astype(float),
            "close": raw["Close"].astype(float),
            "volume": raw["Volume"].astype(float),
        }).dropna(subset=["close"])
    except (KeyError, ValueError):
        return None
    return compute_indicators(out) if len(out) >= 2 else None


def fetch_bulk(symbols: list[str], period: str = "2y", chunk: int = 60, progress=None) -> pd.DataFrame:
    """Threaded download for large universes (e.g. the S&P 500).

    Much faster than fetch_many because yfinance downloads each chunk in parallel.
    Resilient: a failed chunk or ticker is skipped, not fatal.
    """
    symbols = sorted({s.upper().strip() for s in symbols})
    n = len(symbols)
    frames: list[pd.DataFrame] = []
    for i in range(0, n, chunk):
        batch = symbols[i:i + chunk]
        if progress is not None:
            progress(i / max(n, 1), f"{i + 1}–{min(i + chunk, n)} of {n}")
        try:
            data = yf.download(batch, period=period, group_by="ticker",
                               auto_adjust=True, threads=True, progress=False)
        except Exception:  # noqa: BLE001
            continue
        if data is None or data.empty:
            continue
        multi = isinstance(data.columns, pd.MultiIndex)
        for sym in batch:
            try:
                sub = data[sym] if multi else data
            except KeyError:
                continue
            df = _one_ticker_from_bulk(sym, sub)
            if df is not None and not df.empty:
                frames.append(df)
    if progress is not None:
        progress(1.0, "done")
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
