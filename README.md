# Stockr - single page stock viewer

The goal of this project is to create a static page hosted on GitHub Pages that allows me to query a duckdb or sqlite database of stock data. The idea is that I can turn to this page to check how my basket of tickers are doing.

For the sample application, please do the following:
* Create a database with the SLV ticker
* Create a .github workflow to host the page on github pages (not sure if it's necessary, but it would be nice to have it automated, i.e. so that changes are rerendered automatically)
* Create the page

Please prefer using R, quantmod, quarto, duckdb and/or observable to create the application. You can use shiny live, wasm or whatever is needed to achieve the outcome.