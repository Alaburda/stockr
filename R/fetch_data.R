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

# List of tickers to fetch
tickers <- c("SLV", "NVDA", "AAPL", "ADBE", "MP")

# Fetch and combine data
all_data <- NULL

for (symbol in tickers) {
  cat("Fetching", symbol, "stock data...\n")
  tryCatch({
    getSymbols(symbol, src = "yahoo", from = "2020-01-01", to = Sys.Date(), auto.assign = FALSE) -> stock_data
    
    # Convert xts to data frame
    stock_df <- data.frame(
      date = index(stock_data),
      ticker = symbol,
      open = as.numeric(stock_data[, 1]),
      high = as.numeric(stock_data[, 2]),
      low = as.numeric(stock_data[, 3]),
      close = as.numeric(stock_data[, 4]),
      volume = as.numeric(stock_data[, 5]),
      adjusted = as.numeric(stock_data[, 6]),
      row.names = NULL
    )
    
    all_data <- rbind(all_data, stock_df)
  }, error = function(e) {
    cat("Warning: Failed to fetch", symbol, "-", conditionMessage(e), "\n")
  })
}

if (!is.null(all_data)) {
  # Write data to DuckDB
  cat("Writing data to DuckDB...\n")
  dbWriteTable(con, "stock_prices", all_data, overwrite = TRUE)
  
  # Create index for faster queries
  dbExecute(con, "CREATE INDEX IF NOT EXISTS idx_ticker_date ON stock_prices (ticker, date)")
  
  # Verify data
  result <- dbGetQuery(con, "SELECT ticker, COUNT(*) as row_count FROM stock_prices GROUP BY ticker")
  cat("Success! Loaded data:\n")
  print(result)
  
  # Show sample
  sample_query <- "SELECT * FROM stock_prices LIMIT 5"
  cat("Sample data:\n")
  print(dbGetQuery(con, sample_query))
} else {
  cat("Error: No data fetched!\n")
}

dbDisconnect(con)
cat("Database created at:", db_path, "\n")
