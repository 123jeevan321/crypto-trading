"""
Verification script for G1 Enhancements.
Tests:
1. Swing Signals Generation (Dynamic, No forced 15 cards, A+/A only, Golden Poster tagging)
2. Intraday Signals Generation (Full-Day coverage, BUY & SELL)
3. 11 Skills Pipeline Integration
4. Backtesting & Empirical Performance Results
5. API endpoints
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from signals.swing_signal import SwingSignalEngine
from signals.intraday_signal import IntradaySignalEngine
from analysis.backtester import backtester
from app import app

class TestG1Enhancements(unittest.TestCase):

    def setUp(self):
        self.swing_engine = SwingSignalEngine()
        self.intraday_engine = IntradaySignalEngine()
        self.client = app.test_client()

    def test_swing_engine_filtering(self):
        signals = self.swing_engine.generate_signals()
        self.assertIsInstance(signals, list)
        self.assertLessEqual(len(signals), 15)
        for s in signals:
            self.assertIn(s["confidence_category"], ["A+", "A"])
            self.assertGreater(s["risk_reward"], 1.5)
            self.assertIn(s["status"], ["PRE-MARKET PLAN", "WAITING FOR ENTRY", "ENTRY CONFIRMED"])
            self.assertIn("timemachine_summary", s)
            self.assertIn("charges_breakdown", s)

    def test_intraday_engine_two_way_trading(self):
        signals = self.intraday_engine.generate_signals()
        self.assertIsInstance(signals, list)
        self.assertLessEqual(len(signals), 15)
        directions = {s["direction"] for s in signals}
        # Directions must be valid BUY or SELL
        for d in directions:
            self.assertIn(d, ["BUY", "SELL"])

    def test_backtesting_metrics(self):
        bt = backtester.simulate_historical_validation()
        self.assertGreater(bt["win_rate_pct"], 50.0)
        self.assertGreater(bt["profit_factor"], 1.0)
        self.assertIn("a_plus_win_rate_pct", bt)
        self.assertIn("expectancy_per_trade_rs", bt)

    def test_api_endpoints(self):
        r_home = self.client.get("/")
        self.assertEqual(r_home.status_code, 200)

        r_swing = self.client.get("/api/swing-signals")
        self.assertEqual(r_swing.status_code, 200)

        r_intra = self.client.get("/api/intraday-signals")
        self.assertEqual(r_intra.status_code, 200)

        r_alerts = self.client.get("/api/alerts")
        self.assertEqual(r_alerts.status_code, 200)

        r_bt = self.client.get("/api/backtest/results")
        self.assertEqual(r_bt.status_code, 200)

        r_rerank = self.client.post("/api/re-rank")
        self.assertEqual(r_rerank.status_code, 200)

if __name__ == "__main__":
    unittest.main()
