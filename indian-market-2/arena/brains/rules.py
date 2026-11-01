"""
Rules Baseline Decision Engine: Deterministic momentum rules.
Strategy from Guide:
- Opening Range Breakout (first 15-30 min high/low breakout)
- 20 EMA > 50 EMA trend confirmation
- RSI between 45 and 65 for healthy momentum
- Volume expansion > 1.2x 20-period volume average
"""

import logging
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np

from arena.brains.base import DecisionEngine, Decision
from arena.config import get_config

logger = logging.getLogger("arena.brains.rules")

class RulesEngine(DecisionEngine):
    """Deterministic momentum baseline decision engine."""

    def __init__(self, profile_name: str = "balanced"):
        super().__init__(name="Rules Baseline", profile_name=profile_name)

    def is_available(self) -> bool:
        return True  # Rules engine is always available locally

    def decide(self, symbol: str, current_price: float, history_df: Optional[pd.DataFrame] = None, context: Optional[Dict[str, Any]] = None) -> Decision:
        """
        Evaluate stock using deterministic ORB + Trend + RSI strategy.
        """
        if history_df is None or len(history_df) < 50:
            # Need at least 50 bars for EMA 50
            return Decision(
                action="HOLD",
                symbol=symbol,
                quantity=0,
                price=current_price,
                confidence=0.0,
                reason="Insufficient historical data (need >= 50 candles for EMA 50)",
                engine_name=self.name
            )

        close_series = history_df["Close"]
        high_series = history_df["High"]
        low_series = history_df["Low"]
        volume_series = history_df["Volume"] if "Volume" in history_df else None

        # 1. EMA 20 and EMA 50
        ema_20 = close_series.ewm(span=20, adjust=False).mean().iloc[-1]
        ema_50 = close_series.ewm(span=50, adjust=False).mean().iloc[-1]
        trend_bullish = ema_20 > ema_50
        trend_bearish = ema_20 < ema_50

        # 2. RSI (14 period)
        delta = close_series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / (loss.replace(0, np.nan))
        rsi_series = 100 - (100 / (1 + rs))
        current_rsi = float(rsi_series.iloc[-1]) if not pd.isna(rsi_series.iloc[-1]) else 50.0

        # 3. Opening Range Breakout (first 3 candles or past 15 periods high/low)
        recent_window = min(len(history_df), 15)
        recent_high = high_series.iloc[-recent_window:-1].max()
        recent_low = low_series.iloc[-recent_window:-1].min()

        # 4. Volume confirmation
        vol_surge = True
        if volume_series is not None and len(volume_series) >= 20:
            avg_vol = volume_series.iloc[-21:-1].mean()
            last_vol = volume_series.iloc[-1]
            vol_surge = (last_vol > avg_vol * 1.1) or avg_vol == 0

        # Risk parameters based on profile
        sl_pct = self.risk_profile.get("stop_loss_pct", 1.5) / 100.0
        tp_pct = self.risk_profile.get("take_profit_pct", 3.0) / 100.0

        # BUY Condition
        if current_price > recent_high and trend_bullish and (45.0 <= current_rsi <= 72.0) and vol_surge:
            stop_loss = round(current_price * (1.0 - sl_pct), 2)
            take_profit = round(current_price * (1.0 + tp_pct), 2)
            conf = min(0.95, 0.70 + (0.1 if current_rsi > 55 else 0.05) + (0.1 if current_price > ema_20 * 1.01 else 0.05))

            return Decision(
                action="BUY",
                symbol=symbol,
                quantity=0,  # Sized by risk manager
                price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                confidence=round(conf, 2),
                reason=f"ORB breakout above {recent_high:.2f}, EMA20 ({ema_20:.1f}) > EMA50 ({ema_50:.1f}), RSI={current_rsi:.1f}",
                engine_name=self.name,
                metrics={
                    "rsi": round(current_rsi, 2),
                    "ema_20": round(ema_20, 2),
                    "ema_50": round(ema_50, 2),
                    "breakout_level": round(recent_high, 2)
                }
            )

        # SELL / SHORT Condition (Intraday)
        elif current_price < recent_low and trend_bearish and (28.0 <= current_rsi <= 55.0) and vol_surge:
            stop_loss = round(current_price * (1.0 + sl_pct), 2)
            take_profit = round(current_price * (1.0 - tp_pct), 2)
            conf = min(0.95, 0.70 + (0.1 if current_rsi < 45 else 0.05))

            return Decision(
                action="SELL",
                symbol=symbol,
                quantity=0,
                price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                confidence=round(conf, 2),
                reason=f"Breakdown below {recent_low:.2f}, EMA20 ({ema_20:.1f}) < EMA50 ({ema_50:.1f}), RSI={current_rsi:.1f}",
                engine_name=self.name,
                metrics={
                    "rsi": round(current_rsi, 2),
                    "ema_20": round(ema_20, 2),
                    "ema_50": round(ema_50, 2),
                    "breakout_level": round(recent_low, 2)
                }
            )

        return Decision(
            action="HOLD",
            symbol=symbol,
            quantity=0,
            price=current_price,
            confidence=0.50,
            reason=f"Trend consolidation: RSI={current_rsi:.1f}, EMA20={ema_20:.1f}, EMA50={ema_50:.1f}",
            engine_name=self.name,
            metrics={"rsi": round(current_rsi, 2)}
        )
