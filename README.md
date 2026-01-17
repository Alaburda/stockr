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

# 2. Create the stock database
Rscript R/fetch_data.R

# 3. Render the page locally
quarto render index.qmd

# 4. View output
open _output/index.html
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
├── R/fetch_data.R           # Data fetching script
├── data/stocks.duckdb       # Stock price database
└── .github/workflows/       # GitHub Actions configuration
    └── build-deploy.yml     # CI/CD pipeline
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

## 🔧 Customization

### Add More Stock Tickers

Edit `R/fetch_data.R` to include additional symbols:

```r
symbols <- c("SLV", "GLD", "AAPL")
```

### Update Styling

Customize colors and fonts in `styles.css`

### Add Visualizations

Use Observable JavaScript blocks in `index.qmd` for interactive charts

## 🚢 Deployment

1. Push to GitHub
2. Enable GitHub Pages in repository settings
3. Select `gh-pages` branch as source
4. Your site goes live at `https://<username>.github.io/stockr/`

The GitHub Actions workflow automatically:
- Fetches latest stock data daily
- Re-renders the HTML page
- Deploys to GitHub Pages

## 📝 File Descriptions

| File | Purpose |
|------|---------|
| `index.qmd` | Main Quarto document (HTML + R code) |
| `R/fetch_data.R` | Fetches stock data from Yahoo Finance |
| `data/stocks.duckdb` | DuckDB database with stock prices |
| `.github/workflows/build-deploy.yml` | GitHub Actions CI/CD pipeline |
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

## 📚 Learn More

- [Quarto Documentation](https://quarto.org/)
- [quantmod Package](https://www.quantmod.com/)
- [DuckDB Guide](https://duckdb.org/docs/)
- [GitHub Pages Setup](https://pages.github.com/)

## 📋 Next Steps

1. ✅ Add your desired stock tickers to `R/fetch_data.R`
2. ✅ Customize styling in `styles.css`
3. ✅ Create a GitHub repository and enable Pages
4. ✅ Set up scheduled updates (already configured!)
5. ✅ Add interactive visualizations with Observable JS

## 📄 License

MIT - Feel free to fork, modify, and use!

---

**Created with**: R, Quarto, DuckDB, and ❤️