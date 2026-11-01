"""
NSE Trading Holidays & Market Session Hours (IST)
"""

from datetime import datetime, time
import pytz

IST = pytz.timezone("Asia/Kolkata")

# NSE Holidays 2024-2026 (Major standard market holidays)
NSE_HOLIDAYS = {
    # 2024
    "2024-01-22", "2024-01-26", "2024-03-08", "2024-03-25", "2024-03-29",
    "2024-04-11", "2024-04-17", "2024-05-01", "2024-05-20", "2024-06-17",
    "2024-07-17", "2024-08-15", "2024-10-02", "2024-11-01", "2024-11-15",
    "2024-12-25",
    # 2025
    "2025-01-26", "2025-02-26", "2025-03-14", "2025-03-31", "2025-04-10",
    "2025-04-14", "2025-04-18", "2025-05-01", "2025-08-15", "2025-08-27",
    "2025-10-02", "2025-10-21", "2025-10-22", "2025-11-05", "2025-12-25",
    # 2026
    "2026-01-26", "2026-03-06", "2026-03-26", "2026-04-03", "2026-04-14",
    "2026-05-01", "2026-08-15", "2026-10-02", "2026-10-20", "2026-11-10",
    "2026-12-25"
}

def get_current_ist() -> datetime:
    return datetime.now(IST)

def is_trading_day(dt: datetime = None) -> bool:
    if dt is None:
        dt = get_current_ist()
    # Weekends (5 = Saturday, 6 = Sunday)
    if dt.weekday() >= 5:
        return False
    date_str = dt.strftime("%Y-%m-%d")
    if date_str in NSE_HOLIDAYS:
        return False
    return True

def is_market_open(dt: datetime = None) -> bool:
    if dt is None:
        dt = get_current_ist()
    if not is_trading_day(dt):
        return False
    t = dt.time()
    # 09:15 to 15:30 IST
    return time(9, 15) <= t <= time(15, 30)

def is_entry_allowed(dt: datetime = None) -> bool:
    """Blocks new entries after 14:45 IST as per challenge rules."""
    if dt is None:
        dt = get_current_ist()
    if not is_market_open(dt):
        return False
    return dt.time() <= time(14, 45)

def is_square_off_time(dt: datetime = None) -> bool:
    """Squares off intraday positions at 15:15 IST."""
    if dt is None:
        dt = get_current_ist()
    if not is_trading_day(dt):
        return False
    return dt.time() >= time(15, 15)
