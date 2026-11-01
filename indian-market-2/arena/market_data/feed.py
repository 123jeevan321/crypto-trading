"""
Market Data Feed: Live Yahoo Finance / NSE quotes.
"""

import logging
from typing import Dict, List, Optional
import pandas as pd
import warnings
warnings.simplefilter('ignore')

try:
    import yfinance as yf
except ImportError:
    yf = None

logger = logging.getLogger("arena.feed")

class MarketDataFeed:
    def __init__(self, watchlist: List[str]):
        self.watchlist = [s if s.endswith(".NS") else f"{s}.NS" for s in watchlist]
        self._cached_quotes: Dict[str, Dict] = {}

    def fetch_quotes(self) -> Dict[str, float]:
        """Fetch latest market quotes for all symbols in watchlist."""
        price_map = {}
        if yf is None or not self.watchlist:
            return price_map

        try:
            df = yf.download(self.watchlist, period="5d", progress=False)
            if "Close" in df and not df["Close"].empty:
                latest = df["Close"].iloc[-1]
                prev = df["Close"].iloc[-2] if len(df["Close"]) >= 2 else latest

                for sym in self.watchlist:
                    clean_sym = sym.replace(".NS", "")
                    if sym in latest and not str(latest[sym]) == "nan":
                        curr_p = round(float(latest[sym]), 2)
                        prev_p = round(float(prev[sym]), 2) if sym in prev else curr_p
                        chg_pct = round(((curr_p - prev_p) / prev_p) * 100, 2) if prev_p > 0 else 0.0

                        price_map[clean_sym] = curr_p
                        self._cached_quotes[clean_sym] = {
                            "symbol": clean_sym,
                            "price": curr_p,
                            "change_pct": chg_pct,
                            "prev_close": prev_p
                        }
        except Exception as e:
            logger.warning("Error fetching live quotes: %s", e)

        return price_map

    def get_cached_quote(self, symbol: str) -> Optional[Dict]:
        clean_sym = symbol.replace(".NS", "")
        return self._cached_quotes.get(clean_sym)

    def get_all_cached_quotes(self) -> Dict[str, Dict]:
        if not self._cached_quotes:
            self.fetch_quotes()
        return dict(self._cached_quotes)

    def get_history(self, symbol: str, period: str = "1mo", interval: str = "1d") -> pd.DataFrame:
        """Fetch historical bars for a single symbol."""
        sym_ns = symbol if symbol.endswith(".NS") else f"{symbol}.NS"
        if yf is None:
            return pd.DataFrame()
        try:
            ticker = yf.Ticker(sym_ns)
            df = ticker.history(period=period, interval=interval)
            return df
        except Exception as e:
            logger.warning("Error fetching history for %s: %s", symbol, e)
            return pd.DataFrame()
