"""
Risk Management Engine: Enforces capital protection, position sizing, SL/TP bounds,
and trading session rules according to the Breaking Money specification.
"""

import logging
from typing import Dict, Any, Tuple, Optional
from datetime import datetime
import pytz

from arena.config import get_config
from arena.market_data.holidays import is_entry_allowed, is_square_off_time, IST

logger = logging.getLogger("arena.risk")

class RiskManager:
    """Enforces strict risk management protocols."""

    def __init__(self, profile_name: str = "balanced"):
        self.cfg = get_config()
        self.profile_name = profile_name
        self.profile = self.cfg.get_risk_profile(profile_name)

        self.max_position_pct = self.profile.get("max_position_pct", 20.0) / 100.0
        self.max_daily_loss_pct = self.profile.get("max_daily_loss_pct", 3.0) / 100.0
        self.max_open_positions = self.profile.get("max_open_positions", 3)
        self.stop_loss_pct = self.profile.get("stop_loss_pct", 1.5) / 100.0
        self.take_profit_pct = self.profile.get("take_profit_pct", 3.0) / 100.0

    def check_entry_allowed(self, current_dt: Optional[datetime] = None) -> Tuple[bool, str]:
        """Check if time-of-day permits new entries."""
        if current_dt is None:
            current_dt = datetime.now(IST)
        elif current_dt.tzinfo is None:
            current_dt = IST.localize(current_dt)

        if not is_entry_allowed(current_dt):
            return False, f"Entry rejected: Outside trading entry window ({self.cfg.market_open_time} - {self.cfg.entry_cutoff_time} IST)"
        return True, "Entry time valid"

    def check_daily_loss_limit(self, starting_equity: float, current_equity: float) -> Tuple[bool, str]:
        """Check if daily drawdown limit has been reached."""
        daily_loss = starting_equity - current_equity
        max_loss_allowed = starting_equity * self.max_daily_loss_pct
        if daily_loss >= max_loss_allowed:
            return False, f"Risk Alert: Daily loss cap reached (-Rs {daily_loss:.2f} >= max -Rs {max_loss_allowed:.2f}). Trading halted for the session."
        return True, "Within daily loss limits"

    def calculate_position_size(self, current_equity: float, current_price: float, open_positions_count: int) -> Tuple[int, float, str]:
        """
        Calculate maximum allowable quantity adhering to 20% equity cap.
        Returns: (quantity, allocated_capital, reason)
        """
        if open_positions_count >= self.max_open_positions:
            return 0, 0.0, f"Max open positions ({self.max_open_positions}) reached for {self.profile_name} profile."

        max_alloc = current_equity * self.max_position_pct
        if current_price <= 0:
            return 0, 0.0, "Invalid price"

        qty = int(max_alloc // current_price)
        if qty <= 0:
            return 0, 0.0, f"Stock price (Rs {current_price:.2f}) exceeds max position size limit (Rs {max_alloc:.2f})"

        alloc = round(qty * current_price, 2)
        return qty, alloc, f"Allocated Rs {alloc:.2f} ({qty} shares)"

    def sanitize_sl_tp(self, action: str, entry_price: float, proposed_sl: Optional[float], proposed_tp: Optional[float]) -> Tuple[float, float]:
        """Ensure stop-loss and take-profit strictly adhere to risk profile boundaries."""
        if action == "BUY":
            min_sl = round(entry_price * (1.0 - self.stop_loss_pct), 2)
            default_tp = round(entry_price * (1.0 + self.take_profit_pct), 2)
            sl = proposed_sl if (proposed_sl and proposed_sl < entry_price and proposed_sl >= min_sl) else min_sl
            tp = proposed_tp if (proposed_tp and proposed_tp > entry_price) else default_tp
            return sl, tp
        elif action == "SELL":
            max_sl = round(entry_price * (1.0 + self.stop_loss_pct), 2)
            default_tp = round(entry_price * (1.0 - self.take_profit_pct), 2)
            sl = proposed_sl if (proposed_sl and proposed_sl > entry_price and proposed_sl <= max_sl) else max_sl
            tp = proposed_tp if (proposed_tp and proposed_tp < entry_price) else default_tp
            return sl, tp
        return 0.0, 0.0
