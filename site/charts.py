"""Shared chart + table builders for every page on the board.

Kept out of the .qmd files so the three pages (Morning Board, Indicators,
Single Stock View) render the same candles and the same tables from one
definition.
"""
from __future__ import annotations

import json

import pandas as pd
import plotly.graph_objects as go

GREEN, RED = "#18bc9c", "#e74c3c"
INK, BLUE, PURPLE, ORANGE = "#2c3e50", "#3498db", "#9b59b6", "#e67e22"

# label, pandas resample rule (None = daily), bars to show
TIMEFRAMES = [("Daily", None, 130), ("Weekly", "W-FRI", 104), ("Monthly", "ME", 60)]
MA_SPEC = [("sma10", BLUE, 1.0), ("sma20", ORANGE, 1.0), ("sma50", PURPLE, 1.4)]
WEEKEND_BREAK = [dict(bounds=["sat", "mon"])]


# ── formatting ───────────────────────────────────────────────────────────────
def signed(x, dp=2, suffix="%"):
    if pd.isna(x):
        return '<span class="stamp">—</span>'
    return f'<span class="{"up" if x >= 0 else "down"}">{x:+.{dp}f}{suffix}</span>'


def plain(x, dp=2, suffix=""):
    return "—" if pd.isna(x) else f"{x:,.{dp}f}{suffix}"


def html_table(df, spec, first_header="Ticker", first_cell=lambda tk, r: tk):
    """Build a board table. `spec` is [(key, header html, formatter), ...]."""
    head = "".join(f"<th>{lbl}</th>" for _, lbl, _ in spec)
    body = []
    for tk, r in df.iterrows():
        cells = "".join(f"<td>{fmt(r.get(key))}</td>" for key, _, fmt in spec)
        body.append(f"<tr><td>{first_cell(tk, r)}</td>{cells}</tr>")
    return (f"<div class='table-wrap'><table class='board'><thead><tr>"
            f"<th>{first_header}</th>{head}</tr></thead>"
            f"<tbody>{''.join(body)}</tbody></table></div>")


# ── candles ──────────────────────────────────────────────────────────────────
def timeframe_frame(df: pd.DataFrame, rule: str | None, bars: int) -> pd.DataFrame:
    """OHLC at the requested timeframe, with MAs recomputed on that timeframe.

    A 10-period MA means 10 *weeks* on the weekly chart — resampling the daily
    MA instead would just be a sampled daily line wearing a weekly label.
    """
    if rule is None:
        out = df.copy()  # daily: MAs already computed by lib.fetch
    else:
        out = (df.set_index("date")
                 .resample(rule)
                 .agg({"open": "first", "high": "max", "low": "min",
                       "close": "last", "volume": "sum"})
                 .dropna(subset=["close"])
                 .reset_index())
        for col, _, _ in MA_SPEC:
            out[col] = out["close"].rolling(int(col.removeprefix("sma"))).mean()
    return out.tail(bars)


def candle_figure(df: pd.DataFrame, name: str, height: int = 400) -> go.Figure:
    """Candles for all three timeframes; only the daily set starts visible."""
    frames = [timeframe_frame(df, rule, bars) for _, rule, bars in TIMEFRAMES]

    fig = go.Figure()
    for i, f in enumerate(frames):
        vis = i == 0
        fig.add_trace(go.Candlestick(
            x=f["date"], open=f["open"], high=f["high"], low=f["low"], close=f["close"],
            increasing_line_color=GREEN, decreasing_line_color=RED,
            name=name, visible=vis, showlegend=False))
        for col, color, width in MA_SPEC:
            fig.add_trace(go.Scatter(
                x=f["date"], y=f[col], mode="lines", name=col.upper(),
                line=dict(color=color, width=width), visible=vis))

    fig.update_layout(
        height=height, margin=dict(l=8, r=8, t=34, b=26), template="plotly_white",
        xaxis_rangeslider_visible=False, xaxis=dict(rangebreaks=WEEKEND_BREAK),
        yaxis=dict(side="right"),
        legend=dict(orientation="h", y=1.0, yanchor="bottom", x=0, xanchor="left",
                    font=dict(size=11)))
    return fig


def timeframe_switch(host_id: str) -> str:
    """Daily/Weekly/Monthly buttons for the next chart in document order.

    Plotly's own `updatemenus` buttons are locked to ~33px tall regardless of
    font or padding — under the touch-target guideline — and they eat chart
    height by living inside the plot, so these are real buttons.

    The chart is located by document order rather than DOM nesting: Quarto puts
    the switch and the chart in separate `.cell-output` divs, so a
    parentElement lookup finds nothing (this silently broke the buttons once
    already).
    """
    per_tf = 1 + len(MA_SPEC)
    n = len(TIMEFRAMES) * per_tf
    states = []
    for i, _ in enumerate(TIMEFRAMES):
        visible = [False] * n
        for j in range(per_tf):
            visible[i * per_tf + j] = True
        # Weekend gaps only exist on the daily axis; keeping the rangebreak on a
        # weekly/monthly chart would blank out most of the candles.
        states.append({"visible": visible,
                       "rangebreaks": WEEKEND_BREAK if i == 0 else []})

    btns = "".join(
        f'<button type="button" data-tf="{i}"'
        f'{" class=\"active\"" if i == 0 else ""}>{label}</button>'
        for i, (label, _, _) in enumerate(TIMEFRAMES))

    return f"""
<div class="tf-switch" id="{host_id}" role="group" aria-label="Candle timeframe">{btns}</div>
<script>
(function () {{
  var STATES = {json.dumps(states)};
  var host = document.getElementById({host_id!r});
  function chartFor() {{
    var all = document.querySelectorAll('.plotly-graph-div');
    for (var i = 0; i < all.length; i++) {{
      if (host.compareDocumentPosition(all[i]) & Node.DOCUMENT_POSITION_FOLLOWING) {{
        return all[i];
      }}
    }}
    return null;
  }}
  var tries = 0;
  function attach() {{
    var gd = chartFor();
    if ((!gd || typeof Plotly === 'undefined') && tries++ < 100) {{
      return setTimeout(attach, 60);
    }}
    if (!gd) return;
    host.dataset.bound = '1';
    host.addEventListener('click', function (ev) {{
      var b = ev.target.closest('button[data-tf]');
      if (!b) return;
      var s = STATES[+b.dataset.tf];
      Plotly.update(gd, {{visible: s.visible}}, {{'xaxis.rangebreaks': s.rangebreaks}});
      host.querySelectorAll('button').forEach(function (x) {{ x.classList.remove('active'); }});
      b.classList.add('active');
    }});
  }}
  attach();
}})();
</script>
"""
