#!/usr/bin/env Rscript

# Load required libraries
library(quantmod)
library(duckdb)
library(dplyr)

# Create DuckDB connection
data_dir <- file.path(getwd(), "data")
dir.create(data_dir, showWarnings = FALSE)
db_path <- file.path(data_dir, "stocks.duckdb")
con <- dbConnect(duckdb(), dbdir = db_path, read_only = FALSE)

# Fetch SLV data
cat("Fetching SLV stock data...\n")
getSymbols("SLV", src = "yahoo", from = "2020-01-01", to = Sys.Date(), auto.assign = FALSE) -> slv_data

# Convert xts to data frame
slv_df <- data.frame(
  date = index(slv_data),
  ticker = "SLV",
  open = as.numeric(slv_data[, 1]),
  high = as.numeric(slv_data[, 2]),
  low = as.numeric(slv_data[, 3]),
  close = as.numeric(slv_data[, 4]),
  volume = as.numeric(slv_data[, 5]),
  adjusted = as.numeric(slv_data[, 6]),
  row.names = NULL
)

# Create or replace table
cat("Writing data to DuckDB...\n")
dbWriteTable(con, "stock_prices", slv_df, overwrite = TRUE)

# Create index for faster queries
dbExecute(con, "CREATE INDEX IF NOT EXISTS idx_ticker_date ON stock_prices (ticker, date)")

# Verify data
result <- dbGetQuery(con, "SELECT COUNT(*) as row_count FROM stock_prices")
cat("Success! Loaded", result$row_count, "rows of SLV data\n")

# Show sample
sample_query <- "SELECT * FROM stock_prices LIMIT 5"
cat("Sample data:\n")
print(dbGetQuery(con, sample_query))

dbDisconnect(con)
cat("Database created at:", db_path, "\n")
