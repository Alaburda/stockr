# Stockr - Single Page Stock Viewer

The goal of this project is to create a static page hosted on GitHub Pages that allows querying a DuckDB database of stock data. Use this page to check how your basket of tickers are doing.

## ✨ Features

- 📊 **Real-time Stock Data**: Fetches live data from Yahoo Finance using R's quantmod
- 🗄️ **DuckDB Database**: Lightweight SQL database for fast querying
- 🌐 **Static Site**: Generated with Quarto, deployable to GitHub Pages
- ⚙️ **Automated Updates**: GitHub Actions workflow updates data daily
- 📱 **Responsive Design**: Works on desktop, tablet, and mobile
- 🚀 **Zero Maintenance**: No server needed, fully static deployment

## 🚀 Quick Start

```bash
# 1. Clone the repository
git clone <repo-url>
cd stockr

# 2. Render the site locally
Rscript R/render_site.R

# 3. View output
# The rendered site is in docs/ folder
# Test with: httpuv::runStaticServer("docs/", port = 8008)
```

See [setup.md](setup.md) for detailed installation instructions.

## 📋 What's Included

### ✅ Sample Application Components

1. **Database with SLV Ticker**
   - Historical price data from 2020 onwards
   - Stored in DuckDB for efficient querying
   - Easily expandable to multiple tickers

2. **GitHub Pages Workflow**
   - Automated daily updates via GitHub Actions
   - Runs at 2 AM UTC every day
   - Automatically re-renders the page on push to main

3. **Interactive Page**
   - Built with Quarto + R
   - Displays stock statistics and historical data
   - Ready for Observable.js visualizations

## 🏗️ Project Structure

```
stockr/
├── index.qmd                 # Main page (Quarto markdown)
├── _quarto.yml              # Quarto site configuration
├── styles.css               # Custom styling
├── R/
│   ├── fetch_data.R         # Data fetching script
│   └── render_site.R        # Render & deploy script
├── data/stocks.duckdb       # Stock price database
└── docs/                    # Rendered site (published to GitHub Pages)
    ├── index.html
    ├── styles.css
    └── data/stocks.duckdb
```

## 🛠️ Tech Stack

- **R** - Data fetching with `quantmod` and `dplyr`
- **DuckDB** - Lightweight SQL database
- **Quarto** - Static site generation
- **Observable JS** - Interactive visualizations (optional)
- **GitHub Actions** - Automation & deployment
- **GitHub Pages** - Static hosting

## 📦 Requirements

- R 4.1+
- Quarto 1.0+
- Git
- GitHub account (for GitHub Pages deployment)

## � Customization

### Add More Stock Tickers

Edit `R/fetch_data.R` to include additional symbols:

```r
symbols <- c("SLV", "GLD", "AAPL")
```

Then run the render script to update the site:
```bash
Rscript R/render_site.R
```

### Update Styling

Customize colors and fonts in `styles.css`

### Add Visualizations

Use Observable JavaScript blocks in `index.qmd` for interactive charts

## 🚢 Deployment

The site is static and ready to deploy to GitHub Pages:

1. **Render locally**:
   ```bash
   Rscript R/render_site.R
   ```

2. **Commit the rendered site**:
   ```bash
   git add docs/
   git commit -m "Update: rebuild site"
   git push origin master
   ```

3. **Enable GitHub Pages**:
   - Go to repository Settings → Pages
   - Select `docs` folder from `master` branch
   - Your site goes live immediately!

**No CI/CD pipeline needed** — fast, simple, static deployment.

## 📝 File Descriptions

| File | Purpose |
|------|---------|
| `index.qmd` | Main Quarto document (HTML + R code) |
| `R/fetch_data.R` | Fetches stock data from Yahoo Finance |
| `R/render_site.R` | Renders site to `docs/` folder |
| `data/stocks.duckdb` | DuckDB database with stock prices |
| `docs/` | Rendered site (published to GitHub Pages) |
| `_quarto.yml` | Quarto configuration |
| `styles.css` | Custom CSS styling |
| `setup.md` | Detailed setup instructions |

## 🔄 Update Workflow

```bash
# Make changes locally
Rscript R/fetch_data.R      # Update data
quarto render index.qmd      # Render HTML

# Push to trigger deployment
git add .
git commit -m "Update: [description]"
git push origin main
```

GitHub Actions will automatically build and deploy.

## � Update Workflow

```bash
# 1. Make changes to R/fetch_data.R or index.qmd

# 2. Render the site locally
Rscript R/render_site.R

# 3. Check the output in docs/

# 4. Commit and push
git add .
git commit -m "Update: [description of changes]"
git push origin master

# Site updates immediately without waiting for CI/CD!
```