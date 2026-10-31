"""
config.py
---------
Configuration file for J1 Trader - Indian Stock Market Portal.
Edit this file to set API credentials and trading parameters.
"""

# ---------------------------------------------------------------------------
# Angel One SmartAPI Credentials
# ---------------------------------------------------------------------------
# Sign up at https://smartapi.angelbroking.com/ to obtain these values.
ANGEL_ONE_API_KEY = ""
ANGEL_ONE_CLIENT_ID = ""
ANGEL_ONE_PASSWORD = ""
ANGEL_ONE_TOTP = ""          # TOTP secret key (not the 6-digit OTP)

# Set to True once credentials above are filled in.
USE_ANGEL_ONE = False        # Default: use yfinance as data source

# ---------------------------------------------------------------------------
# Paper Trading Capital Allocation (INR)
# ---------------------------------------------------------------------------
PAPER_CAPITAL = 100000       # Total virtual capital
SWING_CAPITAL = 100000       # Capital allocated for swing trades
INTRADAY_CAPITAL = 30000     # Capital allocated for intraday trades

# ---------------------------------------------------------------------------
# Intraday Risk Parameters
# ---------------------------------------------------------------------------
INTRADAY_STOP_LOSS = 1000    # Max loss per intraday session (INR)
INTRADAY_TARGET = 2000       # Profit target per intraday session (INR)

# ---------------------------------------------------------------------------
# Swing Trade Risk Parameters
# ---------------------------------------------------------------------------
SWING_STOP_LOSS_PCT = 2.0           # Stop-loss percentage below entry
SWING_TARGET_PCT_MIN = 5.0          # Minimum target percentage above entry
SWING_TARGET_PCT_MAX = 16.0         # Maximum target percentage above entry

# ---------------------------------------------------------------------------
# Signal Confidence Thresholds (0-100)
# ---------------------------------------------------------------------------
SWING_CONFIDENCE_THRESHOLD = 90      # Minimum confidence to trigger swing alert
INTRADAY_CONFIDENCE_THRESHOLD = 88   # Minimum confidence to trigger intraday alert

# ---------------------------------------------------------------------------
# Watchlists (NSE Symbols without ".NS" suffix)
# ---------------------------------------------------------------------------
WATCHLIST_SWING = [
    "PC-JEWELLER",
    "YESBANK",
    "SUZLON",
    "ADANIPOWER",
    "IRFC",
    "HUDCO",
    "NHPC",
    "COCHINSHIP",
    "RVNL",
    "RAILTEL",
    "SJVN",
    "IREDA",
    "NHPCLPOWER",
    "TATAPOWER",
    "TATAMOTORS",
    "RPOWER",
    "JSWENERGY",
    "ADANIGREEN",
    "VEDL",
    "SAIL",
    "NMDC",
    "HINDCOPPER",
    "BEL",
    "HAL",
    "DIXON",
    "KAYNES",
    "ANGELONE",
    "BSE",
    "MCX",
    "IEX",
]

WATCHLIST_INTRADAY = [
    "RELIANCE",
    "HDFCBANK",
    "ICICIBANK",
    "INFY",
    "TCS",
    "WIPRO",
    "AXISBANK",
    "SBIN",
    "BAJFINANCE",
    "MARUTI",
    "LTIM",
    "TECHM",
    "SUNPHARMA",
    "DRREDDY",
    "CIPLA",
    "DIVISLAB",
    "TITAN",
    "ASIANPAINT",
    "ULTRACEMCO",
    "GRASIM",
    "POWERGRID",
    "NTPC",
    "ONGC",
    "COALINDIA",
    "TATASTEEL",
    "HINDALCO",
    "M&M",
    "EICHERMOT",
    "BAJAJFINSV",
    "KOTAKBANK",
]
