"""
data/angel_one.py
-----------------
AngelOneClient: Interface to Angel One SmartAPI for live trading data
and order placement.

By default (USE_ANGEL_ONE = False) all methods fall back to yfinance so
the rest of the application works without credentials.

To activate live SmartAPI integration:
  1. Install the library:  pip install smartapi-python
  2. Set credentials in config.py.
  3. Set USE_ANGEL_ONE = True in config.py.
  4. Uncomment the SmartAPI code blocks below.
"""

import logging
from typing import Any, Dict, List, Optional

import yfinance as yf

try:
    import sys
    sys.path.insert(0, ".")
    import config
except ImportError:
    # Fallback defaults when config module is not importable.
    class config:  # type: ignore[no-redef]
        USE_ANGEL_ONE = False
        ANGEL_ONE_API_KEY = ""
        ANGEL_ONE_CLIENT_ID = ""
        ANGEL_ONE_PASSWORD = ""
        ANGEL_ONE_TOTP = ""

logger = logging.getLogger(__name__)

IST_TZ = "Asia/Kolkata"


class AngelOneClient:
    """
    Wrapper around Angel One SmartAPI with automatic yfinance fallback.

    Usage (paper / demo mode — no credentials required):
        client = AngelOneClient()
        quote = client.get_live_quote("RELIANCE")

    Usage (live mode — requires valid config.py credentials):
        # 1. Set USE_ANGEL_ONE = True in config.py.
        # 2. Uncomment the SmartAPI blocks in this file.
        # 3. pip install smartapi-python
        client = AngelOneClient()
        client.login()
        quote = client.get_live_quote("RELIANCE")
    """

    def __init__(self) -> None:
        """
        Initialise client.

        Checks config.USE_ANGEL_ONE to decide whether to attempt
        SmartAPI login or remain in yfinance-fallback mode.
        """
        self._use_angel = config.USE_ANGEL_ONE
        self._smart_api = None          # SmartAPI session object (when enabled)
        self._auth_token: str = ""
        self._feed_token: str = ""
        self._is_logged_in: bool = False

        if self._use_angel:
            logger.info("AngelOneClient: SmartAPI mode selected. Call login() to authenticate.")
        else:
            logger.info("AngelOneClient: yfinance fallback mode (USE_ANGEL_ONE=False).")

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def login(self) -> bool:
        """
        Authenticate with Angel One SmartAPI.

        Requires config.py to have valid:
          - ANGEL_ONE_API_KEY
          - ANGEL_ONE_CLIENT_ID
          - ANGEL_ONE_PASSWORD
          - ANGEL_ONE_TOTP  (TOTP secret, not the 6-digit code)

        Returns:
            True on success, False on failure.

        Replace with SmartAPI calls when API key is configured:
        ----------------------------------------------------------
        from SmartApi import SmartConnect
        import pyotp

        totp_code = pyotp.TOTP(config.ANGEL_ONE_TOTP).now()
        smart = SmartConnect(api_key=config.ANGEL_ONE_API_KEY)
        session_data = smart.generateSession(
            config.ANGEL_ONE_CLIENT_ID,
            config.ANGEL_ONE_PASSWORD,
            totp_code,
        )
        self._auth_token = session_data["data"]["jwtToken"]
        self._feed_token = smart.getfeedToken()
        self._smart_api = smart
        self._is_logged_in = True
        ----------------------------------------------------------
        """
        if not self._use_angel:
            logger.warning("login() called but USE_ANGEL_ONE=False. No-op.")
            return False

        if not all([
            config.ANGEL_ONE_API_KEY,
            config.ANGEL_ONE_CLIENT_ID,
            config.ANGEL_ONE_PASSWORD,
            config.ANGEL_ONE_TOTP,
        ]):
            logger.error(
                "Angel One credentials are not set in config.py. "
                "Staying in yfinance fallback mode."
            )
            return False

        # --- Uncomment below when smartapi-python is installed ---
        # try:
        #     from SmartApi import SmartConnect
        #     import pyotp
        #
        #     totp_code = pyotp.TOTP(config.ANGEL_ONE_TOTP).now()
        #     smart = SmartConnect(api_key=config.ANGEL_ONE_API_KEY)
        #     session_data = smart.generateSession(
        #         config.ANGEL_ONE_CLIENT_ID,
        #         config.ANGEL_ONE_PASSWORD,
        #         totp_code,
        #     )
        #     if session_data.get("status"):
        #         self._auth_token = session_data["data"]["jwtToken"]
        #         self._feed_token = smart.getfeedToken()
        #         self._smart_api = smart
        #         self._is_logged_in = True
        #         logger.info("Angel One SmartAPI login successful.")
        #         return True
        #     else:
        #         logger.error("SmartAPI login failed: %s", session_data.get("message"))
        #         return False
        # except Exception as exc:
        #     logger.error("SmartAPI login exception: %s", exc)
        #     return False

        logger.warning("SmartAPI login: uncomment SmartAPI code block in angel_one.py.")
        return False

    def logout(self) -> None:
        """
        Terminate the SmartAPI session.

        Replace with SmartAPI calls when API key is configured:
        ----------------------------------------------------------
        if self._smart_api and self._is_logged_in:
            self._smart_api.terminateSession(config.ANGEL_ONE_CLIENT_ID)
        ----------------------------------------------------------
        """
        self._is_logged_in = False
        self._smart_api = None
        logger.info("AngelOneClient logged out (or session cleared).")

    # ------------------------------------------------------------------
    # Market Data
    # ------------------------------------------------------------------

    def get_live_quote(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch a live market quote.

        Args:
            symbol: NSE ticker without suffix (e.g. 'RELIANCE').

        Returns:
            Dict with price, open, high, low, prev_close, volume.

        Replace with SmartAPI calls when API key is configured:
        ----------------------------------------------------------
        exchange_type = 1  # NSE cash segment
        token = self._lookup_token(symbol)   # map symbol -> SmartAPI token
        params = {"exchange": "NSE", "tradingsymbol": symbol, "symboltoken": token}
        quote = self._smart_api.ltpData(params["exchange"], params["tradingsymbol"], params["symboltoken"])
        return quote["data"]
        ----------------------------------------------------------
        """
        if self._use_angel and self._is_logged_in:
            # Replace with SmartAPI calls when API key is configured:
            # token = self._lookup_token(symbol)
            # quote = self._smart_api.ltpData("NSE", symbol, token)
            # return quote.get("data", {})
            pass

        # yfinance fallback
        try:
            ticker = yf.Ticker(symbol.upper() + ".NS")
            info = ticker.info
            fast = ticker.fast_info
            price = fast.last_price or info.get("currentPrice", 0)
            prev_close = fast.previous_close or info.get("previousClose", 0)
            return {
                "symbol": symbol.upper(),
                "price": round(price, 2),
                "open": round(fast.open or 0, 2),
                "high": round(fast.day_high or 0, 2),
                "low": round(fast.day_low or 0, 2),
                "prev_close": round(prev_close, 2),
                "volume": int(fast.three_month_average_volume or 0),
                "source": "yfinance",
            }
        except Exception as exc:
            logger.error("get_live_quote(%s) yfinance fallback failed: %s", symbol, exc)
            return {}

    def get_historical_data(
        self,
        symbol: str,
        interval: str = "1d",
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch OHLCV historical bars.

        Args:
            symbol:    NSE ticker without suffix.
            interval:  Bar interval. SmartAPI values: 'ONE_DAY', 'ONE_HOUR',
                       'FIFTEEN_MINUTE', etc. yfinance values: '1d', '1h', '15m'.
            from_date: Start date string 'YYYY-MM-DD'. Defaults to 90 days ago.
            to_date:   End date string 'YYYY-MM-DD'. Defaults to today.

        Returns:
            List of OHLCV dicts.

        Replace with SmartAPI calls when API key is configured:
        ----------------------------------------------------------
        token = self._lookup_token(symbol)
        params = {
            "exchange": "NSE",
            "symboltoken": token,
            "interval": interval,      # use SmartAPI interval constants
            "fromdate": from_date + " 09:15",
            "todate": to_date + " 15:30",
        }
        candles = self._smart_api.getCandleData(params)
        # candles["data"] returns list of [timestamp, o, h, l, c, vol]
        return [
            {"datetime": c[0], "open": c[1], "high": c[2],
             "low": c[3], "close": c[4], "volume": c[5]}
            for c in candles.get("data", [])
        ]
        ----------------------------------------------------------
        """
        if self._use_angel and self._is_logged_in:
            # Replace with SmartAPI calls when API key is configured.
            pass

        # yfinance fallback
        try:
            # Map SmartAPI interval tokens to yfinance equivalents.
            interval_map = {
                "ONE_MINUTE": "1m",
                "THREE_MINUTE": "3m",
                "FIVE_MINUTE": "5m",
                "TEN_MINUTE": "10m",
                "FIFTEEN_MINUTE": "15m",
                "THIRTY_MINUTE": "30m",
                "ONE_HOUR": "1h",
                "ONE_DAY": "1d",
            }
            yf_interval = interval_map.get(interval.upper(), interval)

            kwargs: Dict[str, Any] = {
                "progress": False,
                "auto_adjust": True,
                "interval": yf_interval,
            }
            if from_date and to_date:
                kwargs["start"] = from_date
                kwargs["end"] = to_date
            else:
                kwargs["period"] = "3mo"

            df = yf.download(symbol.upper() + ".NS", **kwargs)
            if df.empty:
                return []

            records = []
            for ts, row in df.iterrows():
                records.append({
                    "datetime": ts.strftime("%Y-%m-%d %H:%M:%S"),
                    "open": round(float(row["Open"]), 2),
                    "high": round(float(row["High"]), 2),
                    "low": round(float(row["Low"]), 2),
                    "close": round(float(row["Close"]), 2),
                    "volume": int(row["Volume"]),
                    "source": "yfinance",
                })
            return records
        except Exception as exc:
            logger.error("get_historical_data(%s) yfinance fallback failed: %s", symbol, exc)
            return []

    # ------------------------------------------------------------------
    # Order Placement (Paper Trading)
    # ------------------------------------------------------------------

    def place_order(
        self,
        symbol: str,
        qty: int,
        direction: str,
        order_type: str = "MARKET",
        price: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Place a buy or sell order.

        In paper trading mode (USE_ANGEL_ONE=False) the order is logged
        and a simulated acknowledgement is returned.

        Args:
            symbol:     NSE ticker without suffix (e.g. 'RELIANCE').
            qty:        Number of shares.
            direction:  'BUY' or 'SELL'.
            order_type: 'MARKET', 'LIMIT', 'SL', 'SL-M'.
            price:      Limit / stop-loss price (0 for MARKET orders).

        Returns:
            Dict with order_id, status, message, and trade details.

        Replace with SmartAPI calls when API key is configured:
        ----------------------------------------------------------
        token = self._lookup_token(symbol)
        order_params = {
            "variety": "NORMAL",
            "tradingsymbol": symbol,
            "symboltoken": token,
            "transactiontype": direction,  # "BUY" or "SELL"
            "exchange": "NSE",
            "ordertype": order_type,
            "producttype": "INTRADAY",     # or "DELIVERY"
            "duration": "DAY",
            "price": str(price),
            "quantity": str(qty),
        }
        response = self._smart_api.placeOrder(order_params)
        return response
        ----------------------------------------------------------
        """
        direction = direction.upper()
        order_type = order_type.upper()

        # Fetch approximate current price for the paper trade record.
        try:
            current_price = yf.Ticker(symbol.upper() + ".NS").fast_info.last_price or price
        except Exception:
            current_price = price

        effective_price = price if (order_type == "LIMIT" and price > 0) else current_price
        trade_value = round(effective_price * qty, 2)

        paper_order = {
            "order_id": f"PAPER-{symbol.upper()}-{direction}-{qty}",
            "symbol": symbol.upper(),
            "direction": direction,
            "qty": qty,
            "order_type": order_type,
            "price": round(effective_price, 2),
            "trade_value": trade_value,
            "status": "PAPER_EXECUTED",
            "message": f"[PAPER] Order placed: {direction} {qty} x {symbol.upper()} @ {effective_price:.2f}",
            "source": "paper_trading",
        }

        print(paper_order["message"])
        logger.info(paper_order["message"])

        return paper_order

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def is_connected(self) -> bool:
        """Return True if logged in to SmartAPI, False in fallback mode."""
        return self._use_angel and self._is_logged_in

    def get_profile(self) -> Dict[str, Any]:
        """
        Fetch the broker account profile.

        Replace with SmartAPI calls when API key is configured:
        ----------------------------------------------------------
        profile = self._smart_api.getProfile(self._refresh_token)
        return profile.get("data", {})
        ----------------------------------------------------------
        """
        if self._use_angel and self._is_logged_in:
            # Replace with SmartAPI calls when API key is configured.
            pass

        return {
            "client_id": config.ANGEL_ONE_CLIENT_ID or "DEMO_USER",
            "name": "Paper Trader",
            "email": "",
            "mode": "paper",
            "source": "yfinance_fallback",
        }

    def get_holdings(self) -> List[Dict[str, Any]]:
        """
        Retrieve current portfolio holdings from the broker.

        Replace with SmartAPI calls when API key is configured:
        ----------------------------------------------------------
        holdings = self._smart_api.holding()
        return holdings.get("data", [])
        ----------------------------------------------------------
        """
        if self._use_angel and self._is_logged_in:
            # Replace with SmartAPI calls when API key is configured.
            pass

        logger.info("get_holdings(): paper mode — returning empty list.")
        return []

    def get_positions(self) -> List[Dict[str, Any]]:
        """
        Retrieve open intraday positions.

        Replace with SmartAPI calls when API key is configured:
        ----------------------------------------------------------
        positions = self._smart_api.position()
        return positions.get("data", [])
        ----------------------------------------------------------
        """
        if self._use_angel and self._is_logged_in:
            # Replace with SmartAPI calls when API key is configured.
            pass

        logger.info("get_positions(): paper mode — returning empty list.")
        return []
