"""
smc_analysis.py
---------------
Smart Money Concepts (SMC) analysis for J1 Trader.
Detects Order Blocks, Fair Value Gaps, Liquidity Sweeps,
Change of Character (CHoCH), Break of Structure (BOS),
and Premium/Discount Zones.
"""

import numpy as np
import pandas as pd


class SMCAnalysis:
    """Smart Money Concepts analysis on a pandas OHLCV DataFrame."""

    def __init__(self, df: pd.DataFrame):
        """
        Parameters
        ----------
        df : pd.DataFrame
            Must contain columns: Open, High, Low, Close, Volume
        """
        self.df = df.copy().reset_index(drop=True)

    # ------------------------------------------------------------------
    # Helper utilities
    # ------------------------------------------------------------------

    def _is_bullish(self, i: int) -> bool:
        return float(self.df["Close"].iloc[i]) > float(self.df["Open"].iloc[i])

    def _is_bearish(self, i: int) -> bool:
        return float(self.df["Close"].iloc[i]) < float(self.df["Open"].iloc[i])

    def _body_size(self, i: int) -> float:
        return abs(float(self.df["Close"].iloc[i]) - float(self.df["Open"].iloc[i]))

    def _candle_range(self, i: int) -> float:
        return float(self.df["High"].iloc[i]) - float(self.df["Low"].iloc[i])

    # ------------------------------------------------------------------
    # Order Blocks
    # ------------------------------------------------------------------

    def find_order_blocks(self, lookback: int = 50) -> list:
        """
        Identify bullish and bearish order blocks.

        Bullish OB : last bearish candle before a strong bullish displacement.
        Bearish OB : last bullish candle before a strong bearish displacement.

        Parameters
        ----------
        lookback : int

        Returns
        -------
        list of dict: {type, high, low, index, strength}
        """
        try:
            df = self.df
            n = len(df)
            start = max(0, n - lookback)
            order_blocks = []

            avg_body = df["Close"].diff().abs().rolling(20).mean()

            for i in range(start + 1, n - 1):
                body = self._body_size(i)
                next_body = self._body_size(i + 1)
                avg = float(avg_body.iloc[i]) if not pd.isna(avg_body.iloc[i]) else body

                # Displacement threshold: next candle body > 1.5x average body
                is_displacement = next_body > 1.5 * avg

                if self._is_bearish(i) and self._is_bullish(i + 1) and is_displacement:
                    strength = round(next_body / max(body, 1e-9), 2)
                    order_blocks.append({
                        "type": "BULLISH",
                        "high": float(df["High"].iloc[i]),
                        "low": float(df["Low"].iloc[i]),
                        "index": i,
                        "strength": strength,
                    })

                if self._is_bullish(i) and self._is_bearish(i + 1) and is_displacement:
                    strength = round(next_body / max(body, 1e-9), 2)
                    order_blocks.append({
                        "type": "BEARISH",
                        "high": float(df["High"].iloc[i]),
                        "low": float(df["Low"].iloc[i]),
                        "index": i,
                        "strength": strength,
                    })

            return order_blocks
        except Exception:
            return []

    # ------------------------------------------------------------------
    # Fair Value Gaps
    # ------------------------------------------------------------------

    def find_fair_value_gaps(self, lookback: int = 30) -> list:
        """
        Identify Fair Value Gaps (FVGs) using a 3-candle pattern.

        Bullish FVG : candle[i-1].high < candle[i+1].low
        Bearish FVG : candle[i-1].low > candle[i+1].high

        Parameters
        ----------
        lookback : int

        Returns
        -------
        list of dict: {type, gap_high, gap_low, index, filled}
        """
        try:
            df = self.df
            n = len(df)
            start = max(1, n - lookback)
            fvgs = []
            last_close = float(df["Close"].iloc[-1])

            for i in range(start, n - 1):
                prev_high = float(df["High"].iloc[i - 1])
                prev_low = float(df["Low"].iloc[i - 1])
                next_high = float(df["High"].iloc[i + 1])
                next_low = float(df["Low"].iloc[i + 1])

                # Bullish FVG
                if prev_high < next_low:
                    filled = last_close <= prev_high or last_close <= next_low
                    fvgs.append({
                        "type": "BULLISH",
                        "gap_high": next_low,
                        "gap_low": prev_high,
                        "index": i,
                        "filled": filled,
                    })

                # Bearish FVG
                if prev_low > next_high:
                    filled = last_close >= prev_low or last_close >= next_high
                    fvgs.append({
                        "type": "BEARISH",
                        "gap_high": prev_low,
                        "gap_low": next_high,
                        "index": i,
                        "filled": filled,
                    })

            return fvgs
        except Exception:
            return []

    # ------------------------------------------------------------------
    # Liquidity Sweeps
    # ------------------------------------------------------------------

    def find_liquidity_sweeps(self, lookback: int = 30) -> list:
        """
        Detect liquidity sweeps (turtle soup): price briefly breaks
        a previous swing high/low then reverses.

        Parameters
        ----------
        lookback : int

        Returns
        -------
        list of dict: {type, level, index, swept}
        """
        try:
            df = self.df
            n = len(df)
            start = max(2, n - lookback)
            sweeps = []

            for i in range(start, n - 1):
                # Previous swing high/low using a simple 3-bar pivot
                swing_high = float(df["High"].iloc[i - 1])
                swing_low = float(df["Low"].iloc[i - 1])

                curr_high = float(df["High"].iloc[i])
                curr_low = float(df["Low"].iloc[i])
                curr_close = float(df["Close"].iloc[i])
                next_close = float(df["Close"].iloc[i + 1])

                # Sweep of highs: wick above swing high but closes below it
                if curr_high > swing_high and curr_close < swing_high:
                    swept = next_close < curr_close  # reversal confirmed
                    sweeps.append({
                        "type": "BEARISH_SWEEP",
                        "level": swing_high,
                        "index": i,
                        "swept": swept,
                    })

                # Sweep of lows: wick below swing low but closes above it
                if curr_low < swing_low and curr_close > swing_low:
                    swept = next_close > curr_close  # reversal confirmed
                    sweeps.append({
                        "type": "BULLISH_SWEEP",
                        "level": swing_low,
                        "index": i,
                        "swept": swept,
                    })

            return sweeps
        except Exception:
            return []

    # ------------------------------------------------------------------
    # Change of Character (CHoCH)
    # ------------------------------------------------------------------

    def find_choch(self) -> dict:
        """
        Detect Change of Character: first structural break in the opposite
        direction of the current trend.

        Returns
        -------
        dict: {detected, type, level, index}
        """
        try:
            df = self.df
            n = len(df)
            if n < 10:
                return {"detected": False, "type": "NONE", "level": 0.0, "index": -1}

            # Determine recent trend from first half of window
            mid = n // 2
            trend_up = float(df["Close"].iloc[mid]) > float(df["Close"].iloc[0])

            # Scan second half for opposite structural break
            for i in range(mid + 1, n):
                if trend_up:
                    # Looking for break below recent swing low
                    recent_low = float(df["Low"].iloc[mid:i].min())
                    if float(df["Close"].iloc[i]) < recent_low:
                        return {
                            "detected": True,
                            "type": "BEARISH",
                            "level": recent_low,
                            "index": i,
                        }
                else:
                    # Looking for break above recent swing high
                    recent_high = float(df["High"].iloc[mid:i].max())
                    if float(df["Close"].iloc[i]) > recent_high:
                        return {
                            "detected": True,
                            "type": "BULLISH",
                            "level": recent_high,
                            "index": i,
                        }

            return {"detected": False, "type": "NONE", "level": 0.0, "index": -1}
        except Exception:
            return {"detected": False, "type": "NONE", "level": 0.0, "index": -1}

    # ------------------------------------------------------------------
    # Break of Structure (BOS)
    # ------------------------------------------------------------------

    def find_bos(self) -> list:
        """
        Identify Break of Structure: continuation structural breaks
        in the direction of the existing trend.

        Returns
        -------
        list of dict: {type, level, index}
        """
        try:
            df = self.df
            n = len(df)
            bos_list = []
            window = 5

            for i in range(window, n):
                segment = df.iloc[i - window:i]
                swing_high = float(segment["High"].max())
                swing_low = float(segment["Low"].min())
                curr_close = float(df["Close"].iloc[i])

                # Bullish BOS: close breaks above recent swing high
                if curr_close > swing_high:
                    bos_list.append({"type": "BULLISH", "level": swing_high, "index": i})

                # Bearish BOS: close breaks below recent swing low
                elif curr_close < swing_low:
                    bos_list.append({"type": "BEARISH", "level": swing_low, "index": i})

            return bos_list[-10:]  # Return last 10 BOS events
        except Exception:
            return []

    # ------------------------------------------------------------------
    # Premium / Discount Zones
    # ------------------------------------------------------------------

    def find_premium_discount_zones(self) -> dict:
        """
        Compute Premium and Discount zones based on the most recent
        major swing range (last 50 candles or full dataset).

        Returns
        -------
        dict: {premium_zone_high, premium_zone_low,
               discount_zone_high, discount_zone_low, equilibrium}
        """
        try:
            df = self.df.tail(50)
            swing_high = float(df["High"].max())
            swing_low = float(df["Low"].min())
            total_range = swing_high - swing_low
            equilibrium = swing_low + total_range * 0.5
            premium_low = swing_low + total_range * 0.618
            discount_high = swing_low + total_range * 0.382

            return {
                "premium_zone_high": round(swing_high, 2),
                "premium_zone_low": round(premium_low, 2),
                "discount_zone_high": round(discount_high, 2),
                "discount_zone_low": round(swing_low, 2),
                "equilibrium": round(equilibrium, 2),
            }
        except Exception:
            return {
                "premium_zone_high": 0.0,
                "premium_zone_low": 0.0,
                "discount_zone_high": 0.0,
                "discount_zone_low": 0.0,
                "equilibrium": 0.0,
            }

    # ------------------------------------------------------------------
    # Bias
    # ------------------------------------------------------------------

    def get_smc_bias(self) -> str:
        """
        Determine overall SMC directional bias.

        Returns
        -------
        str: "BULLISH" | "BEARISH" | "NEUTRAL"
        """
        try:
            score = self.get_smc_score()
            if score >= 60:
                return "BULLISH"
            elif score <= 30:
                return "BEARISH"
            return "NEUTRAL"
        except Exception:
            return "NEUTRAL"

    # ------------------------------------------------------------------
    # Composite score
    # ------------------------------------------------------------------

    def get_smc_score(self) -> float:
        """
        Composite SMC score (0-100).

        Scoring:
            +20 price in discount zone + bullish OB nearby
            +20 bullish FVG present and unfilled
            +20 liquidity sweep of lows + reversal
            +20 CHoCH to bullish
            +20 BOS confirmed bullish

        Returns
        -------
        float
        """
        score = 0.0
        try:
            last_close = float(self.df["Close"].iloc[-1])
            zones = self.find_premium_discount_zones()
            obs = self.find_order_blocks()
            fvgs = self.find_fair_value_gaps()
            sweeps = self.find_liquidity_sweeps()
            choch = self.find_choch()
            bos_list = self.find_bos()

            # +20 discount zone + bullish OB nearby
            in_discount = (
                zones["discount_zone_low"] <= last_close <= zones["discount_zone_high"]
            )
            has_bullish_ob = any(
                ob["type"] == "BULLISH" and ob["low"] <= last_close <= ob["high"] * 1.01
                for ob in obs
            )
            if in_discount and has_bullish_ob:
                score += 20
            elif in_discount or has_bullish_ob:
                score += 10

            # +20 bullish FVG present and unfilled
            unfilled_bullish_fvgs = [
                f for f in fvgs if f["type"] == "BULLISH" and not f["filled"]
            ]
            if unfilled_bullish_fvgs:
                score += 20

            # +20 liquidity sweep of lows + reversal
            bullish_sweeps = [s for s in sweeps if s["type"] == "BULLISH_SWEEP" and s["swept"]]
            if bullish_sweeps:
                score += 20

            # +20 CHoCH to bullish
            if choch["detected"] and choch["type"] == "BULLISH":
                score += 20

            # +20 BOS confirmed bullish (recent)
            recent_bos = bos_list[-3:] if bos_list else []
            if any(b["type"] == "BULLISH" for b in recent_bos):
                score += 20

        except Exception:
            pass

        return round(min(score, 100.0), 2)
