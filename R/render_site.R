#!/usr/bin/env Rscript

# Render Stockr site to docs folder for GitHub Pages

cat("Fetching latest stock data...\n")
source("R/fetch_data.R")

cat("\nRendering Quarto document to docs folder...\n")
quarto_cmd <- 'quarto render index.qmd --output-dir docs'
system(quarto_cmd)

cat("\nCopying DuckDB to docs...\n")
dir.create("docs/data", showWarnings = FALSE, recursive = TRUE)
file.copy("data/stocks.duckdb", "docs/data/stocks.duckdb", overwrite = TRUE)

cat("\n✓ Site rendered to docs/ folder\n")
cat("✓ Ready to deploy to GitHub Pages!\n")
cat("\nTo test locally, run:\n")
cat("  httpuv::runStaticServer('docs/', port = 8008)\n")
