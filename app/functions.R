library(quantmod)
library(ggplot2)

df <- getSymbols("CHRS", auto.assign = FALSE)

df <- data.frame(
  date  = index(df),
  value = coredata(df)
)

names(df) <- c("date","open", "high", "low", "close", "volume", "adjusted")


df$SMA20 <- SMA(Cl(df), n = 20)
df$pct_from_sma20 <- (Cl(df) - df$SMA20) / df$SMA20 * 100

df$SMA200 <- SMA(Cl(df), n = 200)
df$pct_from_sma200 <- (Cl(df) - df$SMA200) / df$SMA200 * 100

df$SMA50 <- SMA(Cl(df), n = 50)
df$pct_from_sma50 <- (Cl(df) - df$SMA50) / df$SMA50 * 100

df$sma_pct200 <- TTR::SMA(df$pct_from_sma200, n = 200)

library(TTR)
library(quantmod)

# Calculate StochRSI
# TTR doesn't have StochRSI directly, so we build it:
rsi  <- RSI(df$close, n = 14)
df$stoch_rsi <- stoch(cbind(rsi, rsi, rsi), nFastK = 14, nFastD = 3, nSlowD = 3)

# stoch_rsi has: fastK, fastD, slowD

# get date col

p1 <- df %>%
  filter(date> as.Date("2023-01-01")) %>%
  ggplot(aes(x = date)) +
  geom_line(aes(y = pct_from_sma200), color = "red") +
  geom_line(aes(y = sma_pct200), color = "blue")

p2 <- df %>%
  filter(date> as.Date("2023-01-01")) %>%
  ggplot(aes(x = date)) +
  geom_line(aes(y = close), color = "red")

p3 <- df %>%
  filter(date> as.Date("2023-01-01")) %>%
  ggplot(aes(x = date)) +
  geom_line(aes(y = stoch_rsi), color = "red")


library(patchwork)

p2 / p1
