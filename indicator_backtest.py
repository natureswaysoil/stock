#!/usr/bin/env python3
"""
Multi-indicator backtest — same universe, same methodology as the ADX study,
so results are directly comparable.

For each ticker in the sub-$2 liquid universe, and for each indicator:
  - Find the MOST RECENT signal in the last 6 months (same rule as the
    ADX study: "most recent qualifying cross", not first).
  - Compute return from that signal's price to today's price.
Then aggregate per indicator: # signals, avg return, win rate.

Indicators tested:
  - ADX(10) crosses above 20, +DI > -DI            [baseline/reference]
  - RSI(14) crosses up through 30 (oversold bounce)
  - MACD(12,26,9) line crosses above signal line
  - SMA(10) crosses above SMA(20)
  - 20-day Donchian breakout (close > highest high of prior 20 days)
  - Volume spike (day's volume > 2x the 20-day average volume)
  - Bollinger Band(20,2) upper breakout

Usage:
    pip install yfinance pandas numpy --break-system-packages
    python3 indicator_backtest.py
"""

import sys
import time
from datetime import datetime, timedelta, UTC

import pandas as pd
import numpy as np
import yfinance as yf
from yfinance import EquityQuery

PRICE_MAX = 2.0
PRICE_MIN = 0.10
MIN_VOLUME = 300000
UNIVERSE_CAP = 60
LOOKBACK_MONTHS = 6
HISTORY_MONTHS = LOOKBACK_MONTHS + 3


def fetch_screener():
    query = EquityQuery("and", [
        EquityQuery("eq", ["region", "us"]),
        EquityQuery("lt", ["intradayprice", PRICE_MAX]),
        EquityQuery("gt", ["intradayprice", PRICE_MIN]),
        EquityQuery("gt", ["avgdailyvol3m", MIN_VOLUME]),
    ])
    result = yf.screen(query, size=UNIVERSE_CAP, sortField="avgdailyvol3m", sortAsc=False)
    quotes = result.get("quotes", [])
    if not quotes:
        quotes = result.get("finance", {}).get("result", [{}])[0].get("quotes", [])
    return [q["symbol"] for q in quotes if "symbol" in q]


def fetch_daily(ticker, months_back):
    period_days = months_back * 31
    df = yf.Ticker(ticker).history(period=f"{period_days}d", interval="1d", auto_adjust=True)
    if df is None or df.empty:
        return None
    df = df.reset_index()
    df = df.rename(columns={"Date": "date", "High": "high", "Low": "low",
                             "Close": "close", "Volume": "volume"})
    if not {"date", "high", "low", "close", "volume"}.issubset(df.columns):
        return None
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
    plus_di = [None] * n
    minus_di = [None] * n
    if n < period * 2 + 1:
        return adx, plus_di, minus_di
    sm_tr = sum(tr[1:period + 1]); sm_p = sum(plus_dm[1:period + 1]); sm_m = sum(minus_dm[1:period + 1])
    dxs = []
    di_pairs = []
    def dx_from(sm_tr, sm_p, sm_m):
        pdi = 100 * sm_p / sm_tr if sm_tr else 0
        mdi = 100 * sm_m / sm_tr if sm_tr else 0
        dx = 100 * abs(pdi - mdi) / (pdi + mdi) if (pdi + mdi) else 0
        return dx, pdi, mdi
    dx, pdi, mdi = dx_from(sm_tr, sm_p, sm_m)
    dxs.append(dx); di_pairs.append((pdi, mdi))
    dx_index = [period]
    for i in range(period + 1, n):
        sm_tr = sm_tr - sm_tr/period + tr[i]; sm_p = sm_p - sm_p/period + plus_dm[i]; sm_m = sm_m - sm_m/period + minus_dm[i]
        dx, pdi, mdi = dx_from(sm_tr, sm_p, sm_m)
        dxs.append(dx); di_pairs.append((pdi, mdi)); dx_index.append(i)
    if len(dxs) < period:
        return adx, plus_di, minus_di
    adx_val = sum(dxs[:period]) / period
    adx[dx_index[period - 1]] = adx_val
    plus_di[dx_index[period - 1]] = di_pairs[period - 1][0]
    minus_di[dx_index[period - 1]] = di_pairs[period - 1][1]
    for i in range(period, len(dxs)):
        adx_val = (adx_val * (period - 1) + dxs[i]) / period
        adx[dx_index[i]] = adx_val
        plus_di[dx_index[i]] = di_pairs[i][0]
        minus_di[dx_index[i]] = di_pairs[i][1]
    return adx, plus_di, minus_di


def build_signals(df):
    """Return a dict of {indicator_name: boolean pandas Series} aligned to df rows."""
    close, volume = df["close"], df["volume"]
    n = len(df)

    r = rsi(close, 14)
    rsi_sig = (r.shift(1) < 30) & (r >= 30)

    macd_line, signal_line = macd(close)
    macd_sig = (macd_line.shift(1) < signal_line.shift(1)) & (macd_line >= signal_line)

    sma10, sma20 = close.rolling(10).mean(), close.rolling(20).mean()
    sma_sig = (sma10.shift(1) < sma20.shift(1)) & (sma10 >= sma20)

    donchian_high = df["high"].rolling(20).max().shift(1)
    donchian_sig = close > donchian_high

    avg_vol20 = volume.rolling(20).mean().shift(1)
    volume_sig = volume > (2 * avg_vol20)

    bb_mid = close.rolling(20).mean()
    bb_std = close.rolling(20).std()
    bb_upper = bb_mid + 2 * bb_std
    bb_sig = (close.shift(1) < bb_upper.shift(1)) & (close >= bb_upper)

    adx, plus_di, minus_di = wilder_adx(df, period=10)
    adx_sig = [False] * n
    for i in range(1, n):
        if adx[i-1] is not None and adx[i] is not None and adx[i-1] < 20 <= adx[i]:
            if plus_di[i] is not None and minus_di[i] is not None and plus_di[i] > minus_di[i]:
                adx_sig[i] = True

    return {
        "ADX(10)>20 +DI>-DI": pd.Series(adx_sig),
        "RSI(14) up-thru-30": rsi_sig.fillna(False).reset_index(drop=True),
        "MACD cross up": macd_sig.fillna(False).reset_index(drop=True),
        "SMA10>SMA20 cross": sma_sig.fillna(False).reset_index(drop=True),
        "20d Donchian breakout": donchian_sig.fillna(False).reset_index(drop=True),
        "Volume spike >2x": volume_sig.fillna(False).reset_index(drop=True),
        "Bollinger upper breakout": bb_sig.fillna(False).reset_index(drop=True),
    }


def main():
    print(f"Screening: ${PRICE_MIN} < price < ${PRICE_MAX}, avg 3mo volume > {MIN_VOLUME:,}, US region...")
    tickers = fetch_screener()
    if not tickers:
        sys.exit("Screener returned no tickers.")
    print(f"Universe: {len(tickers)} tickers -> {', '.join(tickers)}\n")

    cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=LOOKBACK_MONTHS * 31)

    # results[indicator_name] = list of return_pct floats
    results = {}
    per_ticker_rows = []

    for i, ticker in enumerate(tickers):
        try:
            df = fetch_daily(ticker, HISTORY_MONTHS)
            if df is None or len(df) < 45:
                print(f"  [{i+1}/{len(tickers)}] {ticker}: insufficient data, skipped")
                continue
            signals = build_signals(df)
            current_price = df["close"].iloc[-1]
            fired_any = False
            for name, sig in signals.items():
                in_window = df["date"] >= cutoff
                hits = df.index[(sig.values) & (in_window.values)].tolist()
                if not hits:
                    continue
                last_hit = hits[-1]
                price_then = df["close"].iloc[last_hit]
                if price_then == 0:
                    continue
                ret = (current_price - price_then) / price_then * 100
                results.setdefault(name, []).append(ret)
                per_ticker_rows.append({
                    "ticker": ticker, "indicator": name,
                    "signal_date": df["date"].iloc[last_hit].strftime("%Y-%m-%d"),
                    "price_then": round(price_then, 3),
                    "price_now": round(current_price, 3),
                    "return_pct": round(ret, 1),
                })
                fired_any = True
            print(f"  [{i+1}/{len(tickers)}] {ticker}: processed" + ("" if fired_any else " (no signals)"))
        except Exception as e:
            print(f"  [{i+1}/{len(tickers)}] {ticker}: error - {e}")
        time.sleep(0.15)

    if not results:
        print("\nNo signals found for any indicator.")
        return

    pd.DataFrame(per_ticker_rows).to_csv("indicator_backtest_detail.csv", index=False)

    print(f"\n{'='*80}\nHEAD-TO-HEAD COMPARISON — same universe, same 6-month window, "
          f"same 'most-recent-signal, return-to-today' rule\n{'='*80}")
    summary_rows = []
    for name, rets in results.items():
        arr = np.array(rets)
        summary_rows.append({
            "indicator": name,
            "signals": len(arr),
            "avg_return_pct": round(arr.mean(), 1),
            "median_return_pct": round(float(np.median(arr)), 1),
            "win_rate_pct": round((arr > 0).mean() * 100, 0),
        })
    summary_df = pd.DataFrame(summary_rows).sort_values("avg_return_pct", ascending=False)
    summary_df.to_csv("indicator_backtest_summary.csv", index=False)
    print(summary_df.to_string(index=False))
    print(f"\nPer-signal detail written to indicator_backtest_detail.csv")
    print(f"Summary written to indicator_backtest_summary.csv")


if __name__ == "__main__":
    main()
