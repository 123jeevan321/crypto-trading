"""
Web Control Panel Backend: Flask REST API, Background Trading Bot Thread, and Dashboard Server.
Runs on Port 5003 (configured in config.toml).
"""

import os
import time
import logging
import threading
from typing import Dict, Any, Optional
from datetime import datetime
from flask import Flask, render_template, jsonify, request, send_file
from flask_cors import CORS

from arena.config import get_config
from arena.engine.challenge import ChallengeManager
from arena.engine.simulation import SimulationEngine
from arena.engine.risk_manager import RiskManager
from arena.brains import get_engine
from arena.market_data.feed import MarketDataFeed
from arena.market_data.synthetic import SyntheticDataFeed
from arena.market_data.holidays import is_market_open, is_entry_allowed, IST
from arena.reports.generator import generate_report, REPORT_PATH

logger = logging.getLogger("arena.web")

# Shared thread controller
_worker_running = True

def run_trading_cycle(sim: SimulationEngine, cm: ChallengeManager, feed: Any, risk: RiskManager, is_live_market: bool = False):
    """Executes a single cycle of quote fetching, SL/TP updates, and strategy evaluation."""
    try:
        quotes = feed.fetch_quotes()
        if not quotes:
            return

        # 1. Update existing open positions (checks SL, TP, trailing, auto square-off)
        closed = sim.update_market_prices(quotes)
        for c in closed:
            logger.info("TRADE CLOSED: %s %s | Net PnL: Rs %.2f (%s)", c.side, c.symbol, c.net_pnl, c.close_reason)

        # 2. Check if challenge is actively running
        if cm.state.get("status") != "ACTIVE":
            cm.sync_sim_state(sim)
            return

        # 3. Check risk limits & open position caps
        if len(sim.positions) >= risk.max_open_positions:
            cm.sync_sim_state(sim)
            return

        # 4. Evaluate setups across watchlist
        brain_name = cm.state.get("active_brain", "auto")
        brain = get_engine(brain_name, profile_name=cm.state.get("profile_name", "balanced"))

        for sym in list(quotes.keys()):
            if len(sim.positions) >= risk.max_open_positions:
                break

            # Avoid holding duplicate positions in the same stock
            already_open = any(p.symbol == sym for p in sim.positions.values())
            if already_open:
                continue

            price = quotes[sym]
            if hasattr(feed, "generate_synthetic_history"):
                hist_df = feed.generate_synthetic_history(sym, 60)
            else:
                hist_df = feed.get_history(sym, period="5d", interval="15m")

            decision = brain.decide(sym, price, hist_df)

            if decision.action in ["BUY", "SELL"]:
                qty, alloc, reason = risk.calculate_position_size(sim.current_equity, price, len(sim.positions))
                if qty > 0:
                    decision.quantity = qty
                    sl, tp = risk.sanitize_sl_tp(decision.action, price, decision.stop_loss, decision.take_profit)
                    decision.stop_loss = sl
                    decision.take_profit = tp
                    pos = sim.execute_entry(decision, price)
                    if pos:
                        logger.info("AUTONOMOUS ENTRY: %s %d %s @ Rs %.2f [Engine: %s]",
                                    pos.side, pos.quantity, pos.symbol, pos.entry_price, pos.engine_name)

        cm.sync_sim_state(sim)

    except Exception as e:
        logger.error("Error in trading cycle: %s", e)

def background_trading_loop(sim: SimulationEngine, cm: ChallengeManager, live_feed: MarketDataFeed, synth_feed: SyntheticDataFeed, risk: RiskManager):
    """Continuously runs the trading loop in the background."""
    logger.info("Background Trading Worker started.")
    while _worker_running:
        dt = datetime.now(IST)
        market_open = is_market_open(dt)

        # On weekends or off-market hours, use synthetic feed so users can test anytime
        active_feed = live_feed if market_open else synth_feed
        run_trading_cycle(sim, cm, active_feed, risk, is_live_market=market_open)

        time.sleep(3)


def create_app(sim_engine: Optional[SimulationEngine] = None,
               challenge_mgr: Optional[ChallengeManager] = None,
               data_feed: Optional[MarketDataFeed] = None) -> Flask:

    app = Flask(__name__,
                template_folder=os.path.join(os.path.dirname(__file__), "templates"),
                static_folder=os.path.join(os.path.dirname(__file__), "static"))
    CORS(app)

    cfg = get_config()
    cm = challenge_mgr or ChallengeManager()
    sim = sim_engine or SimulationEngine(initial_capital=cm.state.get("initial_capital", 100000.0), saved_state=cm.state)
    live_feed = data_feed or MarketDataFeed(watchlist=cfg.watchlist)
    synth_feed = SyntheticDataFeed(watchlist=cfg.watchlist)
    risk = RiskManager(profile_name=cm.state.get("profile_name", "balanced"))

    # Start background daemon trading thread
    worker = threading.Thread(
        target=background_trading_loop,
        args=(sim, cm, live_feed, synth_feed, risk),
        daemon=True
    )
    worker.start()

    @app.route("/")
    def index():
        return render_template("dashboard.html", config=cfg, state=cm.state)

    @app.route("/api/status")
    def get_status():
        cm.sync_sim_state(sim)
        dt = datetime.now(IST)
        return jsonify({
            "status": cm.state.get("status", "NOT_STARTED"),
            "current_day": cm.state.get("current_day", 1),
            "target_days": cm.state.get("target_days", 15),
            "profile_name": cm.state.get("profile_name", "balanced"),
            "active_brain": cm.state.get("active_brain", "auto"),
            "initial_capital": cm.state.get("initial_capital", 100000.0),
            "current_cash": sim.cash,
            "current_equity": sim.current_equity,
            "unrealized_pnl": sim.total_unrealized_pnl,
            "realized_pnl": sim.total_realized_pnl,
            "open_positions_count": len(sim.positions),
            "is_market_open": is_market_open(dt),
            "server_time_ist": dt.strftime("%Y-%m-%d %H:%M:%S"),
            "metrics": cm.state.get("metrics", {})
        })

    @app.route("/api/positions")
    def get_positions():
        return jsonify({
            "open": [p.to_dict() for p in sim.positions.values() if p.status == "OPEN"],
            "closed": [p.to_dict() for p in sim.closed_positions]
        })

    @app.route("/api/quotes")
    def get_quotes():
        dt = datetime.now(IST)
        feed = live_feed if is_market_open(dt) else synth_feed
        quotes = feed.fetch_quotes()
        return jsonify(feed.get_all_cached_quotes())

    @app.route("/api/scan_now", methods=["POST"])
    def trigger_scan_now():
        """Force immediate strategy scan and execution."""
        dt = datetime.now(IST)
        feed = live_feed if is_market_open(dt) else synth_feed
        run_trading_cycle(sim, cm, feed, risk, is_live_market=is_market_open(dt))
        return jsonify({"success": True, "open_positions": len(sim.positions), "state": cm.state})

    @app.route("/api/challenge/start", methods=["POST"])
    def start_challenge():
        data = request.json or {}
        brain = data.get("brain", cm.state.get("active_brain", "auto"))
        profile = data.get("profile", cm.state.get("profile_name", "balanced"))
        cm.start_challenge(brain=brain, profile=profile)
        # Immediately run an initial tick
        dt = datetime.now(IST)
        feed = live_feed if is_market_open(dt) else synth_feed
        run_trading_cycle(sim, cm, feed, risk, is_live_market=is_market_open(dt))
        return jsonify({"success": True, "state": cm.state})

    @app.route("/api/challenge/pause", methods=["POST"])
    def pause_challenge():
        cm.pause_challenge()
        return jsonify({"success": True, "state": cm.state})

    @app.route("/api/challenge/reset", methods=["POST"])
    def reset_challenge():
        if os.path.exists(cm.state_file):
            try:
                os.remove(cm.state_file)
            except Exception:
                pass
        cm.state = cm._load_or_init_state()
        sim.cash = cm.state["initial_capital"]
        sim.positions.clear()
        sim.closed_positions.clear()
        return jsonify({"success": True, "state": cm.state})

    @app.route("/api/position/close/<pos_id>", methods=["POST"])
    def close_single_position(pos_id):
        if pos_id in sim.positions:
            p = sim.positions[pos_id]
            closed = sim.close_position(pos_id, p.current_price, "Manual UI Close")
            cm.sync_sim_state(sim)
            return jsonify({"success": True, "closed": closed.to_dict() if closed else None})
        return jsonify({"error": "Position not found"}), 404

    @app.route("/api/engine/select", methods=["POST"])
    def select_engine():
        data = request.json or {}
        new_brain = data.get("brain")
        if new_brain:
            cm.state["active_brain"] = new_brain
            cm.save_state()
            return jsonify({"success": True, "active_brain": new_brain})
        return jsonify({"error": "No brain specified"}), 400

    @app.route("/api/reports/generate", methods=["POST", "GET"])
    def trigger_report():
        cm.sync_sim_state(sim)
        path = generate_report(cm)
        return send_file(path)

    return app

if __name__ == "__main__":
    cfg = get_config()
    app = create_app()
    app.run(host=cfg.web_host, port=cfg.web_port, debug=False)
