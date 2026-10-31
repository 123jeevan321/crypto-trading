"""Forex Market Sessions and Overlap Engine.

Tracks global market trading sessions in real-time (GMT and Indian Standard Time IST),
detecting high-volume overlap periods (London-New York Overlap) and recommending the best
currency pairs to trade for the current session.
"""

from datetime import datetime, timezone, timedelta

# Forex Session Operating Hours in UTC (GMT)
# (start_hour, end_hour) in UTC
SESSIONS_UTC = {
    "Sydney": {"start": 21, "end": 6, "color": "#38bdf8", "key_currencies": ["AUD", "NZD"]},
    "Tokyo":  {"start": 0,  "end": 9, "color": "#ec4899", "key_currencies": ["JPY", "AUD", "NZD"]},
    "London": {"start": 7,  "end": 16, "color": "#f59e0b", "key_currencies": ["EUR", "GBP", "CHF"]},
    "New York": {"start": 12, "end": 21, "color": "#10b981", "key_currencies": ["USD", "CAD"]}
}

IST_OFFSET = timedelta(hours=5, minutes=30)


def get_current_sessions():
    """Calculates active Forex sessions, overlap state, and optimal currency pairs."""
    now_utc = datetime.now(timezone.utc)
    current_utc_hour = now_utc.hour + (now_utc.minute / 60.0)
    now_ist = now_utc + IST_OFFSET

    active_sessions = []
    for name, s in SESSIONS_UTC.items():
        start = s["start"]
        end = s["end"]
        if start < end:
            is_active = start <= current_utc_hour < end
        else:  # Crosses midnight UTC (e.g. Sydney)
            is_active = current_utc_hour >= start or current_utc_hour < end

        if is_active:
            active_sessions.append(name)

    # Detect London - New York Golden Overlap (12:00 - 16:00 UTC / 17:30 - 21:30 IST)
    is_overlap = ("London" in active_sessions and "New York" in active_sessions)
    is_asian_overlap = ("Tokyo" in active_sessions and "Sydney" in active_sessions)

    # Volume Quality Assessment
    if is_overlap:
        volume_status = "PEAK LIQUIDITY (London + NY Overlap) 🔥"
        trading_recommendation = "Optimal for 5m & 15m Binary Options. Clean trends and reliable breakouts."
        best_pairs = ["EUR/USD", "GBP/USD", "USD/JPY", "USD/CAD", "GBP/JPY"]
    elif "London" in active_sessions:
        volume_status = "HIGH VOLUME (London Session Open)"
        trading_recommendation = "Excellent for EUR & GBP pairs. Strong momentum."
        best_pairs = ["EUR/USD", "GBP/USD", "EUR/GBP", "EUR/JPY", "GBP/JPY"]
    elif "New York" in active_sessions:
        volume_status = "HIGH VOLUME (New York Session)"
        trading_recommendation = "Strong for USD & CAD pairs."
        best_pairs = ["EUR/USD", "USD/JPY", "USD/CAD", "AUD/USD"]
    elif "Tokyo" in active_sessions:
        volume_status = "MODERATE VOLUME (Asian Session)"
        trading_recommendation = "Best for JPY, AUD, and NZD pairs. Avoid EUR/USD scalping (low range)."
        best_pairs = ["USD/JPY", "AUD/JPY", "AUD/USD", "NZD/USD"]
    else:
        volume_status = "LOW VOLUME (Off-Peak Hours)"
        trading_recommendation = "Market is ranging. Use Mean Reversion / Support-Resistance strategies only."
        best_pairs = ["AUD/NZD", "EUR/GBP"]

    return {
        "time_utc": now_utc.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "time_ist": now_ist.strftime("%Y-%m-%d %I:%M:%S %p IST"),
        "active_sessions": active_sessions,
        "is_london_ny_overlap": is_overlap,
        "is_asian_overlap": is_asian_overlap,
        "volume_status": volume_status,
        "trading_recommendation": trading_recommendation,
        "best_pairs_for_session": best_pairs
    }


if __name__ == "__main__":
    import json
    print(json.dumps(get_current_sessions(), indent=2))
