"""Static configuration: default universes and theme colors.

Edit these lists to change what the Refresh tab pulls by default.
"""

# Seeded into watchlist_meta on first run (you then add/remove in the app).
DEFAULT_WATCHLIST = [
    "META", "INTC", "ORCL", "BABA", "ADBE", "DOCN", "RDDT", "GLD", "ACN",
    "GTLB", "ZETA", "IONQ", "TWLO", "NBIS", "KODK", "ENPH", "NVDA", "AAPL",
    "MSFT", "AMZN", "GOOG", "TSLA", "AMD", "CRWD", "PLTR", "SOFI", "MU", "COIN",
]

# Market-context tickers (Yahoo symbols). Pulled by "Refresh indices & ETFs".
DEFAULT_INDICES = ["^VIX", "^VIX3M", "^TNX", "^TYX", "^FVX", "DX-Y.NYB"]
DEFAULT_ETFS = ["SPY", "QQQ", "SMH", "XLK", "RSP", "XBI", "REMX", "WGMI", "USO", "TLT"]

# TradingView watchlist (imported). Stored in its own `tv_watchlist` table.
# Edit this list to change what the "TradingView List" tab tracks.
TV_WATCHLIST = [
    "BB", "SNDK", "MU", "GLW", "PSNL", "ULCC", "FLEX", "RXO", "AMAT", "VSH",
    "KLAR", "KMX", "WRBY", "NESR", "UAL", "INIO", "TER", "NVT", "NEO", "ALGM",
    "JBLU", "NTSK", "BLLN", "PENN", "CGNX", "FRMI", "ALK", "NWL", "KNX", "COMP",
    "VRT", "STUB", "KLAC", "ST", "WDC", "ANET", "Q", "MXL", "PGY", "RCL",
    "OKTA", "ALHC", "PANW", "RSI", "ATI", "SGHC", "ENTG", "AESI", "WSC", "CSTM",
    "VGNT", "APPS", "CAVA", "STX", "SW", "SN", "W", "GFS", "ACHC", "SSRM",
    "HTFL", "CRDO", "UAA", "F", "LION", "CRWD", "APH", "GTX", "AAL", "SOLS",
    "BWA", "CALY", "NXPI", "KSS", "CCL", "M", "NAVN", "FCX", "UPST", "VRNS",
    "STM", "CRSR", "LRCX", "SEI", "BBWI", "ASX", "FDXF", "VIAV", "AMKR", "ON",
    "MCHP", "BIRK", "RHI", "FLR", "AEHR", "SMTC", "NET", "REAL", "NOK", "TDOC",
    "AFRM", "BROS", "TDC", "SUNB", "ALAB", "CNK", "RH", "FROG", "EXTR", "SNOW",
    "TRIP", "TENB", "SG", "BBY", "COHR", "TWLO", "LSCC", "CART", "AADX", "CLOV",
    "LITE", "BFLY", "AMD", "HLIT", "OUST", "TTMI", "NBIS", "DDOG", "NTAP", "EQPT",
    "MGNI", "ETSY", "GEO", "CORZ", "HPQ", "ROKU", "FPS", "BE", "SWKS", "VSXY",
    "ELF", "NAT", "DHT", "SPCX", "VSNT", "HUT", "UMC", "MRVL", "PENG", "HOOD",
    "FRO", "INTC", "AUR", "APLD", "OSCR", "GLXY", "TSEM", "SHLS", "ARM", "WULF",
    "RBRK", "RXT", "QNT", "HPE", "MARA", "ECHO", "CIFR", "LFTO", "CLSK", "RIOT",
    "AMC", "KEEL", "WYFI", "DELL", "BTDR", "HIVE", "FCEL", "ALOY",
]

# ── Relative-strength dashboard groups (the screenshot) ───────────────────────
# Stored in their own `dashboard` table. SPY is the RS benchmark.
DASHBOARD_GROUPS = {
    "Index":       ["RSP", "SPY", "QQQ", "QQQE", "IWM", "DIA", "SPMO", "TLT"],
    "Segment":     ["IJS", "IJR", "IJT", "IJJ", "IJH", "IJK", "IVE", "IVV", "IVW"],
    "EW Sector":   ["RSPD", "RSPH", "RSPU", "RSPN", "RSPF", "RSPS", "RSPR", "RSPM", "RSPT", "RSPG", "RSPC"],
    "SPDR Sector": ["XLU", "XLI", "XLF", "XLV", "XLP", "XLRE", "XLB", "XLK", "XLY", "XLE", "XLC"],
}

DASHBOARD_NAMES = {
    "RSP": "S&P 500 Equal Weight", "SPY": "S&P 500", "QQQ": "Nasdaq-100",
    "QQQE": "Nasdaq-100 Equal Weight", "IWM": "Russell 2000", "DIA": "Dow 30",
    "SPMO": "S&P 500 Momentum", "TLT": "20+ Year Treasury Bonds",
    "IJS": "Small-Cap 600 Value", "IJR": "Small-Cap 600", "IJT": "Small-Cap 600 Growth",
    "IJJ": "MidCap 400 Value", "IJH": "MidCap 400", "IJK": "MidCap 400 Growth",
    "IVE": "Large-Cap 500 Value", "IVV": "S&P 500", "IVW": "Large-Cap 500 Growth",
    "RSPD": "EW Discretionary", "RSPH": "EW Health Care", "RSPU": "EW Utilities",
    "RSPN": "EW Industrial", "RSPF": "EW Financials", "RSPS": "EW Staples",
    "RSPR": "EW Real Estate", "RSPM": "EW Materials", "RSPT": "EW Technology",
    "RSPG": "EW Energy", "RSPC": "EW Communication",
    "XLU": "Utilities", "XLI": "Industrials", "XLF": "Financials", "XLV": "Health Care",
    "XLP": "Consumer Staples", "XLRE": "Real Estate", "XLB": "Materials",
    "XLK": "Technology", "XLY": "Consumer Discretionary", "XLE": "Energy",
    "XLC": "Communication Services",
}

# All unique dashboard tickers (for the refresh job).
DASHBOARD_TICKERS = sorted({t for g in DASHBOARD_GROUPS.values() for t in g})

# Benchmarks offered for "compare vs" pickers (Single Stock Viewer, Dashboard).
# Broad index ETFs + the SPDR sector ETFs — all live in the `dashboard` table.
BENCHMARKS = ["SPY", "QQQ", "RSP", "IWM"] + DASHBOARD_GROUPS["SPDR Sector"]

# Colors (Flatly-ish, to echo the old app).
GREEN = "#18bc9c"
RED = "#e74c3c"
INK = "#2c3e50"
BLUE = "#3498db"
PURPLE = "#9b59b6"
ORANGE = "#e67e22"
