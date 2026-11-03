"""
screener.py
-----------
StockScreener for J1 Trader.
Combines Technical, SMC, Order Flow, Fundamental, and News scores
into a single confluence score and generates trade setups.
"""

import logging
from typing import Optional

import pandas as pd

from analysis.technical import TechnicalAnalysis
from analysis.smc_analysis import SMCAnalysis
from analysis.orderflow import OrderFlowAnalysis
from analysis.fundamental import FundamentalAnalysis

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default watchlists
# ---------------------------------------------------------------------------

WATCHLIST_SWING = [
    "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK",
    "WIPRO", "AXISBANK", "SBIN", "LT", "BAJFINANCE",
    "ADANIPORTS", "TATAMOTORS", "MARUTI", "SUNPHARMA", "DRREDDY",
    "DIVISLAB", "HCLTECH", "POWERGRID", "NTPC", "ONGC",
]

WATCHLIST_INTRADAY = [
    "NIFTY50", "BANKNIFTY", "RELIANCE", "TCS", "ICICIBANK",
    "HDFCBANK", "AXISBANK", "SBIN", "LT", "BAJFINANCE",
    "TATAMOTORS", "ADANIPORTS", "WIPRO", "INFY", "SUNPHARMA",
    "COALINDIA", "HINDUNILVR", "INDUSINDBK", "TECHM", "HCLTECH",
]


class StockScreener:
    """
    Multi-factor stock screener combining Technical, SMC, Order Flow,
    Fundamental, and News scores for the Indian equity market.
    """

    # Score weights (must sum to 1.0)
    WEIGHTS = {
        "technical": 0.25,
        "smc": 0.25,
        "orderflow": 0.20,
        "fundamental": 0.15,
        "news": 0.15,
    }

    # Intraday capital assumption (INR)
    INTRADAY_CAPITAL = 30_000

    def __init__(
        self,
        swing_watchlist: list = None,
        intraday_watchlist: list = None,
    ):
        """
        Parameters
        ----------
        swing_watchlist : list or None — override default swing symbols.
        intraday_watchlist : list or None — override default intraday symbols.
        """
        self.swing_watchlist = swing_watchlist or WATCHLIST_SWING
        self.intraday_watchlist = intraday_watchlist or WATCHLIST_INTRADAY

        self.orderflow = OrderFlowAnalysis()
        self.fundamental = FundamentalAnalysis()

    # ------------------------------------------------------------------
    # Data helpers
    # ------------------------------------------------------------------

    def _fetch_ohlcv(self, symbol: str, period: str = "3mo", interval: str = "1d") -> pd.DataFrame:
        """
        Download OHLCV data from yfinance for an NSE symbol.

        Parameters
        ----------
        symbol : str
        period : str — yfinance period string.
        interval : str — yfinance interval string.

        Returns
        -------
        pd.DataFrame or empty DataFrame on error.
        """
        try:
            import yfinance as yf

            ticker_symbol = symbol.upper() + ".NS" if not symbol.endswith(".NS") else symbol
            df = yf.download(ticker_symbol, period=period, interval=interval, progress=False)
            if df is None or df.empty:
                return pd.DataFrame()

            # Flatten MultiIndex columns if present
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
            return df
        except Exception as exc:
            logger.warning("Failed to fetch OHLCV for %s: %s", symbol, exc)
            return pd.DataFrame()

    # ------------------------------------------------------------------
    # Entry / Exit calculation
    # ------------------------------------------------------------------

    def calculate_entry_exit(
        self,
        symbol: str,
        direction: str,
        current_price: float,
        atr: float,
        mode: str = "SWING",
    ) -> dict:
        """
        Calculate entry, target, and stop-loss levels.

        Modes:
            SWING  BUY : target = price * 1.08, stop = price * 0.98
            SWING  SELL: target = price * 0.92, stop = price * 1.02
            INTRADAY BUY : target = price + ATR*1.5, stop = price - ATR*0.8
            INTRADAY SELL: target = price - ATR*1.5, stop = price + ATR*0.8

        Stop is also capped so max loss <= INR 2,000 on 30,000 capital.

        Parameters
        ----------
        symbol : str
        direction : str — "BUY" | "SELL"
        current_price : float
        atr : float
        mode : str — "SWING" | "INTRADAY"

        Returns
        -------
        dict: {entry, target, stop_loss, risk_reward}
        """
        try:
            if current_price <= 0:
                return {"entry": 0.0, "target": 0.0, "stop_loss": 0.0, "risk_reward": 0.0}

            entry = current_price

            if mode == "SWING":
                if direction == "BUY":
                    target = entry * 1.08
                    stop_loss = entry * 0.98
                else:
                    target = entry * 0.92
                    stop_loss = entry * 1.02
            else:  # INTRADAY
                atr_safe = atr if atr and atr > 0 else current_price * 0.005
                if direction == "BUY":
                    target = entry + atr_safe * 1.5
                    stop_loss = entry - atr_safe * 0.8
                else:
                    target = entry - atr_safe * 1.5
                    stop_loss = entry + atr_safe * 0.8

                # Cap stop so max loss on capital <= INR 2,000
                max_loss_pct = 2_000 / self.INTRADAY_CAPITAL  # ~6.67%
                if direction == "BUY":
                    min_stop = entry * (1 - max_loss_pct)
                    stop_loss = max(stop_loss, min_stop)
                else:
                    max_stop = entry * (1 + max_loss_pct)
                    stop_loss = min(stop_loss, max_stop)

            risk = abs(entry - stop_loss)
            reward = abs(target - entry)
            risk_reward = round(reward / risk, 2) if risk > 0 else 0.0

            return {
                "entry": round(entry, 2),
                "target": round(target, 2),
                "stop_loss": round(stop_loss, 2),
                "risk_reward": risk_reward,
            }
        except Exception as exc:
            logger.warning("Entry/exit calculation error for %s: %s", symbol, exc)
            return {"entry": 0.0, "target": 0.0, "stop_loss": 0.0, "risk_reward": 0.0}

    # ------------------------------------------------------------------
    # Combined score
    # ------------------------------------------------------------------

    def get_combined_score(self, symbol: str, mode: str = "SWING") -> dict:
        """
        Compute a holistic confluence score for a symbol.

        Parameters
        ----------
        symbol : str
        mode : str — "SWING" | "INTRADAY"

        Returns
        -------
        dict: {symbol, price, technical_score, smc_score, orderflow_score,
               fundamental_score, news_score, confluence_score, direction,
               entry, target, stop_loss, risk_reward, reasons}
        """
        default = {
            "symbol": symbol,
            "price": 0.0,
            "technical_score": 0.0,
            "smc_score": 0.0,
            "orderflow_score": 0.0,
            "fundamental_score": 0.0,
            "news_score": 0.0,
            "confluence_score": 0.0,
            "direction": "NONE",
            "entry": 0.0,
            "target": 0.0,
            "stop_loss": 0.0,
            "risk_reward": 0.0,
            "reasons": [],
        }

        try:
            # Event Risk Gatekeeper: Block stock if earnings/board meeting today
            from data.events_calendar import EventsCalendar
            is_event, event_reason = EventsCalendar.is_earnings_or_event_today(symbol)
            if is_event:
                logger.warning("StockScreener: %s blocked by Event Gatekeeper (%s)", symbol, event_reason)
                default["reasons"] = [f"BLOCKED: High-Risk Event Day! {event_reason}"]
                return default

            period = "3mo" if mode == "SWING" else "5d"
            interval = "1d" if mode == "SWING" else "15m"
            df = self._fetch_ohlcv(symbol, period=period, interval=interval)

            if df.empty or len(df) < 20:
                logger.warning("Insufficient data for %s", symbol)
                return default

            current_price = float(df["Close"].iloc[-1])
            reasons = []

            # --- Technical ---
            ta = TechnicalAnalysis(df)
            tech_score = ta.get_technical_score()
            trend = ta.get_trend_direction()
            atr_series = ta.calculate_atr()
            atr = float(atr_series.iloc[-1]) if len(atr_series) > 0 else current_price * 0.01

            if trend == "BULLISH":
                reasons.append("Bullish trend on EMA/RSI")
            elif trend == "BEARISH":
                reasons.append("Bearish trend on EMA/RSI")

            # --- SMC ---
            smc = SMCAnalysis(df)
            smc_score = smc.get_smc_score()
            smc_bias = smc.get_smc_bias()
            if smc_bias != "NEUTRAL":
                reasons.append(f"SMC bias: {smc_bias}")

            # --- Order Flow ---
            of_score = self.orderflow.get_orderflow_score(df)
            inst = self.orderflow.detect_institutional_footprint(df)
            if inst["detected"]:
                reasons.append(f"Institutional {inst['direction']} detected (conf={inst['confidence']:.0f}%)")

            # --- Fundamental ---
            fund_score = self.fundamental.get_fundamental_score(symbol)
            if fund_score >= 60:
                reasons.append("Strong fundamentals")
            elif fund_score <= 30:
                reasons.append("Weak fundamentals")

            # --- News score (placeholder — 0 or 20) ---
            # In production this would query a news API.
            news_score = 0.0  # default neutral

            # --- Weighted confluence ---
            confluence = (
                tech_score * self.WEIGHTS["technical"]
                + smc_score * self.WEIGHTS["smc"]
                + of_score * self.WEIGHTS["orderflow"]
                + fund_score * self.WEIGHTS["fundamental"]
                + news_score * self.WEIGHTS["news"]
            )

            # --- Direction ---
            bull_votes = sum([
                trend == "BULLISH",
                smc_bias == "BULLISH",
                inst.get("direction") == "BUY",
            ])
            direction = "BUY" if bull_votes >= 2 else "SELL"

            # --- Entry / Exit ---
            levels = self.calculate_entry_exit(
                symbol, direction, current_price, atr, mode
            )

            if levels["risk_reward"] >= 2:
                reasons.append(f"Good R:R = {levels['risk_reward']}")

            return {
                "symbol": symbol,
                "price": round(current_price, 2),
                "technical_score": tech_score,
                "smc_score": smc_score,
                "orderflow_score": of_score,
                "fundamental_score": fund_score,
                "news_score": news_score,
                "confluence_score": round(confluence, 2),
                "direction": direction,
                "entry": levels["entry"],
                "target": levels["target"],
                "stop_loss": levels["stop_loss"],
                "risk_reward": levels["risk_reward"],
                "reasons": reasons,
            }

        except Exception as exc:
            logger.error("get_combined_score error for %s: %s", symbol, exc)
            return default

    # ------------------------------------------------------------------
    # Screeners
    # ------------------------------------------------------------------

    def scan_swing_stocks(self) -> list:
        """
        Scan WATCHLIST_SWING for high-conviction swing trade setups.

        Returns
        -------
        list of dicts (top 15, confluence_score >= 90), sorted descending.
        """
        results = []
        for symbol in self.swing_watchlist:
            try:
                result = self.get_combined_score(symbol, mode="SWING")
                if result["confluence_score"] >= 90:
                    results.append(result)
            except Exception as exc:
                logger.warning("scan_swing error for %s: %s", symbol, exc)

        results.sort(key=lambda x: x["confluence_score"], reverse=True)
        return results[:15]

    def scan_intraday_stocks(self) -> list:
        """
        Scan WATCHLIST_INTRADAY for intraday trade setups.

        Returns
        -------
        list of dicts (top 15, confluence_score >= 88), sorted descending.
        """
        results = []
        for symbol in self.intraday_watchlist:
            try:
                result = self.get_combined_score(symbol, mode="INTRADAY")
                if result["confluence_score"] >= 88:
                    results.append(result)
            except Exception as exc:
                logger.warning("scan_intraday error for %s: %s", symbol, exc)

        results.sort(key=lambda x: x["confluence_score"], reverse=True)
        return results[:15]
