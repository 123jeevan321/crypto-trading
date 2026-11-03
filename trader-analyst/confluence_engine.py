"""
Institutional Multi-Confluence Engine (Volume Profile, Order Flow, ICT/SMC, Footprints, Traps, Technicals)
Calculates institutional confluence score (0-100%).
Core Directive: Accuracy & TP hit rate is Priority #1.
Supports Dynamic Scalp & Swing Targets (e.g. TP1 100-300 pts high-probability lock, TP2 runners).
"""

import sys
import os
import math
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, Optional

# Add path for events calendar
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
INDIAN_MARKET_DIR = os.path.join(os.path.dirname(CURRENT_DIR), "indian-market")
if INDIAN_MARKET_DIR not in sys.path:
    sys.path.insert(0, INDIAN_MARKET_DIR)

try:
    from data.events_calendar import EventsCalendar
except ImportError:
    EventsCalendar = None


class InstitutionalConfluenceEngine:
    """
    Advanced Multi-Factor Institutional Confluence Engine.
    Unifies:
    1. Volume Profile (Point of Control - POC, Value Area High - VAH, Value Area Low - VAL)
    2. ICT / SMC (Order Blocks, Fair Value Gaps - FVG, Liquidity Sweeps, CHoCH)
    3. Institutional Footprint & Retail Trap Detection (EQH/EQL sweeps, fakeouts)
    4. Technical Indicators (EMA 9/21/50/200 Stack, MACD Histogram, VWAP)
    5. Event & Macro Calendar Gatekeeper (Earnings blackout, High-impact news)
    6. Priority #1: ACCURATE TP EXECUTION (Tier 1 quick profit lock + Tier 2 runner)
    """

    @staticmethod
    def calculate_volume_profile(df: pd.DataFrame, num_bins: int = 30) -> Dict[str, float]:
        """Calculates Point of Control (POC), Value Area High (VAH), and Value Area Low (VAL)."""
        if df.empty or len(df) < 5:
            return {"poc": 0.0, "vah": 0.0, "val": 0.0}

        price_min = float(df['Low'].min())
        price_max = float(df['High'].max())
        if price_max == price_min:
            return {"poc": price_min, "vah": price_min, "val": price_min}

        bins = np.linspace(price_min, price_max, num_bins + 1)
        bin_volumes = np.zeros(num_bins)

        for _, row in df.iterrows():
            avg_p = (float(row['High']) + float(row['Low']) + float(row['Close'])) / 3.0
            idx = int((avg_p - price_min) / (price_max - price_min) * (num_bins - 1))
            idx = max(0, min(num_bins - 1, idx))
            bin_volumes[idx] += float(row['Volume'])

        poc_idx = int(np.argmax(bin_volumes))
        poc = (bins[poc_idx] + bins[poc_idx + 1]) / 2.0

        # Value area is 70% of total volume centered around POC
        total_vol = float(bin_volumes.sum())
        target_vol = total_vol * 0.70
        accum_vol = float(bin_volumes[poc_idx])
        up_idx = poc_idx
        down_idx = poc_idx

        while accum_vol < target_vol and (up_idx < num_bins - 1 or down_idx > 0):
            vol_up = float(bin_volumes[up_idx + 1]) if up_idx < num_bins - 1 else 0.0
            vol_down = float(bin_volumes[down_idx - 1]) if down_idx > 0 else 0.0

            if vol_up >= vol_down and up_idx < num_bins - 1:
                up_idx += 1
                accum_vol += vol_up
            elif down_idx > 0:
                down_idx -= 1
                accum_vol += vol_down
            elif up_idx < num_bins - 1:
                up_idx += 1
                accum_vol += vol_up
            else:
                break

        val = float(bins[down_idx])
        vah = float(bins[up_idx + 1])

        return {"poc": round(poc, 2), "vah": round(vah, 2), "val": round(val, 2)}

    @staticmethod
    def calculate_smc_ict(df: pd.DataFrame) -> Dict[str, Any]:
        """Detects Order Blocks, Fair Value Gaps (FVG), Liquidity Sweeps, and Market Structure."""
        if len(df) < 10:
            return {"fvg_bullish": False, "fvg_bearish": False, "liquidity_sweep": None, "order_block": None}

        # 1. Fair Value Gap (FVG) in recent candles
        fvg_bullish = False
        fvg_bearish = False
        fvg_price = 0.0

        for i in range(len(df) - 4, len(df) - 1):
            low_next = float(df['Low'].iloc[i + 1])
            high_prev = float(df['High'].iloc[i - 1])
            high_next = float(df['High'].iloc[i + 1])
            low_prev = float(df['Low'].iloc[i - 1])

            if low_next > high_prev:
                fvg_bullish = True
                fvg_price = (low_next + high_prev) / 2.0
            elif high_next < low_prev:
                fvg_bearish = True
                fvg_price = (high_next + low_prev) / 2.0

        # 2. Liquidity Sweep (Stop Hunt)
        recent_high = float(df['High'].iloc[-25:-3].max())
        recent_low = float(df['Low'].iloc[-25:-3].min())

        last_high = float(df['High'].iloc[-3:].max())
        last_low = float(df['Low'].iloc[-3:].min())
        last_close = float(df['Close'].iloc[-1])

        sweep = None
        if last_high > recent_high and last_close < recent_high:
            sweep = "BEARISH_BUY_STOP_HUNT"
        elif last_low < recent_low and last_close > recent_low:
            sweep = "BULLISH_SELL_STOP_HUNT"

        # 3. Order Block
        ob = None
        if fvg_bullish:
            ob = {"type": "BULLISH_DEMAND_OB", "level": round(float(df['Low'].iloc[-4]), 2)}
        elif fvg_bearish:
            ob = {"type": "BEARISH_SUPPLY_OB", "level": round(float(df['High'].iloc[-4]), 2)}

        return {
            "fvg_bullish": bool(fvg_bullish),
            "fvg_bearish": bool(fvg_bearish),
            "fvg_price": round(float(fvg_price), 2) if fvg_price else None,
            "liquidity_sweep": sweep,
            "order_block": ob
        }

    @staticmethod
    def calculate_technical_confluence(df: pd.DataFrame) -> Dict[str, Any]:
        """Calculates EMAs (9, 21, 50, 200), MACD, and VWAP alignment."""
        close = df['Close'].astype(float)
        vol = df['Volume'].astype(float)

        ema9 = float(close.ewm(span=9, adjust=False).mean().iloc[-1])
        ema21 = float(close.ewm(span=21, adjust=False).mean().iloc[-1])
        ema50 = float(close.ewm(span=50, adjust=False).mean().iloc[-1]) if len(close) >= 50 else ema21
        ema200 = float(close.ewm(span=200, adjust=False).mean().iloc[-1]) if len(close) >= 200 else ema50

        # MACD (12, 26, 9)
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd_line = ema12 - ema26
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        macd_hist = macd_line - signal_line

        # VWAP
        cum_vol = float(vol.sum())
        vwap = float((close * vol).sum() / cum_vol) if cum_vol > 0 else float(close.iloc[-1])

        cmp = float(close.iloc[-1])
        bullish_stack = bool(cmp > ema9 > ema21)
        bearish_stack = bool(cmp < ema9 < ema21)
        above_vwap = bool(cmp > vwap)
        macd_trending_up = bool(float(macd_hist.iloc[-1]) > float(macd_hist.iloc[-2])) if len(macd_hist) > 1 else False

        return {
            "cmp": round(cmp, 2),
            "vwap": round(vwap, 2),
            "ema9": round(ema9, 2),
            "ema21": round(ema21, 2),
            "ema50": round(ema50, 2),
            "ema200": round(ema200, 2),
            "macd_hist": round(float(macd_hist.iloc[-1]), 2),
            "macd_trending_up": macd_trending_up,
            "bullish_stack": bullish_stack,
            "bearish_stack": bearish_stack,
            "above_vwap": above_vwap
        }

    @classmethod
    def evaluate(cls, symbol: str, interval: str = "15m", period: str = "5d") -> Dict[str, Any]:
        """
        Runs comprehensive multi-confluence analysis across all pillars.
        Builds high-accuracy tiered targets (TP1 quick lock, TP2 expansion).
        """
        # 1. Mandatory Event Calendar Gatekeeper
        if EventsCalendar and symbol.endswith('.NS'):
            has_event, reason = EventsCalendar.is_earnings_or_event_today(symbol)
            if has_event:
                return {
                    "symbol": symbol,
                    "confluence_score": 0.0,
                    "verdict": "NO_TRADE_EVENT_GATE_BLOCKED",
                    "reason": f"Mandatory Blacklist: {reason}",
                    "details": {}
                }

        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval)
        if df.empty or len(df) < 15:
            return {
                "symbol": symbol,
                "confluence_score": 0.0,
                "verdict": "NO_TRADE_INSUFFICIENT_DATA",
                "reason": "Not enough candle bars to form statistical confluence",
                "details": {}
            }

        vp = cls.calculate_volume_profile(df)
        smc = cls.calculate_smc_ict(df)
        tech = cls.calculate_technical_confluence(df)

        cmp = tech['cmp']
        score = 0.0
        confluences = []
        cautions = []
        bias = "NEUTRAL"

        # Pillar 1: Volume Profile Confluence (20 points)
        if abs(cmp - vp['val']) / cmp < 0.005:
            score += 20
            confluences.append(f"Volume Profile: Rebounding off Value Area Low (VAL {vp['val']})")
            bias = "BULLISH"
        elif abs(cmp - vp['vah']) / cmp < 0.005:
            score += 20
            confluences.append(f"Volume Profile: Testing Value Area High Resistance (VAH {vp['vah']})")
            bias = "BEARISH"
        elif cmp > vp['poc'] and tech['above_vwap']:
            score += 15
            confluences.append(f"Volume Profile: Trading above institutional POC ({vp['poc']}) and VWAP ({tech['vwap']})")
        else:
            cautions.append(f"Volume Profile: In middle chop between VAL ({vp['val']}) and VAH ({vp['vah']})")

        # Pillar 2: SMC / ICT Liquidity Sweep & Order Block (25 points)
        if smc['liquidity_sweep'] == "BULLISH_SELL_STOP_HUNT":
            score += 25
            confluences.append("SMC/ICT: Bullish Sell-Stop Liquidity Hunt confirmed (Retail breakdown trap)")
            bias = "BULLISH"
        elif smc['liquidity_sweep'] == "BEARISH_BUY_STOP_HUNT":
            score += 25
            confluences.append("SMC/ICT: Bearish Buy-Stop Liquidity Hunt confirmed (Retail breakout trap)")
            bias = "BEARISH"
        elif smc['fvg_bullish'] and tech['above_vwap']:
            score += 15
            confluences.append(f"SMC/ICT: Bullish Fair Value Gap (FVG) open at {smc['fvg_price']}")
        elif smc['fvg_bearish'] and not tech['above_vwap']:
            score += 15
            confluences.append(f"SMC/ICT: Bearish Fair Value Gap (FVG) open at {smc['fvg_price']}")

        # Pillar 3: Technical Trend & Moving Average Stack (20 points)
        if tech['bullish_stack'] and tech['macd_trending_up']:
            score += 20
            confluences.append("Technicals: Full EMA alignment (CMP > 9 > 21) with expanding positive MACD momentum")
            if bias == "NEUTRAL": bias = "BULLISH"
        elif tech['bearish_stack'] and not tech['macd_trending_up']:
            score += 20
            confluences.append("Technicals: Full Bearish EMA stack (CMP < 9 < 21) with decaying MACD momentum")
            if bias == "NEUTRAL": bias = "BEARISH"
        elif tech['bullish_stack'] or tech['above_vwap']:
            score += 10
            confluences.append("Technicals: Moderate bullish positioning above VWAP")

        # Pillar 4: Time of Day & Liquidity Cycle Window (15 points)
        now_utc_hour = datetime.now(timezone.utc).hour
        if (7 <= now_utc_hour <= 10) or (13 <= now_utc_hour <= 17):
            score += 15
            confluences.append(f"Time Window: Institutional Session Window active (UTC {now_utc_hour}:00)")
        else:
            cautions.append(f"Time Window: Low-liquidity transition window (UTC {now_utc_hour}:00) - high risk of chop")

        # Pillar 5: High-Accuracy Target Delivery & Structural SL (20 points)
        # Priority #1: Accuracy. TP1 is a high-probability quick scalp (100-300 pts on BTC, 0.4% on stocks)
        # to ensure the trade is locked in green, while TP2 captures larger moves.
        order_ticket = None
        if symbol.startswith('BTC'):
            if bias == "BULLISH":
                sl = round(min(vp['val'], cmp - 220), 2)
                tp1 = round(cmp + 180, 2)   # High-probability quick green lock
                tp2 = round(cmp + 750, 2)   # Extended target
                score += 20
                order_ticket = {
                    "action": "BUY_LONG",
                    "entry": cmp,
                    "sl": sl,
                    "tp1_quick_lock": tp1,
                    "tp2_runner": tp2,
                    "tp1_points": round(tp1 - cmp, 2),
                    "rule": "Move SL to Breakeven immediately when TP1 is hit."
                }
                confluences.append(f"High-Accuracy Target Plan: TP1 (+{round(tp1 - cmp, 0)} pts) quick green lock, SL: {sl}")
            elif bias == "BEARISH":
                sl = round(max(vp['vah'], cmp + 220), 2)
                tp1 = round(cmp - 180, 2)   # High-probability quick green lock
                tp2 = round(cmp - 750, 2)   # Extended target
                score += 20
                order_ticket = {
                    "action": "SELL_SHORT",
                    "entry": cmp,
                    "sl": sl,
                    "tp1_quick_lock": tp1,
                    "tp2_runner": tp2,
                    "tp1_points": round(cmp - tp1, 2),
                    "rule": "Move SL to Breakeven immediately when TP1 is hit."
                }
                confluences.append(f"High-Accuracy Target Plan: TP1 (+{round(cmp - tp1, 0)} pts) quick green lock, SL: {sl}")
            else:
                cautions.append("Bias is Neutral: Wait for liquidity sweep before issuing accurate TP ticket")
        else:
            # Equities Tiered Targets
            if bias == "BULLISH":
                sl = round(min(tech['vwap'] * 0.995, cmp * 0.993), 2)
                tp1 = round(cmp * 1.005, 2)  # +0.5% high probability
                tp2 = round(cmp * 1.015, 2)  # +1.5%
                score += 20
                order_ticket = {
                    "action": "BUY_LONG",
                    "entry": cmp,
                    "sl": sl,
                    "tp1_quick_lock": tp1,
                    "tp2_runner": tp2,
                    "rule": "Move SL to Breakeven immediately when TP1 is hit."
                }
                confluences.append(f"High-Accuracy Target Plan: TP1 ₹{tp1} (+0.5%), TP2 ₹{tp2} (+1.5%), SL ₹{sl}")
            elif bias == "BEARISH":
                sl = round(max(tech['vwap'] * 1.005, cmp * 1.007), 2)
                tp1 = round(cmp * 0.995, 2)
                tp2 = round(cmp * 0.985, 2)
                score += 20
                order_ticket = {
                    "action": "SELL_SHORT",
                    "entry": cmp,
                    "sl": sl,
                    "tp1_quick_lock": tp1,
                    "tp2_runner": tp2,
                    "rule": "Move SL to Breakeven immediately when TP1 is hit."
                }
                confluences.append(f"High-Accuracy Target Plan: TP1 ₹{tp1} (-0.5%), TP2 ₹{tp2} (-1.5%), SL ₹{sl}")
            else:
                cautions.append("Equity trend is Neutral: Wait for VWAP alignment")

        # Final Decision Logic
        if score >= 85:
            verdict = f"GRADE_A_{bias}_ENTRY"
        elif score >= 70:
            verdict = "WATCHLIST_STAGING_WAIT_TRIGGER"
        else:
            verdict = "NO_TRADE_CONDITIONS_NOT_MET"

        return {
            "symbol": symbol,
            "cmp": cmp,
            "confluence_score": round(score, 1),
            "bias": bias,
            "verdict": verdict,
            "order_ticket": order_ticket,
            "volume_profile": vp,
            "smc_ict": smc,
            "technicals": tech,
            "confluences": confluences,
            "cautions": cautions
        }
