# Static site (`site/`)

A Quarto website published to GitHub Pages. It is a **read-only morning
snapshot** — no server, no DuckDB, no secrets. Everything it shows comes from a
fresh Yahoo pull done at build time.

```
scripts/fetch_prices.py  →  site/data/prices.csv  →  quarto render  →  site/_site/
```

## Build it locally

```bash
python scripts/fetch_prices.py
quarto render site
```

Then open `site/_site/index.html`, or serve it:

```bash
python -m http.server 4321 --directory site/_site
```

`quarto preview site` works too, but re-runs the Python chunks on every save.

## Files

| File | Purpose |
|---|---|
| `_quarto.yml` | Site config — theme, navbar, output dir |
| `index.qmd` | **Morning Board** — market strip, SPY chart, watchlist, ETFs |
| `indicators.qmd` | **Indicators** — breadth, new highs/lows, sector RS, RS boards, benchmarks, risk on/off |
| `stock.qmd` | **Single Stock View** — any tracked ticker, arrow-key nav |
| `board.py` | Metrics — the app's SQL views ported to pandas |
| `charts.py` | Shared candle/table builders used by all three pages |
| `styles.scss` | Card + table styling on top of the `flatly` theme |
| `resize-tabs.html` | Resizes Plotly charts when their tab becomes visible |
| `data/` | Generated, gitignored |

## The three pages

**Morning Board** is the glance: market strip, SPY candles, the watchlist
sorted by setup score, ETFs.

**Indicators** is the market internals: S&P 500 breadth, 52-week new
highs/lows, sector RS, the RS boards, the MA matrix, and TLT-vs-SPY.

**Single Stock View** is any tracked ticker with `←`/`→` nav. The whole
universe's candles ship with the page — a static site can't query on demand,
and the point of arrow-key nav is flipping through names without waiting.

To keep that payload honest, moving averages are **computed in the browser**
rather than shipped (they were 3 of 7 arrays; a rolling mean is five lines of
JS) and prices are rounded to 2dp. That took the page from 501 KB to 253 KB
gzipped. Client and server SMAs agree to sub-cent, which is exactly the drift
2dp rounding predicts.

`board.py` ports `v_latest`, `v_perf`, `v_rs_spy` and `v_ma_matrix` from
`db/views.sql` to pandas — same definitions, no database. It imports `HELP`
from `app/streamlit/lib/glossary.py`, so every tooltip on the page is the same
text the Streamlit app shows; there is no second copy to keep in sync.

Hover tooltips are desktop-only (phones have no hover state), which is why the
page also carries a full **Glossary** section at the bottom.

### Returns are anchored to the benchmark calendar

`board._ret` measures every return over **SPY's** last N trading sessions, not
over N rows of the ticker's own series, and takes the last close on or before
that reference date.

This matters more than it sounds. 12 of the 78 tickers don't share SPY's
calendar — `DX-Y.NYB` has *more* bars (the dollar trades when equities don't),
`WGMI` and `GTLB` fewer, `NBIS`/`RDDT` are recent listings. Counting 22 rows
back in each series therefore compared *different date ranges* against SPY's,
which silently corrupted RS: `WGMI`'s RS 1M was wrong by 9.3 percentage
points, `XLRE` and `RSPR` by ~2pp.

`meta.json` records `bars_per_ticker` and `calendar_len` so that if the
published page ever disagrees with a local render, comparing those two says
straight away whether the upstream feed gave the runs different history.

### The setup score

The `n/6` badge is the app's A-setup checklist: ATR ext < 4x, LoD dist < 0.6
ATR, 200-MA rising, 10-MA rising, RS 1M > 0, rel vol >= 1. Hover it to see
which checks passed. The watchlist sorts by this, then by RS — the morning
question is "what is set up", not "what moved yesterday".

## S&P 500 aggregates

`scripts/fetch_sp500.py` pulls the ~500 constituents (list scraped from
Wikipedia by `app/streamlit/lib/universe.py`) and writes **only aggregates** —
never the ~500 x 500 price matrix, which would be a ~100 MB CSV of numbers no
page reads individually:

| File | Contents |
|---|---|
| `breadth.csv` | per date: % of members above their own 20/50/200-day SMA, % up on the day |
| `highlow.csv` | per date: new 52-week highs, new lows, net |
| `sector_rs.csv` | per GICS sector: member count, 1m/3m return and RS vs SPY |

It runs **after** `fetch_prices.py` (it reads SPY's calendar from the board's
own CSV) and is wired with `continue-on-error`. It is the slowest and most
failure-prone step in the build, and the board doesn't depend on it — so when
it fails, the Indicators page renders a short explanation in place of the
breadth panels and everything else still publishes.

It has its own floor: below 70% of constituents it refuses to write, because
"42% above the 50-day" is meaningless if it's 42% of a third of the index.

### Charts in tabs

A Plotly chart that renders inside a hidden tab measures itself at Plotly's
default 700px and never learns its real width, so it stays clipped on a phone
after you tap through. `resize-tabs.html` (wired in via `include-after-body`)
resizes charts when their panel becomes visible. Any new tabbed chart is
covered automatically.

## Data

`scripts/fetch_prices.py` imports `app/streamlit/lib/fetch.py`, so the site's
RSI / ATR extension / ADR are computed by the same code as the Streamlit app.
The ticker universe comes from `app/streamlit/lib/config.py`
(`DEFAULT_WATCHLIST`, `DEFAULT_ETFS`, `DEFAULT_INDICES`) — edit there and both
the app and the site follow.

5 years of history are pulled and the last 1300 bars per ticker are written to
the CSV — the weekly and monthly candle views need that depth (260 daily bars
is only ~12 monthly candles). The CSV is not published; Quarto reads it at
render time and bakes the numbers into `index.html`.

The fetch fails the build if fewer than 80% of tickers return data
(`MIN_COVERAGE`), so a bad Yahoo night leaves yesterday's page up instead of
publishing a board that's silently half empty.

### Yahoo is less reliable from CI than from a laptop

Yahoo's bulk endpoint degrades noticeably from datacenter IPs. A run that
returned 78/78 complete series locally came back from GitHub Actions with
`^VIX3M` missing entirely and 38 tickers gapped — which silently deleted the
VIX3M/VIX stress tile from the published page while coverage read 77/78 and
passed. Two defences:

- `backfill()` re-requests any dropped or short ticker one at a time, which
  uses a different endpoint and usually fills them in. It's a no-op locally.
- `REQUIRED` lists the tickers the market strip is built from. Losing one
  never trips a percentage-based guard, so those fail the build outright —
  yesterday's page staying up beats today's page quietly missing a signal.

If a build fails on `REQUIRED`, that's Yahoo, not the code. Re-run the
workflow; the site keeps serving the last good page meanwhile.

## Candle timeframes

The Daily / Weekly / Monthly switch is computed at build time: `timeframe_frame`
resamples the daily OHLC and **recomputes** the moving averages on the new
timeframe, so a 10-period MA means 10 weeks on the weekly chart. All three sets
of traces ship in the figure and `timeframe_switch` toggles their visibility —
no server, and it works offline.

The switch uses plain HTML buttons rather than Plotly's `updatemenus`, whose
buttons are locked to ~33px tall (under the touch-target guideline) and eat
chart height by sitting inside the plot.

## Mobile

The page is checked at 375px: it must never scroll sideways as a whole. Wide
tables scroll inside their own `.table-wrap` container with the ticker column
pinned via `position: sticky`. If you add a table, wrap it the same way.

## Schedule

`.github/workflows/pages.yml` runs at **23:00 UTC, Tue–Sat** (≈02:00 Vilnius,
about two hours after the US close), and on any push to `site/` or `scripts/`.
Change the `cron:` line to move it.

## Adding a page

Drop a new `.qmd` in this folder and add it to the `navbar` in `_quarto.yml`.
Load the data with the same three lines `index.qmd` uses:

```python
px_all = pd.read_csv(Path("data") / "prices.csv", parse_dates=["date"])
meta = json.loads((Path("data") / "meta.json").read_text(encoding="utf-8"))
```
