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
| `index.qmd` | The Morning Board page (market strip, SPY chart, tables) |
| `styles.scss` | Card + table styling on top of the `flatly` theme |
| `data/` | Generated, gitignored — `prices.csv` + `meta.json` |

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
