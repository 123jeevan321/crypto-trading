"""
Web Control Panel Backend: Flask REST API and dashboard server for AI Trading Arena.
Runs on Port 5003 (configured in config.toml).
"""

import os
import logging
from typing import Dict, Any, Optional
from flask import Flask, render_template, jsonify, request, send_file
from flask_cors import CORS

from arena.config import get_config
from arena.engine.challenge import ChallengeManager
from arena.engine.simulation import SimulationEngine
from arena.engine.risk_manager import RiskManager
from arena.brains import get_engine
from arena.market_data.feed import MarketDataFeed
from arena.reports.generator import generate_report, REPORT_PATH

logger = logging.getLogger("arena.web")

def create_app(sim_engine: Optional[SimulationEngine] = None,
               challenge_mgr: Optional[ChallengeManager] = None,
               data_feed: Optional[MarketDataFeed] = None) -> Flask:

    app = Flask(__name__,
                template_folder=os.path.join(os.path.dirname(__file__), "templates"),
                static_folder=os.path.join(os.path.dirname(__file__), "static"))
    CORS(app)

    cfg = get_config()
    cm = challenge_mgr or ChallengeManager()
    sim = sim_engine or SimulationEngine(initial_capital=cm.state.get("initial_capital", 100000.0))
    feed = data_feed or MarketDataFeed(watchlist=cfg.watchlist)
    risk = RiskManager(profile_name=cm.state.get("profile_name", "balanced"))

    @app.route("/")
    def index():
        return render_template("dashboard.html", config=cfg, state=cm.state)

    @app.route("/api/status")
    def get_status():
        cm.sync_sim_state(sim)
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
        quotes = feed.fetch_quotes()
        return jsonify(feed.get_all_cached_quotes())

    @app.route("/api/challenge/start", methods=["POST"])
    def start_challenge():
        data = request.json or {}
        brain = data.get("brain", cm.state.get("active_brain", "auto"))
        profile = data.get("profile", cm.state.get("profile_name", "balanced"))
        cm.start_challenge(brain=brain, profile=profile)
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
