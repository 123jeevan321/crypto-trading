# -*- coding: utf-8 -*-
"""
Swing Signal Engine for J1 Trader Indian Stock Market Portal.
Generates multi-day swing trade signals from screener results.
"""

import sys
import os
import logging
from datetime import datetime
from typing import List, Dict, Any

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

# NSE company name mapping (symbol -> full name)
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
    "ONGC": "Oil and Natural Gas Corporation Ltd",
    "NTPC": "NTPC Ltd",
    "JSWSTEEL": "JSW Steel Ltd",
    "TATASTEEL": "Tata Steel Ltd",
    "HINDALCO": "Hindalco Industries Ltd",
    "ADANIENT": "Adani Enterprises Ltd",
    "ADANIPORTS": "Adani Ports and Special Economic Zone Ltd",
    "TECHM": "Tech Mahindra Ltd",
    "HCLTECH": "HCL Technologies Ltd",
    "DRREDDY": "Dr. Reddys Laboratories Ltd",
}


def _get_nse_name(symbol: str) -> str:
    """Return full NSE company name or derive a readable form."""
    return NSE_COMPANY_NAMES.get(symbol.upper(), f"{symbol} Ltd")


class SwingSignalEngine:
    """
    Generates swing trade signals for Indian equities listed on NSE.

    Swing signals are multi-day (1-7 days) BUY recommendations derived
    from the StockScreener scan and enriched with news catalysts.
    """

    DEFAULT_CAPITAL = 100_000  # INR 1,00,000 per trade
    MIN_SCORE = 90             # Screener score threshold

    def __init__(self):
        self.screener = StockScreener() if StockScreener is not None else None
        self.news_fetcher = NewsFetcher() if NewsFetcher is not None else None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_signals(self) -> List[Dict[str, Any]]:
        """
        Scan stocks and return a list of swing trade signal dicts.

        Returns an empty list on any failure.
        """
        signals: List[Dict[str, Any]] = []

        if self.screener is None:
            logger.warning("StockScreener not available; returning empty signals.")
            return signals

        try:
            candidates = self.screener.scan_swing_stocks()
        except Exception as exc:
            logger.error("screener.scan_swing_stocks() failed: %s", exc)
            return signals

        for stock in candidates:
            try:
                score = float(stock.get("score", 0))
                if score < self.MIN_SCORE:
                    continue

                symbol = stock.get("symbol", "").upper()
                entry_price = float(stock.get("entry_price", stock.get("ltp", 0)))
                target_price = float(stock.get("target_price", entry_price * 1.05))
                stop_loss = float(stock.get("stop_loss", entry_price * 0.97))
                volatility = float(stock.get("volatility", 2.0))  # percentage

                if entry_price <= 0:
                    continue

                risk = entry_price - stop_loss
                reward = target_price - entry_price
                risk_reward = round(reward / risk, 2) if risk > 0 else 0.0
                confidence = round(min(score, 100.0), 2)
                quantity = max(1, int(self.DEFAULT_CAPITAL / entry_price))
                potential_profit = round((target_price - entry_price) * quantity, 2)
                raw_loss = (entry_price - stop_loss) * quantity
                max_loss = round(min(raw_loss, 2000.0), 2)
                holding_period = self.calculate_holding_period(volatility, score)

                reasons = self._build_reasons(stock)
                catalyst = self._build_catalyst(stock, symbol)
                timestamp = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")

                signal: Dict[str, Any] = {
                    "symbol": symbol,
                    "nse_name": _get_nse_name(symbol),
                    "signal_type": "SWING",
                    "direction": "BUY",
                    "entry_price": round(entry_price, 2),
                    "target_price": round(target_price, 2),
                    "stop_loss": round(stop_loss, 2),
                    "risk_reward": risk_reward,
                    "confidence": confidence,
                    "holding_period": holding_period,
                    "capital": self.DEFAULT_CAPITAL,
                    "quantity": quantity,
                    "potential_profit": potential_profit,
                    "max_loss": max_loss,
                    "reasons": reasons,
                    "catalyst": catalyst,
                    "timestamp": timestamp,
                    "card_color": "green",
                }
                signals.append(signal)

            except Exception as exc:
                logger.error("Error building swing signal for %s: %s", stock, exc)
                continue

        signals.sort(key=lambda s: s["confidence"], reverse=True)
        return signals

    def get_signal_summary(self) -> str:
        """Return a human-readable summary of current swing signals."""
        try:
            signals = self.generate_signals()
            if not signals:
                return "No swing signals available at this time."

            lines = [
                f"=== Swing Trade Signals ({datetime.now(IST).strftime('%d-%b-%Y %H:%M IST')}) ===",
                f"Total Signals: {len(signals)}",
                "",
            ]
            for i, sig in enumerate(signals, 1):
                lines.append(
                    f"[{i}] {sig['symbol']} | {sig['nse_name']}"
                    f"\n    Entry: Rs.{sig['entry_price']}"
                    f" | Target: Rs.{sig['target_price']}"
                    f" | SL: Rs.{sig['stop_loss']}"
                    f"\n    R:R = {sig['risk_reward']} | Confidence: {sig['confidence']}%"
                    f" | Hold: {sig['holding_period']}"
                    f"\n    Catalyst: {sig['catalyst']}"
                    f"\n    Qty: {sig['quantity']} | Profit: Rs.{sig['potential_profit']}"
                    f" | Max Loss: Rs.{sig['max_loss']}"
                )
            return "\n".join(lines)
        except Exception as exc:
            logger.error("get_signal_summary failed: %s", exc)
            return "Error generating signal summary."

    @staticmethod
    def calculate_holding_period(volatility: float, score: float) -> str:
        """
        Determine holding period based on volatility and score.

        Returns "1-2 Days" for high-conviction, high-volatility setups,
        otherwise "3-7 Days" for lower-velocity trades.
        """
        if score > 95 and volatility > 3.0:
            return "1-2 Days"
        return "3-7 Days"

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_reasons(self, stock: Dict[str, Any]) -> List[str]:
        """Compile a list of trade reasons from screener data."""
        reasons: List[str] = []
        if stock.get("breakout"):
            reasons.append("Price breakout above resistance")
        if stock.get("volume_surge"):
            reasons.append("Significant volume surge detected")
        if stock.get("rsi"):
            rsi = float(stock["rsi"])
            if 55 <= rsi <= 75:
                reasons.append(f"RSI in momentum zone ({rsi:.1f})")
        if stock.get("macd_crossover"):
            reasons.append("Bullish MACD crossover")
        if stock.get("order_block"):
            reasons.append("Strong demand order block identified")
        if stock.get("fii_buying"):
            reasons.append("FII net buying interest")
        if stock.get("bulk_deal"):
            reasons.append("Bulk deal activity detected")
        if not reasons:
            reasons.append("Strong technical setup on daily chart")
        return reasons

    def _build_catalyst(self, stock: Dict[str, Any], symbol: str) -> str:
        """Derive a short catalyst string from screener flags and news."""
        parts: List[str] = []
        if stock.get("bulk_deal"):
            parts.append("Bulk Deal")
        if stock.get("order_block"):
            parts.append("Order Block")
        if stock.get("fii_buying"):
            parts.append("FII Buying")
        if stock.get("breakout"):
            parts.append("Breakout")

        # Optionally enrich from news
        if self.news_fetcher is not None:
            try:
                headlines = self.news_fetcher.get_latest(symbol, limit=1)
                if headlines:
                    parts.append("News Catalyst")
            except Exception:
                pass

        return " + ".join(parts) if parts else "Technical Setup"
