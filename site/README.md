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

2 years of history are pulled (so the 200-day SMA is warm) and the last 260
bars per ticker are written to the CSV. The CSV is not published — Quarto reads
it at render time and bakes the numbers into `index.html`.

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
