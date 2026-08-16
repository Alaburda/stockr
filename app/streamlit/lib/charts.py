"""Plotly chart builders. Pure functions: DataFrame in, figure out."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from lib.config import GREEN, RED, INK, BLUE, PURPLE, ORANGE

_LAYOUT = dict(
    margin=dict(l=10, r=55, t=30, b=30),
    hovermode="x unified",
    legend=dict(orientation="h", y=-0.12),
    template="plotly_white",
)


def detect_gaps(df: pd.DataFrame, min_pct: float = 0.003) -> list[dict]:
    """Find price gaps and whether they've been filled.

    Bullish gap: today's low > prior day's high (gap up). Bearish: today's high <
    prior low (gap down). A gap is 'filled' once price later trades back through it.
    `min_pct` drops tiny noise gaps. Returns dicts with date/top/bottom/direction/fill_date.
    """
    h, l, dt = df["high"].to_numpy(), df["low"].to_numpy(), df["date"].to_numpy()
    out = []
    for i in range(1, len(df)):
        if l[i] > h[i - 1]:
            top, bottom, direction = l[i], h[i - 1], "bull"
        elif h[i] < l[i - 1]:
            top, bottom, direction = l[i - 1], h[i], "bear"
        else:
            continue
        if bottom <= 0 or (top - bottom) / bottom < min_pct:
            continue
        fill = None
        for j in range(i + 1, len(df)):
            if (direction == "bull" and l[j] <= bottom) or (direction == "bear" and h[j] >= top):
                fill = dt[j]
                break
        out.append({"date": dt[i], "top": top, "bottom": bottom,
                    "direction": direction, "fill_date": fill})
    return out


def candle(df: pd.DataFrame, symbol: str, overlays: dict | None = None,
           ichimoku_df: pd.DataFrame | None = None,
           vpoc_df: pd.DataFrame | None = None) -> go.Figure:
    overlays = overlays or {}
    vol_color = ["rgba(24,188,156,0.5)" if c >= o else "rgba(231,76,60,0.5)"
                 for c, o in zip(df["close"], df["open"])]
    fig = go.Figure()
    fig.add_bar(x=df["date"], y=df["volume"], marker_color=vol_color,
                name="Volume", yaxis="y2", showlegend=False, hoverinfo="skip")
    fig.add_candlestick(x=df["date"], open=df["open"], high=df["high"],
                        low=df["low"], close=df["close"], name=symbol,
                        increasing_line_color=GREEN, increasing_fillcolor=GREEN,
                        decreasing_line_color=RED, decreasing_fillcolor=RED)

    lines = {"sma10": ("SMA 10", "#16a085"), "sma20": ("SMA 20", ORANGE),
             "sma50": ("SMA 50", BLUE), "sma100": ("SMA 100", "#7f8c8d"),
             "sma200": ("SMA 200", PURPLE), "ema8": ("EMA 8", "#e84393"),
             "ema21": ("EMA 21", "#2c3e50")}
    for key, (name, color) in lines.items():
        if overlays.get(key) and key in df:
            fig.add_scatter(x=df["date"], y=df[key], name=name, mode="lines",
                            line=dict(color=color, width=1.2))

    if overlays.get("bbands") and "bb_upper" in df:
        fig.add_scatter(x=df["date"], y=df["bb_upper"], name="BB",
                        line=dict(width=0), showlegend=False, hoverinfo="skip")
        fig.add_scatter(x=df["date"], y=df["bb_lower"], name="BB", fill="tonexty",
                        fillcolor="rgba(52,152,219,0.08)", line=dict(width=0),
                        showlegend=False, hoverinfo="skip")

    # 20-SMA with ±1/2/3 standard-deviation bands, shaded. Each band gets a
    # translucent fill between its +kσ and −kσ edges; because the fills overlap
    # (±3 contains ±2 contains ±1), the alphas stack so the innermost ±1σ zone
    # reads strongest and the shading fades outward — no per-annulus traces
    # needed. Fill traces skip hover/legend (legend would show 6 extra rows);
    # the thin σ edge lines keep per-level hover values.
    if overlays.get("sd_bands"):
        mid = df["close"].rolling(20).mean()
        sd = df["close"].rolling(20).std()
        fig.add_scatter(x=df["date"], y=mid, name="SMA 20",
                        line=dict(color=BLUE, width=1, dash="dot"))
        for k, line_op, fill_op in ((3, 0.35, 0.04), (2, 0.6, 0.05), (1, 0.9, 0.08)):
            col = f"rgba(52,152,219,{line_op})"
            fill = f"rgba(52,152,219,{fill_op})"
            # Upper edge first (baseline), then lower edge filled up to it.
            fig.add_scatter(x=df["date"], y=mid + k * sd, name=f"+{k}σ",
                            line=dict(color=col, width=0.7), showlegend=False,
                            legendgroup="sd_bands",
                            hovertemplate=f"+{k}σ: %{{y:.2f}}<extra></extra>")
            fig.add_scatter(x=df["date"], y=mid - k * sd, name=f"-{k}σ",
                            fill="tonexty", fillcolor=fill,
                            line=dict(color=col, width=0.7), showlegend=False,
                            legendgroup="sd_bands",
                            hovertemplate=f"-{k}σ: %{{y:.2f}}<extra></extra>")

    # ATR extension bands off the 50-day SMA: +4x = entry-danger line (red
    # dashed), +6x/+7x = a lightly-shaded profit-take zone for existing longs.
    if overlays.get("atr_bands") and "sma50" in df and "atr" in df:
        band4 = df["sma50"] + 4 * df["atr"]
        band6 = df["sma50"] + 6 * df["atr"]
        band7 = df["sma50"] + 7 * df["atr"]
        fig.add_scatter(x=df["date"], y=band4, name="+4x ATR (entry danger)",
                        line=dict(color=RED, width=1.1, dash="dash"))
        fig.add_scatter(x=df["date"], y=band6, name="+6x ATR", line=dict(width=0),
                        showlegend=False, hoverinfo="skip")
        fig.add_scatter(x=df["date"], y=band7, name="+7x ATR (profit-take zone)",
                        fill="tonexty", fillcolor="rgba(24,188,156,0.15)",
                        line=dict(color=GREEN, width=1, dash="dot"))

    # Unfilled gaps as persistent support (green) / resistance (red) zones.
    if overlays.get("gaps"):
        last_date = df["date"].max()
        for g in detect_gaps(df):
            if g["fill_date"] is not None:
                continue
            bull = g["direction"] == "bull"
            fig.add_shape(type="rect", x0=g["date"], x1=last_date,
                          y0=g["bottom"], y1=g["top"], layer="below", line=dict(width=0),
                          fillcolor="rgba(24,188,156,0.18)" if bull else "rgba(231,76,60,0.18)")

    # Ichimoku Kinko Hyo: Tenkan/Kijun lines, forward-shifted Senkou cloud
    # (green tint where A>B, red where B>A), dotted Chikou lagging line.
    if overlays.get("ichimoku") and ichimoku_df is not None and not ichimoku_df.empty:
        idf = ichimoku_df
        fig.add_scatter(x=idf["date"], y=idf["tenkan"], name="Tenkan",
                        line=dict(color="#e67e22", width=1), opacity=0.85)
        fig.add_scatter(x=idf["date"], y=idf["kijun"], name="Kijun",
                        line=dict(color="#2980b9", width=1), opacity=0.85)
        fig.add_scatter(x=idf["date"], y=idf["chikou"], name="Chikou",
                        line=dict(color="#7f8c8d", width=1, dash="dot"), opacity=0.7)
        # Cloud: plotted on plot_date (senkou spans shifted 26 sessions ahead).
        cloud = idf.dropna(subset=["senkou_a", "senkou_b"]).sort_values("plot_date")
        if not cloud.empty:
            bullish = cloud["senkou_a"] >= cloud["senkou_b"]
            # Two fill traces so the ribbon tints green where A>=B, red otherwise:
            # draw senkou_b as an invisible baseline, then senkou_a filled to it
            # with a color that reflects the *majority* relationship (simple
            # single-color approach — still shows the cloud's overall bias).
            fill_color = "rgba(24,188,156,0.15)" if bullish.mean() >= 0.5 else "rgba(231,76,60,0.15)"
            fig.add_scatter(x=cloud["plot_date"], y=cloud["senkou_b"], name="Senkou B",
                            line=dict(width=0), showlegend=False, hoverinfo="skip")
            fig.add_scatter(x=cloud["plot_date"], y=cloud["senkou_a"], name="Cloud",
                            fill="tonexty", fillcolor=fill_color,
                            line=dict(color="#95a5a6", width=0.8, dash="dot"),
                            showlegend=True, hoverinfo="skip")

    # Monthly volume profile: translucent value-area band + VPOC line per month.
    if overlays.get("vpoc") and vpoc_df is not None and not vpoc_df.empty:
        for _, row in vpoc_df.tail(36).iterrows():
            fig.add_shape(type="rect", x0=row["month_start"], x1=row["month_end"],
                          y0=row["va_low"], y1=row["va_high"], layer="below",
                          line=dict(width=0), fillcolor="rgba(52,152,219,0.15)")
            fig.add_shape(type="line", x0=row["month_start"], x1=row["month_end"],
                          y0=row["vpoc"], y1=row["vpoc"], layer="below",
                          line=dict(color="rgba(41,128,185,0.6)", width=1.5))

    fig.update_layout(
        xaxis=dict(rangeslider=dict(visible=False), title=""),
        yaxis=dict(title="Price", side="right"),
        yaxis2=dict(overlaying="y", side="left", showgrid=False,
                    showticklabels=False, range=[0, df["volume"].max() * 5]),
        **_LAYOUT,
    )
    return fig


def forming_candle(df: pd.DataFrame, symbol: str, unit: str) -> go.Figure:
    """Cumulative month-to-date / week-to-date candle, one bar per trading day.

    `df` comes from the forming_candles(sym, unit, since) macro: date,
    period_start, f_open, f_high, f_low, f_close. Faint vertical lines mark
    where period_start changes (new month/week boundary); the daily close is
    also drawn as a thin line so you can see the actual day-to-day path
    underneath the "as it stood so far" candle.
    """
    fig = go.Figure()
    fig.add_candlestick(
        x=df["date"], open=df["f_open"], high=df["f_high"], low=df["f_low"], close=df["f_close"],
        name=f"{symbol} forming {unit}",
        increasing_line_color=GREEN, increasing_fillcolor=GREEN,
        decreasing_line_color=RED, decreasing_fillcolor=RED,
    )
    fig.add_scatter(x=df["date"], y=df["f_close"], name="Daily close",
                    line=dict(color=INK, width=0.8), opacity=0.5)

    boundaries = df.loc[df["period_start"] != df["period_start"].shift(1), "date"]
    for b in boundaries.iloc[1:]:  # skip the very first row (not a real boundary)
        fig.add_vline(x=b, line=dict(color="#bdc3c7", width=1, dash="dot"))

    fig.update_layout(
        xaxis=dict(rangeslider=dict(visible=False), title=""),
        yaxis=dict(title="Price", side="right"),
        **_LAYOUT,
    )
    return fig


def ad_line(df: pd.DataFrame) -> go.Figure:
    """Cumulative advance/decline line. `df` has columns date, ad."""
    fig = go.Figure()
    fig.add_scatter(x=df["date"], y=df["ad"], name="A/D line",
                    line=dict(color=INK, width=1.5),
                    hovertemplate="%{x|%Y-%m-%d}<br>A/D: %{y:,.0f}<extra></extra>")
    fig.add_hline(y=0, line=dict(color="#7f8c8d", dash="dot", width=1))
    fig.update_layout(xaxis=dict(title=""), yaxis=dict(title="Cum. A/D", side="right"),
                      height=180, **_LAYOUT)
    return fig


def line(df: pd.DataFrame, symbol: str) -> go.Figure:
    fig = go.Figure()
    fig.add_scatter(x=df["date"], y=df["close"], name=symbol,
                    line=dict(color=INK, width=1.6))
    for key, name, color in [("sma50", "SMA 50", BLUE), ("sma200", "SMA 200", PURPLE)]:
        if key in df:
            fig.add_scatter(x=df["date"], y=df[key], name=name,
                            line=dict(color=color, width=1, dash="dash"))
    fig.update_layout(xaxis=dict(title=""), yaxis=dict(title="Close", side="right"), **_LAYOUT)
    return fig


def rsi(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_scatter(x=df["date"], y=df["rsi"], name="RSI 14", line=dict(color=PURPLE, width=1.5))
    for lvl, color in [(70, RED), (30, GREEN)]:
        fig.add_hline(y=lvl, line=dict(color=color, dash="dot", width=1))
    fig.update_layout(xaxis=dict(title=""), yaxis=dict(title="RSI", range=[0, 100], side="right"), **_LAYOUT)
    return fig


def stochastic_panel(df: pd.DataFrame, k_col: str, d_col: str, title: str) -> go.Figure:
    """K/D oscillator sub-panel (Stochastic 14,3 or StochRSI) with 20/80 dashed hlines."""
    fig = go.Figure()
    fig.add_scatter(x=df["date"], y=df[k_col], name="%K", line=dict(color=BLUE, width=1.3))
    fig.add_scatter(x=df["date"], y=df[d_col], name="%D", line=dict(color=ORANGE, width=1.1, dash="dash"))
    for lvl, color in [(80, RED), (20, GREEN)]:
        fig.add_hline(y=lvl, line=dict(color=color, dash="dot", width=1))
    fig.update_layout(xaxis=dict(title=""), yaxis=dict(title=title, range=[0, 100], side="right"), **_LAYOUT)
    return fig


def macd_panel(df: pd.DataFrame) -> go.Figure:
    """Classic MACD panel: histogram bars (green/red by sign) + MACD/signal lines, zero dashed."""
    colors = [GREEN if v >= 0 else RED for v in df["macd_hist"].fillna(0)]
    fig = go.Figure()
    fig.add_bar(x=df["date"], y=df["macd_hist"], marker_color=colors, name="Histogram")
    fig.add_scatter(x=df["date"], y=df["macd"], name="MACD", line=dict(color=INK, width=1.3))
    fig.add_scatter(x=df["date"], y=df["macd_signal"], name="Signal",
                    line=dict(color=ORANGE, width=1.1, dash="dash"))
    fig.add_hline(y=0, line=dict(color="#7f8c8d", dash="dot", width=1))
    fig.update_layout(xaxis=dict(title=""), yaxis=dict(title="MACD", side="right", zeroline=True), **_LAYOUT)
    return fig


def hist_bars(df: pd.DataFrame, col: str, title: str) -> go.Figure:
    """Diverging bar sub-panel (e.g. ROC, % from EMA8)."""
    colors = [GREEN if v >= 0 else RED for v in df[col].fillna(0)]
    fig = go.Figure(go.Bar(x=df["date"], y=df[col], marker_color=colors, name=title))
    fig.update_layout(xaxis=dict(title=""), yaxis=dict(title=title, side="right", zeroline=True), **_LAYOUT)
    return fig


def volume_panel(df: pd.DataFrame) -> go.Figure:
    """Volume bars (colored by up/down day) with the 20-day volume SMA."""
    colors = ["rgba(24,188,156,0.6)" if c >= o else "rgba(231,76,60,0.6)"
              for c, o in zip(df["close"], df["open"])]
    fig = go.Figure()
    fig.add_bar(x=df["date"], y=df["volume"], marker_color=colors, name="Volume")
    if "vol_ma20" in df:
        fig.add_scatter(x=df["date"], y=df["vol_ma20"], name="Vol SMA20",
                        line=dict(color=ORANGE, width=1.3))
    fig.update_layout(xaxis=dict(title=""), yaxis=dict(title="Volume", side="right"), **_LAYOUT)
    return fig


def line_panel(df: pd.DataFrame, col: str, title: str, scale: float = 1.0,
               smooth: int | None = None, color: str = PURPLE) -> go.Figure:
    """Generic line sub-panel, with an optional smoothing SMA overlay."""
    y = df[col] * scale
    fig = go.Figure()
    fig.add_scatter(x=df["date"], y=y, name=title, line=dict(color=color, width=1.4))
    if smooth:
        fig.add_scatter(x=df["date"], y=y.rolling(smooth).mean(), name=f"SMA {smooth}",
                        line=dict(color=ORANGE, width=1, dash="dash"))
    fig.update_layout(xaxis=dict(title=""), yaxis=dict(title=title, side="right"), **_LAYOUT)
    return fig


def breadth(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    series = [("pct_above_ema8", "8 EMA", ORANGE),
              ("pct_above_ema21", "21 EMA", BLUE),
              ("pct_above_sma50", "50 SMA", PURPLE)]
    for key, name, color in series:
        if key in df:
            fig.add_scatter(x=df["date"], y=df[key], name=name, line=dict(color=color, width=1.3))
    fig.add_hline(y=50, line=dict(color="#7f8c8d", dash="dot", width=1))
    fig.update_layout(xaxis=dict(title=""), yaxis=dict(title="% of universe", range=[0, 100]), **_LAYOUT)
    return fig


def stress(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_scatter(x=df["date"], y=df["stress"], name="VIX3M / VIX", line=dict(color=RED, width=1.5))
    fig.add_hline(y=1.0, line=dict(color="#7f8c8d", dash="dot", width=1))
    fig.update_layout(xaxis=dict(title=""), yaxis=dict(title="VIX3M / VIX"), **_LAYOUT)
    return fig


def compare(frames: dict[str, pd.DataFrame]) -> go.Figure:
    """Normalized (% return from first point) comparison."""
    fig = go.Figure()
    for name, d in frames.items():
        if d is None or d.empty:
            continue
        base = d["close"].dropna().iloc[0]
        fig.add_scatter(x=d["date"], y=(d["close"] / base - 1) * 100, name=name, mode="lines")
    fig.update_layout(xaxis=dict(title=""), yaxis=dict(title="Return %", side="right", zeroline=True), **_LAYOUT)
    return fig
