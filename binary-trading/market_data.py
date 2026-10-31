"""Market Data & Technical Indicator Engine for Quotex Currency Pairs.

Fetches real-time candles and calculates indicators:
- EMA 9, EMA 20, EMA 50
- RSI (14)
- Bollinger Bands (20, 2)
- MACD (12, 26, 9)
- Key Support and Resistance Levels (Recent Highs/Lows and Psychological Round Numbers)
"""

import json
import urllib.request
from datetime import datetime, timezone


def fetch_pair_candles(ticker, interval="5m", range_str="1d"):
    """Fetches real-time candlestick data from Yahoo Finance."""
    url = f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}?interval={interval}&range={range_str}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    try:
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        result = data.get("chart", {}).get("result", [])
        if not result:
            return None
        res0 = result[0]
        meta = res0.get("meta", {})
        indicators = res0.get("indicators", {}).get("quote", [{}])[0]
        timestamps = res0.get("timestamp", [])

        opens = indicators.get("open", [])
        highs = indicators.get("high", [])
        lows = indicators.get("low", [])
        closes = indicators.get("close", [])

        valid_candles = []
        for i in range(len(timestamps)):
            if closes[i] is not None and opens[i] is not None:
                valid_candles.append({
                    "time": timestamps[i],
                    "open": float(opens[i]),
                    "high": float(highs[i] or closes[i]),
                    "low": float(lows[i] or closes[i]),
                    "close": float(closes[i])
                })
        return {
            "symbol": ticker,
            "currency": meta.get("currency", "USD"),
            "regularMarketPrice": meta.get("regularMarketPrice", closes[-1] if closes else 0.0),
            "candles": valid_candles
        }
    except Exception as e:
        return None


def calculate_ema(series, period):
    """Calculates Exponential Moving Average (EMA)."""
    if len(series) < period:
        return [None] * len(series)
    multiplier = 2.0 / (period + 1.0)
    ema_values = [None] * (period - 1)
    # First EMA is Simple Moving Average
    sma = sum(series[:period]) / period
    ema_values.append(sma)
    for price in series[period:]:
        current_ema = (price - ema_values[-1]) * multiplier + ema_values[-1]
        ema_values.append(current_ema)
    return ema_values


def calculate_rsi(closes, period=14):
    """Calculates Relative Strength Index (RSI)."""
    if len(closes) < period + 1:
        return 50.0
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [max(d, 0.0) for d in deltas]
    losses = [abs(min(d, 0.0)) for d in deltas]

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100.0 - (100.0 / (1.0 + rs)), 2)


def calculate_bollinger_bands(closes, period=20, std_dev=2.0):
    """Calculates upper, middle (SMA), and lower Bollinger Bands."""
    if len(closes) < period:
        c = closes[-1] if closes else 1.0
        return {"upper": c * 1.01, "middle": c, "lower": c * 0.99}
    slice_data = closes[-period:]
    sma = sum(slice_data) / period
    variance = sum((x - sma) ** 2 for x in slice_data) / period
    std = variance ** 0.5
    return {
        "upper": round(sma + (std_dev * std), 5),
        "middle": round(sma, 5),
        "lower": round(sma - (std_dev * std), 5)
    }


def calculate_macd(closes, fast=12, slow=26, signal=9):
    """Calculates MACD Line, Signal Line, and Histogram."""
    if len(closes) < slow + signal:
        return {"macd": 0.0, "signal": 0.0, "hist": 0.0}
    ema_fast = calculate_ema(closes, fast)
    ema_slow = calculate_ema(closes, slow)

    macd_line = []
    for f, s in zip(ema_fast, ema_slow):
        if f is not None and s is not None:
            macd_line.append(f - s)

    if len(macd_line) < signal:
        return {"macd": 0.0, "signal": 0.0, "hist": 0.0}

    signal_line = calculate_ema(macd_line, signal)
    curr_macd = macd_line[-1] if macd_line else 0.0
    curr_signal = signal_line[-1] if signal_line and signal_line[-1] is not None else 0.0
    return {
        "macd": round(curr_macd, 5),
        "signal": round(curr_signal, 5),
        "hist": round(curr_macd - curr_signal, 5)
    }


def calculate_support_resistance(candles, lookback=30):
    """Detects swing highs, swing lows, and institutional round number levels."""
    if not candles:
        return {"support": 0.0, "resistance": 0.0, "round_level": 0.0}
    recent = candles[-lookback:]
    highs = [c["high"] for c in recent]
    lows = [c["low"] for c in recent]
    resistance = max(highs)
    support = min(lows)

    curr_price = candles[-1]["close"]
    # Round number psychological magnet (e.g. 1.08500, 150.00)
    if curr_price > 50:  # JPY or INR pairs
        round_level = round(curr_price)
    else:  # Standard 4-5 decimal FX pairs
        round_level = round(curr_price, 3)

    return {
        "support": round(support, 5),
        "resistance": round(resistance, 5),
        "round_level": round(round_level, 5)
    }


def analyze_market_snapshot(pair_config):
    """Compiles a complete technical profile for a currency pair."""
    ticker = pair_config["ticker"]
    res = fetch_pair_candles(ticker, interval="5m", range_str="1d")
    if not res or not res.get("candles"):
        return None

    candles = res["candles"]
    closes = [c["close"] for c in candles]
    curr_price = closes[-1]

    ema20_vals = calculate_ema(closes, 20)
    ema50_vals = calculate_ema(closes, 50)
    ema20 = ema20_vals[-1] if ema20_vals and ema20_vals[-1] is not None else curr_price
    ema50 = ema50_vals[-1] if ema50_vals and ema50_vals[-1] is not None else curr_price

    rsi = calculate_rsi(closes, 14)
    bb = calculate_bollinger_bands(closes, 20, 2.0)
    macd = calculate_macd(closes)
    sr = calculate_support_resistance(candles)

    # Candlestick characteristics (rejection wick ratio)
    last_candle = candles[-1]
    body = abs(last_candle["close"] - last_candle["open"])
    upper_wick = last_candle["high"] - max(last_candle["close"], last_candle["open"])
    lower_wick = min(last_candle["close"], last_candle["open"]) - last_candle["low"]

    return {
        "symbol": pair_config["symbol"],
        "ticker": ticker,
        "payout": pair_config["payout"],
        "category": pair_config["category"],
        "price": curr_price,
        "prev_close": closes[-2] if len(closes) >= 2 else curr_price,
        "ema20": round(ema20, 5),
        "ema50": round(ema50, 5),
        "rsi": rsi,
        "bb_upper": bb["upper"],
        "bb_middle": bb["middle"],
        "bb_lower": bb["lower"],
        "macd": macd,
        "support": sr["support"],
        "resistance": sr["resistance"],
        "round_level": sr["round_level"],
        "candle_body": round(body, 5),
        "upper_wick": round(upper_wick, 5),
        "lower_wick": round(lower_wick, 5),
        "is_bullish_candle": last_candle["close"] >= last_candle["open"],
        "candles": candles
    }
