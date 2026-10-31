# -*- coding: utf-8 -*-
"""
Intraday Signal Engine for J1 Trader Indian Stock Market Portal.
Generates intraday (same-day) BUY/SELL signals for NSE equities.
"""

import sys
import os
import logging
from datetime import datetime, time as dtime, timedelta
from typing import List, Dict, Any, Optional

import pytz

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from analysis.screener import StockScreener
except ImportError:
    StockScreener = None

try:
    from data.news_fetcher import NewsFetcher
except ImportError:
    NewsFetcher = None

logger = logging.getLogger(__name__)

IST = pytz.timezone("Asia/Kolkata")

# Intraday capital per trade (INR)
INTRADAY_CAPITAL = 30_000

# NSE company name map (keep consistent with swing_signal)
NSE_COMPANY_NAMES: Dict[str, str] = {
    "RELIANCE": "Reliance Industries Ltd",
    "TCS": "Tata Consultancy Services Ltd",
    "INFY": "Infosys Ltd",
    "HDFCBANK": "HDFC Bank Ltd",
    "ICICIBANK": "ICICI Bank Ltd",
    "SBIN": "State Bank of India",
    "WIPRO": "Wipro Ltd",
    "AXISBANK": "Axis Bank Ltd",
    "BAJFINANCE": "Bajaj Finance Ltd",
    "BHARTIARTL": "Bharti Airtel Ltd",
    "LT": "Larsen & Toubro Ltd",
    "HINDUNILVR": "Hindustan Unilever Ltd",
    "ITC": "ITC Ltd",
    "KOTAKBANK": "Kotak Mahindra Bank Ltd",
    "MARUTI": "Maruti Suzuki India Ltd",
    "TITAN": "Titan Company Ltd",
    "SUNPHARMA": "Sun Pharmaceutical Industries Ltd",
    "ULTRACEMCO": "UltraTech Cement Ltd",
    "NESTLEIND": "Nestle India Ltd",
    "POWERGRID": "Power Grid Corporation of India Ltd",
    "ADANIENT": "Adani Enterprises Ltd",
    "ADANIPORTS": "Adani Ports and Special Economic Zone Ltd",
    "TECHM": "Tech Mahindra Ltd",
    "HCLTECH": "HCL Technologies Ltd",
    "DRREDDY": "Dr. Reddys Laboratories Ltd",
}

MARKET_OPEN = dtime(9, 15)
MARKET_CLOSE = dtime(15, 30)
TRADING_DAYS = {0, 1, 2, 3, 4}  # Monday=0 ... Friday=4


def _get_nse_name(symbol: str) -> str:
    return NSE_COMPANY_NAMES.get(symbol.upper(), f"{symbol} Ltd")


def _format_time_window(base_dt: datetime, duration_minutes: int = 15) -> str:
    """Return a '9:35 AM - 9:50 AM' style window string."""
    # Add a small offset from exact open so entries feel realistic
    start = base_dt.replace(second=0, microsecond=0)
    end = start + timedelta(minutes=duration_minutes)
    fmt = "%I:%M %p"
    return f"{start.strftime(fmt)} - {end.strftime(fmt)}"


class IntradaySignalEngine:
    """
    Generates intraday BUY and SELL signals for NSE-listed stocks.

    When the market is open the engine uses live screener data.
    When the market is closed it generates next-open projections from
    the daily timeframe so the UI always has content to display.
    """

    MIN_SCORE = 80  # Lower bar than swing for intraday
    MAX_LOSS_CAP = 1_000   # INR hard cap per trade
    MIN_PROFIT_TARGET = 2_000  # INR minimum profit aim

    def __init__(self):
        self.screener = StockScreener() if StockScreener is not None else None
        self.news_fetcher = NewsFetcher() if NewsFetcher is not None else None

    # ------------------------------------------------------------------
    # Market timing helpers
    # ------------------------------------------------------------------

    def is_market_open(self) -> bool:
        """Return True if NSE regular session is currently active."""
        try:
            now_ist = datetime.now(IST)
            if now_ist.weekday() not in TRADING_DAYS:
                return False
            current_time = now_ist.time()
            return MARKET_OPEN <= current_time <= MARKET_CLOSE
        except Exception as exc:
            logger.error("is_market_open error: %s", exc)
            return False

    def _next_market_open_dt(self) -> datetime:
        """Return the IST datetime of the next market open."""
        now_ist = datetime.now(IST)
        candidate = now_ist.replace(
            hour=MARKET_OPEN.hour, minute=MARKET_OPEN.minute,
            second=0, microsecond=0
        )
        # If today's open has already passed, move to next trading day
        if now_ist >= candidate or now_ist.weekday() not in TRADING_DAYS:
            candidate += timedelta(days=1)
        # Skip weekends
        while candidate.weekday() not in TRADING_DAYS:
            candidate += timedelta(days=1)
        return candidate

    # ------------------------------------------------------------------
    # Signal generation
    # ------------------------------------------------------------------

    def generate_signals(self) -> List[Dict[str, Any]]:
        """
        Return a list of intraday signal dicts.

        - If market is open  -> uses live screener data.
        - If market is closed -> projects signals for next open from daily TF.
        """
        market_open = self.is_market_open()
        signals: List[Dict[str, Any]] = []

        if self.screener is None:
            logger.warning("StockScreener not available; returning empty signals.")
            return signals

        try:
            if market_open:
                candidates = self.screener.scan_intraday_stocks()
            else:
                # Daily timeframe projections for next open
                candidates = self.screener.scan_intraday_stocks(timeframe="daily")
        except Exception as exc:
            logger.error("screener scan failed: %s", exc)
            return signals

        base_dt = datetime.now(IST)
        if not market_open:
            base_dt = self._next_market_open_dt()
            # Start window 20 min after open for realistic entry
            base_dt = base_dt.replace(
                hour=MARKET_OPEN.hour,
                minute=MARKET_OPEN.minute + 20,
                second=0,
                microsecond=0,
            )

        for stock in candidates:
            try:
                score = float(stock.get("score", 0))
                if score < self.MIN_SCORE:
                    continue

                symbol = stock.get("symbol", "").upper()
                direction: str = stock.get("direction", "BUY").upper()
                entry_price = float(stock.get("entry_price", stock.get("ltp", 0)))

                if entry_price <= 0:
                    continue

                # Target and stop loss derived from screener or defaults
                if direction == "BUY":
                    target_price = float(
                        stock.get("target_price", entry_price * 1.015)
                    )
                    stop_loss = float(
                        stock.get("stop_loss", entry_price * 0.99)
                    )
                    card_color = "green"
                else:
                    target_price = float(
                        stock.get("target_price", entry_price * 0.985)
                    )
                    stop_loss = float(
                        stock.get("stop_loss", entry_price * 1.01)
                    )
                    card_color = "red"

                risk = abs(entry_price - stop_loss)
                reward = abs(target_price - entry_price)
                risk_reward = round(reward / risk, 2) if risk > 0 else 0.0
                confidence = round(min(score, 100.0), 2)
                quantity = max(1, int(INTRADAY_CAPITAL / entry_price))
                potential_profit = round(reward * quantity, 2)
                raw_loss = risk * quantity
                max_loss = round(min(raw_loss, self.MAX_LOSS_CAP), 2)

                # Determine if this is a scalp (news-driven, < 5 min)
                has_news_catalyst = bool(stock.get("news_catalyst") or stock.get("bulk_deal"))
                scalp_mode = has_news_catalyst and score >= 92

                # Time window: scalp = 5 min, normal = 15-30 min
                window_duration = 5 if scalp_mode else (15 if score >= 90 else 30)
                time_window = _format_time_window(base_dt, window_duration)

                reasons = self._build_reasons(stock, direction)
                timestamp = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")

                signal: Dict[str, Any] = {
                    "symbol": symbol,
                    "nse_name": _get_nse_name(symbol),
                    "signal_type": "INTRADAY",
                    "direction": direction,
                    "entry_price": round(entry_price, 2),
                    "target_price": round(target_price, 2),
                    "stop_loss": round(stop_loss, 2),
                    "risk_reward": risk_reward,
                    "confidence": confidence,
                    "time_window": time_window,
                    "capital": INTRADAY_CAPITAL,
                    "quantity": quantity,
                    "potential_profit": potential_profit,
                    "max_loss": max_loss,
                    "reasons": reasons,
                    "scalp_mode": scalp_mode,
                    "timestamp": timestamp,
                    "card_color": card_color,
                }
                signals.append(signal)

            except Exception as exc:
                logger.error("Error building intraday signal for %s: %s", stock, exc)
                continue

        # Sort: scalp signals first, then by confidence
        signals.sort(
            key=lambda s: (s["scalp_mode"], s["confidence"]),
            reverse=True,
        )
        return signals

    def get_scalp_signals(self) -> List[Dict[str, Any]]:
        """
        Return only scalp signals (scalp_mode=True).

        These are high-momentum, news-driven entries expected to resolve
        within 5 minutes of entry.
        """
        try:
            all_signals = self.generate_signals()
            return [s for s in all_signals if s.get("scalp_mode")]
        except Exception as exc:
            logger.error("get_scalp_signals failed: %s", exc)
            return []

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_reasons(self, stock: Dict[str, Any], direction: str) -> List[str]:
        """Compile trade reasons from screener flags."""
        reasons: List[str] = []
        if stock.get("breakout") and direction == "BUY":
            reasons.append("Price breakout on 5-min chart")
        if stock.get("breakdown") and direction == "SELL":
            reasons.append("Price breakdown below support")
        if stock.get("volume_surge"):
            reasons.append("Volume spike relative to 20-period average")
        if stock.get("rsi"):
            rsi = float(stock["rsi"])
            if direction == "BUY" and rsi > 60:
                reasons.append(f"RSI bullish momentum ({rsi:.1f})")
            elif direction == "SELL" and rsi < 40:
                reasons.append(f"RSI bearish momentum ({rsi:.1f})")
        if stock.get("vwap_crossover"):
            reasons.append("VWAP crossover confirming direction")
        if stock.get("news_catalyst"):
            reasons.append("Live news catalyst identified")
        if stock.get("bulk_deal"):
            reasons.append("Bulk/block deal activity in pre-market")
        if not reasons:
            reasons.append("Strong intraday momentum setup")
        return reasons
