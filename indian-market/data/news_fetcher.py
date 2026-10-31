"""
data/news_fetcher.py
--------------------
NewsFetcher: Retrieves market news, economic events, and commodity data
for the J1 Trader Indian stock market portal.

Data sources:
  - Google News RSS feed (via feedparser)
  - yfinance (commodities and forex)
"""

import logging
from typing import Any, Dict, List

import feedparser
import yfinance as yf

logger = logging.getLogger(__name__)

# Maximum news items returned per category.
MAX_NEWS_ITEMS = 20

# Google News RSS base URL
GNEWS_RSS_BASE = "https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"

# Commodity / forex tickers on yfinance
COMMODITY_TICKERS = {
    "gold_usd": "GC=F",
    "crude_oil_usd": "CL=F",
    "usd_inr": "USDINR=X",
    "silver_usd": "SI=F",
    "natural_gas_usd": "NG=F",
}

# Static economic calendar — update quarterly or connect to a live API.
ECONOMIC_CALENDAR = [
    {
        "event": "RBI Monetary Policy Committee (MPC) Meeting",
        "date": "2025-02-07",
        "expected": "Repo Rate Decision",
        "importance": "HIGH",
    },
    {
        "event": "India GDP Growth Rate (Q3 FY25)",
        "date": "2025-02-28",
        "expected": "~6.5%",
        "importance": "HIGH",
    },
    {
        "event": "India CPI Inflation (January 2025)",
        "date": "2025-02-12",
        "expected": "~5.0%",
        "importance": "HIGH",
    },
    {
        "event": "India IIP (Industrial Production - December 2024)",
        "date": "2025-02-12",
        "expected": "~3.5%",
        "importance": "MEDIUM",
    },
    {
        "event": "India WPI Inflation (January 2025)",
        "date": "2025-02-14",
        "expected": "~2.5%",
        "importance": "MEDIUM",
    },
    {
        "event": "US Federal Reserve FOMC Meeting",
        "date": "2025-03-19",
        "expected": "Interest Rate Decision",
        "importance": "HIGH",
    },
    {
        "event": "India Union Budget Presentation",
        "date": "2025-02-01",
        "expected": "FY26 Budget",
        "importance": "HIGH",
    },
    {
        "event": "RBI MPC Meeting",
        "date": "2025-04-07",
        "expected": "Repo Rate Decision",
        "importance": "HIGH",
    },
    {
        "event": "India GDP Growth Rate (Q4 FY25)",
        "date": "2025-05-30",
        "expected": "~6.8%",
        "importance": "HIGH",
    },
]

# Sector news search queries
SECTOR_NEWS_QUERIES = {
    "Banking": "Indian banking sector HDFC SBI ICICI",
    "IT": "Indian IT sector TCS Infosys Wipro",
    "Pharma": "Indian pharma sector Sun Pharma DrReddy Cipla",
    "Auto": "Indian automobile sector Maruti Tata Motors",
    "Energy": "Indian energy sector NTPC Power Grid Adani",
    "Metals": "Indian metals sector SAIL Tata Steel Hindalco",
    "FMCG": "Indian FMCG sector HUL ITC Nestle",
}


class NewsFetcher:
    """
    Fetches news headlines, economic events, and commodity data
    relevant to the Indian stock market.
    """

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_rss(query: str) -> List[Dict[str, Any]]:
        """
        Parse Google News RSS for a given search query.

        Args:
            query: URL-encoded search query string.

        Returns:
            List of news item dicts.
        """
        url = GNEWS_RSS_BASE.format(query=query.replace(" ", "+"))
        try:
            feed = feedparser.parse(url)
            items = []
            for entry in feed.entries[:MAX_NEWS_ITEMS]:
                items.append({
                    "title": getattr(entry, "title", ""),
                    "summary": getattr(entry, "summary", ""),
                    "link": getattr(entry, "link", ""),
                    "published": getattr(entry, "published", ""),
                    "source": getattr(entry, "source", {}).get("title", "Google News"),
                })
            return items
        except Exception as exc:
            logger.error("RSS parse failed for query '%s': %s", query, exc)
            return []

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    def get_market_news(self) -> List[Dict[str, Any]]:
        """
        Fetch general NSE / Indian stock market news.

        Returns:
            List of up to MAX_NEWS_ITEMS news dicts with keys:
            title, summary, link, published, source.
        """
        return self._parse_rss("NSE India stock market")

    def get_stock_news(self, symbol: str) -> List[Dict[str, Any]]:
        """
        Fetch news specific to a single stock.

        Args:
            symbol: NSE ticker (e.g. 'RELIANCE').

        Returns:
            List of up to MAX_NEWS_ITEMS news dicts.
        """
        query = f"{symbol.upper()} NSE India stock"
        return self._parse_rss(query)

    def get_economic_events(self) -> List[Dict[str, Any]]:
        """
        Return a static calendar of upcoming Indian economic events.

        This list should be updated quarterly. Future versions may pull
        from a live economic calendar API.

        Returns:
            List of event dicts with keys: event, date, expected, importance.
        """
        return ECONOMIC_CALENDAR

    def get_commodity_data(self) -> Dict[str, Any]:
        """
        Fetch current prices for key commodities and the USD/INR rate.

        Commodities covered:
          - Gold (GC=F)
          - Crude Oil WTI (CL=F)
          - Silver (SI=F)
          - Natural Gas (NG=F)
          - USD/INR forex rate (USDINR=X)

        Returns:
            Dict mapping commodity names to price dicts
            (price, change, change_pct, currency).
        """
        result = {}
        for name, ticker_sym in COMMODITY_TICKERS.items():
            try:
                ticker = yf.Ticker(ticker_sym)
                fast = ticker.fast_info

                price = fast.last_price or 0
                prev_close = fast.previous_close or 0
                change = round(price - prev_close, 4) if prev_close else 0
                change_pct = round((change / prev_close) * 100, 2) if prev_close else 0

                currency = "INR" if "inr" in name.lower() else "USD"
                result[name] = {
                    "ticker": ticker_sym,
                    "price": round(price, 4),
                    "change": change,
                    "change_pct": change_pct,
                    "currency": currency,
                }
            except Exception as exc:
                logger.error("Commodity fetch failed for %s (%s): %s", name, ticker_sym, exc)
                result[name] = {"ticker": ticker_sym, "price": None, "error": str(exc)}

        return result

    def get_sector_news(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Fetch news headlines grouped by market sector.

        Sectors covered: Banking, IT, Pharma, Auto, Energy, Metals, FMCG.

        Returns:
            Dict mapping sector name to list of news dicts.
        """
        sector_data: Dict[str, List[Dict[str, Any]]] = {}
        for sector, query in SECTOR_NEWS_QUERIES.items():
            sector_data[sector] = self._parse_rss(query)
        return sector_data
