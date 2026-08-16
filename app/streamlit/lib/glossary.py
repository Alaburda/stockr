"""Single source of truth for every "why is this red/green" explanation.

Every pass/fail icon, heat-styled column, and judgment-carrying metric in the
app should point at an entry here instead of inlining its own text — that way
the wording only needs fixing in one place, and the whole app stays consistent
about what a given number *means* and what the rule of thumb is.

Usage:
    from lib import glossary
    st.metric("VIX3M / VIX", ..., help=glossary.HELP["vix_ratio"])
    st.dataframe(df, column_config={
        "ATR ext": st.column_config.NumberColumn(help=glossary.HELP["sma50_atr_ext"]),
    })
"""
from __future__ import annotations

HELP: dict[str, str] = {
    # ── market strip / breadth ────────────────────────────────────────────
    "vix_ratio": (
        "VIX3M ÷ VIX (term-structure ratio). Above 1.0 = normal, contango "
        "term structure (calm market pricing more risk further out). Below "
        "1.0 = inverted ('backwardation') — near-term fear exceeds longer-term "
        "fear, which usually means the market is under acute stress right now."
    ),
    "breadth_50": (
        "% of S&P 500 constituents trading above their own 50-day SMA. A "
        "medium-term breadth gauge: readings above ~60% support an uptrend, "
        "below ~40% warns the rally is narrowing to fewer stocks even if the "
        "index itself looks fine."
    ),
    "breadth_200": (
        "% of S&P 500 constituents trading above their own 200-day SMA. The "
        "long-term breadth gauge — persistently below 50% flags a market where "
        "most stocks are in longer-term downtrends, regardless of what the "
        "cap-weighted index is doing."
    ),
    "breadth_20": (
        "% of S&P 500 constituents trading above their own 20-day SMA. The "
        "fastest breadth read — swings hard within days and is most useful "
        "for spotting short-term thrusts or exhaustion, not trend direction."
    ),
    "nh_nl": (
        "Net new 52-week highs minus new 52-week lows across the S&P 500 "
        "today. Positive and expanding = broad participation in the up move; "
        "negative, especially while price makes new highs, is a classic "
        "divergence warning that the rally is thinning out underneath."
    ),
    "rsp_spy": (
        "1-month return of RSP (equal-weight S&P 500) minus SPY (cap-weight). "
        "Positive = the average stock is leading the mega-caps ('healthy', "
        "broad-based rotation). Negative = a handful of large names are "
        "carrying the index while the average stock lags."
    ),
    "tnx": (
        "10-year Treasury yield (^TNX). Rising yields can pressure high-"
        "multiple growth stocks and rate-sensitive sectors; falling yields "
        "typically support them. Watch the direction/speed of the move more "
        "than the absolute level."
    ),
    # ── per-ticker setup checks ───────────────────────────────────────────
    "sma50_atr_ext": (
        "Distance of price above/below its 50-day SMA, expressed in ATR "
        "multiples. Rule of thumb: under 4x is a normal, tradeable extension; "
        "4x+ is parabolic and chasing new entries here is high-risk; 6-7x is "
        "a classic profit-taking / trim zone for existing longs."
    ),
    "lod_atr_pct": (
        "(close − low) ÷ ATR — how far today's close sits above the low of "
        "day, in ATR fractions. Low values (< 0.6) mean the stock closed near "
        "its high of the day (strong close); high values mean it closed weak, "
        "near the day's low, which is a poor look for a fresh entry."
    ),
    "sma200_rising": (
        "Is the 200-day SMA higher than it was 5 sessions ago? A rising "
        "200-day is the textbook definition of an intact long-term uptrend — "
        "flat or falling means the long-term trend has stalled or reversed."
    ),
    "sma10_rising": (
        "Is the 10-day SMA higher than it was 5 sessions ago? A fast read on "
        "short-term momentum — rising means the last couple weeks have trended "
        "up; flat/falling means short-term momentum has cooled."
    ),
    "rs_1m": (
        "1-month return minus SPY's 1-month return, in percentage points. "
        "Positive = the stock is outperforming the market (relative "
        "strength); negative = it's lagging the market even if its own price "
        "is up."
    ),
    "rs_3m": (
        "3-month return minus SPY's 3-month return, in percentage points. "
        "Same idea as RS 1M but over a longer window — smooths out noise and "
        "better reflects a durable leadership/laggard trend."
    ),
    "rel_vol": (
        "Today's volume relative to its 20-day average. Rule of thumb: ≥ 1.0x "
        "means above-average participation (a move worth paying attention "
        "to); well below 1.0x means today's price action is happening on "
        "thin volume and is less trustworthy."
    ),
    "setup_checklist": (
        "The 'A-setup' checklist (from a standard swing-trading routine): 6 "
        "conditions that together describe a stock that's trending, not "
        "over-extended, and closing strong on above-average volume. More "
        "checks passing = a cleaner, lower-risk entry candidate — it is not a "
        "buy signal by itself, just a filter."
    ),
    "pct_off_52w_high": (
        "% below the trailing 52-week high. Near 0% = making new highs "
        "(strength, but also more extended); a large negative number means "
        "the stock is well off its highs and either basing, recovering, or "
        "still in a downtrend."
    ),
    # ── screener / general indicators ─────────────────────────────────────
    "rsi": (
        "14-day Relative Strength Index (0-100). Traditionally > 70 is "
        "'overbought' and < 30 is 'oversold', but in a strong trend RSI can "
        "stay pinned at extremes for a long time — treat it as a momentum "
        "read, not a standalone reversal signal."
    ),
    "pct_sma200": (
        "% distance of price from its 200-day SMA. Deeply negative means the "
        "stock is far below its long-term average (either a bargain or a "
        "broken trend); deeply positive means it's far above (strong trend, "
        "but also stretched)."
    ),
    "adr": (
        "Average Daily Range % — the average size of the stock's daily "
        "high-low swing as a % of price. Higher ADR means bigger, faster "
        "moves in both directions; useful for sizing stops and expectations, "
        "not a directional signal."
    ),
    "ret_1w": "Trailing 1-week (5-session) total return.",
    "ret_1m": "Trailing 1-month (21-session) total return.",
    "ret_3m": "Trailing 3-month (63-session) total return.",
    "ret_6m": "Trailing 6-month (126-session) total return.",
    "ret_ytd": "Return since the first close on or after January 1 of the current year.",
    "mom": (
        "High-momentum flag: Average Daily Range (ADR) is at least 9% of "
        "price. Flags stocks making unusually large, fast daily swings — "
        "bigger opportunity, but also bigger risk and wider stops needed."
    ),
    # ── sector RS ─────────────────────────────────────────────────────────
    "sector_rs_1m": (
        "Equal-weighted sector return minus SPY's return over the trailing "
        "21 sessions, in percentage points. Positive = the sector is leading "
        "the market this month; sectors near the top are where money is "
        "rotating into."
    ),
    "sector_rs_3m": (
        "Same as sector RS 1M but over 63 sessions — a steadier read on which "
        "sectors have been leading/lagging for a full quarter, filtering out "
        "single-week noise."
    ),
    "rs_1m_high": (
        "Flags a sector whose 1-month RS vs. SPY is at its own highest point "
        "in the trailing month — i.e. sector leadership is freshly "
        "accelerating right now, not just historically strong."
    ),
    # ── chart overlays ────────────────────────────────────────────────────
    "atr_bands": (
        "Extension bands anchored to the 50-day SMA, in ATR multiples. The "
        "red dashed line at +4×ATR marks where new entries get risky "
        "(parabolic extension); the shaded zone between +6×ATR and +7×ATR is "
        "a classic zone for taking profits on existing longs, not for buying."
    ),
    "forming_candle": (
        "Each daily bar shows the month-to-date (or week-to-date) candle as "
        "it stood on that day: open = first open of the period, high/low = "
        "the running extreme so far, close = that day's actual close. It "
        "shows how the period's candle evolved — e.g. a monthly high made "
        "mid-month that later got given back."
    ),
    "stoch": (
        "Stochastic oscillator (14, 3): %K measures where today's close sits "
        "within the trailing 14-day high/low range (0-100); %D is %K's 3-day "
        "SMA. Above 80 = 'overbought' (near the top of its recent range), "
        "below 20 = 'oversold' (near the bottom) — a %K/%D crossover through "
        "those zones is the classic signal, but like RSI it can stay pinned "
        "at extremes through a strong trend."
    ),
    "stochrsi": (
        "Stochastic RSI (14,14,3,3): the stochastic formula applied to RSI "
        "itself instead of price, then smoothed. Much more sensitive than "
        "plain RSI or the price stochastic — swings between 0-100 faster and "
        "crosses 20/80 more often, so it's best read as an early/eager "
        "momentum signal rather than a standalone timing tool."
    ),
    "roc2": (
        "2-day Rate of Change % — the fastest momentum read in the app. "
        "Large swings are normal noise; mainly useful for spotting sudden "
        "sharp thrusts or air-pockets that slower indicators (RSI, ROC-12) "
        "won't show for several more days."
    ),
    "macd": (
        "MACD (12, 26, 9): the 12-day EMA minus the 26-day EMA, with a 9-day "
        "EMA of that difference as the signal line, and the histogram = MACD "
        "− signal. MACD crossing above its signal line (or the histogram "
        "flipping positive) is a bullish momentum shift, crossing below is "
        "bearish; MACD crossing the zero line marks the 12/26-EMA trend "
        "itself flipping. Histogram divergence — price making a new high/low "
        "while the histogram doesn't — is a classic (if noisy) warning that "
        "momentum is fading before price confirms it."
    ),
    "ichimoku": (
        "Ichimoku Kinko Hyo (9/26/52): Tenkan (fast) and Kijun (slow) lines "
        "work like fast/slow moving averages — a Tenkan/Kijun cross is a "
        "trend-change signal. The cloud (Senkou A/B, plotted 26 sessions "
        "ahead) is a forward-projected support/resistance zone: price above a "
        "green cloud (A > B) is bullish, below a red cloud (B > A) is "
        "bearish, and price inside the cloud means no clear trend. Chikou is "
        "today's close plotted 26 sessions back, for comparing current price "
        "action against where price was a month-plus ago."
    ),
    "ma_matrix": (
        "Above/below key moving averages (5/10/20/50/100/150/200-day) for "
        "each benchmark's latest close. More MAs held above = a stronger, "
        "more aligned uptrend across timeframes; failing the shorter MAs "
        "first while still above the longer ones is an early sign of "
        "short-term weakness inside a still-intact long-term trend. The "
        "'Percent positive' row is a breadth read across the whole benchmark "
        "list, same idea as S&P breadth but for major indices/segments."
    ),
    "vpoc": (
        "Monthly volume profile: each month's volume is distributed across "
        "the price levels it traded at, and the value area (blue band) is "
        "the tightest price range holding 70% of that month's volume, "
        "centered on the point of control (VPOC — the single most-traded "
        "price). Value areas often act as support/resistance on later "
        "retests — price re-entering a prior month's value area from above "
        "often stalls near its VPOC or edges."
    ),
    "tlt_spy_ratio": (
        "TLT (20+ year Treasury bonds) relative to SPY, normalized to 100 at "
        "the start of the window. Rising = bonds outperforming stocks — "
        "typically a flight-to-safety / risk-off signal. Falling = equities "
        "leading bonds — typically risk-on. Read the trend/slope, not the "
        "absolute level."
    ),
    "event_study": (
        "Forward % change at each horizon (1d out to 6m) measured from every "
        "date your condition matched, not just the single horizon above. "
        "Green/red heat by sign, with Average/Median/% Positive summary rows "
        "— a horizon where the sign and win-rate stay consistent across the "
        "table is a much stronger signal than one good number at a single "
        "horizon."
    ),
    "returns_lab_baseline": (
        "'Baseline' = every row in the chosen universe/date range with a "
        "valid forward return, regardless of your condition. Compare matched "
        "vs. baseline to see whether your condition actually shifts the odds, "
        "or whether the universe just behaves that way generally."
    ),
}
