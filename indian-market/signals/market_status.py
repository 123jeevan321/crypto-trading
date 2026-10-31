# -*- coding: utf-8 -*-
"""
Market Status Checker for J1 Trader Indian Stock Market Portal.
Provides real-time NSE session info, trading-day metadata, and market mood.
"""

import logging
from datetime import datetime, date, time as dtime, timedelta
from typing import Any, Dict, Optional

import pytz

try:
    import yfinance as yf
    _YFINANCE_AVAILABLE = True
except ImportError:
    _YFINANCE_AVAILABLE = False

logger = logging.getLogger(__name__)

IST = pytz.timezone("Asia/Kolkata")

# NSE session times (IST)
PRE_OPEN_START = dtime(9, 0)
MARKET_OPEN = dtime(9, 15)
MARKET_CLOSE = dtime(15, 30)
POST_CLOSE_END = dtime(16, 0)

# Weekday indices (Mon=0, Fri=4)
TRADING_DAYS = {0, 1, 2, 3, 4}

# NSE public holidays 2024-2025 (YYYY-MM-DD) — update annually
NSE_HOLIDAYS = {
    "2024-01-22", "2024-03-25", "2024-03-29", "2024-04-14",
    "2024-04-17", "2024-05-23", "2024-06-17", "2024-07-17",
    "2024-08-15", "2024-10-02", "2024-11-01", "2024-11-15",
    "2024-11-20", "2024-12-25",
    "2025-01-26", "2025-02-26", "2025-03-14", "2025-04-10",
    "2025-04-14", "2025-04-18", "2025-05-01", "2025-08-15",
    "2025-08-27", "2025-10-02", "2025-10-02", "2025-10-21",
    "2025-10-24", "2025-11-05", "2025-12-25",
    # 2026 (partial)
    "2026-01-26", "2026-03-30", "2026-04-02", "2026-04-14",
    "2026-05-01", "2026-08-15", "2026-10-02",
}

# Monthly expiry lookup (NSE F&O — last Thursday of each month)
def _last_thursday(year: int, month: int) -> date:
    """Return the last Thursday of a given month."""
    # Find the last day of the month
    if month == 12:
        last_day = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(year, month + 1, 1) - timedelta(days=1)
    # Go backwards to Thursday (weekday 3)
    offset = (last_day.weekday() - 3) % 7
    return last_day - timedelta(days=offset)


class MarketStatusChecker:
    """
    Utility class for NSE market session detection and market mood analysis.
    """

    # ------------------------------------------------------------------
    # IST helpers
    # ------------------------------------------------------------------

    @staticmethod
    def get_ist_time() -> datetime:
        """Return the current datetime in IST."""
        return datetime.now(IST)

    # ------------------------------------------------------------------
    # Market open / session
    # ------------------------------------------------------------------

    def is_market_open(self) -> bool:
        """Return True if the NSE regular session is currently active."""
        try:
            now = self.get_ist_time()
            date_str = now.strftime("%Y-%m-%d")
            if date_str in NSE_HOLIDAYS:
                return False
            if now.weekday() not in TRADING_DAYS:
                return False
            return MARKET_OPEN <= now.time() <= MARKET_CLOSE
        except Exception as exc:
            logger.error("is_market_open error: %s", exc)
            return False

    def get_session_info(self) -> Dict[str, Any]:
        """
        Return the current NSE session and time-to-open/close strings.

        Returns:
            {
                session: "PRE_OPEN" | "REGULAR" | "POST_CLOSE" | "CLOSED",
                time_to_open: str,   # e.g., "0h 45m" or "N/A"
                time_to_close: str,  # e.g., "5h 10m" or "N/A"
            }
        """
        try:
            now = self.get_ist_time()
            now_time = now.time()
            date_str = now.strftime("%Y-%m-%d")

            is_holiday = date_str in NSE_HOLIDAYS
            is_weekend = now.weekday() not in TRADING_DAYS

            if is_holiday or is_weekend:
                next_open_dt = self._next_trading_day_open(now)
                delta = next_open_dt - now
                return {
                    "session": "CLOSED",
                    "time_to_open": _fmt_timedelta(delta),
                    "time_to_close": "N/A",
                }

            if PRE_OPEN_START <= now_time < MARKET_OPEN:
                open_dt = now.replace(
                    hour=MARKET_OPEN.hour, minute=MARKET_OPEN.minute,
                    second=0, microsecond=0
                )
                return {
                    "session": "PRE_OPEN",
                    "time_to_open": _fmt_timedelta(open_dt - now),
                    "time_to_close": "N/A",
                }

            if MARKET_OPEN <= now_time <= MARKET_CLOSE:
                close_dt = now.replace(
                    hour=MARKET_CLOSE.hour, minute=MARKET_CLOSE.minute,
                    second=0, microsecond=0
                )
                return {
                    "session": "REGULAR",
                    "time_to_open": "N/A",
                    "time_to_close": _fmt_timedelta(close_dt - now),
                }

            if MARKET_CLOSE < now_time < POST_CLOSE_END:
                next_open_dt = self._next_trading_day_open(now)
                return {
                    "session": "POST_CLOSE",
                    "time_to_open": _fmt_timedelta(next_open_dt - now),
                    "time_to_close": "N/A",
                }

            # Late evening / night
            next_open_dt = self._next_trading_day_open(now)
            return {
                "session": "CLOSED",
                "time_to_open": _fmt_timedelta(next_open_dt - now),
                "time_to_close": "N/A",
            }

        except Exception as exc:
            logger.error("get_session_info error: %s", exc)
            return {"session": "CLOSED", "time_to_open": "N/A", "time_to_close": "N/A"}

    # ------------------------------------------------------------------
    # Trading day metadata
    # ------------------------------------------------------------------

    def get_trading_day_status(self) -> Dict[str, Any]:
        """
        Return trading-day metadata for today.

        Returns:
            {
                is_trading_day: bool,
                next_trading_day: str,   # YYYY-MM-DD
                is_expiry_day: bool,     # NSE F&O monthly expiry (last Thu)
            }
        """
        try:
            now = self.get_ist_time()
            today = now.date()
            today_str = today.strftime("%Y-%m-%d")

            is_trading = (
                today.weekday() in TRADING_DAYS
                and today_str not in NSE_HOLIDAYS
            )

            # Next trading day
            candidate = today + timedelta(days=1)
            while (
                candidate.weekday() not in TRADING_DAYS
                or candidate.strftime("%Y-%m-%d") in NSE_HOLIDAYS
            ):
                candidate += timedelta(days=1)
            next_trading_day = candidate.strftime("%Y-%m-%d")

            # Expiry day check (last Thursday of month)
            expiry = _last_thursday(today.year, today.month)
            is_expiry = (today == expiry) and is_trading

            return {
                "is_trading_day": is_trading,
                "next_trading_day": next_trading_day,
                "is_expiry_day": is_expiry,
            }
        except Exception as exc:
            logger.error("get_trading_day_status error: %s", exc)
            return {
                "is_trading_day": False,
                "next_trading_day": "",
                "is_expiry_day": False,
            }

    # ------------------------------------------------------------------
    # Market mood (India VIX)
    # ------------------------------------------------------------------

    def get_market_mood(self) -> Dict[str, Any]:
        """
        Fetch India VIX from yfinance and classify market mood.

        Returns:
            {
                vix_approx: float,
                mood: "FEAR" | "GREED" | "NEUTRAL"
            }
        """
        if not _YFINANCE_AVAILABLE:
            logger.warning("yfinance not installed; returning default mood.")
            return {"vix_approx": 0.0, "mood": "NEUTRAL"}

        try:
            ticker = yf.Ticker("^INDIAVIX")
            hist = ticker.history(period="1d", interval="1d")
            if hist.empty:
                raise ValueError("Empty VIX data returned")

            vix = float(hist["Close"].iloc[-1])
            if vix >= 20:
                mood = "FEAR"
            elif vix <= 13:
                mood = "GREED"
            else:
                mood = "NEUTRAL"

            return {"vix_approx": round(vix, 2), "mood": mood}

        except Exception as exc:
            logger.error("get_market_mood VIX fetch failed: %s", exc)
            return {"vix_approx": 0.0, "mood": "NEUTRAL"}

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _next_trading_day_open(self, from_dt: datetime) -> datetime:
        """Return the IST datetime of the next trading day's market open."""
        candidate = from_dt + timedelta(days=1)
        candidate = candidate.replace(
            hour=MARKET_OPEN.hour, minute=MARKET_OPEN.minute,
            second=0, microsecond=0
        )
        while (
            candidate.weekday() not in TRADING_DAYS
            or candidate.strftime("%Y-%m-%d") in NSE_HOLIDAYS
        ):
            candidate += timedelta(days=1)
        return candidate


# ------------------------------------------------------------------
# Module-level utility
# ------------------------------------------------------------------

def _fmt_timedelta(delta: timedelta) -> str:
    """Format a timedelta as 'Xh Ym'."""
    total_seconds = max(int(delta.total_seconds()), 0)
    hours, remainder = divmod(total_seconds, 3600)
    minutes = remainder // 60
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"
