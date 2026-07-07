#!/usr/bin/env python3
"""
Indicator comparison: which signal(s) would have triggered a trade on
OTLK and YMAT ahead of their big runs?

Tests, on daily bars:
  - RSI(14) crossing up through 30 (oversold bounce)
  - MACD(12,26,9) line crossing above signal line
  - SMA(10) crossing above SMA(20) (short-term golden cross)
  - 20-day Donchian breakout (close > highest high of prior 20 days)
  - Volume spike (day's volume > 2x the 20-day average volume)
  - Bollinger Band(20,2) breakout (close crosses above upper band)

For comparison, also shows where the ADX(10)/20 daily cross fired
(the signal that originally caught these two).

Usage:
    pip install yfinance pandas numpy --break-system-packages
    python3 indicator_comparison.py
"""

import sys
import pandas as pd
import numpy as np
import yfinance as yf

TICKERS = ["OTLK", "YMAT"]
LOOKBACK_DAYS = 240  # ~9 months buffer for indicator warmup


def fetch_daily(ticker):
    df = yf.Ticker(ticker).history(period=f"{LOOKBACK_DAYS}d", interval="1d", auto_adjust=True)
    if df is None or df.empty:
        return None
    df = df.reset_index()
    df = df.rename(columns={"Date": "date", "Open": "open", "High": "high",
                             "Low": "low", "Close": "close", "Volume": "volume"})
    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
    df = df.sort_values("date").reset_index(drop=True)
    return df


def rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def macd(series, fast=12, slow=26, signal=9):
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line, signal_line


def wilder_adx(df, period=10):
    high, low, close = df["high"].values, df["low"].values, df["close"].values
    n = len(df)
    plus_dm = [0.0] * n
    minus_dm = [0.0] * n
    tr = [0.0] * n
    for i in range(1, n):
        up_move = high[i] - high[i - 1]
        down_move = low[i - 1] - low[i]
        plus_dm[i] = up_move if (up_move > down_move and up_move > 0) else 0.0
        minus_dm[i] = down_move if (down_move > up_move and down_move > 0) else 0.0
        tr[i] = max(high[i] - low[i], abs(high[i] - close[i - 1]), abs(low[i] - close[i - 1]))
    adx = [None] * n
    if n < period * 2 + 1:
        return adx
    sm_tr = sum(tr[1:period + 1]); sm_p = sum(plus_dm[1:period + 1]); sm_m = sum(minus_dm[1:period + 1])
    dxs = []
    def dx_from(sm_tr, sm_p, sm_m):
        pdi = 100 * sm_p / sm_tr if sm_tr else 0
        mdi = 100 * sm_m / sm_tr if sm_tr else 0
        return 100 * abs(pdi - mdi) / (pdi + mdi) if (pdi + mdi) else 0
    dxs.append(dx_from(sm_tr, sm_p, sm_m))
    dx_index = [period]
    for i in range(period + 1, n):
        sm_tr = sm_tr - sm_tr/period + tr[i]; sm_p = sm_p - sm_p/period + plus_dm[i]; sm_m = sm_m - sm_m/period + minus_dm[i]
        dxs.append(dx_from(sm_tr, sm_p, sm_m)); dx_index.append(i)
    if len(dxs) < period:
        return adx
    adx_val = sum(dxs[:period]) / period
    adx[dx_index[period - 1]] = adx_val
    for i in range(period, len(dxs)):
        adx_val = (adx_val * (period - 1) + dxs[i]) / period
        adx[dx_index[i]] = adx_val
    return adx


def find_first_signal(bool_series, dates):
    """Return the date of the first True value, or None."""
    for i, v in enumerate(bool_series):
        if v:
            return dates.iloc[i]
    return None


def analyze(ticker):
    df = fetch_daily(ticker)
    if df is None or len(df) < 60:
        print(f"{ticker}: insufficient data")
        return

    close, volume = df["close"], df["volume"]

    # RSI(14) crossing up through 30
    r = rsi(close, 14)
    rsi_signal = (r.shift(1) < 30) & (r >= 30)

    # MACD line crossing above signal line
    macd_line, signal_line = macd(close)
    macd_signal = (macd_line.shift(1) < signal_line.shift(1)) & (macd_line >= signal_line)

    # SMA(10) crossing above SMA(20)
    sma10, sma20 = close.rolling(10).mean(), close.rolling(20).mean()
    sma_signal = (sma10.shift(1) < sma20.shift(1)) & (sma10 >= sma20)

    # 20-day Donchian breakout
    donchian_high = df["high"].rolling(20).max().shift(1)
    donchian_signal = close > donchian_high

    # Volume spike: today's volume > 2x 20-day avg
    avg_vol20 = volume.rolling(20).mean().shift(1)
    volume_signal = volume > (2 * avg_vol20)

    # Bollinger Band(20,2) breakout
    bb_mid = close.rolling(20).mean()
    bb_std = close.rolling(20).std()
    bb_upper = bb_mid + 2 * bb_std
    bb_signal = (close.shift(1) < bb_upper.shift(1)) & (close >= bb_upper)

    # ADX(10) crossing 20, for reference (the original signal that caught these)
    adx = wilder_adx(df, period=10)
    adx_signal = [False] * len(df)
    for i in range(1, len(df)):
        if adx[i-1] is not None and adx[i] is not None and adx[i-1] < 20 <= adx[i]:
            adx_signal[i] = True

    only_last_6mo = df["date"] >= (df["date"].max() - pd.Timedelta(days=185))

    print(f"\n{'='*70}\n{ticker}  (last close ${close.iloc[-1]:.2f}, "
          f"6mo ago ${close[only_last_6mo].iloc[0]:.2f})\n{'='*70}")

    signals = {
        "RSI(14) cross up thru 30": rsi_signal,
        "MACD line crosses signal": macd_signal,
        "SMA10 crosses above SMA20": sma_signal,
        "20-day Donchian breakout": donchian_signal,
        "Volume spike (>2x 20d avg)": volume_signal,
        "Bollinger upper band breakout": bb_signal,
        "ADX(10) crosses 20 [reference]": pd.Series(adx_signal),
    }

    for name, sig in signals.items():
        sig_in_window = sig & only_last_6mo.reset_index(drop=True)
        dates_hit = df["date"][sig_in_window.values].tolist()
        if not dates_hit:
            print(f"  {name:35s}: no signal in last 6 months")
            continue
        first_date = dates_hit[0]
        first_idx = df.index[df["date"] == first_date][0]
        price_then = close.iloc[first_idx]
        price_now = close.iloc[-1]
        ret = (price_now - price_then) / price_then * 100
        extra = f" (+{len(dates_hit)-1} more)" if len(dates_hit) > 1 else ""
        print(f"  {name:35s}: FIRST FIRED {first_date.date()} @ ${price_then:.3f} "
              f"-> now ${price_now:.3f} ({ret:+.1f}%){extra}")


def main():
    for t in TICKERS:
        analyze(t)


if __name__ == "__main__":
    main()
