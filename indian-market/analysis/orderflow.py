"""
orderflow.py
------------
Order Flow Analysis for J1 Trader.
Approximates institutional activity, volume delta, absorption,
and cumulative volume delta from OHLCV data.
"""

import numpy as np
import pandas as pd


class OrderFlowAnalysis:
    """Approximate order flow signals from OHLCV data."""

    # ------------------------------------------------------------------
    # Cumulative Volume Delta
    # ------------------------------------------------------------------

    def calculate_cvd(self, df: pd.DataFrame) -> pd.Series:
        """
        Cumulative Volume Delta (CVD).

        Approximation: bullish candles (close > open) add volume;
        bearish candles subtract volume.

        Parameters
        ----------
        df : pd.DataFrame
            OHLCV DataFrame.

        Returns
        -------
        pd.Series — cumulative volume delta over the entire series.
        """
        try:
            direction = np.where(df["Close"] >= df["Open"], 1, -1)
            delta = direction * df["Volume"]
            cvd = delta.cumsum()
            cvd.name = "CVD"
            return cvd
        except Exception:
            return pd.Series(dtype=float)

    # ------------------------------------------------------------------
    # Volume Delta per candle
    # ------------------------------------------------------------------

    def calculate_volume_delta(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Estimate buy and sell volume per candle.

        Method:
            body_pct = |close - open| / (high - low + epsilon)
            If bullish: buy_vol = volume * (0.5 + body_pct/2), sell_vol = remainder
            If bearish: sell_vol = volume * (0.5 + body_pct/2), buy_vol = remainder

        Parameters
        ----------
        df : pd.DataFrame

        Returns
        -------
        pd.DataFrame with columns: buy_vol, sell_vol, delta
        """
        try:
            candle_range = (df["High"] - df["Low"]).replace(0, np.nan)
            body = (df["Close"] - df["Open"]).abs()
            body_pct = (body / candle_range).fillna(0).clip(0, 1)

            is_bullish = df["Close"] >= df["Open"]
            buy_ratio = np.where(is_bullish, 0.5 + body_pct / 2, 0.5 - body_pct / 2)
            sell_ratio = 1 - buy_ratio

            buy_vol = df["Volume"] * buy_ratio
            sell_vol = df["Volume"] * sell_ratio
            delta = buy_vol - sell_vol

            result = pd.DataFrame(
                {"buy_vol": buy_vol, "sell_vol": sell_vol, "delta": delta},
                index=df.index,
            )
            return result
        except Exception:
            return pd.DataFrame(columns=["buy_vol", "sell_vol", "delta"])

    # ------------------------------------------------------------------
    # Absorption
    # ------------------------------------------------------------------

    def detect_absorption(self, df: pd.DataFrame, lookback: int = 10) -> dict:
        """
        Detect absorption: high volume with a small candle body indicates
        that aggressive orders were absorbed by passive limit orders.

        Parameters
        ----------
        df : pd.DataFrame
        lookback : int — number of recent candles to scan.

        Returns
        -------
        dict: {bullish_absorption, bearish_absorption, strength}
        """
        try:
            window = df.tail(lookback).copy()
            avg_vol = df["Volume"].rolling(20).mean().iloc[-1]
            if pd.isna(avg_vol) or avg_vol == 0:
                avg_vol = df["Volume"].mean()

            avg_body = (df["Close"] - df["Open"]).abs().rolling(20).mean().iloc[-1]
            if pd.isna(avg_body) or avg_body == 0:
                avg_body = (df["Close"] - df["Open"]).abs().mean()

            bullish_absorption = False
            bearish_absorption = False
            strength = 0.0

            for i in range(len(window)):
                vol = float(window["Volume"].iloc[i])
                body = abs(float(window["Close"].iloc[i]) - float(window["Open"].iloc[i]))
                is_high_vol = vol > 1.5 * avg_vol
                is_small_body = body < 0.5 * avg_body

                if is_high_vol and is_small_body:
                    vol_ratio = vol / max(avg_vol, 1)
                    strength = max(strength, round(min(vol_ratio / 3.0, 1.0) * 100, 2))
                    if float(window["Close"].iloc[i]) >= float(window["Open"].iloc[i]):
                        bullish_absorption = True
                    else:
                        bearish_absorption = True

            return {
                "bullish_absorption": bullish_absorption,
                "bearish_absorption": bearish_absorption,
                "strength": strength,
            }
        except Exception:
            return {"bullish_absorption": False, "bearish_absorption": False, "strength": 0.0}

    # ------------------------------------------------------------------
    # Institutional Footprint
    # ------------------------------------------------------------------

    def detect_institutional_footprint(self, df: pd.DataFrame) -> dict:
        """
        Detect potential institutional participation via large volume spikes
        combined with price continuation in the same direction.

        Parameters
        ----------
        df : pd.DataFrame

        Returns
        -------
        dict: {detected, direction, confidence}
        """
        try:
            avg_vol = df["Volume"].rolling(20).mean()
            last_vol = float(df["Volume"].iloc[-1])
            last_avg = float(avg_vol.iloc[-1]) if not pd.isna(avg_vol.iloc[-1]) else float(df["Volume"].mean())

            vol_ratio = last_vol / max(last_avg, 1)
            is_spike = vol_ratio >= 2.0

            if not is_spike:
                return {"detected": False, "direction": "NEUTRAL", "confidence": 0.0}

            # Check price continuation in last 3 candles
            last3 = df.tail(3)
            net_move = float(last3["Close"].iloc[-1]) - float(last3["Open"].iloc[0])
            is_bullish = net_move > 0

            confidence = round(min(vol_ratio / 5.0, 1.0) * 100, 2)

            return {
                "detected": True,
                "direction": "BUY" if is_bullish else "SELL",
                "confidence": confidence,
            }
        except Exception:
            return {"detected": False, "direction": "NEUTRAL", "confidence": 0.0}

    # ------------------------------------------------------------------
    # Delivery Strength (NSE-specific)
    # ------------------------------------------------------------------

    def calculate_delivery_strength(self, delivery_pct: float) -> float:
        """
        Score based on NSE delivery percentage.

        delivery_pct > 70 : very strong institutional conviction
        delivery_pct > 50 : strong
        delivery_pct > 30 : moderate
        otherwise         : weak

        Parameters
        ----------
        delivery_pct : float  (0-100)

        Returns
        -------
        float  (0-100)
        """
        try:
            if delivery_pct is None or delivery_pct < 0:
                return 50.0
            if delivery_pct >= 70:
                return 100.0
            elif delivery_pct >= 50:
                return 75.0
            elif delivery_pct >= 30:
                return 50.0
            return 25.0
        except Exception:
            return 50.0

    # ------------------------------------------------------------------
    # Volume Climax
    # ------------------------------------------------------------------

    def detect_volume_climax(self, df: pd.DataFrame) -> bool:
        """
        Detect a volume climax event (potential reversal signal).

        Condition: latest candle volume > 3x 20-period average.

        Parameters
        ----------
        df : pd.DataFrame

        Returns
        -------
        bool
        """
        try:
            avg_vol = df["Volume"].rolling(20).mean().iloc[-1]
            last_vol = float(df["Volume"].iloc[-1])
            if pd.isna(avg_vol) or avg_vol == 0:
                return False
            return last_vol > 3.0 * avg_vol
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Composite score
    # ------------------------------------------------------------------

    def get_orderflow_score(self, df: pd.DataFrame, delivery_pct: float = None) -> float:
        """
        Composite order flow score (0-100).

        Scoring breakdown:
            +25 institutional footprint detected (BUY direction)
            +20 bullish absorption
            +20 CVD rising (positive trend over last 10 bars)
            +15 delivery strength > 50
            +10 no volume climax (climax = potential reversal = risky)
            +10 volume delta positive (more buying than selling)

        Parameters
        ----------
        df : pd.DataFrame
        delivery_pct : float or None

        Returns
        -------
        float
        """
        score = 0.0
        try:
            inst = self.detect_institutional_footprint(df)
            absorption = self.detect_absorption(df)
            cvd = self.calculate_cvd(df)
            climax = self.detect_volume_climax(df)
            vol_delta_df = self.calculate_volume_delta(df)

            # +25 institutional BUY footprint
            if inst["detected"] and inst["direction"] == "BUY":
                score += 25
            elif inst["detected"]:
                score += 10  # SELL detected — partial

            # +20 bullish absorption
            if absorption["bullish_absorption"]:
                score += 20

            # +20 CVD rising
            if len(cvd) >= 10:
                cvd_recent = cvd.iloc[-10:]
                if float(cvd_recent.iloc[-1]) > float(cvd_recent.iloc[0]):
                    score += 20

            # +15 delivery strength
            if delivery_pct is not None:
                d_score = self.calculate_delivery_strength(delivery_pct)
                score += (d_score / 100) * 15

            # +10 no climax (climax often signals exhaustion)
            if not climax:
                score += 10

            # +10 positive volume delta on last candle
            if len(vol_delta_df) > 0:
                last_delta = float(vol_delta_df["delta"].iloc[-1])
                if last_delta > 0:
                    score += 10

        except Exception:
            pass

        return round(min(score, 100.0), 2)
