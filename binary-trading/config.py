"""Quotex Binary Trading Configuration.

Defines the top 20 currency pairs, Quotex payout rates, timeframes, and session parameters.
"""

# Top 20 Currency Pairs for Quotex Binary Trading
# Each pair includes Yahoo Finance ticker, base/quote, typical Quotex payout %, and volatility rating
QUOTEX_PAIRS = [
    {"symbol": "EUR/USD", "ticker": "EURUSD=X", "payout": 90, "category": "Major", "active_sessions": ["London", "New York"]},
    {"symbol": "GBP/USD", "ticker": "GBPUSD=X", "payout": 88, "category": "Major", "active_sessions": ["London", "New York"]},
    {"symbol": "USD/JPY", "ticker": "JPY=X", "payout": 87, "category": "Major", "active_sessions": ["Tokyo", "New York"]},
    {"symbol": "AUD/USD", "ticker": "AUDUSD=X", "payout": 85, "category": "Major", "active_sessions": ["Sydney", "Tokyo", "New York"]},
    {"symbol": "USD/CAD", "ticker": "CAD=X", "payout": 85, "category": "Major", "active_sessions": ["New York"]},
    {"symbol": "USD/CHF", "ticker": "CHF=X", "payout": 84, "category": "Major", "active_sessions": ["London", "New York"]},
    {"symbol": "NZD/USD", "ticker": "NZDUSD=X", "payout": 83, "category": "Major", "active_sessions": ["Sydney", "Tokyo"]},
    {"symbol": "EUR/GBP", "ticker": "EURGBP=X", "payout": 86, "category": "Cross", "active_sessions": ["London"]},
    {"symbol": "EUR/JPY", "ticker": "EURJPY=X", "payout": 88, "category": "Cross", "active_sessions": ["London", "Tokyo"]},
    {"symbol": "GBP/JPY", "ticker": "GBPJPY=X", "payout": 89, "category": "Cross", "active_sessions": ["London", "Tokyo"]},
    {"symbol": "AUD/JPY", "ticker": "AUDJPY=X", "payout": 85, "category": "Cross", "active_sessions": ["Sydney", "Tokyo"]},
    {"symbol": "CAD/JPY", "ticker": "CADJPY=X", "payout": 84, "category": "Cross", "active_sessions": ["Tokyo", "New York"]},
    {"symbol": "EUR/AUD", "ticker": "EURAUD=X", "payout": 85, "category": "Cross", "active_sessions": ["London", "Sydney"]},
    {"symbol": "GBP/AUD", "ticker": "GBPAUD=X", "payout": 86, "category": "Cross", "active_sessions": ["London", "Sydney"]},
    {"symbol": "EUR/CAD", "ticker": "EURCAD=X", "payout": 84, "category": "Cross", "active_sessions": ["London", "New York"]},
    {"symbol": "GBP/CAD", "ticker": "GBPCAD=X", "payout": 85, "category": "Cross", "active_sessions": ["London", "New York"]},
    {"symbol": "AUD/NZD", "ticker": "AUDNZD=X", "payout": 82, "category": "Cross", "active_sessions": ["Sydney", "Tokyo"]},
    {"symbol": "NZD/JPY", "ticker": "NZDJPY=X", "payout": 83, "category": "Cross", "active_sessions": ["Sydney", "Tokyo"]},
    {"symbol": "EUR/CHF", "ticker": "EURCHF=X", "payout": 82, "category": "Cross", "active_sessions": ["London"]},
    {"symbol": "USD/INR", "ticker": "INR=X", "payout": 82, "category": "Exotic", "active_sessions": ["Asian", "London"]}
]

# Minimum payout filter (User criteria: 80% - 90%+)
MIN_PAYOUT_THRESHOLD = 80

# Supported Expiry Timeframes for Quotex
TIMEFRAMES = {
    "1m": {"label": "1 Minute", "noise_level": "High", "risk": "High", "expirations_recommended": [1]},
    "5m": {"label": "5 Minutes", "noise_level": "Medium-Low", "risk": "Balanced", "expirations_recommended": [3, 5]},
    "15m": {"label": "15 Minutes", "noise_level": "Low", "risk": "Low", "expirations_recommended": [10, 15]},
    "1h": {"label": "1 Hour", "noise_level": "Very Low", "risk": "Lowest", "expirations_recommended": [30, 60]}
}

# Signal Confidence Tiers
CONFIDENCE_TIERS = {
    "A+": {"min_confluence": 3, "min_probability": 88, "badge": "STRONG HIGH-PROBABILITY", "color": "#00d09c"},
    "A":  {"min_confluence": 2, "min_probability": 75, "badge": "MODERATE SIGNAL", "color": "#f59e0b"},
    "B":  {"min_confluence": 1, "min_probability": 60, "badge": "WEAK SETUP - CAUTION", "color": "#9ca3af"}
}
