"""
technical.py
------------
TechnicalAnalysis class for J1 Trader.
Calculates common technical indicators on OHLCV DataFrames.
"""

import numpy as np
import pandas as pd


class TechnicalAnalysis:
    """Compute technical indicators on a pandas OHLCV DataFrame."""

    def __init__(self, df: pd.DataFrame):
        """
        Parameters
        ----------
        df : pd.DataFrame
            Must contain columns: Open, High, Low, Close, Volume
        """
        self.df = df.copy()
        self._validate()

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate(self):
        required = {"Open", "High", "Low", "Close", "Volume"}
        missing = required - set(self.df.columns)
        if missing:
            raise ValueError(f"DataFrame missing columns: {missing}")

    # ------------------------------------------------------------------
    # Core indicators
    # ------------------------------------------------------------------

    def calculate_ema(self, period: int) -> pd.Series:
        """
        Exponential Moving Average.

        Parameters
        ----------
        period : int
            Look-back window.

        Returns
        -------
        pd.Series
        """
        try:
            return self.df["Close"].ewm(span=period, adjust=False).mean()
        except Exception:
            return pd.Series(dtype=float)

    def calculate_rsi(self, period: int = 14) -> pd.Series:
        """
        Relative Strength Index (0-100).

        Parameters
        ----------
        period : int

        Returns
        -------
        pd.Series
        """
        try:
            delta = self.df["Close"].diff()
            gain = delta.clip(lower=0)
            loss = -delta.clip(upper=0)
            avg_gain = gain.ewm(com=period - 1, adjust=False).mean()
            avg_loss = loss.ewm(com=period - 1, adjust=False).mean()
            rs = avg_gain / avg_loss.replace(0, np.nan)
            rsi = 100 - (100 / (1 + rs))
            return rsi.fillna(50)
        except Exception:
            return pd.Series(dtype=float)

    def calculate_macd(self) -> dict:
        """
        MACD (12-26-9).

        Returns
        -------
        dict with keys: macd_line, signal_line, histogram (all pd.Series)
        """
        try:
            ema12 = self.df["Close"].ewm(span=12, adjust=False).mean()
            ema26 = self.df["Close"].ewm(span=26, adjust=False).mean()
            macd_line = ema12 - ema26
            signal_line = macd_line.ewm(span=9, adjust=False).mean()
            histogram = macd_line - signal_line
            return {
                "macd_line": macd_line,
                "signal_line": signal_line,
                "histogram": histogram,
            }
        except Exception:
            empty = pd.Series(dtype=float)
            return {"macd_line": empty, "signal_line": empty, "histogram": empty}

    def calculate_bollinger_bands(self, period: int = 20, std: float = 2) -> dict:
        """
        Bollinger Bands.

        Returns
        -------
        dict with keys: upper, middle, lower (pd.Series), squeeze (bool)
        """
        try:
            middle = self.df["Close"].rolling(window=period).mean()
            rolling_std = self.df["Close"].rolling(window=period).std()
            upper = middle + std * rolling_std
            lower = middle - std * rolling_std

            # Squeeze: bandwidth below 20-period average bandwidth
            bandwidth = (upper - lower) / middle
            avg_bandwidth = bandwidth.rolling(window=period).mean()
            squeeze = bool(bandwidth.iloc[-1] < avg_bandwidth.iloc[-1]) if len(bandwidth) >= period else False

            return {"upper": upper, "middle": middle, "lower": lower, "squeeze": squeeze}
        except Exception:
            empty = pd.Series(dtype=float)
            return {"upper": empty, "middle": empty, "lower": empty, "squeeze": False}

    def calculate_vwap(self) -> pd.Series:
        """
        Intraday VWAP (Volume Weighted Average Price).

        Returns
        -------
        pd.Series
        """
        try:
            typical_price = (self.df["High"] + self.df["Low"] + self.df["Close"]) / 3
            cumulative_tp_vol = (typical_price * self.df["Volume"]).cumsum()
            cumulative_vol = self.df["Volume"].cumsum()
            vwap = cumulative_tp_vol / cumulative_vol
            return vwap
        except Exception:
            return pd.Series(dtype=float)

    def calculate_atr(self, period: int = 14) -> pd.Series:
        """
        Average True Range.

        Parameters
        ----------
        period : int

        Returns
        -------
        pd.Series
        """
        try:
            high_low = self.df["High"] - self.df["Low"]
            high_close = (self.df["High"] - self.df["Close"].shift(1)).abs()
            low_close = (self.df["Low"] - self.df["Close"].shift(1)).abs()
            tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            atr = tr.ewm(com=period - 1, adjust=False).mean()
            return atr
        except Exception:
            return pd.Series(dtype=float)

    def calculate_supertrend(self, period: int = 10, multiplier: float = 3) -> dict:
        """
        SuperTrend indicator.

        Returns
        -------
        dict with keys: supertrend (pd.Series), direction (pd.Series: 1=bullish, -1=bearish)
        """
        try:
            hl2 = (self.df["High"] + self.df["Low"]) / 2
            atr = self.calculate_atr(period)

            upper_band = hl2 + multiplier * atr
            lower_band = hl2 - multiplier * atr

            supertrend = pd.Series(index=self.df.index, dtype=float)
            direction = pd.Series(index=self.df.index, dtype=int)

            close = self.df["Close"]

            for i in range(1, len(self.df)):
                prev_upper = upper_band.iloc[i - 1]
                prev_lower = lower_band.iloc[i - 1]
                curr_upper = upper_band.iloc[i]
                curr_lower = lower_band.iloc[i]

                # Adjust bands
                upper_band.iloc[i] = (
                    curr_upper if curr_upper < prev_upper or close.iloc[i - 1] > prev_upper else prev_upper
                )
                lower_band.iloc[i] = (
                    curr_lower if curr_lower > prev_lower or close.iloc[i - 1] < prev_lower else prev_lower
                )

                prev_dir = direction.iloc[i - 1] if i > 1 else 1
                if prev_dir == -1 and close.iloc[i] > upper_band.iloc[i]:
                    direction.iloc[i] = 1
                elif prev_dir == 1 and close.iloc[i] < lower_band.iloc[i]:
                    direction.iloc[i] = -1
                else:
                    direction.iloc[i] = prev_dir

                supertrend.iloc[i] = lower_band.iloc[i] if direction.iloc[i] == 1 else upper_band.iloc[i]

            return {"supertrend": supertrend, "direction": direction}
        except Exception:
            empty = pd.Series(dtype=float)
            return {"supertrend": empty, "direction": empty}

    def calculate_stochastic(self, k: int = 14, d: int = 3) -> dict:
        """
        Stochastic Oscillator (%K and %D).

        Returns
        -------
        dict with keys: k (pd.Series), d (pd.Series)
        """
        try:
            low_min = self.df["Low"].rolling(window=k).min()
            high_max = self.df["High"].rolling(window=k).max()
            stoch_k = 100 * (self.df["Close"] - low_min) / (high_max - low_min).replace(0, np.nan)
            stoch_d = stoch_k.rolling(window=d).mean()
            return {"k": stoch_k.fillna(50), "d": stoch_d.fillna(50)}
        except Exception:
            empty = pd.Series(dtype=float)
            return {"k": empty, "d": empty}

    # ------------------------------------------------------------------
    # Support / Resistance
    # ------------------------------------------------------------------

    def get_support_resistance(self, lookback: int = 50) -> dict:
        """
        Identify swing highs (resistance) and swing lows (support) using
        a simple pivot-point method.

        Parameters
        ----------
        lookback : int
            Number of candles to look back.

        Returns
        -------
        dict with keys: supports (list of float), resistances (list of float)
        """
        try:
            df = self.df.tail(lookback).reset_index(drop=True)
            supports = []
            resistances = []

            for i in range(1, len(df) - 1):
                if df["Low"].iloc[i] < df["Low"].iloc[i - 1] and df["Low"].iloc[i] < df["Low"].iloc[i + 1]:
                    supports.append(float(df["Low"].iloc[i]))
                if df["High"].iloc[i] > df["High"].iloc[i - 1] and df["High"].iloc[i] > df["High"].iloc[i + 1]:
                    resistances.append(float(df["High"].iloc[i]))

            # Deduplicate close levels (within 0.5%)
            def deduplicate(levels):
                if not levels:
                    return []
                levels = sorted(set(levels))
                merged = [levels[0]]
                for lvl in levels[1:]:
                    if abs(lvl - merged[-1]) / merged[-1] > 0.005:
                        merged.append(lvl)
                return merged

            return {
                "supports": deduplicate(supports),
                "resistances": deduplicate(resistances),
            }
        except Exception:
            return {"supports": [], "resistances": []}

    # ------------------------------------------------------------------
    # Trend
    # ------------------------------------------------------------------

    def get_trend_direction(self) -> str:
        """
        Determine overall price trend.

        Returns
        -------
        str: "BULLISH" | "BEARISH" | "SIDEWAYS"
        """
        try:
            ema20 = self.calculate_ema(20)
            ema50 = self.calculate_ema(50)
            rsi = self.calculate_rsi()

            last_close = self.df["Close"].iloc[-1]
            last_ema20 = ema20.iloc[-1]
            last_ema50 = ema50.iloc[-1]
            last_rsi = rsi.iloc[-1]

            bullish_signals = sum([
                last_close > last_ema20,
                last_ema20 > last_ema50,
                last_rsi > 55,
            ])
            bearish_signals = sum([
                last_close < last_ema20,
                last_ema20 < last_ema50,
                last_rsi < 45,
            ])

            if bullish_signals >= 2:
                return "BULLISH"
            elif bearish_signals >= 2:
                return "BEARISH"
            return "SIDEWAYS"
        except Exception:
            return "SIDEWAYS"

    # ------------------------------------------------------------------
    # Composite score
    # ------------------------------------------------------------------

    def get_technical_score(self) -> float:
        """
        Composite technical confluence score (0-100).

        Scoring:
            +15 price > EMA20
            +15 EMA20 > EMA50
            +15 RSI in 40-60 or trending
            +15 MACD > signal
            +10 near lower/upper Bollinger Band
            +15 volume spike (> 1.5x 20-day avg)
            +15 SuperTrend bullish

        Returns
        -------
        float
        """
        score = 0.0
        try:
            close = self.df["Close"]
            volume = self.df["Volume"]

            ema20 = self.calculate_ema(20)
            ema50 = self.calculate_ema(50)
            rsi = self.calculate_rsi()
            macd = self.calculate_macd()
            bb = self.calculate_bollinger_bands()
            st = self.calculate_supertrend()

            last_close = close.iloc[-1]
            last_ema20 = ema20.iloc[-1]
            last_ema50 = ema50.iloc[-1]
            last_rsi = rsi.iloc[-1]
            last_macd = macd["macd_line"].iloc[-1]
            last_signal = macd["signal_line"].iloc[-1]
            last_upper = bb["upper"].iloc[-1]
            last_lower = bb["lower"].iloc[-1]
            last_middle = bb["middle"].iloc[-1]
            last_direction = st["direction"].iloc[-1] if len(st["direction"]) > 0 else -1

            # +15 price > EMA20
            if last_close > last_ema20:
                score += 15

            # +15 EMA20 > EMA50
            if last_ema20 > last_ema50:
                score += 15

            # +15 RSI neutral-bullish or trending
            if 40 <= last_rsi <= 60:
                score += 10
            elif last_rsi > 60:
                score += 15
            elif last_rsi > 35:
                score += 5

            # +15 MACD > signal
            if last_macd > last_signal:
                score += 15

            # +10 near Bollinger Band
            band_range = last_upper - last_lower
            if band_range > 0:
                lower_pct = (last_close - last_lower) / band_range
                if lower_pct < 0.25:
                    score += 10  # near lower band (buy zone)
                elif lower_pct > 0.75:
                    score += 5   # near upper band (partial credit)

            # +15 volume spike
            avg_vol_20 = volume.rolling(20).mean().iloc[-1]
            last_vol = volume.iloc[-1]
            if avg_vol_20 > 0 and last_vol > 1.5 * avg_vol_20:
                score += 15

            # +15 SuperTrend bullish
            if last_direction == 1:
                score += 15

        except Exception:
            pass

        return round(min(score, 100.0), 2)
