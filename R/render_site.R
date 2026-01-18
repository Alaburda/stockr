#!/usr/bin/env Rscript

# Render Stockr site to docs folder for GitHub Pages

cat("Fetching latest stock data...\n")
source("R/fetch_data.R")

cat("\nExporting stock data to CSV...\n")
library(duckdb)
con <- dbConnect(duckdb(), dbdir = "data/stocks.duckdb", read_only = TRUE)
stock_data <- dbGetQuery(con, "SELECT * FROM stock_prices ORDER BY date")
dbDisconnect(con)

# Export to CSV
write.csv(stock_data, "data/stock_data.csv", row.names = FALSE)
cat("✓ Exported to data/stock_data.csv\n")

cat("\nRendering Quarto document to docs folder...\n")
quarto_cmd <- 'quarto render index.qmd --output-dir docs'
system(quarto_cmd)

cat("\nCopying data files to docs...\n")
dir.create("docs/data", showWarnings = FALSE, recursive = TRUE)
file.copy("data/stock_data.csv", "docs/data/stock_data.csv", overwrite = TRUE)
file.copy("data/stocks.duckdb", "docs/data/stocks.duckdb", overwrite = TRUE)

cat("\n✓ Site rendered to docs/ folder\n")
cat("✓ Ready to deploy to GitHub Pages!\n")
cat("\nTo test locally, run:\n")
cat("  httpuv::runStaticServer('docs/', port = 8008)\n")
