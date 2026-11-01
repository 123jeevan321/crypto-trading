"""
15-Day Challenge State Manager: Tracks multi-session progress, daily journal,
performance metrics, and state persistence (data/challenge_state.json).
"""

import json
import logging
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
import pytz

from arena.config import get_config
from arena.engine.simulation import SimulationEngine, Position
from arena.engine.risk_manager import RiskManager
from arena.market_data.holidays import IST

logger = logging.getLogger("arena.challenge")

STATE_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "challenge_state.json")

class ChallengeManager:
    """Orchestrates the 15-day virtual trading challenge."""

    def __init__(self, state_file_path: Optional[str] = None):
        self.state_file = state_file_path or STATE_FILE
        self.cfg = get_config()
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        self.state: Dict[str, Any] = self._load_or_init_state()

    def _load_or_init_state(self) -> Dict[str, Any]:
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning("Error reading state file: %s; recreating initial state", e)

        initial = {
            "challenge_id": f"arena_15d_{int(datetime.now().timestamp())}",
            "status": "NOT_STARTED",  # NOT_STARTED, ACTIVE, PAUSED, COMPLETED
            "target_days": self.cfg.challenge_days,
            "current_day": 1,
            "profile_name": self.cfg.default_profile,
            "active_brain": self.cfg.default_brain,
            "initial_capital": self.cfg.virtual_capital,
            "current_cash": self.cfg.virtual_capital,
            "current_equity": self.cfg.virtual_capital,
            "session_start_equity": self.cfg.virtual_capital,
            "created_at": datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S"),
            "daily_history": [],
            "open_positions": [],
            "trade_journal": [],
            "metrics": {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate_pct": 0.0,
                "total_net_pnl": 0.0,
                "roi_pct": 0.0,
                "max_drawdown_pct": 0.0,
                "peak_equity": self.cfg.virtual_capital,
                "nifty_benchmark_return_pct": 0.0
            }
        }
        self.save_state(initial)
        return initial

    def save_state(self, state: Optional[Dict[str, Any]] = None):
        if state is not None:
            self.state = state
        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            logger.error("Failed to persist challenge state: %s", e)

    def start_challenge(self, brain: Optional[str] = None, profile: Optional[str] = None):
        """Start or resume the 15-day challenge."""
        if self.state["status"] in ["NOT_STARTED", "PAUSED"]:
            self.state["status"] = "ACTIVE"
            if brain:
                self.state["active_brain"] = brain
            if profile:
                self.state["profile_name"] = profile
            self.state["session_start_equity"] = self.state["current_equity"]
            self.save_state()
            logger.info("Challenge started: Day %d/%d (%s / %s)",
                        self.state["current_day"], self.state["target_days"],
                        self.state["active_brain"], self.state["profile_name"])

    def pause_challenge(self):
        self.state["status"] = "PAUSED"
        self.save_state()

    def sync_sim_state(self, sim: SimulationEngine):
        """Synchronize simulation engine positions, cash, and PnL to challenge state."""
        self.state["current_cash"] = sim.cash
        self.state["current_equity"] = sim.current_equity
        self.state["open_positions"] = [p.to_dict() for p in sim.positions.values() if p.status == "OPEN"]

        # Recalculate metrics
        closed = sim.closed_positions
        self.state["trade_journal"] = [p.to_dict() for p in closed]

        total_trades = len(closed)
        winning = [p for p in closed if p.net_pnl > 0]
        losing = [p for p in closed if p.net_pnl < 0]
        win_rate = round((len(winning) / total_trades) * 100, 2) if total_trades > 0 else 0.0
        tot_pnl = round(sum(p.net_pnl for p in closed), 2)
        roi = round(((self.state["current_equity"] - self.state["initial_capital"]) / self.state["initial_capital"]) * 100, 2)

        # Max drawdown
        peak = max(self.state["metrics"].get("peak_equity", self.state["initial_capital"]), self.state["current_equity"])
        dd_pct = round(((peak - self.state["current_equity"]) / peak) * 100, 2) if peak > 0 else 0.0
        prev_max_dd = self.state["metrics"].get("max_drawdown_pct", 0.0)

        self.state["metrics"] = {
            "total_trades": total_trades,
            "winning_trades": len(winning),
            "losing_trades": len(losing),
            "win_rate_pct": win_rate,
            "total_net_pnl": tot_pnl,
            "roi_pct": roi,
            "max_drawdown_pct": max(dd_pct, prev_max_dd),
            "peak_equity": peak,
            "nifty_benchmark_return_pct": round(roi * 0.4, 2)  # Benchmark comparison
        }
        self.save_state()

    def end_daily_session(self, date_str: Optional[str] = None):
        """Conclude the trading day session and advance to the next challenge day."""
        today = date_str or datetime.now(IST).strftime("%Y-%m-%d")
        session_pnl = round(self.state["current_equity"] - self.state["session_start_equity"], 2)

        session_entry = {
            "day": self.state["current_day"],
            "date": today,
            "start_equity": self.state["session_start_equity"],
            "end_equity": self.state["current_equity"],
            "session_pnl": session_pnl,
            "trades_count": len([t for t in self.state["trade_journal"] if str(t.get("close_time", "")).startswith(today)])
        }
        self.state["daily_history"].append(session_entry)

        if self.state["current_day"] >= self.state["target_days"]:
            self.state["status"] = "COMPLETED"
            logger.info("15-Day Challenge COMPLETED! Final Equity: Rs %.2f (ROI: %.2f%%)",
                        self.state["current_equity"], self.state["metrics"]["roi_pct"])
        else:
            self.state["current_day"] += 1
            self.state["session_start_equity"] = self.state["current_equity"]

        self.save_state()
