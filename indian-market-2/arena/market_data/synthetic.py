"""
Synthetic / Fictional Market Data Generator for Offline Demo Mode
(python -m arena demo)
"""

import random
from datetime import datetime, timedelta
import pandas as pd
from typing import Dict, List

DEFAULT_BASELINE_PRICES = {
    "RELIANCE": 1165.0,
    "HDFCBANK": 692.0,
    "ICICIBANK": 1398.0,
    "SBIN": 962.0,
    "INFY": 1185.0,
    "TCS": 2505.0,
    "BHARTIARTL": 1975.0,
    "TATASTEEL": 168.0,
    "SUZLON": 34.0,
    "PCJEWELLER": 15.5,
    "IRFC": 73.5,
    "HUDCO": 143.0,
    "BEL": 370.0,
    "TATAPOWER": 345.0,
    "HAL": 4850.0
}

class SyntheticDataFeed:
    """Generates realistic tick movements and synthetic bars for demo mode."""
    def __init__(self, watchlist: List[str] = None):
        self.watchlist = [s.replace(".NS", "") for s in (watchlist or list(DEFAULT_BASELINE_PRICES.keys()))]
        self.prices: Dict[str, float] = {
            s: DEFAULT_BASELINE_PRICES.get(s, 100.0) for s in self.watchlist
        }
        self.prev_close = dict(self.prices)

    def fetch_quotes(self) -> Dict[str, float]:
        """Simulate realistic 0.1% - 0.4% price fluctuations."""
        for sym in self.watchlist:
            drift = random.uniform(-0.003, 0.0035)
            self.prices[sym] = round(self.prices[sym] * (1.0 + drift), 2)
        return dict(self.prices)

    def get_cached_quote(self, symbol: str) -> Dict:
        clean_sym = symbol.replace(".NS", "")
        price = self.prices.get(clean_sym, 100.0)
        p_close = self.prev_close.get(clean_sym, price)
        chg_pct = round(((price - p_close) / p_close) * 100, 2)
        return {
            "symbol": clean_sym,
            "price": price,
            "change_pct": chg_pct,
            "prev_close": p_close
        }

    def get_all_cached_quotes(self) -> Dict[str, Dict]:
        return {s: self.get_cached_quote(s) for s in self.watchlist}

    def generate_synthetic_history(self, symbol: str, n_bars: int = 60) -> pd.DataFrame:
        clean_sym = symbol.replace(".NS", "")
        base_p = self.prices.get(clean_sym, 100.0)
        dates = [datetime.now() - timedelta(minutes=15 * i) for i in range(n_bars)][::-1]

        data = []
        curr = base_p * 0.96
        for dt in dates:
            o = round(curr * random.uniform(0.995, 1.005), 2)
            c = round(o * random.uniform(0.99, 1.015), 2)
            h = round(max(o, c) * random.uniform(1.0, 1.01), 2)
            l = round(min(o, c) * random.uniform(0.99, 1.0), 2)
            v = random.randint(50000, 500000)
            data.append({"Open": o, "High": h, "Low": l, "Close": c, "Volume": v})
            curr = c

        return pd.DataFrame(data, index=dates)

    def get_history(self, symbol: str, period: str = "1mo", interval: str = "1d") -> pd.DataFrame:
        """Generate synthetic OHLCV bars."""
        clean_sym = symbol.replace(".NS", "")
        base_p = self.prices.get(clean_sym, 100.0)

        n_bars = 20
        dates = [datetime.now() - timedelta(days=i) for i in range(n_bars)][::-1]

        data = []
        curr = base_p * 0.95
        for dt in dates:
            o = round(curr * random.uniform(0.99, 1.01), 2)
            c = round(o * random.uniform(0.985, 1.025), 2)
            h = round(max(o, c) * random.uniform(1.0, 1.015), 2)
            l = round(min(o, c) * random.uniform(0.985, 1.0), 2)
            v = random.randint(500000, 3000000)
            data.append({"Open": o, "High": h, "Low": l, "Close": c, "Volume": v},)
            curr = c

        df = pd.DataFrame(data, index=dates)
        return df
