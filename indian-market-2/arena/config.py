"""
Configuration loader for The AI Trading Arena.
Parses config.toml and loads .env keys.
"""

import os
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

# Python 3.11+ tomllib
try:
    import tomllib
except ImportError:
    import toml as tomllib

def get_project_root() -> Path:
    return Path(__file__).resolve().parent.parent

def load_env_file():
    env_path = get_project_root() / ".env"
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())

class ArenaConfig:
    def __init__(self, config_path: str = None):
        load_env_file()
        if config_path is None:
            config_path = get_project_root() / "config.toml"
        else:
            config_path = Path(config_path)

        if config_path.exists():
            with open(config_path, "rb") as f:
                self.raw = tomllib.load(f)
        else:
            self.raw = {}

        # Challenge
        c = self.raw.get("challenge", {})
        self.challenge_name = c.get("name", "Breaking Money Challenge")
        self.virtual_capital = float(c.get("virtual_capital", 100000.0))
        self.duration_sessions = int(c.get("duration_sessions", 15))
        self.brain = c.get("brain", "auto").lower()
        self.risk_profile = c.get("risk_profile", "balanced").lower()
        self.mode = c.get("mode", "intraday").lower()
        self.strategy_note = c.get("strategy_note", "Only trade confirmed breakouts above opening range.")

        # Market
        m = self.raw.get("market", {})
        self.poll_interval = int(m.get("poll_interval_seconds", 30))
        self.decision_interval = int(m.get("decision_interval_minutes", 15))
        self.market_open = m.get("market_open", "09:15")
        self.market_close = m.get("market_close", "15:30")
        self.entry_cutoff = m.get("entry_cutoff", "14:45")
        self.square_off_time = m.get("square_off_time", "15:15")
        self.timezone = m.get("timezone", "Asia/Kolkata")
        self.feed = m.get("feed", "yahoo").lower()
        self.watchlist = m.get("watchlist", [
            "RELIANCE.NS", "HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "INFY.NS",
            "TCS.NS", "BHARTIARTL.NS", "TATASTEEL.NS", "SUZLON.NS", "PCJEWELLER.NS",
            "IRFC.NS", "HUDCO.NS", "BEL.NS", "TATAPOWER.NS", "HAL.NS"
        ])

        # Risk parameters
        r_group = self.raw.get("risk", {}).get(self.risk_profile, {})
        self.max_position_equity_pct = float(r_group.get("max_position_equity_pct", 20.0))
        self.stop_loss_pct = float(r_group.get("stop_loss_pct", 1.5))
        self.target_pct = float(r_group.get("target_pct", 3.0))
        self.max_daily_loss_pct = float(r_group.get("max_daily_loss_pct", 3.0))

        # Modeled Costs & Friction
        costs = self.raw.get("costs", {})
        self.stt_pct = float(costs.get("stt_pct", 0.025))
        self.exchange_turnover_pct = float(costs.get("exchange_turnover_pct", 0.00345))
        self.gst_pct = float(costs.get("gst_pct", 18.0))
        self.stamp_duty_pct = float(costs.get("stamp_duty_pct", 0.003))
        self.simulated_slippage_pct = float(costs.get("simulated_slippage_pct", 0.05))

        # Web UI
        w = self.raw.get("web", {})
        self.web_host = w.get("host", "127.0.0.1")
        self.web_port = int(w.get("port", 5003))
        self.web_debug = bool(w.get("debug", True))

        # API Keys
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "")

        # Aliases for convenience across modules
        self.default_brain = self.brain
        self.default_profile = self.risk_profile
        self.challenge_days = self.duration_sessions
        self.market_open_time = self.market_open
        self.entry_cutoff_time = self.entry_cutoff
        self.slippage_pct = self.simulated_slippage_pct
        self.brokerage_per_order = float(costs.get("brokerage_per_order", 0.0))
        self.stt_intraday_sell_pct = self.stt_pct
        self.turnover_charge_pct = self.exchange_turnover_pct
        self.stamp_duty_buy_pct = self.stamp_duty_pct

    def get_risk_profile(self, name: str = None) -> dict:
        p_name = (name or self.risk_profile).lower()
        profile_data = self.raw.get("risk", {}).get(p_name, {})
        return {
            "max_position_pct": float(profile_data.get("max_position_equity_pct", self.max_position_equity_pct)),
            "stop_loss_pct": float(profile_data.get("stop_loss_pct", self.stop_loss_pct)),
            "take_profit_pct": float(profile_data.get("target_pct", self.target_pct)),
            "max_daily_loss_pct": float(profile_data.get("max_daily_loss_pct", self.max_daily_loss_pct)),
            "max_open_positions": int(profile_data.get("max_open_positions", 3))
        }

# Global default config singleton
_config_instance = None

def get_config(config_path: str = None) -> ArenaConfig:
    global _config_instance
    if _config_instance is None or config_path is not None:
        _config_instance = ArenaConfig(config_path)
    return _config_instance

config = get_config()
