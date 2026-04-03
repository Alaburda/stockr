# Stockr - Modern Shiny App with bslib UI
# Live stock analysis using quantmod + plotly

library(shiny)
library(bslib)
library(bsicons)
library(plotly)
library(quantmod)
library(TTR)
library(xts)
library(DT)
library(gt)
library(gtExtras)

normalize_tickers <- function(tickers) {
  tickers <- toupper(trimws(tickers))
  tickers <- tickers[nzchar(tickers)]
  unique(tickers)
}

starter_tickers <- normalize_tickers(c("AAPL", "MSFT", "NVDA", "GOOG", "AMZN"))

# Custom theme with modern look
app_theme <- bs_theme(
  version = 5,
  bootswatch = "flatly",
  primary = "#2c3e50",
  secondary = "#18bc9c",
  success = "#18bc9c",
  info = "#3498db",
  warning = "#f39c12",
  danger = "#e74c3c",
  base_font = font_google("Inter"),
  heading_font = font_google("Inter"),
  font_scale = 0.95
)

ui <- page_navbar(
  title = tags$span(
    bs_icon("graph-up-arrow", size = "1.2em"),
    " Stockr"
  ),
  theme = app_theme,
  fillable = TRUE,
  nav_spacer(),
  nav_panel(
    title = "Analysis",
    icon = bs_icon("bar-chart-line"),
    layout_sidebar(
      sidebar = sidebar(
        width = 300,
        bg = "#f8f9fa",
        title = tags$span(bs_icon("sliders"), " Controls"),
        selectizeInput(
          "ticker",
          label = tags$span(bs_icon("tag"), " Ticker"),
          choices = starter_tickers,
          selected = starter_tickers[1],
          options = list(
            placeholder = "Select or type ticker..."
          )
        ),
        textInput(
          "custom_ticker",
          label = tags$span(bs_icon("search"), " Custom Ticker"),
          placeholder = "Type any symbol, e.g. CRWD"
        ),
        actionButton(
          "add_custom_ticker",
          label = tagList(bs_icon("plus-circle"), " Load Ticker"),
          class = "btn-outline-primary w-100"
        ),
        div(
          class = "small text-muted mt-1",
          "Choose a starter ticker or load any symbol manually."
        ),
        radioButtons(
          "chart_interval",
          label = tags$span(bs_icon("bar-chart-steps"), " Chart Interval"),
          choices = c("Daily" = "daily", "Weekly" = "weekly", "Monthly" = "monthly"),
          selected = "daily",
          inline = TRUE
        ),
        hr(),
        dateRangeInput(
          "date_range",
          label = tags$span(bs_icon("calendar-range"), " Date Range"),
          start = Sys.Date() - 365,
          end = Sys.Date(),
          min = Sys.Date() - 3650,
          max = Sys.Date()
        ),
        hr(),
        tags$label(tags$span(bs_icon("layers"), " Overlays"), class = "form-label"),
        checkboxInput("show_ema9", "EMA 9", value = FALSE),
        checkboxInput("show_sma13", "SMA 13", value = FALSE),
        checkboxInput("show_sma30", "SMA 30", value = FALSE),
        checkboxInput("show_sma50", "SMA 50", value = TRUE),
        checkboxInput("show_sma200", "SMA 200", value = TRUE),
        checkboxInput("show_bbands", "Bollinger Bands (20,2)", value = FALSE),
        checkboxInput("show_sma20_bands", "SMA20 Std Dev Bands (1/2/3σ)", value = FALSE),
        checkboxInput("show_ichimoku", "Ichimoku Cloud", value = FALSE),
        checkboxInput("show_vwap", "VWAP (Volume Weighted Avg Price)", value = FALSE),
        checkboxInput("show_volume_ma", "Volume MA20 + Std Dev Bands", value = FALSE),
        hr(),
        tags$label(tags$span(bs_icon("activity"), " Indicators"), class = "form-label"),
        checkboxInput("show_pct_from_ema8", "% Close from 8 EMA", value = FALSE),
        checkboxInput("show_atr_extension", "ATR% Extension (MA50/ATR30)", value = FALSE),
        checkboxInput("show_rsi", "RSI (14)", value = FALSE),
        checkboxInput("show_roc", "Rate of Change (12)", value = FALSE),
        checkboxInput("show_price_stddev", "Price Std Dev (20)", value = FALSE),
        checkboxInput("show_velocity", "Velocity (ATR σ / Vol σ)", value = FALSE),
        checkboxInput("show_volume_profile", "Volume Profile (POC/VAH/VAL)", value = FALSE),
        conditionalPanel(
          condition = "input.show_volume_profile",
          div(
            class = "ps-3 small",
            dateInput("vp_date", "Target Date", value = Sys.Date()),
            numericInput("vp_lookback", "Lookback Days", value = 20, min = 5, max = 252, step = 5),
            sliderInput("vp_value_area", "Value Area %", min = 50, max = 90, value = 70, step = 5)
          )
        ),
        hr(),
        tags$label(tags$span(bs_icon("trophy"), " Alerts"), class = "form-label"),
        checkboxInput("show_52w_alert", "52-Week High/Low Alert 🎯", value = TRUE),
        uiOutput("week52_alert"),
        hr(),
        card(
          card_header(class = "bg-light", tags$span(bs_icon("clipboard-data"), " Key Metrics")),
          card_body(
            class = "p-2",
            tableOutput("metrics_table")
          )
        )
      ),
      layout_columns(
        col_widths = c(12),
        card(
          full_screen = TRUE,
          card_header(
            class = "d-flex justify-content-between align-items-center",
            tags$span(
              bs_icon("graph-up"),
              textOutput("chart_title", inline = TRUE)
            ),
            popover(
              bs_icon("gear", class = "text-muted"),
              title = "Chart Info",
              "Candlestick chart with optional overlays. Toggle in sidebar."
            )
          ),
          card_body(
            class = "p-1",
            plotlyOutput("candle_plot", height = "500px")
          )
        ),
        conditionalPanel(
          condition = "input.show_atr_extension",
          card(
            full_screen = TRUE,
            card_header(
              tags$span(bs_icon("activity"), " ATR% Extension (MA50 / ATR30)")
            ),
            card_body(
              class = "p-1",
              plotlyOutput("atr_extension_plot", height = "160px")
            )
          )
        ),
        conditionalPanel(
          condition = "input.show_rsi",
          card(
            full_screen = TRUE,
            card_header(
              tags$span(bs_icon("speedometer2"), " RSI (14)")
            ),
            card_body(
              class = "p-1",
              plotlyOutput("rsi_plot", height = "160px")
            )
          )
        ),
        conditionalPanel(
          condition = "input.show_roc",
          card(
            full_screen = TRUE,
            card_header(
              tags$span(bs_icon("percent"), " Rate of Change (12)")
            ),
            card_body(
              class = "p-1",
              plotlyOutput("roc_plot", height = "160px")
            )
          )
        ),
        conditionalPanel(
          condition = "input.show_pct_from_ema8",
          card(
            full_screen = TRUE,
            card_header(
              tags$span(bs_icon("graph-down-arrow"), " % Close from 8 EMA")
            ),
            card_body(
              class = "p-1",
              plotlyOutput("pct_from_ema8_plot", height = "160px")
            )
          )
        ),
        conditionalPanel(
          condition = "input.show_price_stddev",
          card(
            full_screen = TRUE,
            card_header(
              tags$span(bs_icon("graph-up"), " Price Std Dev (20)")
            ),
            card_body(
              class = "p-1",
              plotlyOutput("price_stddev_plot", height = "160px")
            )
          )
        ),
        conditionalPanel(
          condition = "input.show_velocity",
          card(
            full_screen = TRUE,
            card_header(
              tags$span(bs_icon("speedometer"), " Velocity (ATR σ / Vol σ)")
            ),
            card_body(
              class = "p-1",
              plotlyOutput("velocity_plot", height = "160px")
            )
          )
        )
      )
    )
  ),
  nav_panel(
    title = "Dashboard",
    icon = bs_icon("grid-1x2"),
    layout_sidebar(
      sidebar = sidebar(
        width = 280,
        bg = "#f8f9fa",
        title = tags$span(bs_icon("calendar-check"), " Date Filter"),
        dateInput(
          "dashboard_date",
          label = tags$span(bs_icon("calendar"), " Target Date"),
          value = Sys.Date(),
          max = Sys.Date()
        ),
        hr(),
        card(
          card_header(class = "bg-light", "Legend"),
          card_body(
            class = "small",
            tags$ul(
              class = "list-unstyled mb-0",
              tags$li("✅ = Bullish condition"),
              tags$li("❌ = Bearish condition"),
              tags$li("➖ = Neutral/N/A")
            )
          )
        )
      ),
      card(
        full_screen = TRUE,
        card_header(
          tags$span(bs_icon("table"), " Tracked Ticker Overview")
        ),
        card_body(
          gt_output("dashboard_table")
        )
      )
    )
  ),
  nav_panel(
    title = "Comparison",
    icon = bs_icon("columns-gap"),
    layout_sidebar(
      sidebar = sidebar(
        width = 280,
        bg = "#f8f9fa",
        title = tags$span(bs_icon("list-check"), " Compare"),
        selectizeInput(
          "compare_tickers",
          label = tags$span(bs_icon("tags"), " Select Tickers"),
          choices = starter_tickers,
          selected = starter_tickers[seq_len(min(3, length(starter_tickers)))],
          multiple = TRUE,
          options = list(
            maxItems = 6,
            plugins = list("remove_button")
          )
        ),
        dateRangeInput(
          "compare_date_range",
          label = tags$span(bs_icon("calendar-range"), " Date Range"),
          start = Sys.Date() - 180,
          end = Sys.Date(),
          min = Sys.Date() - 3650,
          max = Sys.Date()
        ),
        actionButton(
          "compare_btn",
          label = tagList(bs_icon("arrow-repeat"), " Compare"),
          class = "btn-secondary w-100 btn-lg"
        )
      ),
      card(
        full_screen = TRUE,
        card_header(
          tags$span(bs_icon("graph-up-arrow"), " Normalized Price Comparison")
        ),
        card_body(
          plotlyOutput("compare_plot", height = "500px")
        )
      )
    )
  ),
  nav_panel(
    title = "Data",
    icon = bs_icon("table"),
    card(
      card_header(
        class = "d-flex justify-content-between align-items-center",
        tags$span(bs_icon("database"), " Raw OHLCV Data"),
        downloadButton("download_csv", "Download CSV", class = "btn-sm btn-outline-primary")
      ),
      card_body(
        DTOutput("data_table")
      )
    )
  ),
  nav_panel(
    title = "Latest Move",
    icon = bs_icon("lightning-charge"),
    layout_sidebar(
      sidebar = sidebar(
        width = 300,
        bg = "#f8f9fa",
        title = tags$span(bs_icon("clipboard-check"), " Setup Criteria"),
        card(
          card_header(class = "bg-light", "Checklist"),
          card_body(
            class = "small",
            tags$ul(
              class = "list-unstyled mb-0",
              tags$li(bs_icon("check-circle"), " 3+ consecutive up days"),
              tags$li(bs_icon("check-circle"), " 2 overnight gap ups"),
              tags$li(bs_icon("check-circle"), " 2/3 range expansion days"),
              tags$li(bs_icon("check-circle"), " 2 volume expansion days"),
              tags$li(bs_icon("check-circle"), " Climax gap up (critical)")
            )
          )
        ),
        hr(),
        card(
          card_header(class = "bg-light", "Grading Scale"),
          card_body(
            class = "small",
            tags$ul(
              class = "list-unstyled mb-0",
              tags$li(tags$strong("A+ (9-10):"), " Ideal setup"),
              tags$li(tags$strong("A (7-8):"), " Strong candidate"),
              tags$li(tags$strong("B (5-6):"), " Viable setup"),
              tags$li(tags$strong("C (3-4):"), " Weak setup"),
              tags$li(tags$strong("D (0-2):"), " Not ready")
            )
          )
        ),
        hr(),
      ),
      layout_columns(
        col_widths = c(12),
        card(
          card_header(
            tags$span(bs_icon("speedometer2"), " Latest Move Setup Scores")
          ),
          card_body(
            DTOutput("parabolic_table")
          )
        ),
        card(
          card_header(
            tags$span(bs_icon("table"), " Last 5 Days Detail (Selected Ticker)")
          ),
          card_body(
            DTOutput("parabolic_detail_table")
          )
        )
      )
    )
  ),
  nav_item(
    tags$a(
      href = "https://github.com/Alaburda/stockr",
      target = "_blank",
      class = "nav-link",
      bs_icon("github"),
      " GitHub"
    )
  )
)

server <- function(input, output, session) {
  # Reactive list of tickers available across the app for the current session.
  tracked_tickers <- reactiveVal(starter_tickers)

  sync_ticker_inputs <- function(selected_ticker = NULL, selected_compare = NULL) {
    choice_values <- normalize_tickers(c(
      tracked_tickers(),
      selected_ticker %||% character(),
      selected_compare %||% character()
    ))
    choices <- stats::setNames(choice_values, choice_values)
    selected_ticker_value <- normalize_tickers(selected_ticker %||% character())
    if (length(selected_ticker_value) == 0) {
      selected_ticker_value <- tracked_tickers()[1]
    }
    compare_selected <- normalize_tickers(selected_compare %||% character())
    updateSelectizeInput(
      session,
      "ticker",
      choices = choices,
      selected = selected_ticker_value[1],
      server = TRUE
    )
    updateSelectizeInput(
      session,
      "compare_tickers",
      choices = choices,
      selected = compare_selected[seq_len(min(6, length(compare_selected)))],
      server = TRUE
    )
  }

  observeEvent(input$add_custom_ticker, {
    ticker <- normalize_tickers(input$custom_ticker)[1]
    req(!is.null(ticker), nzchar(ticker))
    if (!is.null(ticker) && nzchar(ticker) && !(ticker %in% tracked_tickers())) {
      new_tracked <- normalize_tickers(c(tracked_tickers(), ticker))
      tracked_tickers(new_tracked)
      current_compare <- intersect(input$compare_tickers %||% character(), new_tracked)
      if (!ticker %in% current_compare) {
        current_compare <- c(current_compare, ticker)
      }
      sync_ticker_inputs(
        selected_ticker = ticker,
        selected_compare = current_compare
      )
    } else {
      sync_ticker_inputs(
        selected_ticker = ticker,
        selected_compare = input$compare_tickers
      )
    }
    updateTextInput(session, "custom_ticker", value = "")
  })

  observe({
    compare_tickers <- normalize_tickers(input$compare_tickers %||% character())
    missing_tickers <- setdiff(compare_tickers, tracked_tickers())
    if (length(missing_tickers) > 0) {
      tracked_tickers(normalize_tickers(c(tracked_tickers(), missing_tickers)))
      sync_ticker_inputs(
        selected_ticker = input$ticker,
        selected_compare = compare_tickers
      )
    }
  })

  # Fetch single ticker data - now reactive to ticker/date_range changes
  ticker_data <- reactive({
    req(input$ticker)
    sym <- toupper(input$ticker)
    dr <- input$date_range
    interval <- input$chart_interval %||% "daily"

    withProgress(message = paste("Fetching", sym, "..."), value = 0.3, {
      xt <- tryCatch(
        getSymbols(sym, src = "yahoo", auto.assign = FALSE, warnings = FALSE),
        error = function(e) {
          showNotification(paste("Error fetching", sym), type = "error")
          return(NULL)
        }
      )
      req(!is.null(xt))
      incProgress(0.4)

      xt <- xt[order(zoo::index(xt)), ]
      if (identical(interval, "weekly")) {
        xt <- to.weekly(xt, OHLC = TRUE, name = NULL)
      } else if (identical(interval, "monthly")) {
        xt <- to.monthly(xt, OHLC = TRUE, name = NULL)
        zoo::index(xt) <- as.Date(zoo::index(xt), frac = 1)
      }
      if (!is.null(dr) && length(dr) == 2) {
        xt <- xt[paste(dr[1], dr[2], sep = "/")]
      }
      req(nrow(xt) > 0)

      close_xt <- Cl(xt)
      open_xt <- Op(xt)
      high_xt <- Hi(xt)
      low_xt <- Lo(xt)
      vol_xt <- Vo(xt)
      n_rows <- nrow(xt)

      # EMAs
      ema8 <- if (n_rows >= 8) EMA(close_xt, 8) else rep(NA, n_rows)
      ema9 <- if (n_rows >= 9) EMA(close_xt, 9) else rep(NA, n_rows)
      pct_from_ema8 <- ((as.numeric(close_xt) - as.numeric(ema8)) / as.numeric(ema8)) * 100

      # SMAs - return NA vector if not enough data
      sma13 <- if (n_rows >= 13) SMA(close_xt, 13) else rep(NA, n_rows)
      sma30 <- if (n_rows >= 30) SMA(close_xt, 30) else rep(NA, n_rows)
      sma50 <- if (n_rows >= 50) SMA(close_xt, 50) else rep(NA, n_rows)
      sma200 <- if (n_rows >= 200) SMA(close_xt, 200) else rep(NA, n_rows)

      # Bollinger Bands
      bb <- if (n_rows >= 20) BBands(HLC(xt), n = 20, sd = 2) else matrix(NA, nrow = n_rows, ncol = 4, dimnames = list(NULL, c("dn", "mavg", "up", "pctB")))

      # SMA20 with 1/2/3 standard deviation bands
      sma20 <- if (n_rows >= 20) SMA(close_xt, 20) else rep(NA, n_rows)
      sd20 <- if (n_rows >= 20) runSD(close_xt, 20) else rep(NA, n_rows)
      sma20_1up <- sma20 + sd20
      sma20_1dn <- sma20 - sd20
      sma20_2up <- sma20 + 2 * sd20
      sma20_2dn <- sma20 - 2 * sd20
      sma20_3up <- sma20 + 3 * sd20
      sma20_3dn <- sma20 - 3 * sd20

      # Ichimoku (needs at least 52 periods)
      ichi <- tryCatch({
        if (n_rows < 52) stop("Not enough data")
        # Tenkan-sen (9), Kijun-sen (26), Senkou Span A/B (52)
        tenkan <- (runMax(high_xt, 9) + runMin(low_xt, 9)) / 2
        kijun <- (runMax(high_xt, 26) + runMin(low_xt, 26)) / 2
        senkou_a <- (tenkan + kijun) / 2
        senkou_b <- (runMax(high_xt, 52) + runMin(low_xt, 52)) / 2
        list(tenkan = tenkan, kijun = kijun, senkou_a = senkou_a, senkou_b = senkou_b)
      }, error = function(e) NULL)

      # ATR metrics - graceful fallback if not enough data
      atr14 <- if (n_rows >= 14) ATR(HLC(xt), n = 14)[, "atr"] else rep(NA, n_rows)
      atr30 <- if (n_rows >= 30) ATR(HLC(xt), n = 30)[, "atr"] else rep(NA, n_rows)
      atr_pct <- (atr14 / close_xt) * 100
      atr30_pct <- (atr30 / close_xt) * 100
      pct_from_ma50 <- ((close_xt - sma50) / sma50) * 100
      pct_from_sma200 <- (close_xt / sma200 - 1) * 100
      extension_ratio <- pct_from_ma50 / atr_pct
      atr_extension_ratio <- pct_from_ma50 / atr30_pct

      # RSI
      rsi14 <- if (n_rows >= 14) RSI(close_xt, n = 14) else rep(NA, n_rows)

      # Rate of Change (12-period)
      roc12 <- if (n_rows >= 12) ROC(close_xt, n = 12, type = "discrete") * 100 else rep(NA, n_rows)

      # Volume Moving Average (20-period)
      vol_ma20 <- if (n_rows >= 20) SMA(vol_xt, 20) else rep(NA, n_rows)
      vol_ratio <- as.numeric(vol_xt) / as.numeric(vol_ma20)  # Volume relative to MA
      vol_sd20 <- if (n_rows >= 20) runSD(vol_xt, 20) else rep(NA, n_rows)

      # Price Standard Deviation (20-period rolling)
      price_sd20 <- if (n_rows >= 20) runSD(close_xt, 20) else rep(NA, n_rows)

      # VWAP (cumulative for the visible period)
      typical_price <- (as.numeric(high_xt) + as.numeric(low_xt) + as.numeric(close_xt)) / 3
      cum_tp_vol <- cumsum(typical_price * as.numeric(vol_xt))
      cum_vol <- cumsum(as.numeric(vol_xt))
      vwap <- cum_tp_vol / cum_vol

      # Volume std dev bands (1/2/3 sigma)
      vol_ma20_1up <- as.numeric(vol_ma20) + as.numeric(vol_sd20)
      vol_ma20_1dn <- pmax(0, as.numeric(vol_ma20) - as.numeric(vol_sd20))
      vol_ma20_2up <- as.numeric(vol_ma20) + 2 * as.numeric(vol_sd20)
      vol_ma20_2dn <- pmax(0, as.numeric(vol_ma20) - 2 * as.numeric(vol_sd20))
      vol_ma20_3up <- as.numeric(vol_ma20) + 3 * as.numeric(vol_sd20)
      vol_ma20_3dn <- pmax(0, as.numeric(vol_ma20) - 3 * as.numeric(vol_sd20))

      # Velocity indicator: rolling std dev of ATR / rolling std dev of Volume
      # This measures the ratio of price volatility dispersion to volume dispersion
      atr_sd20 <- if (n_rows >= 20) runSD(atr14, 20) else rep(NA, n_rows)
      # Normalize by dividing ATR std by mean ATR and Vol std by mean Vol to make ratio meaningful
      atr_cv <- as.numeric(atr_sd20) / as.numeric(if (n_rows >= 20) SMA(atr14, 20) else rep(NA, n_rows))
      vol_cv <- as.numeric(vol_sd20) / as.numeric(vol_ma20)
      velocity <- atr_cv / vol_cv  # Ratio of coefficient of variations

      incProgress(0.3)

      df <- data.frame(
        Date = zoo::index(xt),
        Open = as.numeric(open_xt),
        High = as.numeric(high_xt),
        Low = as.numeric(low_xt),
        Close = as.numeric(close_xt),
        Volume = as.numeric(vol_xt),
        EMA8 = as.numeric(ema8),
        EMA9 = as.numeric(ema9),
        Pct_from_EMA8 = as.numeric(pct_from_ema8),
        SMA13 = as.numeric(sma13),
        SMA30 = as.numeric(sma30),
        SMA50 = as.numeric(sma50),
        SMA200 = as.numeric(sma200),
        BB_upper = as.numeric(bb[, "up"]),
        BB_mid = as.numeric(bb[, "mavg"]),
        BB_lower = as.numeric(bb[, "dn"]),
        SMA20 = as.numeric(sma20),
        SMA20_1up = as.numeric(sma20_1up),
        SMA20_1dn = as.numeric(sma20_1dn),
        SMA20_2up = as.numeric(sma20_2up),
        SMA20_2dn = as.numeric(sma20_2dn),
        SMA20_3up = as.numeric(sma20_3up),
        SMA20_3dn = as.numeric(sma20_3dn),
        ATR14 = as.numeric(atr14),
        ATR30 = as.numeric(atr30),
        ATR_pct = as.numeric(atr_pct),
        ATR30_pct = as.numeric(atr30_pct),
        ATR_Extension = as.numeric(atr_extension_ratio),
        RSI14 = as.numeric(rsi14),
        ROC12 = as.numeric(roc12),
        Pct_from_MA50 = as.numeric(pct_from_ma50),
        Pct_from_SMA200 = as.numeric(pct_from_sma200),
        Extension_Ratio = as.numeric(extension_ratio),
        Vol_MA20 = as.numeric(vol_ma20),
        Vol_Ratio = as.numeric(vol_ratio),
        Vol_MA20_1up = vol_ma20_1up,
        Vol_MA20_1dn = vol_ma20_1dn,
        Vol_MA20_2up = vol_ma20_2up,
        Vol_MA20_2dn = vol_ma20_2dn,
        Vol_MA20_3up = vol_ma20_3up,
        Vol_MA20_3dn = vol_ma20_3dn,
        Price_SD20 = as.numeric(price_sd20),
        VWAP = as.numeric(vwap),
        Velocity = as.numeric(velocity)
      )

      if (!is.null(ichi)) {
        df$Tenkan <- as.numeric(ichi$tenkan)
        df$Kijun <- as.numeric(ichi$kijun)
        df$Senkou_A <- as.numeric(ichi$senkou_a)
        df$Senkou_B <- as.numeric(ichi$senkou_b)
      }

      list(symbol = sym, df = df)
    })
  }) %>% bindCache(input$ticker, input$date_range, input$chart_interval)

  # LVN/HVN calculation function - uses target date and lookback days
  # Calculate Volume Profile: POC (Point of Control), VAH (Value Area High), VAL (Value Area Low)
  calculate_volume_profile <- function(df, target_date, lookback_days = 20, value_area_pct = 70) {
    n_bins <- 50  # Fixed resolution for smooth histogram
    n <- nrow(df)
    if (n < 10) return(list(poc = NA, vah = NA, val = NA, profile = NULL))
    
    # Filter data: from (target_date - lookback_days) to target_date
    target_date <- as.Date(target_date)
    start_date <- target_date - lookback_days
    
    subset_df <- df[df$Date >= start_date & df$Date <= target_date, ]
    if (nrow(subset_df) < 5) return(list(poc = NA, vah = NA, val = NA, profile = NULL))
    
    price_high <- max(subset_df$High, na.rm = TRUE)
    price_low <- min(subset_df$Low, na.rm = TRUE)
    if (price_high <= price_low) return(list(poc = NA, vah = NA, val = NA, profile = NULL))
    
    step <- (price_high - price_low) / n_bins
    price_levels <- price_low + (0:(n_bins - 1) + 0.5) * step
    bin_bottoms <- price_low + (0:(n_bins - 1)) * step
    bin_tops <- bin_bottoms + step
    volume_at_price <- rep(0, n_bins)
    
    # Distribute volume across price bins (TPO-style)
    for (i in seq_len(nrow(subset_df))) {
      h <- subset_df$High[i]
      l <- subset_df$Low[i]
      v <- subset_df$Volume[i]
      if (is.na(h) || is.na(l) || is.na(v) || v <= 0) next
      
      low_bin <- max(1, min(n_bins, floor((l - price_low) / step) + 1))
      high_bin <- max(1, min(n_bins, floor((h - price_low) / step) + 1))
      bins_touched <- max(1, high_bin - low_bin + 1)
      vol_per_bin <- v / bins_touched
      
      for (bin in low_bin:high_bin) {
        if (bin >= 1 && bin <= n_bins) {
          volume_at_price[bin] <- volume_at_price[bin] + vol_per_bin
        }
      }
    }
    
    total_vol <- sum(volume_at_price, na.rm = TRUE)
    if (total_vol <= 0) return(list(poc = NA, vah = NA, val = NA, profile = NULL))
    
    # POC = price level with highest volume
    poc_idx <- which.max(volume_at_price)
    poc <- price_levels[poc_idx]
    
    # Value Area: expand from POC until we capture value_area_pct% of total volume
    target_vol <- total_vol * (value_area_pct / 100)
    va_vol <- volume_at_price[poc_idx]
    va_low_idx <- poc_idx
    va_high_idx <- poc_idx
    
    while (va_vol < target_vol && (va_low_idx > 1 || va_high_idx < n_bins)) {
      vol_below <- if (va_low_idx > 1) volume_at_price[va_low_idx - 1] else 0
      vol_above <- if (va_high_idx < n_bins) volume_at_price[va_high_idx + 1] else 0
      
      if (vol_below >= vol_above && va_low_idx > 1) {
        va_low_idx <- va_low_idx - 1
        va_vol <- va_vol + volume_at_price[va_low_idx]
      } else if (va_high_idx < n_bins) {
        va_high_idx <- va_high_idx + 1
        va_vol <- va_vol + volume_at_price[va_high_idx]
      } else if (va_low_idx > 1) {
        va_low_idx <- va_low_idx - 1
        va_vol <- va_vol + volume_at_price[va_low_idx]
      } else {
        break
      }
    }
    
    val <- price_low + (va_low_idx - 1) * step
    vah <- price_low + va_high_idx * step
    
    # Build profile data frame for histogram overlay
    in_va <- seq_len(n_bins) >= va_low_idx & seq_len(n_bins) <= va_high_idx
    is_poc <- seq_len(n_bins) == poc_idx
    
    profile <- data.frame(
      price_mid = price_levels,
      bin_bottom = bin_bottoms,
      bin_top = bin_tops,
      volume = volume_at_price,
      vol_norm = volume_at_price / max(volume_at_price),
      in_value_area = in_va,
      is_poc = is_poc,
      stringsAsFactors = FALSE
    )
    
    list(poc = poc, vah = vah, val = val, profile = profile)
  }

  # Chart title
  output$chart_title <- renderText({
    data <- ticker_data()
    req(data)
    interval_label <- switch(
      input$chart_interval %||% "daily",
      daily = "Daily",
      weekly = "Weekly",
      monthly = "Monthly",
      "Daily"
    )
    paste0(" ", data$symbol, " — ", interval_label, " Price Chart")
  })

  # Candlestick chart with optional overlays
  output$candle_plot <- renderPlotly({
    data <- ticker_data()
    req(data)
    df <- data$df
    req(nrow(df) > 0)

    # Volume bar colors
    vol_colors <- ifelse(df$Close >= df$Open, "rgba(24, 188, 156, 0.6)", "rgba(231, 76, 60, 0.6)")

    p <- plot_ly(df, x = ~Date) %>%
      # Volume bars on secondary y-axis (add first so they're behind candles)
      add_bars(
        y = ~Volume, 
        marker = list(color = vol_colors),
        name = "Volume",
        yaxis = "y2",
        showlegend = FALSE,
        hoverinfo = "text",
        text = ~paste0("Vol: ", formatC(Volume, format = "d", big.mark = ","))
      )

    # Volume MA20 with Std Dev Bands overlay (on y2 axis)
    if (isTRUE(input$show_volume_ma)) {
      p <- p %>%
        # 3 sigma band (outermost, lightest)
        add_ribbons(
          ymin = ~Vol_MA20_3dn,
          ymax = ~Vol_MA20_3up,
          fillcolor = "rgba(255, 152, 0, 0.08)",
          line = list(width = 0),
          name = "Vol 3σ",
          yaxis = "y2",
          showlegend = FALSE
        ) %>%
        # 2 sigma band
        add_ribbons(
          ymin = ~Vol_MA20_2dn,
          ymax = ~Vol_MA20_2up,
          fillcolor = "rgba(255, 152, 0, 0.12)",
          line = list(width = 0),
          name = "Vol 2σ",
          yaxis = "y2",
          showlegend = FALSE
        ) %>%
        # 1 sigma band (innermost, darkest)
        add_ribbons(
          ymin = ~Vol_MA20_1dn,
          ymax = ~Vol_MA20_1up,
          fillcolor = "rgba(255, 152, 0, 0.18)",
          line = list(width = 0),
          name = "Vol 1σ",
          yaxis = "y2",
          showlegend = FALSE
        ) %>%
        add_lines(y = ~Vol_MA20, name = "Vol MA20", line = list(color = "#ff9800", width = 1.5), yaxis = "y2")
    }

    p <- p %>%
      add_trace(
        type = "candlestick",
        open = ~Open, high = ~High, low = ~Low, close = ~Close,
        name = data$symbol,
        increasing = list(line = list(color = "#18bc9c")),
        decreasing = list(line = list(color = "#e74c3c"))
      )

    # Ichimoku cloud (add first so it's behind price)
    if (isTRUE(input$show_ichimoku) && "Senkou_A" %in% names(df)) {
      p <- p %>%
        add_ribbons(
          ymin = ~pmin(Senkou_A, Senkou_B),
          ymax = ~pmax(Senkou_A, Senkou_B),
          fillcolor = "rgba(156, 39, 176, 0.15)",
          line = list(width = 0),
          name = "Kumo",
          showlegend = FALSE
        ) %>%
        add_lines(y = ~Tenkan, name = "Tenkan (9)", line = list(color = "#2196F3", width = 1, dash = "dot")) %>%
        add_lines(y = ~Kijun, name = "Kijun (26)", line = list(color = "#9C27B0", width = 1, dash = "dot"))
    }

    # Bollinger Bands
    if (isTRUE(input$show_bbands)) {
      p <- p %>%
        add_ribbons(
          ymin = ~BB_lower,
          ymax = ~BB_upper,
          fillcolor = "rgba(100, 100, 100, 0.1)",
          line = list(width = 0),
          name = "BB Band",
          showlegend = FALSE
        ) %>%
        add_lines(y = ~BB_upper, name = "BB Upper", line = list(color = "#888", width = 1, dash = "dash")) %>%
        add_lines(y = ~BB_lower, name = "BB Lower", line = list(color = "#888", width = 1, dash = "dash")) %>%
        add_lines(y = ~BB_mid, name = "BB Mid", line = list(color = "#555", width = 1))
    }

    # SMA20 Standard Deviation Bands (1/2/3 sigma)
    if (isTRUE(input$show_sma20_bands)) {
      p <- p %>%
        # 3 sigma band (outermost, lightest)
        add_ribbons(
          ymin = ~SMA20_3dn,
          ymax = ~SMA20_3up,
          fillcolor = "rgba(33, 150, 243, 0.08)",
          line = list(width = 0),
          name = "3σ",
          showlegend = FALSE
        ) %>%
        # 2 sigma band
        add_ribbons(
          ymin = ~SMA20_2dn,
          ymax = ~SMA20_2up,
          fillcolor = "rgba(33, 150, 243, 0.12)",
          line = list(width = 0),
          name = "2σ",
          showlegend = FALSE
        ) %>%
        # 1 sigma band (innermost, darkest)
        add_ribbons(
          ymin = ~SMA20_1dn,
          ymax = ~SMA20_1up,
          fillcolor = "rgba(33, 150, 243, 0.18)",
          line = list(width = 0),
          name = "1σ",
          showlegend = FALSE
        ) %>%
        add_lines(y = ~SMA20_3up, name = "+3σ", line = list(color = "#90CAF9", width = 0.8, dash = "dot"), showlegend = FALSE) %>%
        add_lines(y = ~SMA20_3dn, name = "-3σ", line = list(color = "#90CAF9", width = 0.8, dash = "dot"), showlegend = FALSE) %>%
        add_lines(y = ~SMA20_2up, name = "+2σ", line = list(color = "#64B5F6", width = 0.8, dash = "dash"), showlegend = FALSE) %>%
        add_lines(y = ~SMA20_2dn, name = "-2σ", line = list(color = "#64B5F6", width = 0.8, dash = "dash"), showlegend = FALSE) %>%
        add_lines(y = ~SMA20_1up, name = "+1σ", line = list(color = "#42A5F5", width = 1), showlegend = FALSE) %>%
        add_lines(y = ~SMA20_1dn, name = "-1σ", line = list(color = "#42A5F5", width = 1), showlegend = FALSE) %>%
        add_lines(y = ~SMA20, name = "SMA 20", line = list(color = "#1976D2", width = 1.5))
    }

    # EMAs
    if (isTRUE(input$show_ema9)) {
      p <- p %>% add_lines(y = ~EMA9, name = "EMA 9", line = list(color = "#9c27b0", width = 1.2))
    }

    # SMAs
    if (isTRUE(input$show_sma13)) {
      p <- p %>% add_lines(y = ~SMA13, name = "SMA 13", line = list(color = "#e91e63", width = 1.2))
    }
    if (isTRUE(input$show_sma30)) {
      p <- p %>% add_lines(y = ~SMA30, name = "SMA 30", line = list(color = "#00bcd4", width = 1.2))
    }
    if (isTRUE(input$show_sma50)) {
      p <- p %>% add_lines(y = ~SMA50, name = "SMA 50", line = list(color = "#3498db", width = 1.5))
    }
    if (isTRUE(input$show_sma200)) {
      p <- p %>% add_lines(y = ~SMA200, name = "SMA 200", line = list(color = "#f39c12", width = 1.5))
    }

    # VWAP overlay
    if (isTRUE(input$show_vwap)) {
      p <- p %>% add_lines(y = ~VWAP, name = "VWAP", line = list(color = "#ff5722", width = 2, dash = "solid"))
    }

    # Volume Profile: histogram overlay with POC/VAH/VAL
    if (isTRUE(input$show_volume_profile)) {
      vp <- calculate_volume_profile(
        df,
        target_date = input$vp_date %||% Sys.Date(),
        lookback_days = input$vp_lookback %||% 20,
        value_area_pct = input$vp_value_area %||% 70
      )
      
      if (!is.null(vp$profile) && !is.na(vp$poc)) {
        prof <- vp$profile
        
        # Map histogram bars onto the right ~20% of the x-axis date range
        date_range <- as.numeric(max(df$Date) - min(df$Date))
        bar_start <- max(df$Date) + 1  # start just after last candle
        max_bar_width <- date_range * 0.18  # bars span up to 18% of chart width
        
        # Add rectangle shapes for each bin
        shapes <- lapply(seq_len(nrow(prof)), function(i) {
          bar_width <- prof$vol_norm[i] * max_bar_width
          fill_color <- if (prof$is_poc[i]) {
            "rgba(255, 82, 82, 0.55)"   # POC - red
          } else if (prof$in_value_area[i]) {
            "rgba(66, 165, 245, 0.35)"   # Value area - blue
          } else {
            "rgba(158, 158, 158, 0.2)"   # Outside VA - grey
          }
          list(
            type = "rect",
            xref = "x", yref = "y",
            x0 = as.character(bar_start),
            x1 = as.character(bar_start + bar_width),
            y0 = prof$bin_bottom[i],
            y1 = prof$bin_top[i],
            fillcolor = fill_color,
            line = list(width = 0)
          )
        })
        
        # Extend x-axis to accommodate histogram
        x_end <- bar_start + max_bar_width + date_range * 0.02
        
        # POC/VAH/VAL annotation lines (dashed, spanning full chart)
        poc_line <- list(
          type = "line", xref = "x", yref = "y",
          x0 = as.character(min(df$Date)), x1 = as.character(x_end),
          y0 = vp$poc, y1 = vp$poc,
          line = list(color = "rgba(255, 82, 82, 0.7)", width = 1.5, dash = "dot")
        )
        vah_line <- list(
          type = "line", xref = "x", yref = "y",
          x0 = as.character(min(df$Date)), x1 = as.character(x_end),
          y0 = vp$vah, y1 = vp$vah,
          line = list(color = "rgba(66, 165, 245, 0.6)", width = 1, dash = "dash")
        )
        val_line <- list(
          type = "line", xref = "x", yref = "y",
          x0 = as.character(min(df$Date)), x1 = as.character(x_end),
          y0 = vp$val, y1 = vp$val,
          line = list(color = "rgba(66, 165, 245, 0.6)", width = 1, dash = "dash")
        )
        
        all_shapes <- c(shapes, list(poc_line, vah_line, val_line))
        
        # Annotations for POC/VAH/VAL labels
        annots <- list(
          list(x = as.character(bar_start), y = vp$poc, text = paste0("POC $", round(vp$poc, 2)),
               xref = "x", yref = "y", showarrow = FALSE, font = list(size = 10, color = "#ff5252"),
               xanchor = "left", yanchor = "bottom"),
          list(x = as.character(bar_start), y = vp$vah, text = paste0("VAH $", round(vp$vah, 2)),
               xref = "x", yref = "y", showarrow = FALSE, font = list(size = 10, color = "#42a5f5"),
               xanchor = "left", yanchor = "bottom"),
          list(x = as.character(bar_start), y = vp$val, text = paste0("VAL $", round(vp$val, 2)),
               xref = "x", yref = "y", showarrow = FALSE, font = list(size = 10, color = "#42a5f5"),
               xanchor = "left", yanchor = "top")
        )
        
        p <- p %>% layout(
          shapes = all_shapes,
          annotations = annots,
          xaxis = list(range = list(as.character(min(df$Date)), as.character(x_end)))
        )
      }
    }

    # 52-Week High/Low markers
    if (isTRUE(input$show_52w_alert)) {
      n <- nrow(df)
      is_52w_high <- rep(FALSE, n)
      is_52w_low <- rep(FALSE, n)
      
      for (i in 1:n) {
        lookback <- min(252, i)
        start_idx <- max(1, i - lookback + 1)
        window_closes <- df$Close[start_idx:i]
        
        # Only mark if we have at least 20 days of data
        if (length(window_closes) >= 20) {
          if (df$Close[i] >= max(window_closes, na.rm = TRUE)) {
            is_52w_high[i] <- TRUE
          }
          if (df$Close[i] <= min(window_closes, na.rm = TRUE)) {
            is_52w_low[i] <- TRUE
          }
        }
      }
      
      # Add 52-week high markers (green triangles above candles)
      highs_df <- df[is_52w_high, ]
      if (nrow(highs_df) > 0) {
        p <- p %>% add_trace(
          data = highs_df,
          x = ~Date,
          y = ~High * 1.01,
          type = "scatter",
          mode = "markers",
          marker = list(
            symbol = "triangle-down",
            size = 10,
            color = "#2ecc71"
          ),
          name = "52W High 🚀",
          hoverinfo = "text",
          text = ~paste0("🚀 52W HIGH\n$", round(Close, 2), "\n", Date)
        )
      }
      
      # Add 52-week low markers (red triangles below candles)
      lows_df <- df[is_52w_low, ]
      if (nrow(lows_df) > 0) {
        p <- p %>% add_trace(
          data = lows_df,
          x = ~Date,
          y = ~Low * 0.99,
          type = "scatter",
          mode = "markers",
          marker = list(
            symbol = "triangle-up",
            size = 10,
            color = "#e74c3c"
          ),
          name = "52W Low 💀",
          hoverinfo = "text",
          text = ~paste0("💀 52W LOW\n$", round(Close, 2), "\n", Date)
        )
      }
    }

    p %>% layout(
      xaxis = list(
        title = "",
        rangeslider = list(visible = FALSE),
        type = "date"
      ),
      yaxis = list(title = "Price ($)", domain = c(0.25, 1)),
      yaxis2 = list(title = "Vol", domain = c(0, 0.2), showgrid = FALSE),
      legend = list(orientation = "h", y = 1.12, x = 0.5, xanchor = "center"),
      margin = list(t = 50, b = 10),
      hovermode = "x unified"
    ) %>%
      config(displayModeBar = TRUE, displaylogo = FALSE)
  })

  # ATR Extension chart
  output$atr_extension_plot <- renderPlotly({
    data <- ticker_data()
    req(data)
    df <- data$df
    req(nrow(df) > 0)

    plot_ly(df, x = ~Date) %>%
      add_lines(y = ~ATR_Extension, name = "ATR Ext", line = list(color = "#3498db", width = 1.5), showlegend = FALSE) %>%
      add_lines(y = ~rep(10, nrow(df)), name = "10", line = list(color = "#e74c3c", width = 1, dash = "dot"), showlegend = FALSE) %>%
      add_lines(y = ~rep(7, nrow(df)), name = "7", line = list(color = "#f39c12", width = 1, dash = "dot"), showlegend = FALSE) %>%
      add_lines(y = ~rep(3, nrow(df)), name = "3", line = list(color = "#18bc9c", width = 1, dash = "dot"), showlegend = FALSE) %>%
      add_lines(y = ~rep(0, nrow(df)), name = "0", line = list(color = "#888", width = 0.5), showlegend = FALSE) %>%
      layout(
        xaxis = list(title = ""),
        yaxis = list(title = "Ext", zeroline = TRUE),
        margin = list(t = 5, b = 20),
        hovermode = "x unified"
      ) %>%
      config(displayModeBar = FALSE)
  })

  # RSI chart
  output$rsi_plot <- renderPlotly({
    data <- ticker_data()
    req(data)
    df <- data$df
    req(nrow(df) > 0)

    # Color RSI line based on overbought/oversold
    plot_ly(df, x = ~Date) %>%
      add_lines(y = ~RSI14, name = "RSI", line = list(color = "#9c27b0", width = 1.5), showlegend = FALSE) %>%
      add_lines(y = ~rep(70, nrow(df)), name = "Overbought", line = list(color = "#e74c3c", width = 1, dash = "dash"), showlegend = FALSE) %>%
      add_lines(y = ~rep(30, nrow(df)), name = "Oversold", line = list(color = "#18bc9c", width = 1, dash = "dash"), showlegend = FALSE) %>%
      add_lines(y = ~rep(50, nrow(df)), name = "Mid", line = list(color = "#888", width = 0.5), showlegend = FALSE) %>%
      add_ribbons(ymin = 30, ymax = 70, fillcolor = "rgba(156, 39, 176, 0.08)", line = list(width = 0), showlegend = FALSE) %>%
      layout(
        xaxis = list(title = ""),
        yaxis = list(title = "RSI", range = c(0, 100)),
        margin = list(t = 5, b = 20),
        hovermode = "x unified"
      ) %>%
      config(displayModeBar = FALSE)
  })

  # ROC (Rate of Change) chart
  output$roc_plot <- renderPlotly({
    data <- ticker_data()
    req(data)
    df <- data$df
    req(nrow(df) > 0)

    # Color based on positive/negative
    colors <- ifelse(df$ROC12 >= 0, "#18bc9c", "#e74c3c")
    
    plot_ly(df, x = ~Date) %>%
      add_bars(y = ~ROC12, marker = list(color = colors), name = "ROC", showlegend = FALSE) %>%
      add_lines(y = ~rep(0, nrow(df)), line = list(color = "#333", width = 1), showlegend = FALSE) %>%
      layout(
        xaxis = list(title = ""),
        yaxis = list(title = "ROC %"),
        margin = list(t = 5, b = 20),
        hovermode = "x unified"
      ) %>%
      config(displayModeBar = FALSE)
  })

  # % Close from 8 EMA chart
  output$pct_from_ema8_plot <- renderPlotly({
    data <- ticker_data()
    req(data)
    df <- data$df
    req(nrow(df) > 0)

    # Color based on positive/negative (above/below EMA)
    colors <- ifelse(df$Pct_from_EMA8 >= 0, "#9c27b0", "#ff9800")
    
    plot_ly(df, x = ~Date) %>%
      add_bars(y = ~Pct_from_EMA8, marker = list(color = colors), name = "% from 8 EMA", showlegend = FALSE) %>%
      add_lines(y = ~rep(0, nrow(df)), line = list(color = "#333", width = 1), showlegend = FALSE) %>%
      layout(
        xaxis = list(title = ""),
        yaxis = list(title = "% from 8 EMA"),
        margin = list(t = 5, b = 20),
        hovermode = "x unified"
      ) %>%
      config(displayModeBar = FALSE)
  })

  # Price Standard Deviation chart
  output$price_stddev_plot <- renderPlotly({
    data <- ticker_data()
    req(data)
    df <- data$df
    req(nrow(df) > 0)

    plot_ly(df, x = ~Date) %>%
      add_lines(y = ~Price_SD20, name = "Price SD", line = list(color = "#673ab7", width = 1.5), showlegend = FALSE) %>%
      layout(
        xaxis = list(title = ""),
        yaxis = list(title = "Price SD (20)"),
        margin = list(t = 5, b = 20),
        hovermode = "x unified"
      ) %>%
      config(displayModeBar = FALSE)
  })

  # Velocity indicator chart (ATR CV / Volume CV)
  output$velocity_plot <- renderPlotly({
    data <- ticker_data()
    req(data)
    df <- data$df
    req(nrow(df) > 0)

    plot_ly(df, x = ~Date) %>%
      add_lines(y = ~Velocity, name = "Velocity", line = list(color = "#00bcd4", width = 1.5), showlegend = FALSE) %>%
      add_lines(y = ~rep(1, nrow(df)), name = "Baseline", line = list(color = "#888", width = 1, dash = "dash"), showlegend = FALSE) %>%
      layout(
        xaxis = list(title = ""),
        yaxis = list(title = "Velocity"),
        margin = list(t = 5, b = 20),
        hovermode = "x unified"
      ) %>%
      config(displayModeBar = FALSE)
  })

  # 52-Week High/Low Alert
  output$week52_alert <- renderUI({
    if (!isTRUE(input$show_52w_alert)) return(NULL)
    
    data <- ticker_data()
    req(data)
    df <- data$df
    req(nrow(df) > 0)
    
    n <- nrow(df)
    
    # Calculate rolling 52-week highs/lows for all points
    high_count <- 0
    low_count <- 0
    for (i in 1:n) {
      lookback <- min(252, i)
      start_idx <- max(1, i - lookback + 1)
      window_closes <- df$Close[start_idx:i]
      if (length(window_closes) >= 20) {
        if (df$Close[i] >= max(window_closes, na.rm = TRUE)) high_count <- high_count + 1
        if (df$Close[i] <= min(window_closes, na.rm = TRUE)) low_count <- low_count + 1
      }
    }
    
    # Latest day status
    lookback_latest <- min(252, n)
    recent_closes <- df$Close[max(1, n - lookback_latest + 1):n]
    latest_close <- df$Close[n]
    high_52w <- max(recent_closes, na.rm = TRUE)
    low_52w <- min(recent_closes, na.rm = TRUE)
    
    at_high <- latest_close >= high_52w
    at_low <- latest_close <= low_52w
    near_high <- latest_close >= high_52w * 0.99
    near_low <- latest_close <= low_52w * 1.01
    
    # Build alert
    status_div <- if (at_high) {
      div(
        class = "alert alert-success py-2 px-3 mb-2",
        style = "font-size: 0.9rem;",
        tags$strong("🚀🎉 52-WEEK HIGH! 🔥🏆"),
        br(),
        paste0("$", round(high_52w, 2), " — To the moon! 🌙")
      )
    } else if (at_low) {
      div(
        class = "alert alert-danger py-2 px-3 mb-2",
        style = "font-size: 0.9rem;",
        tags$strong("📉💀 52-WEEK LOW! 😱🆘"),
        br(),
        paste0("$", round(low_52w, 2), " — Oof, that's rough 🥲")
      )
    } else if (near_high) {
      div(
        class = "alert alert-info py-2 px-3 mb-2",
        style = "font-size: 0.9rem;",
        tags$strong("📈 Near 52-Week High! 👀"),
        br(),
        paste0("High: $", round(high_52w, 2), " — So close! 🤞")
      )
    } else if (near_low) {
      div(
        class = "alert alert-warning py-2 px-3 mb-2",
        style = "font-size: 0.9rem;",
        tags$strong("⚠️ Near 52-Week Low 😬"),
        br(),
        paste0("Low: $", round(low_52w, 2), " — Yikes! 🫣")
      )
    } else {
      pct_from_high <- ((high_52w - latest_close) / high_52w) * 100
      pct_from_low <- ((latest_close - low_52w) / low_52w) * 100
      div(
        class = "small text-muted mb-2",
        paste0("52W: $", round(low_52w, 2), " - $", round(high_52w, 2)),
        br(),
        paste0(round(pct_from_high, 1), "% from high, +", round(pct_from_low, 1), "% from low")
      )
    }
    
    # Add counts summary
    tagList(
      status_div,
      div(
        class = "small text-muted",
        style = "font-size: 0.8rem;",
        paste0("🚀 ", high_count, " highs / 💀 ", low_count, " lows in view")
      )
    )
  })

  # Metrics table
  output$metrics_table <- renderTable({
    data <- ticker_data()
    req(data)
    df <- data$df
    req(nrow(df) > 0)
    latest <- tail(df[complete.cases(df), ], 1)
    req(nrow(latest) == 1)

    data.frame(
      Metric = c("Close", "SMA 50", "SMA 200", "% from SMA200", "ATR (14)", "ATR %", "Extension Ratio"),
      Value = c(
        paste0("$", formatC(latest$Close, format = "f", digits = 2, big.mark = ",")),
        paste0("$", formatC(latest$SMA50, format = "f", digits = 2, big.mark = ",")),
        paste0("$", formatC(latest$SMA200, format = "f", digits = 2, big.mark = ",")),
        paste0(round(latest$Pct_from_SMA200, 2), "%"),
        paste0("$", round(latest$ATR14, 2)),
        paste0(round(latest$ATR_pct, 2), "%"),
        round(latest$Extension_Ratio, 2)
      ),
      stringsAsFactors = FALSE
    )
  }, striped = TRUE, hover = TRUE, bordered = TRUE, width = "100%")

  # Data table
  output$data_table <- renderDT({
    data <- ticker_data()
    req(data)
    df <- data$df
    req(nrow(df) > 0)

    display_df <- df[, c("Date", "Open", "High", "Low", "Close", "Volume")]
    display_df <- display_df[order(display_df$Date, decreasing = TRUE), ]

    datatable(
      display_df,
      options = list(
        pageLength = 25,
        dom = 'frtip',
        scrollX = TRUE
      ),
      rownames = FALSE
    ) %>%
      formatCurrency(c("Open", "High", "Low", "Close"), currency = "$", digits = 2) %>%
      formatRound("Volume", digits = 0)
  })

  # Download CSV
  output$download_csv <- downloadHandler(
    filename = function() {
      data <- ticker_data()
      paste0(data$symbol, "_", Sys.Date(), ".csv")
    },
    content = function(file) {
      data <- ticker_data()
      write.csv(data$df, file, row.names = FALSE)
    }
  )

  # ============================================================================
  # DASHBOARD TABLE
  # ============================================================================

  calc_dashboard_metrics <- function(sym, target_date) {
    xt <- tryCatch(
      getSymbols(sym, src = "yahoo", auto.assign = FALSE, warnings = FALSE),
      error = function(e) NULL
    )

    if (is.null(xt) || nrow(xt) < 52) {
      return(list(
        Ticker = sym,
        Price = NA_real_,
        Vol_Above_VMA = NA,
        Above_Ichimoku = NA,
        SMA13_Above_SMA30 = NA,
        Price_SD_Spark = list(c(NA_real_)),
        Pct_Above_SMA200 = NA_real_,
        ATR_Extension = NA_real_
      ))
    }

    xt <- xt[order(zoo::index(xt)), ]
    df <- data.frame(
      date = zoo::index(xt),
      open = as.numeric(Op(xt)),
      high = as.numeric(Hi(xt)),
      low = as.numeric(Lo(xt)),
      close = as.numeric(Cl(xt)),
      volume = as.numeric(Vo(xt))
    )
    
    n <- nrow(df)
    
    # Find target date index
    target_date <- as.Date(target_date)
    target_idx <- which(df$date <= target_date)
    if (length(target_idx) == 0) target_idx <- 1 else target_idx <- max(target_idx)
    
    close_vec <- df$close
    high_vec <- df$high
    low_vec <- df$low
    vol_vec <- df$volume
    
    # Calculate indicators manually (no xts needed)
    sma <- function(x, n) {
      if (length(x) < n) return(rep(NA, length(x)))
      stats::filter(x, rep(1/n, n), sides = 1)
    }
    
    run_sd <- function(x, n) {
      if (length(x) < n) return(rep(NA, length(x)))
      result <- rep(NA, length(x))
      for (i in n:length(x)) {
        result[i] <- sd(x[(i-n+1):i], na.rm = TRUE)
      }
      result
    }
    
    run_max <- function(x, n) {
      if (length(x) < n) return(rep(NA, length(x)))
      result <- rep(NA, length(x))
      for (i in n:length(x)) {
        result[i] <- max(x[(i-n+1):i], na.rm = TRUE)
      }
      result
    }
    
    run_min <- function(x, n) {
      if (length(x) < n) return(rep(NA, length(x)))
      result <- rep(NA, length(x))
      for (i in n:length(x)) {
        result[i] <- min(x[(i-n+1):i], na.rm = TRUE)
      }
      result
    }
    
    # ATR calculation
    calc_atr <- function(high, low, close, n = 14) {
      if (length(close) < n + 1) return(rep(NA, length(close)))
      tr <- rep(NA, length(close))
      tr[1] <- high[1] - low[1]
      for (i in 2:length(close)) {
        tr[i] <- max(high[i] - low[i], abs(high[i] - close[i-1]), abs(low[i] - close[i-1]))
      }
      sma(tr, n)
    }
    
    sma13 <- sma(close_vec, 13)
    sma30 <- sma(close_vec, 30)
    sma50 <- sma(close_vec, 50)
    sma200 <- if (n >= 200) sma(close_vec, 200) else rep(NA, n)
    vol_ma20 <- sma(vol_vec, 20)
    price_sd20 <- run_sd(close_vec, 20)
    atr14 <- calc_atr(high_vec, low_vec, close_vec, 14)
    
    # Ichimoku
    tenkan <- (run_max(high_vec, 9) + run_min(low_vec, 9)) / 2
    kijun <- (run_max(high_vec, 26) + run_min(low_vec, 26)) / 2
    senkou_a <- (tenkan + kijun) / 2
    senkou_b <- (run_max(high_vec, 52) + run_min(low_vec, 52)) / 2
    
    # Get values at target date
    price <- close_vec[target_idx]
    vol <- vol_vec[target_idx]
    vol_ma <- vol_ma20[target_idx]
    sma13_val <- sma13[target_idx]
    sma30_val <- sma30[target_idx]
    sma50_val <- sma50[target_idx]
    sma200_val <- sma200[target_idx]
    cloud_a <- senkou_a[target_idx]
    cloud_b <- senkou_b[target_idx]
    cloud_top <- if (!is.na(cloud_a) && !is.na(cloud_b)) max(cloud_a, cloud_b) else NA
    atr_val <- atr14[target_idx]
    
    # Conditions
    vol_above_vma <- if (!is.na(vol) && !is.na(vol_ma)) vol > vol_ma else NA
    above_ichimoku <- if (!is.na(price) && !is.na(cloud_top)) price > cloud_top else NA
    sma13_above_sma30 <- if (!is.na(sma13_val) && !is.na(sma30_val)) sma13_val > sma30_val else NA
    
    # Pct above SMA200
    pct_above_sma200 <- if (!is.na(price) && !is.na(sma200_val) && sma200_val > 0) {
      ((price / sma200_val) - 1) * 100
    } else NA_real_
    
    # ATR% Extension
    atr_pct <- if (!is.na(atr_val) && !is.na(price) && price > 0) (atr_val / price) * 100 else NA
    pct_from_ma50 <- if (!is.na(price) && !is.na(sma50_val) && sma50_val > 0) ((price - sma50_val) / sma50_val) * 100 else NA
    atr_extension <- if (!is.na(pct_from_ma50) && !is.na(atr_pct) && atr_pct > 0) pct_from_ma50 / atr_pct else NA_real_
    
    # Sparkline data: last 60 days of price std dev
    spark_start <- max(1, target_idx - 59)
    spark_data <- price_sd20[spark_start:target_idx]
    spark_data <- spark_data[!is.na(spark_data)]
    if (length(spark_data) < 5) spark_data <- c(NA_real_)
    
    list(
      Ticker = sym,
      Price = as.numeric(price),
      Vol_Above_VMA = vol_above_vma,
      Above_Ichimoku = above_ichimoku,
      SMA13_Above_SMA30 = sma13_above_sma30,
      Price_SD_Spark = list(as.numeric(spark_data)),
      Pct_Above_SMA200 = as.numeric(pct_above_sma200),
      ATR_Extension = as.numeric(atr_extension)
    )
  }

  dashboard_data <- reactive({
    tickers <- tracked_tickers()
    target_date <- input$dashboard_date
    
    withProgress(message = "Building dashboard...", value = 0, {
      results <- lapply(seq_along(tickers), function(i) {
        incProgress(1 / length(tickers), detail = tickers[i])
        calc_dashboard_metrics(tickers[i], target_date)
      })
      # Convert list of lists to data frame - handle list column separately
      df <- data.frame(
        Ticker = sapply(results, `[[`, "Ticker"),
        Price = sapply(results, `[[`, "Price"),
        Vol_Above_VMA = sapply(results, `[[`, "Vol_Above_VMA"),
        Above_Ichimoku = sapply(results, `[[`, "Above_Ichimoku"),
        SMA13_Above_SMA30 = sapply(results, `[[`, "SMA13_Above_SMA30"),
        Pct_Above_SMA200 = sapply(results, `[[`, "Pct_Above_SMA200"),
        ATR_Extension = sapply(results, `[[`, "ATR_Extension"),
        stringsAsFactors = FALSE
      )
      # Add list column for sparklines
      df$Price_SD_Spark <- lapply(results, function(x) x$Price_SD_Spark[[1]])
      df
    })
  })

  # Render gt table
  output$dashboard_table <- render_gt({
    df <- dashboard_data()
    req(df)
    req(nrow(df) > 0)
    
    # Format boolean columns with emojis
    format_bool <- function(x) {
      sapply(x, function(val) {
        if (is.na(val)) "➖"
        else if (val) "✅"
        else "❌"
      })
    }
    
    df$Vol_Above_VMA <- format_bool(df$Vol_Above_VMA)
    df$Above_Ichimoku <- format_bool(df$Above_Ichimoku)
    df$SMA13_Above_SMA30 <- format_bool(df$SMA13_Above_SMA30)
    
    # Build gt table
    gt_tbl <- df %>%
      gt() %>%
      cols_label(
        Ticker = "Ticker",
        Price = "Price",
        Vol_Above_VMA = "Vol > VMA",
        Above_Ichimoku = "Above Cloud",
        SMA13_Above_SMA30 = "SMA13 > SMA30",
        Price_SD_Spark = "Price σ (60d)",
        Pct_Above_SMA200 = "% Above SMA200",
        ATR_Extension = "ATR Ext"
      ) %>%
      fmt_currency(
        columns = "Price",
        currency = "USD",
        decimals = 2
      ) %>%
      fmt_number(
        columns = c("Pct_Above_SMA200", "ATR_Extension"),
        decimals = 2
      ) %>%
      gt_plt_sparkline(
        column = "Price_SD_Spark",
        type = "shaded",
        fig_dim = c(50, 20),
        palette = c("#3498db", "#3498db", "#e74c3c", "#18bc9c", "#95a5a6"),
        same_limit = FALSE
      ) %>%
      cols_width(
        Ticker ~ px(80),
        Price ~ px(90),
        Vol_Above_VMA ~ px(80),
        Above_Ichimoku ~ px(90),
        SMA13_Above_SMA30 ~ px(100),
        Price_SD_Spark ~ px(70),
        Pct_Above_SMA200 ~ px(120),
        ATR_Extension ~ px(80)
      ) %>%
      cols_align(
        align = "center",
        columns = c("Vol_Above_VMA", "Above_Ichimoku", "SMA13_Above_SMA30")
      ) %>%
      tab_style(
        style = cell_fill(color = "#f8f9fa"),
        locations = cells_body(rows = seq(1, nrow(df), 2))
      ) %>%
      tab_options(
        table.font.size = px(14),
        heading.title.font.size = px(16),
        column_labels.font.weight = "bold",
        table.width = pct(100)
      )
    
    gt_tbl
  })

  # Comparison data
  compare_data <- eventReactive(input$compare_btn, {
    req(input$compare_tickers)
    tickers <- input$compare_tickers
    dr <- input$compare_date_range

    withProgress(message = "Fetching comparison data...", value = 0, {
      all_data <- list()
      for (i in seq_along(tickers)) {
        sym <- tickers[i]
        incProgress(1 / length(tickers), detail = sym)

        xt <- tryCatch(
          getSymbols(sym, src = "yahoo", auto.assign = FALSE, warnings = FALSE),
          error = function(e) NULL
        )
        if (is.null(xt)) next

        xt <- xt[order(zoo::index(xt)), ]
        if (!is.null(dr) && length(dr) == 2) {
          xt <- xt[paste(dr[1], dr[2], sep = "/")]
        }
        if (nrow(xt) == 0) next

        close_xt <- Cl(xt)
        first_close <- as.numeric(close_xt[1])
        normalized <- (as.numeric(close_xt) / first_close - 1) * 100

        df <- data.frame(
          Date = zoo::index(xt),
          Ticker = sym,
          Close = as.numeric(close_xt),
          Normalized = normalized
        )
        all_data[[sym]] <- df
      }
      do.call(rbind, all_data)
    })
  })

  # Comparison plot
  output$compare_plot <- renderPlotly({
    df <- compare_data()
    req(df)
    req(nrow(df) > 0)

    plot_ly(df, x = ~Date, y = ~Normalized, color = ~Ticker, type = "scatter", mode = "lines") %>%
      layout(
        xaxis = list(title = ""),
        yaxis = list(title = "% Change from Start"),
        legend = list(orientation = "h", y = 1.1),
        hovermode = "x unified"
      ) %>%
      config(displayModeBar = TRUE, displaylogo = FALSE)
  })

  # ============================================================================
  # PARABOLIC SHORT SETUP CHECKER
  # ============================================================================

  # Function to calculate parabolic short metrics for a single ticker
  calc_parabolic_metrics <- function(sym) {
    xt <- tryCatch(
      getSymbols(sym, src = "yahoo", auto.assign = FALSE, warnings = FALSE),
      error = function(e) NULL
    )
    if (is.null(xt) || nrow(xt) < 10) {
      return(data.frame(
        Ticker = sym,
        Date = NA,
        ConsecUpDays = NA,
        GapUps = NA,
        RangeExp = NA,
        VolumeExp = NA,
        ClimaxGap = NA,
        Score = NA,
        Grade = "No Data",
        ChangeLastDay = NA_real_,
        VolumeTrend = NA_character_,
        PctFromSMA200 = NA_real_,
        stringsAsFactors = FALSE
      ))
    }

    xt <- xt[order(zoo::index(xt)), ]
    n <- nrow(xt)
    lookback <- 5

    # Get last 5 days
    recent_idx <- max(1, n - lookback + 1):n
    recent <- xt[recent_idx, ]
    dates <- zoo::index(recent)
    opens <- as.numeric(Op(recent))
    highs <- as.numeric(Hi(recent))
    lows <- as.numeric(Lo(recent))
    closes <- as.numeric(Cl(recent))
    volumes <- as.numeric(Vo(recent))
    lb <- length(closes)

    # Previous close for gap calculation (need one more day before lookback)
    if (n > lookback) {
      prev_day_close <- as.numeric(Cl(xt[n - lookback, ]))
      prev_closes <- c(prev_day_close, closes[-lb])
    } else {
      prev_closes <- c(NA, closes[-lb])
    }

    # Calculate metrics
    overnight_gaps <- (opens - prev_closes) / prev_closes * 100
    range_pct <- (highs - lows) / lows * 100
    up_days <- closes > prev_closes

    # 1. Consecutive up days from the end
    consecutive_up <- 0
    for (i in lb:1) {
      if (!is.na(up_days[i]) && up_days[i]) {
        consecutive_up <- consecutive_up + 1
      } else {
        break
      }
    }

    # 2. Overnight gap ups in last 3 days
    last3_gaps <- tail(overnight_gaps, 3)
    overnight_gaps_up <- sum(last3_gaps > 0, na.rm = TRUE)

    # 3. Range expansion (current > previous)
    range_expansion <- range_pct[-1] > range_pct[-lb]
    range_expansion_count <- sum(tail(range_expansion, 3), na.rm = TRUE)

    # 4. Volume expansion
    vol_expansion <- volumes[-1] > volumes[-lb]
    vol_expansion_count <- sum(tail(vol_expansion, 3), na.rm = TRUE)

    # 5. Climax gap up on most recent day
    climax_gap <- !is.na(overnight_gaps[lb]) && overnight_gaps[lb] > 0

    # Calculate score (max 10 points)
    score <- 0
    if (consecutive_up >= 3) score <- score + 2
    else if (consecutive_up >= 2) score <- score + 1
    score <- score + min(overnight_gaps_up, 2)
    score <- score + min(range_expansion_count, 2)
    score <- score + min(vol_expansion_count, 2)
    if (climax_gap) score <- score + 2

    # Grade
    grade <- if (score >= 9) "A+ (Ideal)"
             else if (score >= 7) "A (Strong)"
             else if (score >= 5) "B (Viable)"
             else if (score >= 3) "C (Weak)"
             else "D (Not Ready)"

    # --- New metrics ---

    # Change from last day (% change of most recent close vs previous close)
    change_last_day <- if (!is.na(closes[lb]) && !is.na(prev_closes[lb]) && prev_closes[lb] != 0) {
      (closes[lb] - prev_closes[lb]) / prev_closes[lb] * 100
    } else NA_real_

    # Volume trend: compare average of last 3 days vs average of first 2 days in window
    vol_trend <- if (lb >= 5) {
      avg_recent_vol <- mean(tail(volumes, 3), na.rm = TRUE)
      avg_early_vol  <- mean(head(volumes, 2), na.rm = TRUE)
      if (!is.na(avg_recent_vol) && !is.na(avg_early_vol) && avg_early_vol > 0) {
        pct_diff <- (avg_recent_vol - avg_early_vol) / avg_early_vol * 100
        if (pct_diff > 10) "Rising" else if (pct_diff < -10) "Falling" else "Flat"
      } else NA_character_
    } else NA_character_

    # % above/below 200-day SMA
    sma200_val <- if (n >= 200) {
      mean(as.numeric(Cl(xt[(n - 199):n])), na.rm = TRUE)
    } else NA_real_
    pct_from_sma200 <- if (!is.na(sma200_val) && sma200_val > 0) {
      (closes[lb] / sma200_val - 1) * 100
    } else NA_real_

    data.frame(
      Ticker = sym,
      Date = as.character(dates[lb]),
      ConsecUpDays = consecutive_up,
      GapUps = overnight_gaps_up,
      RangeExp = range_expansion_count,
      VolumeExp = vol_expansion_count,
      ClimaxGap = ifelse(climax_gap, "Yes", "No"),
      Score = score,
      Grade = grade,
      ChangeLastDay = change_last_day,
      VolumeTrend = vol_trend,
      PctFromSMA200 = pct_from_sma200,
      stringsAsFactors = FALSE
    )
  }

  # Reactive: fetch parabolic data for all tracked tickers
  parabolic_data <- reactive({
    tickers <- tracked_tickers()
    withProgress(message = "Analyzing parabolic setups...", value = 0, {
      results <- lapply(seq_along(tickers), function(i) {
        incProgress(1 / length(tickers), detail = tickers[i])
        calc_parabolic_metrics(tickers[i])
      })
      do.call(rbind, results)
    })
  })

  # Latest Move summary table
  output$parabolic_table <- renderDT({
    df <- parabolic_data()
    req(df)

    # Add visual indicators
    display_df <- df
    display_df$ConsecUpDays <- paste0(
      df$ConsecUpDays, " ",
      ifelse(df$ConsecUpDays >= 3, "✅", ifelse(df$ConsecUpDays >= 2, "⚠️", "❌"))
    )
    display_df$GapUps <- paste0(
      df$GapUps, "/3 ",
      ifelse(df$GapUps >= 2, "✅", ifelse(df$GapUps >= 1, "⚠️", "❌"))
    )
    display_df$RangeExp <- paste0(
      df$RangeExp, "/3 ",
      ifelse(df$RangeExp >= 2, "✅", ifelse(df$RangeExp >= 1, "⚠️", "❌"))
    )
    display_df$VolumeExp <- paste0(
      df$VolumeExp, "/3 ",
      ifelse(df$VolumeExp >= 2, "✅", ifelse(df$VolumeExp >= 1, "⚠️", "❌"))
    )
    display_df$ClimaxGap <- ifelse(df$ClimaxGap == "Yes", "Yes ✅", "No ❌")
    display_df$Score <- paste0(df$Score, "/10")

    # Format new columns
    display_df$ChangeLastDay <- ifelse(
      is.na(df$ChangeLastDay), "-",
      paste0(ifelse(df$ChangeLastDay >= 0, "+", ""), round(df$ChangeLastDay, 2), "%")
    )
    display_df$VolumeTrend <- ifelse(
      is.na(df$VolumeTrend), "-",
      ifelse(df$VolumeTrend == "Rising", "Rising ✅",
             ifelse(df$VolumeTrend == "Falling", "Falling ❌", "Flat ➡️"))
    )
    display_df$PctFromSMA200 <- ifelse(
      is.na(df$PctFromSMA200), "-",
      paste0(ifelse(df$PctFromSMA200 >= 0, "+", ""), round(df$PctFromSMA200, 2), "%")
    )

    # Rename columns for display
    names(display_df) <- c("Ticker", "Date", "Up Days", "Gap Ups", "Range Exp", "Vol Exp", "Climax Gap", "Score", "Grade", "Chg (1d)", "Vol Trend", "vs SMA200")

    # Sort by score descending
    display_df <- display_df[order(-df$Score), ]

    datatable(
      display_df,
      selection = "single",
      options = list(
        pageLength = 15,
        dom = 't',
        ordering = FALSE
      ),
      rownames = FALSE
    )
  })

  # Selected ticker for detail
  selected_parabolic_ticker <- reactive({
    sel <- input$parabolic_table_rows_selected
    if (is.null(sel) || length(sel) == 0) {
      return(tracked_tickers()[1])
    }
    df <- parabolic_data()
    # Sort same way as display
    df <- df[order(-df$Score), ]
    df$Ticker[sel]
  })

  # Detail table for selected ticker
  output$parabolic_detail_table <- renderDT({
    sym <- selected_parabolic_ticker()
    req(sym)

    xt <- tryCatch(
      getSymbols(sym, src = "yahoo", auto.assign = FALSE, warnings = FALSE),
      error = function(e) NULL
    )
    req(!is.null(xt))

    xt <- xt[order(zoo::index(xt)), ]
    n <- nrow(xt)
    req(n >= 5)

    # Last 5 days
    recent <- tail(xt, 5)
    dates <- zoo::index(recent)
    opens <- as.numeric(Op(recent))
    highs <- as.numeric(Hi(recent))
    lows <- as.numeric(Lo(recent))
    closes <- as.numeric(Cl(recent))
    volumes <- as.numeric(Vo(recent))

    # Previous close (need 6th day back for first gap)
    if (n > 5) {
      prev_close_first <- as.numeric(Cl(xt[n - 5, ]))
      prev_closes <- c(prev_close_first, closes[-5])
    } else {
      prev_closes <- c(NA, closes[-5])
    }

    # Calculate metrics
    daily_chg <- (closes - prev_closes) / prev_closes * 100
    overnight_gap <- (opens - prev_closes) / prev_closes * 100
    range_pct <- (highs - lows) / lows * 100
    up_day <- closes > prev_closes

    detail_df <- data.frame(
      Date = as.character(dates),
      Open = paste0("$", round(opens, 2)),
      Close = paste0("$", round(closes, 2)),
      `Daily Chg` = ifelse(is.na(daily_chg), "-", paste0(round(daily_chg, 2), "%")),
      `Gap` = ifelse(is.na(overnight_gap), "-", paste0(round(overnight_gap, 2), "%")),
      `Range` = paste0(round(range_pct, 2), "%"),
      Volume = format(volumes, big.mark = ","),
      `Up Day` = ifelse(is.na(up_day), "-", ifelse(up_day, "✅", "❌")),
      check.names = FALSE,
      stringsAsFactors = FALSE
    )

    datatable(
      detail_df,
      options = list(
        pageLength = 5,
        dom = 't',
        ordering = FALSE
      ),
      rownames = FALSE
    )
  })
}

shinyApp(ui, server)
