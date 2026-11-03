"""
events_calendar.py
------------------
Corporate Events & Earnings Calendar Gatekeeper for J1 Trader.
Automatically inspects company earnings dates, board meetings, and high-impact
corporate events to protect traders from binary algorithmic whipsaws.

Rule: NEVER recommend or enter a stock on the day of its quarterly earnings release.
"""

import logging
from datetime import datetime, date
from typing import Tuple, Dict, Any, Optional

try:
    import yfinance as yf
except ImportError:
    yf = None

logger = logging.getLogger("j1trader.events_calendar")

class EventsCalendar:
    """Detects corporate earnings releases, board meetings, and high-risk event dates."""
    
    _cache: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def is_earnings_or_event_today(cls, symbol: str, target_date: Optional[date] = None) -> Tuple[bool, str]:
        """
        Returns (is_event_today, event_description).
        If True, the stock MUST BE BLOCKED from intraday/swing trading.
        """
        if target_date is None:
            target_date = date.today()

        clean_symbol = symbol.replace(".NS", "").replace(".BO", "").upper()
        cache_key = f"{clean_symbol}_{target_date}"
        if cache_key in cls._cache:
            cached = cls._cache[cache_key]
            return cached["is_blocked"], cached["reason"]

        if yf is None:
            return False, "yfinance not available"

        try:
            ticker = yf.Ticker(f"{clean_symbol}.NS")
            cal = ticker.calendar
            
            if cal and isinstance(cal, dict):
                earnings_dates = cal.get("Earnings Date", [])
                if earnings_dates:
                    if not isinstance(earnings_dates, (list, tuple)):
                        earnings_dates = [earnings_dates]
                    
                    for ed in earnings_dates:
                        # Normalize to date object
                        if hasattr(ed, "date"):
                            ed_date = ed.date()
                        elif isinstance(ed, date):
                            ed_date = ed
                        elif isinstance(ed, str):
                            try:
                                ed_date = datetime.strptime(ed[:10], "%Y-%m-%d").date()
                            except Exception:
                                continue
                        else:
                            continue
                            
                        if ed_date == target_date:
                            reason = f"Q2/Q3/Q4 Earnings Results scheduled TODAY ({target_date})"
                            cls._cache[cache_key] = {"is_blocked": True, "reason": reason}
                            logger.warning("EVENT BLOCK TRIGGERED: %s has %s", clean_symbol, reason)
                            return True, reason

            # Also check news for board meeting / results keywords today
            news = ticker.news
            if news and isinstance(news, list):
                for item in news[:5]:
                    title = item.get("title", "") or (item.get("content", {}) or {}).get("title", "")
                    title_lower = title.lower()
                    if any(w in title_lower for w in ["q2 result", "q3 result", "q1 result", "q4 result", "board meeting today", "earnings today"]):
                        reason = f"Breaking corporate earnings news headline: '{title}'"
                        cls._cache[cache_key] = {"is_blocked": True, "reason": reason}
                        logger.warning("EVENT BLOCK TRIGGERED: %s has %s", clean_symbol, reason)
                        return True, reason

        except Exception as e:
            logger.debug("Error checking corporate calendar for %s: %s", clean_symbol, e)

        cls._cache[cache_key] = {"is_blocked": False, "reason": "No high-risk earnings events today"}
        return False, "No high-risk earnings events today"
