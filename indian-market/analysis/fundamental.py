"""
fundamental.py
--------------
Fundamental analysis for Indian equities using yfinance.
All figures are in Indian Rupees (INR) unless stated otherwise.
"""

import logging

logger = logging.getLogger(__name__)


class FundamentalAnalysis:
    """Fetch and score fundamental data for NSE-listed stocks via yfinance."""

    # Market cap thresholds in INR Crores
    LARGE_CAP_THRESHOLD = 20_000  # > 20,000 Cr
    MID_CAP_THRESHOLD = 5_000     # 5,000 – 20,000 Cr

    def __init__(self):
        self._info_cache: dict = {}

    # ------------------------------------------------------------------
    # Data fetch
    # ------------------------------------------------------------------

    def get_fundamentals(self, symbol: str) -> dict:
        """
        Fetch yfinance info dict for an NSE symbol.

        Parameters
        ----------
        symbol : str
            NSE ticker without suffix (e.g. "RELIANCE").

        Returns
        -------
        dict — yfinance .info dict, or empty dict on error.
        """
        try:
            import yfinance as yf

            ticker_symbol = symbol.upper() + ".NS"
            if ticker_symbol in self._info_cache:
                return self._info_cache[ticker_symbol]

            ticker = yf.Ticker(ticker_symbol)
            info = ticker.info or {}
            self._info_cache[ticker_symbol] = info
            return info
        except Exception as exc:
            logger.warning("Failed to fetch fundamentals for %s: %s", symbol, exc)
            return {}

    # ------------------------------------------------------------------
    # Individual getters
    # ------------------------------------------------------------------

    def get_pe_ratio(self, symbol: str = None, info: dict = None) -> float:
        """
        Trailing P/E ratio.

        Parameters
        ----------
        symbol : str or None
        info : dict or None — pre-fetched info dict.

        Returns
        -------
        float — P/E, or 0.0 on error/unavailable.
        """
        try:
            data = info if info is not None else self.get_fundamentals(symbol or "")
            return float(data.get("trailingPE") or data.get("forwardPE") or 0.0)
        except Exception:
            return 0.0

    def get_eps(self, symbol: str = None, info: dict = None) -> float:
        """
        Trailing EPS (earnings per share).

        Returns
        -------
        float
        """
        try:
            data = info if info is not None else self.get_fundamentals(symbol or "")
            return float(data.get("trailingEps") or data.get("forwardEps") or 0.0)
        except Exception:
            return 0.0

    def get_book_value(self, symbol: str = None, info: dict = None) -> float:
        """
        Book value per share.

        Returns
        -------
        float
        """
        try:
            data = info if info is not None else self.get_fundamentals(symbol or "")
            return float(data.get("bookValue") or 0.0)
        except Exception:
            return 0.0

    def get_promoter_holding(self, symbol: str) -> float:
        """
        Promoter holding percentage from quarterly holdings data via yfinance.

        Falls back to 0.0 if unavailable.

        Parameters
        ----------
        symbol : str

        Returns
        -------
        float — percentage (0-100)
        """
        try:
            import yfinance as yf

            ticker = yf.Ticker(symbol.upper() + ".NS")
            holders = ticker.institutional_holders
            if holders is not None and not holders.empty:
                # yfinance doesn't expose Indian promoter holding directly.
                # We approximate using major shareholders if available.
                pct_col = [c for c in holders.columns if "%" in c or "pct" in c.lower()]
                if pct_col:
                    total = float(holders[pct_col[0]].sum())
                    return round(min(total * 100, 100.0), 2)
            return 0.0
        except Exception:
            return 0.0

    def get_debt_equity(self, symbol: str = None, info: dict = None) -> float:
        """
        Debt-to-equity ratio.

        Returns
        -------
        float
        """
        try:
            data = info if info is not None else self.get_fundamentals(symbol or "")
            return float(data.get("debtToEquity") or 0.0)
        except Exception:
            return 0.0

    def get_roe(self, symbol: str = None, info: dict = None) -> float:
        """
        Return on Equity (as percentage, e.g. 18.5 means 18.5%).

        Returns
        -------
        float
        """
        try:
            data = info if info is not None else self.get_fundamentals(symbol or "")
            roe = data.get("returnOnEquity")
            if roe is None:
                return 0.0
            return round(float(roe) * 100, 2)  # yfinance returns decimal
        except Exception:
            return 0.0

    def get_market_cap_category(self, symbol: str = None, info: dict = None) -> str:
        """
        Classify stock by market capitalisation (NSE convention).

        Thresholds (INR Crores):
            Large Cap : > 20,000 Cr
            Mid Cap   : 5,000 – 20,000 Cr
            Small Cap : < 5,000 Cr

        Returns
        -------
        str: "LARGE_CAP" | "MID_CAP" | "SMALL_CAP"
        """
        try:
            data = info if info is not None else self.get_fundamentals(symbol or "")
            market_cap_inr = float(data.get("marketCap") or 0.0)
            # yfinance market cap is in INR for .NS tickers
            market_cap_cr = market_cap_inr / 1e7  # convert to crores

            if market_cap_cr >= self.LARGE_CAP_THRESHOLD:
                return "LARGE_CAP"
            elif market_cap_cr >= self.MID_CAP_THRESHOLD:
                return "MID_CAP"
            return "SMALL_CAP"
        except Exception:
            return "SMALL_CAP"

    def is_fundamentally_sound(self, symbol: str = None, info: dict = None) -> bool:
        """
        Quick health-check: reasonable PE, positive EPS, manageable debt.

        Returns
        -------
        bool
        """
        try:
            data = info if info is not None else self.get_fundamentals(symbol or "")
            pe = self.get_pe_ratio(info=data)
            eps = self.get_eps(info=data)
            de = self.get_debt_equity(info=data)

            reasonable_pe = 0 < pe < 50 if pe > 0 else False
            positive_eps = eps > 0
            low_debt = de < 2.0 if de > 0 else True  # no debt data = assume OK

            return reasonable_pe and positive_eps and low_debt
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Composite score
    # ------------------------------------------------------------------

    def get_fundamental_score(self, symbol: str, info: dict = None) -> float:
        """
        Composite fundamental score (0-100).

        Scoring:
            +20 PE < 25 (or sector avg proxy)
            +20 positive EPS
            +20 ROE > 15%
            +20 debt/equity < 1
            +20 promoter holding > 50%

        Parameters
        ----------
        symbol : str
        info : dict or None — pre-fetched info dict.

        Returns
        -------
        float
        """
        score = 0.0
        try:
            data = info if info is not None else self.get_fundamentals(symbol)
            pe = self.get_pe_ratio(info=data)
            eps = self.get_eps(info=data)
            roe = self.get_roe(info=data)
            de = self.get_debt_equity(info=data)
            promoter = self.get_promoter_holding(symbol)

            # +20 PE < 25
            if 0 < pe < 25:
                score += 20
            elif 25 <= pe < 40:
                score += 10

            # +20 positive EPS
            if eps > 0:
                score += 20

            # +20 ROE > 15%
            if roe > 15:
                score += 20
            elif roe > 10:
                score += 10

            # +20 debt/equity < 1
            if 0 <= de < 1:
                score += 20
            elif de < 2:
                score += 10

            # +20 promoter holding > 50%
            if promoter > 50:
                score += 20
            elif promoter > 35:
                score += 10

        except Exception as exc:
            logger.warning("Fundamental score error for %s: %s", symbol, exc)

        return round(min(score, 100.0), 2)
