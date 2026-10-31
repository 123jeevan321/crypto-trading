"""
data/nse_fetcher.py
-------------------
NSEFetcher: Comprehensive data fetcher for NSE (National Stock Exchange) India.
Uses yfinance as the primary data source with optional NSE API scraping.
All timestamps are IST (Asia/Kolkata, UTC+5:30) aware.
"""

import datetime
import logging
from typing import Any, Dict, List, Optional

import pytz
import requests
import yfinance as yf

logger = logging.getLogger(__name__)

IST = pytz.timezone("Asia/Kolkata")

# NSE scraping headers — mimic a browser session to reduce blocking.
NSE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.nseindia.com/",
    "Origin": "https://www.nseindia.com",
    "Connection": "keep-alive",
}

# Sector ETF / index proxies available on yfinance
SECTOR_ETF_MAP = {
    "PHARMA": "NIFTYPHARMA.NS",
    "BANK": "^NSEBANK",
    "IT": "^CNXIT",
    "AUTO": "^CNXAUTO",
    "FMCG": "^CNXFMCG",
    "METAL": "^CNXMETAL",
    "ENERGY": "^CNXENERGY",
    "INFRA": "^CNXINFRA",
    "REALTY": "^CNXREALTY",
    "MEDIA": "^CNXMEDIA",
}

NIFTY50_COMPONENTS = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
    "HINDUNILVR", "ITC", "SBIN", "BAJFINANCE", "BHARTIARTL",
    "KOTAKBANK", "LICI", "LT", "AXISBANK", "HCLTECH",
    "ASIANPAINT", "MARUTI", "SUNPHARMA", "TITAN", "ULTRACEMCO",
    "WIPRO", "ONGC", "NTPC", "POWERGRID", "COALINDIA",
    "NESTLEIND", "BAJAJFINSV", "JSWSTEEL", "TATAMOTORS", "TATASTEEL",
    "TECHM", "ADANIENT", "ADANIPORTS", "M&M", "DRREDDY",
    "CIPLA", "DIVISLAB", "EICHERMOT", "HINDALCO", "GRASIM",
    "BPCL", "HEROMOTOCO", "TATACONSUM", "BRITANNIA", "APOLLOHOSP",
    "SBILIFE", "HDFCLIFE", "BAJAJ-AUTO", "UPL", "VEDL",
]


class NSEFetcher:
    """
    Fetches market data for NSE (National Stock Exchange) India stocks.

    Primary data source: yfinance (no credentials required).
    Secondary: NSE public REST APIs (may be rate-limited or geo-blocked).
    """

    def __init__(self, session_timeout: int = 10):
        """
        Initialise the fetcher.

        Args:
            session_timeout: HTTP request timeout in seconds.
        """
        self._timeout = session_timeout
        self._nse_session: Optional[requests.Session] = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _nse_session_obj(self) -> requests.Session:
        """Return a requests.Session pre-loaded with NSE cookies."""
        if self._nse_session is None:
            session = requests.Session()
            session.headers.update(NSE_HEADERS)
            try:
                # Fetch the homepage first to obtain necessary cookies.
                session.get("https://www.nseindia.com", timeout=self._timeout)
            except Exception as exc:
                logger.warning("Could not initialise NSE session: %s", exc)
            self._nse_session = session
        return self._nse_session

    @staticmethod
    def _ns(symbol: str) -> str:
        """Append '.NS' suffix for yfinance NSE lookups."""
        return symbol.upper() + ".NS"

    @staticmethod
    def _now_ist() -> datetime.datetime:
        """Return the current datetime in IST."""
        return datetime.datetime.now(tz=IST)

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    def get_stock_quote(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch a live quote for an NSE stock.

        Args:
            symbol: NSE ticker without suffix (e.g. 'RELIANCE').

        Returns:
            Dict with keys: symbol, price, open, high, low, prev_close,
            change, change_pct, volume, market_cap, timestamp.
        """
        try:
            ticker = yf.Ticker(self._ns(symbol))
            info = ticker.info
            fast = ticker.fast_info

            price = fast.last_price or info.get("currentPrice", 0)
            prev_close = fast.previous_close or info.get("previousClose", 0)
            change = round(price - prev_close, 2) if prev_close else 0
            change_pct = round((change / prev_close) * 100, 2) if prev_close else 0

            return {
                "symbol": symbol.upper(),
                "price": round(price, 2),
                "open": round(fast.open or info.get("open", 0), 2),
                "high": round(fast.day_high or info.get("dayHigh", 0), 2),
                "low": round(fast.day_low or info.get("dayLow", 0), 2),
                "prev_close": round(prev_close, 2),
                "change": change,
                "change_pct": change_pct,
                "volume": int(fast.three_month_average_volume or info.get("volume", 0)),
                "market_cap": info.get("marketCap", 0),
                "timestamp": self._now_ist().isoformat(),
            }
        except Exception as exc:
            logger.error("get_stock_quote(%s) failed: %s", symbol, exc)
            return {}

    def get_historical_data(
        self,
        symbol: str,
        period: str = "3mo",
        interval: str = "1d",
    ) -> List[Dict[str, Any]]:
        """
        Fetch OHLCV historical data for an NSE stock.

        Args:
            symbol: NSE ticker without suffix.
            period: yfinance period string (e.g. '3mo', '1y').
            interval: yfinance interval string (e.g. '1d', '1wk').

        Returns:
            List of dicts with keys: date, open, high, low, close, volume.
        """
        try:
            df = yf.download(
                self._ns(symbol),
                period=period,
                interval=interval,
                progress=False,
                auto_adjust=True,
            )
            if df.empty:
                return []

            records = []
            for ts, row in df.iterrows():
                records.append({
                    "date": ts.strftime("%Y-%m-%d %H:%M:%S"),
                    "open": round(float(row["Open"]), 2),
                    "high": round(float(row["High"]), 2),
                    "low": round(float(row["Low"]), 2),
                    "close": round(float(row["Close"]), 2),
                    "volume": int(row["Volume"]),
                })
            return records
        except Exception as exc:
            logger.error("get_historical_data(%s) failed: %s", symbol, exc)
            return []

    def get_intraday_data(
        self,
        symbol: str,
        period: str = "1d",
        interval: str = "5m",
    ) -> List[Dict[str, Any]]:
        """
        Fetch intraday OHLCV bars for an NSE stock.

        Args:
            symbol: NSE ticker without suffix.
            period: yfinance period string (e.g. '1d', '5d').
            interval: Bar interval (e.g. '1m', '5m', '15m').

        Returns:
            List of dicts with keys: datetime, open, high, low, close, volume.
        """
        try:
            df = yf.download(
                self._ns(symbol),
                period=period,
                interval=interval,
                progress=False,
                auto_adjust=True,
            )
            if df.empty:
                return []

            records = []
            for ts, row in df.iterrows():
                # Convert to IST
                ts_ist = ts.astimezone(IST) if ts.tzinfo else IST.localize(ts)
                records.append({
                    "datetime": ts_ist.isoformat(),
                    "open": round(float(row["Open"]), 2),
                    "high": round(float(row["High"]), 2),
                    "low": round(float(row["Low"]), 2),
                    "close": round(float(row["Close"]), 2),
                    "volume": int(row["Volume"]),
                })
            return records
        except Exception as exc:
            logger.error("get_intraday_data(%s) failed: %s", symbol, exc)
            return []

    def _fetch_nse_api(self, endpoint: str) -> Any:
        """
        Internal helper to call NSE public REST API endpoints.

        Args:
            endpoint: Full URL of the NSE API endpoint.

        Returns:
            Parsed JSON (dict or list) on success, None on failure.
        """
        try:
            session = self._nse_session_obj()
            response = session.get(endpoint, timeout=self._timeout)
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            logger.warning("NSE API call failed for %s: %s", endpoint, exc)
            return None

    def get_bulk_deals(self) -> List[Dict[str, Any]]:
        """
        Fetch bulk deals from NSE.

        Returns:
            List of dicts with deal details. Falls back to mock data if blocked.
        """
        data = self._fetch_nse_api("https://www.nseindia.com/api/bulk-deals")
        if data and isinstance(data, dict):
            return data.get("data", [])

        # Fallback mock data so the rest of the application can still function.
        logger.info("Using mock bulk-deal data (NSE API unreachable).")
        return [
            {
                "symbol": "RELIANCE",
                "client_name": "Sample Client A",
                "buy_sell": "BUY",
                "quantity": 500000,
                "price": 2850.50,
                "exchange": "NSE",
                "date": self._now_ist().strftime("%Y-%m-%d"),
                "note": "mock",
            }
        ]

    def get_block_deals(self) -> List[Dict[str, Any]]:
        """
        Fetch block deals from NSE.

        Returns:
            List of dicts with deal details. Falls back to mock data if blocked.
        """
        data = self._fetch_nse_api("https://www.nseindia.com/api/block-deals")
        if data and isinstance(data, dict):
            return data.get("data", [])

        logger.info("Using mock block-deal data (NSE API unreachable).")
        return [
            {
                "symbol": "HDFCBANK",
                "client_name": "Sample Client B",
                "buy_sell": "SELL",
                "quantity": 200000,
                "price": 1620.00,
                "exchange": "NSE",
                "date": self._now_ist().strftime("%Y-%m-%d"),
                "note": "mock",
            }
        ]

    def get_fii_dii_data(self) -> Dict[str, Any]:
        """
        Fetch FII/DII (Foreign/Domestic Institutional Investor) activity.

        Returns:
            Dict with FII and DII buy/sell/net values (INR crores).
            Falls back to mock data if NSE API is unreachable.
        """
        data = self._fetch_nse_api(
            "https://www.nseindia.com/api/fiidiiTradeReact"
        )
        if data:
            return data

        logger.info("Using mock FII/DII data.")
        today = self._now_ist().strftime("%Y-%m-%d")
        return {
            "date": today,
            "FII": {"buy": 12500.0, "sell": 11200.0, "net": 1300.0},
            "DII": {"buy": 8900.0, "sell": 7600.0, "net": 1300.0},
            "note": "mock",
        }

    def get_market_status(self) -> Dict[str, Any]:
        """
        Determine whether the NSE cash market is currently open.

        Market hours: Monday to Friday, 09:15 to 15:30 IST.

        Returns:
            Dict with keys: is_open (bool), current_time (str), session (str).
        """
        now = self._now_ist()
        market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
        market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)

        is_weekday = now.weekday() < 5  # Monday=0 … Friday=4
        in_hours = market_open <= now <= market_close

        if is_weekday and now < market_open:
            session = "Pre-Open"
        elif is_weekday and in_hours:
            session = "Regular"
        elif is_weekday and now > market_close:
            session = "Post-Close"
        else:
            session = "Closed (Weekend)"

        return {
            "is_open": is_weekday and in_hours,
            "current_time": now.strftime("%Y-%m-%d %H:%M:%S %Z"),
            "session": session,
        }

    def get_52_week_high_low(self, symbol: str) -> Dict[str, Any]:
        """
        Retrieve 52-week high and low prices for a stock.

        Args:
            symbol: NSE ticker without suffix.

        Returns:
            Dict with keys: symbol, week52_high, week52_low, current_price.
        """
        try:
            info = yf.Ticker(self._ns(symbol)).info
            return {
                "symbol": symbol.upper(),
                "week52_high": info.get("fiftyTwoWeekHigh", None),
                "week52_low": info.get("fiftyTwoWeekLow", None),
                "current_price": info.get("currentPrice", None),
            }
        except Exception as exc:
            logger.error("get_52_week_high_low(%s) failed: %s", symbol, exc)
            return {}

    def get_delivery_data(self, symbol: str) -> Dict[str, Any]:
        """
        Estimate delivery percentage for a stock.

        NSE bhavcopy delivery data requires direct file downloads; this
        implementation uses yfinance volume as a proxy and returns a
        placeholder delivery percentage.

        Args:
            symbol: NSE ticker without suffix.

        Returns:
            Dict with keys: symbol, total_volume, delivery_volume,
            delivery_pct, note.
        """
        try:
            ticker = yf.Ticker(self._ns(symbol))
            hist = ticker.history(period="1d")
            volume = int(hist["Volume"].iloc[-1]) if not hist.empty else 0
            # Delivery data not available via yfinance; return placeholder.
            return {
                "symbol": symbol.upper(),
                "total_volume": volume,
                "delivery_volume": None,
                "delivery_pct": None,
                "note": "Delivery data requires NSE bhavcopy; unavailable via yfinance.",
            }
        except Exception as exc:
            logger.error("get_delivery_data(%s) failed: %s", symbol, exc)
            return {}

    def get_circuit_breakers(self, symbols: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Identify stocks that have hit upper or lower circuit limits.

        Uses a heuristic: single-day price change >= +10% (upper) or
        <= -10% (lower) is treated as a circuit event.

        Args:
            symbols: List of NSE tickers. Defaults to a small sample set.

        Returns:
            List of dicts for stocks near/at circuit limits.
        """
        if symbols is None:
            symbols = ["YESBANK", "SUZLON", "ADANIPOWER", "IRFC", "RPOWER"]

        results = []
        for sym in symbols:
            try:
                ticker = yf.Ticker(self._ns(sym))
                hist = ticker.history(period="2d")
                if len(hist) < 2:
                    continue
                prev_close = float(hist["Close"].iloc[-2])
                last_close = float(hist["Close"].iloc[-1])
                pct = ((last_close - prev_close) / prev_close) * 100 if prev_close else 0

                if abs(pct) >= 10:
                    results.append({
                        "symbol": sym,
                        "prev_close": round(prev_close, 2),
                        "last_close": round(last_close, 2),
                        "change_pct": round(pct, 2),
                        "circuit": "UPPER" if pct >= 10 else "LOWER",
                    })
            except Exception as exc:
                logger.warning("Circuit check failed for %s: %s", sym, exc)

        return results

    def get_corporate_actions(self, symbol: str) -> Dict[str, Any]:
        """
        Retrieve upcoming and recent corporate actions for a stock.

        Args:
            symbol: NSE ticker without suffix.

        Returns:
            Dict with keys: dividends (list), splits (list).
        """
        try:
            ticker = yf.Ticker(self._ns(symbol))

            dividends = []
            for date, amount in ticker.dividends.items():
                dividends.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "amount": round(float(amount), 4),
                })

            splits = []
            for date, ratio in ticker.splits.items():
                splits.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "ratio": float(ratio),
                })

            return {
                "symbol": symbol.upper(),
                "dividends": dividends[-10:],  # last 10 dividends
                "splits": splits[-10:],         # last 10 splits
            }
        except Exception as exc:
            logger.error("get_corporate_actions(%s) failed: %s", symbol, exc)
            return {}

    def get_nifty50_data(self) -> Dict[str, Any]:
        """
        Fetch Nifty 50 index quote and its constituent tickers.

        Returns:
            Dict with keys: index (quote dict), components (list of symbols).
        """
        try:
            ticker = yf.Ticker("^NSEI")
            info = ticker.info
            fast = ticker.fast_info

            price = fast.last_price or info.get("regularMarketPrice", 0)
            prev_close = fast.previous_close or info.get("previousClose", 0)
            change = round(price - prev_close, 2) if prev_close else 0
            change_pct = round((change / prev_close) * 100, 2) if prev_close else 0

            return {
                "index": {
                    "name": "NIFTY 50",
                    "price": round(price, 2),
                    "change": change,
                    "change_pct": change_pct,
                    "high": round(fast.day_high or 0, 2),
                    "low": round(fast.day_low or 0, 2),
                    "timestamp": self._now_ist().isoformat(),
                },
                "components": NIFTY50_COMPONENTS,
            }
        except Exception as exc:
            logger.error("get_nifty50_data() failed: %s", exc)
            return {}

    def get_sector_data(self, sector: str) -> Dict[str, Any]:
        """
        Fetch performance data for a market sector using ETF/index proxies.

        Args:
            sector: Sector name key from SECTOR_ETF_MAP
                    (e.g. 'BANK', 'IT', 'PHARMA').

        Returns:
            Dict with sector quote information, or empty dict if unknown.
        """
        sector_upper = sector.upper()
        etf_ticker = SECTOR_ETF_MAP.get(sector_upper)
        if not etf_ticker:
            logger.warning("Unknown sector: %s. Available: %s", sector, list(SECTOR_ETF_MAP.keys()))
            return {}

        try:
            ticker = yf.Ticker(etf_ticker)
            info = ticker.info
            fast = ticker.fast_info

            price = fast.last_price or info.get("regularMarketPrice", 0)
            prev_close = fast.previous_close or info.get("previousClose", 0)
            change = round(price - prev_close, 2) if prev_close else 0
            change_pct = round((change / prev_close) * 100, 2) if prev_close else 0

            return {
                "sector": sector_upper,
                "ticker": etf_ticker,
                "price": round(price, 2),
                "change": change,
                "change_pct": change_pct,
                "timestamp": self._now_ist().isoformat(),
            }
        except Exception as exc:
            logger.error("get_sector_data(%s) failed: %s", sector, exc)
            return {}
