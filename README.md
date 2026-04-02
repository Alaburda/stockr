# Stockr

[![Deploy To shinyapps.io](https://github.com/Alaburda/stockr/actions/workflows/deploy-shinyapps.yml/badge.svg)](https://github.com/Alaburda/stockr/actions/workflows/deploy-shinyapps.yml)

Stockr is an R Shiny app for stock analysis with technical overlays, momentum indicators, dashboard summaries, and a parabolic short scanner.

## Features

- Live market data from Yahoo Finance via quantmod
- Starter ticker choices plus a custom ticker input for any stock you want to pass to Yahoo Finance
- Daily, weekly, and monthly chart intervals for the analysis view
- Technical overlays including SMA, EMA, Bollinger Bands, VWAP, Ichimoku, and volume profile
- Dashboard summary table for tracked ticker signals
- Parabolic short grading view for recent setup quality

## Quick Start

```bash
cd app
Rscript -e "shiny::runApp('.', port = 3838)"
```

## Requirements

```r
install.packages(c(
	"shiny", "bslib", "bsicons", "plotly", "quantmod", "TTR",
	"xts", "DT", "gt", "gtExtras", "rsconnect"
))
```

## Deployment

GitHub Actions can deploy the app to shinyapps.io using the workflow in `.github/workflows/deploy-shinyapps.yml`.

Add these repository secrets before enabling deployment:

- `SHINYAPPS_ACCOUNT`
- `SHINYAPPS_TOKEN`
- `SHINYAPPS_SECRET`
- `SHINYAPPS_APP_NAME`

The workflow deploys the `app` directory on pushes to `master` and on manual dispatch.

## Project Structure

```text
stockr/
├── .github/workflows/deploy-shinyapps.yml
├── app/
│   ├── app.R
│   └── functions.R
├── README.md
└── .gitignore
```

## License

MIT