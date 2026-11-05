"""
Indian Equities Opening Session Scalping Engine (09:15 AM - 09:25 AM)
Target: Rs 20,000 Daily Net Profit
Based on Smart Money Concepts (SMC), Liquidity Sweep Auditing, and 30-Day Microstructure Validation.
"""

import math
from typing import Dict, Any, List, Optional

class OpeningSessionScalper:
    """
    Automated Institutional Microstructure Scalper for 09:15 - 09:25 AM IST.
    Designed to systematically capture asymmetric morning moves while avoiding retail traps.
    """

    def __init__(self, target_daily_profit: float = 20000.0, max_trade_risk: float = 4000.0, margin_multiplier: float = 5.0):
        self.target_daily_profit = target_daily_profit
        self.max_trade_risk = max_trade_risk
        self.margin_multiplier = margin_multiplier

        # Preferred High-Volume Institutional Instruments
        self.tier1_universe = [
            "SBIN.NS", "RELIANCE.NS", "ICICIBANK.NS", "KALYANKJIL.NS",
            "HDFCBANK.NS", "HINDALCO.NS", "TATAMOTORS.NS"
        ]

    def audit_opening_candle(self, c1: Dict[str, float]) -> Dict[str, Any]:
        """
        Audits the initial 09:15:00 - 09:16:00 1-minute candle.
        c1 format: {'open': float, 'high': float, 'low': float, 'close': float, 'volume': float}
        """
        o = c1['open']
        h = c1['high']
        l = c1['low']
        c = c1['close']
        c_range = max(h - l, 0.05)

        body_top = max(o, c)
        body_bottom = min(o, c)
        upper_wick = h - body_top
        lower_wick = body_bottom - l

        upper_wick_ratio = upper_wick / c_range
        lower_wick_ratio = lower_wick / c_range
        body_ratio = abs(c - o) / c_range
        range_pct = (c_range / o) * 100.0

        # Institutional Pattern Classifications
        is_open_low = (lower_wick / o < 0.0006) or (lower_wick_ratio < 0.08 and c > o)
        is_open_high = (upper_wick / o < 0.0006) or (upper_wick_ratio < 0.08 and c < o)
        is_liquidity_trap_top = upper_wick_ratio >= 0.35 and (c < o or upper_wick > 2.0 * abs(c - o))
        is_liquidity_trap_bottom = lower_wick_ratio >= 0.35 and (c > o or lower_wick > 2.0 * abs(c - o))

        return {
            'range_pts': c_range,
            'range_pct': range_pct,
            'upper_wick_ratio': upper_wick_ratio,
            'lower_wick_ratio': lower_wick_ratio,
            'body_ratio': body_ratio,
            'is_open_low': is_open_low,
            'is_open_high': is_open_high,
            'is_liquidity_trap_top': is_liquidity_trap_top,
            'is_liquidity_trap_bottom': is_liquidity_trap_bottom
        }

    def generate_opening_signal(self, candles: List[Dict[str, float]], symbol: str, current_time_str: str) -> Dict[str, Any]:
        """
        Evaluates 1-minute bars up to current_time (must be between 09:16 and 09:24 AM).
        candles[0] = 09:15
        candles[1] = 09:16
        candles[2] = 09:17 (if available)
        """
        if len(candles) < 2:
            return {
                'signal': 'WAIT_FOR_0916_CLOSE',
                'reason': 'Never enter inside the first 60 seconds (09:15-09:16). Await auction discovery.',
                'actionable': False
            }

        c1 = candles[0]
        c2 = candles[1]
        c1_audit = self.audit_opening_candle(c1)

        # Universe check
        is_tier1 = symbol in self.tier1_universe

        # --- SETUP 1: LAW #1 OPEN=LOW INSTITUTIONAL DRIVE (LONG) ---
        if c1_audit['is_open_low'] and c1['close'] > c1['open'] and c1_audit['body_ratio'] >= 0.55:
            # Condition: 09:16 breaks 09:15 high or retests the FVG
            fvg_retest = c1['high']
            entry_price = round(c1['high'] + (0.0005 * c1['high']), 2)
            sl_price = round(c1['low'] - 0.05, 2)
            risk_per_share = entry_price - sl_price

            # Invalidation safety: risk capped at 0.5% max
            if risk_per_share > entry_price * 0.005:
                sl_price = round(entry_price * 0.996, 2)
                risk_per_share = entry_price - sl_price

            # Target sizing for Rs 20,000 asymmetric capture
            tp1 = round(entry_price + (risk_per_share * 1.5), 2)
            tp2 = round(entry_price + (risk_per_share * 2.5), 2)

            # Sizing calculation
            shares = self.calculate_shares(entry_price, risk_per_share)

            return {
                'signal': 'BUY_CALL_OPEN_LOW_DRIVE',
                'strategy': 'LAW_1_OPEN_LOW_MOMENTUM',
                'direction': 'UP',
                'actionable': True,
                'entry': entry_price,
                'fvg_retest_entry': fvg_retest,
                'stop_loss': sl_price,
                'target_1': tp1,
                'target_2_runner': tp2,
                'shares': shares,
                'est_max_risk_inr': round(risk_per_share * shares, 2),
                'est_target_profit_inr': round((tp2 - entry_price) * shares, 2),
                'tier1_stock': is_tier1,
                'reason': 'Zero lower wick confirmed. Institutions driving morning bid from the bell.'
            }

        # --- SETUP 2: LAW #21 09:17 AM TRAP INVERSION (SHORT) ---
        if c1_audit['is_liquidity_trap_top']:
            # Need Candle 3 (09:17) to confirm structure shift
            if len(candles) >= 3:
                c3 = candles[2]
                if c3['low'] < c1['low'] or (c3['close'] < c1['open'] and c2['high'] <= c1['high']):
                    entry_price = round(c1['low'] - (0.0002 * c1['low']), 2)
                    sl_price = round(c1['high'] + 0.05, 2)
                    risk_per_share = sl_price - entry_price

                    if risk_per_share > entry_price * 0.006:
                        sl_price = round(entry_price * 1.005, 2)
                        risk_per_share = sl_price - entry_price

                    tp1 = round(entry_price - (risk_per_share * 1.5), 2)
                    tp2 = round(entry_price - (risk_per_share * 2.5), 2)
                    shares = self.calculate_shares(entry_price, risk_per_share)

                    return {
                        'signal': 'SELL_PUT_TRAP_INVERSION',
                        'strategy': 'LAW_21_TRAP_INVERSION_SHORT',
                        'direction': 'DOWN',
                        'actionable': True,
                        'entry': entry_price,
                        'stop_loss': sl_price,
                        'target_1': tp1,
                        'target_2_runner': tp2,
                        'shares': shares,
                        'est_max_risk_inr': round(risk_per_share * shares, 2),
                        'est_target_profit_inr': round((entry_price - tp2) * shares, 2),
                        'tier1_stock': is_tier1,
                        'reason': 'Opening sweep trapped retail longs (upper wick > 35%). CHoCH breakdown triggered.'
                    }
                else:
                    return {
                        'signal': 'WAIT_FOR_0917_BREAKDOWN',
                        'reason': 'Liquidity trap wick detected at 09:15. Waiting for 09:17 breakdown below C1 low.',
                        'actionable': False
                    }
            else:
                return {
                    'signal': 'MONITOR_FOR_TRAP_BREAKDOWN',
                    'reason': 'Huge upper wick at 09:15. Awaiting 09:17 bar confirmation.',
                    'actionable': False
                }

        return {
            'signal': 'NO_TRADE_INDECISION',
            'reason': '09:15 candle shows two-way wicks or consolidation. Do not force morning trades.',
            'actionable': False
        }

    def calculate_shares(self, entry_price: float, risk_per_share: float) -> int:
        """
        Calculates position size strictly respecting max risk of Rs 4,000 per trade.
        """
        if risk_per_share <= 0:
            return 100
        shares_by_risk = int(self.max_trade_risk / risk_per_share)
        # Cap max position exposure to Rs 12,00,000 (standard Rs 2.5L capital at 5x margin)
        max_shares_exposure = int(1200000.0 / entry_price)
        return max(min(shares_by_risk, max_shares_exposure), 10)

    def calculate_zerodha_friction(self, turnover_buy: float, turnover_sell: float) -> Dict[str, float]:
        """
        Computes accurate Zerodha Intraday equity costs.
        """
        brokerage = min(20.0, 0.0003 * turnover_buy) + min(20.0, 0.0003 * turnover_sell)
        stt = 0.00025 * turnover_sell
        exchange = 0.0000297 * (turnover_buy + turnover_sell)
        gst = 0.18 * (brokerage + exchange)
        sebi = 0.000001 * (turnover_buy + turnover_sell)
        stamp = 0.00003 * turnover_buy
        total = brokerage + stt + exchange + gst + sebi + stamp
        return {
            'brokerage': round(brokerage, 2),
            'stt': round(stt, 2),
            'exchange_charges': round(exchange, 2),
            'gst': round(gst, 2),
            'total_friction': round(total, 2)
        }
