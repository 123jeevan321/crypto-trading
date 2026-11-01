"""
Simulation Engine: Virtual execution with realistic market frictions, slippage,
and Indian market regulatory charges (STT, GST, exchange fees, stamp duty).
"""

import uuid
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field
from datetime import datetime
import pytz

from arena.config import get_config
from arena.brains.base import Decision
from arena.market_data.holidays import is_square_off_time, IST

logger = logging.getLogger("arena.sim")

@dataclass
class Position:
    id: str
    symbol: str
    side: str  # "BUY" or "SELL"
    quantity: int
    entry_price: float
    entry_time: str
    stop_loss: float
    take_profit: float
    current_price: float
    unrealized_pnl: float = 0.0
    status: str = "OPEN"  # "OPEN" or "CLOSED"
    close_price: Optional[float] = None
    close_time: Optional[str] = None
    close_reason: Optional[str] = None
    charges: float = 0.0
    gross_pnl: float = 0.0
    net_pnl: float = 0.0
    engine_name: str = "Auto"
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SimulationEngine:
    """Manages virtual trading portfolio, order execution, and fee calculation."""

    def __init__(self, initial_capital: float = 100000.0, saved_state: Optional[Dict[str, Any]] = None):
        self.cfg = get_config()
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions: Dict[str, Position] = {}
        self.closed_positions: List[Position] = []
        self.slippage_pct = self.cfg.slippage_pct / 100.0
        self.brokerage_per_order = self.cfg.brokerage_per_order
        self.stt_rate = self.cfg.stt_intraday_sell_pct / 100.0
        self.turnover_rate = self.cfg.turnover_charge_pct / 100.0
        self.gst_rate = self.cfg.gst_pct / 100.0
        self.stamp_duty_rate = self.cfg.stamp_duty_buy_pct / 100.0

        if saved_state:
            self.restore_state(saved_state)

    def restore_state(self, state: Dict[str, Any]):
        """Restore cash and positions from saved state."""
        self.cash = float(state.get("current_cash", self.initial_capital))
        self.positions.clear()
        for p in state.get("open_positions", []):
            pos = Position(**p)
            self.positions[pos.id] = pos

        self.closed_positions.clear()
        for p in state.get("trade_journal", []):
            pos = Position(**p)
            self.closed_positions.append(pos)

    @property
    def total_unrealized_pnl(self) -> float:
        return round(sum(p.unrealized_pnl for p in self.positions.values() if p.status == "OPEN"), 2)

    @property
    def total_realized_pnl(self) -> float:
        return round(sum(p.net_pnl for p in self.closed_positions), 2)

    @property
    def current_equity(self) -> float:
        return round(self.cash + sum(p.current_price * p.quantity for p in self.positions.values() if p.status == "OPEN"), 2)

    def calculate_charges(self, side: str, turnover: float, is_entry: bool = True) -> float:
        """Calculate statutory NSE transaction charges and brokerage."""
        brokerage = self.brokerage_per_order
        turnover_charge = turnover * self.turnover_rate
        gst = (brokerage + turnover_charge) * self.gst_rate

        stt = 0.0
        stamp_duty = 0.0

        if side == "BUY" and is_entry:
            stamp_duty = turnover * self.stamp_duty_rate
        elif side == "SELL" or (side == "BUY" and not is_entry):
            # STT applies on sell leg for intraday
            stt = turnover * self.stt_rate

        total_charges = round(brokerage + turnover_charge + gst + stamp_duty + stt, 2)
        return total_charges

    def execute_entry(self, decision: Decision, quote_price: float, current_dt: Optional[datetime] = None) -> Optional[Position]:
        """Execute a simulated market entry with slippage and charges."""
        if decision.quantity <= 0 or decision.action not in ["BUY", "SELL"]:
            return None

        dt_str = (current_dt or datetime.now(IST)).strftime("%Y-%m-%d %H:%M:%S")

        # Apply realistic 0.05% slippage against execution price
        if decision.action == "BUY":
            exec_price = round(quote_price * (1.0 + self.slippage_pct), 2)
        else:
            exec_price = round(quote_price * (1.0 - self.slippage_pct), 2)

        order_val = round(exec_price * decision.quantity, 2)
        entry_charges = self.calculate_charges(decision.action, order_val, is_entry=True)

        if order_val + entry_charges > self.cash:
            logger.warning("Insufficient cash for entry: req Rs %.2f, cash Rs %.2f", order_val + entry_charges, self.cash)
            return None

        # Deduct cash
        self.cash -= (order_val + entry_charges)

        pos_id = str(uuid.uuid4())[:8]
        pos = Position(
            id=pos_id,
            symbol=decision.symbol,
            side=decision.action,
            quantity=decision.quantity,
            entry_price=exec_price,
            entry_time=dt_str,
            stop_loss=decision.stop_loss or (exec_price * 0.985),
            take_profit=decision.take_profit or (exec_price * 1.03),
            current_price=exec_price,
            unrealized_pnl=0.0,
            charges=entry_charges,
            engine_name=decision.engine_name,
            notes=decision.reason
        )

        self.positions[pos_id] = pos
        logger.info("EXEC ENTRY %s: %s %d @ Rs %.2f (Fee: Rs %.2f)", pos.side, pos.symbol, pos.quantity, exec_price, entry_charges)
        return pos

    def update_market_prices(self, price_map: Dict[str, float], current_dt: Optional[datetime] = None) -> List[Position]:
        """
        Mark open positions to market, check SL/TP triggers and auto 15:15 IST square-off.
        Returns list of positions closed during this tick.
        """
        closed_this_tick: List[Position] = []
        if current_dt is None:
            current_dt = datetime.now(IST)

        force_square_off = is_square_off_time(current_dt)

        for pos_id, pos in list(self.positions.items()):
            if pos.symbol not in price_map:
                continue

            market_p = price_map[pos.symbol]
            pos.current_price = market_p

            # Calculate unrealized gross PnL
            if pos.side == "BUY":
                pos.unrealized_pnl = round((market_p - pos.entry_price) * pos.quantity, 2)
                # Check Take Profit
                if market_p >= pos.take_profit:
                    closed = self.close_position(pos_id, pos.take_profit, "Take Profit Hit", current_dt)
                    if closed: closed_this_tick.append(closed)
                # Check Stop Loss
                elif market_p <= pos.stop_loss:
                    closed = self.close_position(pos_id, pos.stop_loss, "Stop Loss Triggered", current_dt)
                    if closed: closed_this_tick.append(closed)
                # Mandatory Intraday Square-off at 15:15 IST
                elif force_square_off:
                    closed = self.close_position(pos_id, market_p, "Auto Square-Off (15:15 IST)", current_dt)
                    if closed: closed_this_tick.append(closed)

            elif pos.side == "SELL":
                pos.unrealized_pnl = round((pos.entry_price - market_p) * pos.quantity, 2)
                # Check Take Profit
                if market_p <= pos.take_profit:
                    closed = self.close_position(pos_id, pos.take_profit, "Take Profit Hit", current_dt)
                    if closed: closed_this_tick.append(closed)
                # Check Stop Loss
                elif market_p >= pos.stop_loss:
                    closed = self.close_position(pos_id, pos.stop_loss, "Stop Loss Triggered", current_dt)
                    if closed: closed_this_tick.append(closed)
                elif force_square_off:
                    closed = self.close_position(pos_id, market_p, "Auto Square-Off (15:15 IST)", current_dt)
                    if closed: closed_this_tick.append(closed)

        return closed_this_tick

    def close_position(self, pos_id: str, quote_exit_price: float, reason: str, current_dt: Optional[datetime] = None) -> Optional[Position]:
        """Close an open position, deduct exit charges and slippage, and credit cash."""
        if pos_id not in self.positions:
            return None

        pos = self.positions.pop(pos_id)
        dt_str = (current_dt or datetime.now(IST)).strftime("%Y-%m-%d %H:%M:%S")

        # Apply slippage on exit
        if pos.side == "BUY":
            exec_exit = round(quote_exit_price * (1.0 - self.slippage_pct), 2)
        else:
            exec_exit = round(quote_exit_price * (1.0 + self.slippage_pct), 2)

        turnover = round(exec_exit * pos.quantity, 2)
        exit_charges = self.calculate_charges(pos.side, turnover, is_entry=False)
        total_charges = round(pos.charges + exit_charges, 2)

        if pos.side == "BUY":
            gross_pnl = round((exec_exit - pos.entry_price) * pos.quantity, 2)
            net_proceeds = round(turnover - exit_charges, 2)
        else:
            gross_pnl = round((pos.entry_price - exec_exit) * pos.quantity, 2)
            net_proceeds = round((pos.entry_price * pos.quantity) + gross_pnl - exit_charges, 2)

        net_pnl = round(gross_pnl - total_charges, 2)

        pos.status = "CLOSED"
        pos.close_price = exec_exit
        pos.close_time = dt_str
        pos.close_reason = reason
        pos.charges = total_charges
        pos.gross_pnl = gross_pnl
        pos.net_pnl = net_pnl
        pos.unrealized_pnl = 0.0

        # Credit back cash
        self.cash = round(self.cash + turnover - exit_charges, 2)
        self.closed_positions.append(pos)

        logger.info("CLOSED %s %s: Exit Rs %.2f | Gross PnL: Rs %.2f | Net PnL: Rs %.2f (%s)",
                    pos.side, pos.symbol, exec_exit, gross_pnl, net_pnl, reason)
        return pos
