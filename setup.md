# Getting Started with Stockr

## Prerequisites

- **R** (4.1 or higher) - [Download](https://cran.r-project.org/)
- **Quarto** (1.0 or higher) - [Download](https://quarto.org/docs/get-started/)
- **Git** - [Download](https://git-scm.com/)

## Installation

### 1. Install R Packages

```bash
Rscript -e "install.packages(c('quantmod', 'duckdb', 'dplyr'))"
```

### 2. Clone or Setup Repository

```bash
git clone <repository-url>
cd stockr
```

### 3. Create Initial Database

```bash
Rscript R/fetch_data.R
```

This will:
- Fetch SLV stock data from Yahoo Finance (since 2020-01-01)
- Create a DuckDB database at `data/stocks.duckdb`
- Display summary statistics

### 4. Render the Page Locally

```bash
quarto render index.qmd
```

The HTML output will be generated in `_output/index.html`

## Project Structure

```
stockr/
├── README.md              # Project documentation
├── setup.md               # Setup instructions (this file)
├── index.qmd              # Main Quarto document
├── _quarto.yml            # Quarto configuration
├── styles.css             # Custom CSS styles
├── R/
│   └── fetch_data.R       # Script to fetch stock data and create database
├── data/
│   └── stocks.duckdb      # DuckDB database with stock prices
└── .github/
    └── workflows/
        └── build-deploy.yml  # GitHub Actions workflow for GitHub Pages
```

## Adding More Stocks

To track additional stock tickers:

1. Edit `R/fetch_data.R` and add more symbols to the data fetching section:

```r
# Fetch multiple stocks
symbols <- c("SLV", "GLD", "AAPL")
all_data <- NULL

for (symbol in symbols) {
  getSymbols(symbol, src = "yahoo", auto.assign = FALSE) -> data
  # Process and append to all_data
}
```

2. Re-run the fetch script:
```bash
Rscript R/fetch_data.R
```

3. Re-render the page:
```bash
quarto render index.qmd
```

## GitHub Pages Deployment

The project includes a GitHub Actions workflow (`.github/workflows/build-deploy.yml`) that:

1. **Runs on push** to the main branch
2. **Daily at 2 AM UTC** to update stock data automatically
3. **Fetches the latest data** using the R script
4. **Renders the Quarto document** to HTML
5. **Deploys to GitHub Pages** automatically

### Setup GitHub Pages:

1. Push this repository to GitHub
2. Go to repository Settings → Pages
3. Select "Deploy from a branch"
4. Choose the `gh-pages` branch
5. Your site will be live at `https://<username>.github.io/<repo-name>/`

## Technologies

- **R & quantmod**: Fetching real stock data from Yahoo Finance
- **DuckDB**: Lightweight SQL database for efficient data querying
- **Quarto**: Static site generation with R integration
- **Observable/OJS**: Interactive JavaScript visualizations (optional)
- **GitHub Actions**: CI/CD pipeline for automated updates
- **GitHub Pages**: Free static hosting

## Troubleshooting

### Database won't create
- Ensure R packages are installed: `install.packages(c('quantmod', 'duckdb', 'dplyr'))`
- Check that `data/` directory exists or gets created

### Quarto render fails
- Ensure Quarto is installed: `quarto --version`
- Check R is in your PATH: `Rscript --version`

### GitHub Actions fails
- Check that `.github/workflows/build-deploy.yml` is properly formatted YAML
- Review workflow logs in GitHub Actions tab
- Ensure `GITHUB_TOKEN` secret is available (should be automatic)

## Development Workflow

```bash
# 1. Make changes to R/fetch_data.R or index.qmd
# 2. Test locally:
Rscript R/fetch_data.R
quarto render index.qmd

# 3. View output:
# Open _output/index.html in your browser

# 4. Commit and push:
git add .
git commit -m "Update: [description of changes]"
git push origin main

# 5. GitHub Actions will automatically:
#    - Run the workflow
#    - Deploy to GitHub Pages
#    - Your changes will be live!
```

## Next Steps

- Add more tickers to track your portfolio
- Customize styling in `styles.css`
- Add interactive charts using Observable JavaScript
- Set up email alerts for price movements (advanced)

---

For more information:
- [Quarto Documentation](https://quarto.org/)
- [quantmod R Package](https://cran.r-project.org/package=quantmod)
- [DuckDB Documentation](https://duckdb.org/)
- [GitHub Pages Guide](https://docs.github.com/en/pages)
