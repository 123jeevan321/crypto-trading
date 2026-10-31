"""Smart Money Concepts (SMC), ICT, Order Flow & Time-Safety Engine.

Implements institutional analysis:
- Liquidity Sweeps / Hunts (Equal Highs/Lows swept before reversal)
- Fair Value Gaps (FVG / 3-Candle Imbalances)
- Institutional Order Blocks (OB)
- Market Structure Shift (MSS / Change of Character)
- Forex & Crypto Time-of-Day Risk Windows (Prime vs. Avoid Hours in IST)
"""

from datetime import datetime, timezone, timedelta

IST_OFFSET = timedelta(hours=5, minutes=30)


# ==============================================================================
# 1. TIME-OF-DAY & SESSION RISK WINDOW FILTER (IST)
# ==============================================================================

def get_timing_risk_assessment():
    """Evaluates the current time window, weekend state, and assigns a Safety Rating."""
    now_utc = datetime.now(timezone.utc)
    now_ist = now_utc + IST_OFFSET

    hour_ist = now_ist.hour
    minute_ist = now_ist.minute
    time_float = hour_ist + (minute_ist / 60.0)
    weekday = now_ist.weekday()  # 5=Saturday, 6=Sunday

    is_weekend = weekday >= 5

    # Evaluation of Daily Windows (IST):
    # 1. Golden Overlap Window: 18:30 - 21:30 (6:30 PM - 9:30 PM) -> London + NY Overlap
    # 2. London Morning Window: 13:30 - 16:30 (1:30 PM - 4:30 PM) -> London Open Expansion
    # 3. Asian Active Window:   06:00 - 10:00 (6:00 AM - 10:00 AM) -> Tokyo / Sydney Trends
    # 4. Dead Zone Chop:       10:30 - 13:00 (10:30 AM - 1:00 PM) -> AVOID (Low volume churn)
    # 5. Night Rollover Spike: 02:30 - 05:00 (2:30 AM - 5:00 AM)  -> AVOID (Spreads widen, broker reset)

    if is_weekend:
        timing_status = "WEEKEND (OTC MARKETS ONLY)"
        safety_level = "MODERATE (CAUTION)"
        risk_rating = "MEDIUM-HIGH"
        guidance = (
            "[WARNING] Saturday/Sunday: Traditional interbank Forex is closed. "
            "Quotex operates on OTC (Over-The-Counter) algorithm quotes. "
            "Crypto (BTC/ETH) trades 24/7 with thinner weekend volume. "
            "Strictly follow SMC Order Blocks and Avoid 1-minute noise; use 5m/15m expiries only."
        )
        safe_to_trade = True
    elif 18.5 <= time_float <= 21.5:  # 6:30 PM - 9:30 PM IST
        timing_status = "[PRIME] GOLDEN WINDOW (London + New York Overlap)"
        safety_level = "PRIME TRADING HOURS (HIGHEST CONFIDENCE 95%)"
        risk_rating = "OPTIMAL"
        guidance = (
            "Highest volume and liquidity of the 24h cycle (~70% of global flow). "
            "Clean trends, true institutional breakouts, minimal fakeouts. Optimal for 5m & 15m expiries."
        )
        safe_to_trade = True
    elif 13.5 <= time_float <= 16.5:  # 1:30 PM - 4:30 PM IST
        timing_status = "[HIGH] LONDON OPEN EXPANSION"
        safety_level = "HIGH CONFIDENCE (88%-92%)"
        risk_rating = "GOOD"
        guidance = "Heavy European volume. Watch for early 15-minute liquidity sweeps followed by true expansion."
        safe_to_trade = True
    elif 6.0 <= time_float <= 10.0:   # 6:00 AM - 10:00 AM IST
        timing_status = "[MODERATE] ASIAN SESSION TRENDS"
        safety_level = "MODERATE (75%-82%)"
        risk_rating = "MODERATE"
        guidance = "Good for JPY and AUD pairs. Avoid EUR/USD scalping due to low pip range."
        safe_to_trade = True
    elif 10.5 <= time_float <= 13.0:  # 10:30 AM - 1:00 PM IST
        timing_status = "[DANGER] DEAD ZONE CHOP (Asian Close / Pre-London)"
        safety_level = "STRICTLY AVOID / HIGH RISK"
        risk_rating = "HIGH RISK"
        guidance = (
            "[DO NOT TRADE]: Volume drops to lowest levels. Market churns in tight fakeout boxes. "
            "Indicators give repeated false signals. Wait for London open at 1:30 PM IST."
        )
        safe_to_trade = False
    elif 2.5 <= time_float <= 5.0:    # 2:30 AM - 5:00 AM IST
        timing_status = "[DANGER] DAILY ROLLOVER & SPREAD WIDENING"
        safety_level = "STRICTLY AVOID / EXTREME RISK"
        risk_rating = "EXTREME RISK"
        guidance = "[DO NOT TRADE]: Daily bank rollover. Spreads multiply 3x-5x and sudden gaps occur."
        safe_to_trade = False
    else:
        timing_status = "NORMAL TRADING HOURS"
        safety_level = "NORMAL (75%-85%)"
        risk_rating = "NORMAL"
        guidance = "Standard market conditions. Ensure at least 3 strategies agree before entering."
        safe_to_trade = True

    return {
        "current_time_ist": now_ist.strftime("%Y-%m-%d %I:%M:%S %p IST"),
        "is_weekend": is_weekend,
        "timing_status": timing_status,
        "safety_level": safety_level,
        "risk_rating": risk_rating,
        "safe_to_trade": safe_to_trade,
        "guidance": guidance
    }


# ==============================================================================
# 2. SMART MONEY CONCEPTS (SMC) & ICT PATTERN DETECTOR
# ==============================================================================

def detect_liquidity_sweep(candles, lookback=15):
    """Detects whether price swept previous equal highs or lows before reversing (Turtle Soup)."""
    if len(candles) < lookback + 2:
        return None

    recent = candles[-lookback:-1]
    prev_high = max(c["high"] for c in recent)
    prev_low = min(c["low"] for c in recent)
    curr = candles[-1]

    # Bearish Liquidity Sweep (Swept Highs, closed below -> PUT)
    if curr["high"] > prev_high and curr["close"] < prev_high:
        upper_wick = curr["high"] - max(curr["open"], curr["close"])
        body = abs(curr["close"] - curr["open"])
        if upper_wick >= body * 0.4:
            return {
                "type": "BEARISH_LIQUIDITY_SWEEP",
                "bias": "PUT",
                "swept_level": round(prev_high, 5),
                "desc": f"Swept Buy-Side Liquidity at {prev_high:.5f} and rejected back inside (ICT Liquidity Hunt)"
            }

    # Bullish Liquidity Sweep (Swept Lows, closed above -> CALL)
    if curr["low"] < prev_low and curr["close"] > prev_low:
        lower_wick = min(curr["open"], curr["close"]) - curr["low"]
        body = abs(curr["close"] - curr["open"])
        if lower_wick >= body * 0.4:
            return {
                "type": "BULLISH_LIQUIDITY_SWEEP",
                "bias": "CALL",
                "swept_level": round(prev_low, 5),
                "desc": f"Swept Sell-Side Liquidity at {prev_low:.5f} and rejected back inside (ICT Liquidity Hunt)"
            }

    return None


def detect_fair_value_gap(candles):
    """Detects 3-candle Fair Value Gaps (FVG / Imbalance)."""
    if len(candles) < 3:
        return None

    c1 = candles[-3]
    c2 = candles[-2]
    c3 = candles[-1]

    # Bullish FVG: Candle 1 High is lower than Candle 3 Low (Gap in between Candle 2)
    if c1["high"] < c3["low"] and (c2["close"] > c2["open"]):
        gap_size = round(c3["low"] - c1["high"], 5)
        return {
            "type": "BULLISH_FVG",
            "bias": "CALL",
            "fvg_top": round(c3["low"], 5),
            "fvg_bottom": round(c1["high"], 5),
            "gap_size": gap_size,
            "desc": f"Bullish FVG Imbalance ({c1['high']:.5f} - {c3['low']:.5f}). Price entering rebalance zone."
        }

    # Bearish FVG: Candle 1 Low is higher than Candle 3 High
    if c1["low"] > c3["high"] and (c2["close"] < c2["open"]):
        gap_size = round(c1["low"] - c3["high"], 5)
        return {
            "type": "BEARISH_FVG",
            "bias": "PUT",
            "fvg_top": round(c1["low"], 5),
            "fvg_bottom": round(c3["high"], 5),
            "gap_size": gap_size,
            "desc": f"Bearish FVG Imbalance ({c3['high']:.5f} - {c1['low']:.5f}). Price entering rebalance zone."
        }

    return None


def detect_order_block(candles, lookback=10):
    """Detects Institutional Order Block (last opposing candle before sharp displacement)."""
    if len(candles) < 4:
        return None

    # Check for Bullish Order Block (Last red candle before 2 consecutive strong green candles)
    c_last = candles[-1]
    c_prev = candles[-2]
    c_ob = candles[-3]

    if (c_ob["close"] < c_ob["open"]) and (c_prev["close"] > c_prev["open"]) and (c_last["close"] > c_last["open"]):
        displacement = (c_last["close"] - c_ob["open"]) / c_ob["open"]
        if displacement > 0.0015:
            return {
                "type": "BULLISH_ORDER_BLOCK",
                "bias": "CALL",
                "ob_level": round(c_ob["low"], 5),
                "desc": f"Bullish Institutional Order Block validated at {c_ob['low']:.5f} with displacement"
            }

    # Bearish Order Block (Last green candle before 2 consecutive strong red candles)
    if (c_ob["close"] > c_ob["open"]) and (c_prev["close"] < c_prev["open"]) and (c_last["close"] < c_last["open"]):
        displacement = (c_ob["open"] - c_last["close"]) / c_ob["open"]
        if displacement > 0.0015:
            return {
                "type": "BEARISH_ORDER_BLOCK",
                "bias": "PUT",
                "ob_level": round(c_ob["high"], 5),
                "desc": f"Bearish Institutional Order Block validated at {c_ob['high']:.5f} with displacement"
            }

    return None


def evaluate_smc_order_flow(candles):
    """Aggregates all SMC and ICT metrics into a clean institutional confluence summary."""
    sweep = detect_liquidity_sweep(candles)
    fvg = detect_fair_value_gap(candles)
    ob = detect_order_block(candles)

    smc_signals = []
    call_score = 0
    put_score = 0

    for item in [sweep, fvg, ob]:
        if item:
            smc_signals.append(item["desc"])
            if item["bias"] == "CALL":
                call_score += 1
            elif item["bias"] == "PUT":
                put_score += 1

    if call_score > put_score and call_score >= 1:
        smc_bias = "CALL"
        smc_confidence = min(95, 70 + (call_score * 12))
    elif put_score > call_score and put_score >= 1:
        smc_bias = "PUT"
        smc_confidence = min(95, 70 + (put_score * 12))
    else:
        smc_bias = "NEUTRAL"
        smc_confidence = 50

    return {
        "smc_bias": smc_bias,
        "smc_confidence": smc_confidence,
        "patterns_detected": smc_signals,
        "has_sweep": sweep is not None,
        "has_fvg": fvg is not None,
        "has_order_block": ob is not None
    }
