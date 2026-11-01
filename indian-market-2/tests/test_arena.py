"""
Comprehensive Test Suite for Breaking Money AI Trading Arena.
"""

import os
import unittest
import pandas as pd
from datetime import datetime, time
import pytz

from arena.config import get_config
from arena.brains.rules import RulesEngine
from arena.brains.auto import AutoFallbackEngine
from arena.engine.risk_manager import RiskManager
from arena.engine.simulation import SimulationEngine, Position
from arena.engine.challenge import ChallengeManager
from arena.web.app import create_app

class TestArenaComponents(unittest.TestCase):

    def setUp(self):
        self.cfg = get_config()
        self.risk = RiskManager("balanced")
        self.sim = SimulationEngine(initial_capital=100000.0)

    def test_risk_manager_position_sizing(self):
        # 20% of 1,00,000 = 20,000 max capital per trade
        price = 500.0
        qty, alloc, reason = self.risk.calculate_position_size(100000.0, price, 0)
        self.assertEqual(qty, 40)
        self.assertEqual(alloc, 20000.0)

        # Max open positions limit = 3
        qty_blocked, _, _ = self.risk.calculate_position_size(100000.0, price, 3)
        self.assertEqual(qty_blocked, 0)

    def test_friction_and_charges(self):
        turnover = 20000.0
        charges = self.sim.calculate_charges("BUY", turnover, is_entry=True)
        # Brokerage (0) + Turnover (20000 * 0.0000345 = 0.69) + GST (18% of 0.69 = 0.12) + Stamp Duty (20000 * 0.00003 = 0.60) = ~1.41
        self.assertGreater(charges, 0.0)
        self.assertLess(charges, 50.0)

    def test_rules_engine_decide(self):
        engine = RulesEngine("balanced")
        self.assertTrue(engine.is_available())

        # Test with synthetic uptrending dataframe
        dates = pd.date_range("2026-10-01", periods=60, freq="15min")
        data = {
            "Open": [100.0 + i * 0.5 for i in range(60)],
            "High": [101.0 + i * 0.5 for i in range(60)],
            "Low": [99.5 + i * 0.5 for i in range(60)],
            "Close": [100.8 + i * 0.5 for i in range(60)],
            "Volume": [100000 for _ in range(60)]
        }
        df = pd.DataFrame(data, index=dates)
        curr_price = 135.0
        decision = engine.decide("RELIANCE", curr_price, df)
        self.assertIn(decision.action, ["BUY", "SELL", "HOLD"])

    def test_auto_fallback_engine(self):
        auto = AutoFallbackEngine("balanced")
        self.assertTrue(auto.is_available())
        selected = auto.get_selected_engine()
        self.assertIsNotNone(selected)

    def test_web_app_endpoints(self):
        app = create_app(sim_engine=self.sim)
        client = app.test_client()

        res_home = client.get("/")
        self.assertEqual(res_home.status_code, 200)

        res_status = client.get("/api/status")
        self.assertEqual(res_status.status_code, 200)
        data = res_status.get_json()
        self.assertEqual(data["initial_capital"], 100000.0)

        res_pos = client.get("/api/positions")
        self.assertEqual(res_pos.status_code, 200)

if __name__ == "__main__":
    unittest.main()
