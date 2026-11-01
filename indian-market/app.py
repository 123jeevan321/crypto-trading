"""
app.py
------
Main Flask application for J1 Trader — Indian Stock Market Portal.

Serves the UI and exposes a comprehensive REST API backed by:
  - MarketStatusChecker  : live NSE market status + VIX mood
  - NewsFetcher          : market news, commodities
  - NSEFetcher           : bulk deals, FII/DII, circuit breakers, Nifty 50
  - SwingSignalEngine    : multi-day swing trade signals
  - IntradaySignalEngine : intraday trade signals
  - Nifty50Analysis      : spot price, trend, PCR, gainers/losers
  - PaperTradingEngine   : paper portfolio management

Run:
    python app.py
"""

from __future__ import annotations

import logging
import os
import sys
import threading
import datetime
from typing import Any, Dict

import pytz
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS

# ---------------------------------------------------------------------------
# Path setup — allow sibling-package imports from this directory.
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.dirname(__file__))

# ---------------------------------------------------------------------------
# Module imports (each wrapped in try/except so the server starts even when
# an optional dependency or module is temporarily broken).
# ---------------------------------------------------------------------------

try:
    from data.news_fetcher import NewsFetcher
    _news_fetcher = NewsFetcher()
except Exception as _e:
    logging.warning("NewsFetcher unavailable: %s", _e)
    _news_fetcher = None  # type: ignore[assignment]

try:
    from data.nse_fetcher import NSEFetcher
    _nse_fetcher = NSEFetcher()
except Exception as _e:
    logging.warning("NSEFetcher unavailable: %s", _e)
    _nse_fetcher = None  # type: ignore[assignment]

try:
    from signals.swing_signal import SwingSignalEngine
    _swing_engine = SwingSignalEngine()
except Exception as _e:
    logging.warning("SwingSignalEngine unavailable: %s", _e)
    _swing_engine = None  # type: ignore[assignment]

# IntradaySignalEngine — may not exist yet; degrade gracefully.
try:
    from signals.intraday_signal import IntradaySignalEngine
    _intraday_engine = IntradaySignalEngine()
except Exception as _e:
    logging.warning("IntradaySignalEngine unavailable: %s", _e)
    _intraday_engine = None  # type: ignore[assignment]

# Nifty50Analysis
try:
    from analysis.nifty50_options import Nifty50Analysis
    _nifty50_analysis = Nifty50Analysis()
except Exception as _e:
    logging.warning("Nifty50Analysis unavailable: %s", _e)
    _nifty50_analysis = None  # type: ignore[assignment]

# PaperTradingEngine
try:
    from signals.paper_trade import PaperTradingEngine
    _paper_trading = PaperTradingEngine()
except Exception as _e:
    logging.warning("PaperTradingEngine unavailable: %s", _e)
    _paper_trading = None  # type: ignore[assignment]

# MarketStatusChecker
try:
    from signals.market_status import MarketStatusChecker
    _market_status_checker = MarketStatusChecker()
except Exception as _e:
    logging.warning("MarketStatusChecker unavailable (will use NSEFetcher): %s", _e)
    _market_status_checker = None  # type: ignore[assignment]

# IPO Modules
try:
    from data.ipo_fetcher import IPOFetcher
    from analysis.ipo_engine import IPOEngine
    _ipo_fetcher = IPOFetcher()
    _ipo_engine = IPOEngine(num_accounts=3)
except Exception as _e:
    logging.warning("IPO modules unavailable: %s", _e)
    _ipo_fetcher = None
    _ipo_engine = None

# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("j1trader.app")

IST = pytz.timezone("Asia/Kolkata")

# ---------------------------------------------------------------------------
# Flask app
# ---------------------------------------------------------------------------
app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), "ui", "templates"),
    static_folder=os.path.join(os.path.dirname(__file__), "ui", "static"),
)
CORS(app)

# ---------------------------------------------------------------------------
# Signal cache (refreshed every 5 minutes in a background thread)
# ---------------------------------------------------------------------------
_signal_cache: Dict[str, Any] = {
    "swing": [],
    "intraday": [],
    "last_refresh": None,
}
_cache_lock = threading.Lock()


def _refresh_signals() -> None:
    """Populate the in-memory signal cache."""
    logger.info("Refreshing signal cache …")
    swing: list = []
    intraday: list = []

    if _swing_engine is not None:
        try:
            swing = _swing_engine.generate_signals()
        except Exception as exc:
            logger.error("Swing signal refresh failed: %s", exc)

    if _intraday_engine is not None:
        try:
            intraday = _intraday_engine.generate_signals()
        except Exception as exc:
            logger.error("Intraday signal refresh failed: %s", exc)

    now_ist = datetime.datetime.now(IST).isoformat()
    with _cache_lock:
        _signal_cache["swing"] = swing
        _signal_cache["intraday"] = intraday
        _signal_cache["last_refresh"] = now_ist

    logger.info(
        "Signal cache refreshed — swing: %d, intraday: %d",
        len(swing),
        len(intraday),
    )


def _background_refresh_loop() -> None:
    """Run signal refresh every 5 minutes, forever, in a daemon thread."""
    _refresh_signals()          # Immediate first run on startup
    interval = 5 * 60          # 5 minutes
    timer = threading.Event()
    while True:
        timer.wait(interval)   # Non-blocking sleep
        _refresh_signals()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _success(data: Any) -> Any:
    """Wrap data in a standard success envelope."""
    return jsonify({
        "success": True,
        "data": data,
        "timestamp": datetime.datetime.now(IST).isoformat(),
    })


def _error(message: str, status: int = 500) -> Any:
    """Wrap an error message in a standard error envelope."""
    return jsonify({
        "success": False,
        "error": message,
        "timestamp": datetime.datetime.now(IST).isoformat(),
    }), status


def _market_status_data() -> Dict[str, Any]:
    """Return market-status dict, using MarketStatusChecker or NSEFetcher."""
    if _market_status_checker is not None:
        try:
            return _market_status_checker.get_status()
        except Exception:
            pass

    # Fallback: NSEFetcher
    if _nse_fetcher is not None:
        base = _nse_fetcher.get_market_status()
        now_ist = datetime.datetime.now(IST)
        return {
            "is_open": base.get("is_open", False),
            "session": base.get("session", "Unknown"),
            "ist_time": now_ist.strftime("%Y-%m-%d %H:%M:%S IST"),
            "mood": "Bullish" if base.get("is_open") else "Closed",
            "vix": 0.0,
        }

    # Bare minimum when nothing is available
    now_ist = datetime.datetime.now(IST)
    weekday = now_ist.weekday() < 5
    market_open_time = now_ist.replace(hour=9, minute=15, second=0, microsecond=0)
    market_close_time = now_ist.replace(hour=15, minute=30, second=0, microsecond=0)
    is_open = weekday and market_open_time <= now_ist <= market_close_time
    return {
        "is_open": is_open,
        "session": "Regular" if is_open else "Closed",
        "ist_time": now_ist.strftime("%Y-%m-%d %H:%M:%S IST"),
        "mood": "Active" if is_open else "Closed",
        "vix": 0.0,
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    """Serve the main UI."""
    try:
        return render_template("index.html")
    except Exception as exc:
        logger.error("Template render failed: %s", exc)
        return (
            "<h2>J1 Trader — Backend Running</h2>"
            "<p>UI template not found. Place <code>index.html</code> in "
            "<code>ui/templates/</code>.</p>",
            200,
        )


@app.route("/api/market-status")
def api_market_status():
    """GET /api/market-status — Live NSE market status."""
    try:
        data = _market_status_data()
        return _success(data)
    except Exception as exc:
        logger.exception("api_market_status error")
        return _error(str(exc))


@app.route("/api/news")
def api_news():
    """GET /api/news — Last 20 market news items."""
    try:
        if _news_fetcher is None:
            return _error("NewsFetcher not available", 503)
        news = _news_fetcher.get_market_news()
        return _success(news[:20])
    except Exception as exc:
        logger.exception("api_news error")
        return _error(str(exc))


@app.route("/api/commodities")
def api_commodities():
    """GET /api/commodities — Gold, Crude Oil, USD/INR."""
    try:
        if _news_fetcher is None:
            return _error("NewsFetcher not available", 503)
        data = _news_fetcher.get_commodity_data()
        return _success(data)
    except Exception as exc:
        logger.exception("api_commodities error")
        return _error(str(exc))


@app.route("/api/bulk-deals")
def api_bulk_deals():
    """GET /api/bulk-deals — Last 10 NSE bulk deals."""
    try:
        if _nse_fetcher is None:
            return _error("NSEFetcher not available", 503)
        deals = _nse_fetcher.get_bulk_deals()
        return _success(deals[:10])
    except Exception as exc:
        logger.exception("api_bulk_deals error")
        return _error(str(exc))


@app.route("/api/fii-dii")
def api_fii_dii():
    """GET /api/fii-dii — FII / DII net activity."""
    try:
        if _nse_fetcher is None:
            return _error("NSEFetcher not available", 503)
        data = _nse_fetcher.get_fii_dii_data()
        return _success(data)
    except Exception as exc:
        logger.exception("api_fii_dii error")
        return _error(str(exc))


@app.route("/api/circuit-breakers")
def api_circuit_breakers():
    """GET /api/circuit-breakers — Stocks that hit upper/lower circuit."""
    try:
        if _nse_fetcher is None:
            return _error("NSEFetcher not available", 503)
        data = _nse_fetcher.get_circuit_breakers()
        return _success(data)
    except Exception as exc:
        logger.exception("api_circuit_breakers error")
        return _error(str(exc))


@app.route("/api/swing-signals")
def api_swing_signals():
    """GET /api/swing-signals — Multi-day swing trade signal cards (15 curated institutional setups)."""
    try:
        with _cache_lock:
            signals = list(_signal_cache["swing"])

        if not signals and _swing_engine is not None:
            signals = _swing_engine.generate_signals()
            with _cache_lock:
                _signal_cache["swing"] = signals

        return _success(signals)
    except Exception as exc:
        logger.exception("api_swing_signals error")
        return _error(str(exc))


@app.route("/api/intraday-signals")
def api_intraday_signals():
    """GET /api/intraday-signals — Intraday signal cards (15 curated setups: BUY & SELL)."""
    try:
        with _cache_lock:
            signals = list(_signal_cache["intraday"])

        if not signals and _intraday_engine is not None:
            signals = _intraday_engine.generate_signals()
            with _cache_lock:
                _signal_cache["intraday"] = signals

        return _success(signals)
    except Exception as exc:
        logger.exception("api_intraday_signals error")
        return _error(str(exc))


@app.route("/api/alerts")
def api_alerts():
    """GET /api/alerts — Real-time event notifications from trader-alerts skill."""
    try:
        from analysis.skills_engine import SkillsPipelineEngine
        pipeline = getattr(_swing_engine, "pipeline", None) or getattr(_intraday_engine, "pipeline", None)
        alerts = pipeline.alerts_log if pipeline else []
        return _success(alerts)
    except Exception as exc:
        logger.exception("api_alerts error")
        return _error(str(exc))


@app.route("/api/backtest/results")
def api_backtest_results():
    """GET /api/backtest/results — Comprehensive strategy backtesting and empirical validation."""
    try:
        from analysis.backtester import backtester
        results = backtester.simulate_historical_validation()
        return _success(results)
    except Exception as exc:
        logger.exception("api_backtest_results error")
        return _error(str(exc))


@app.route("/api/re-rank", methods=["POST", "GET"])
def api_re_rank():
    """POST /api/re-rank — Forces immediate news re-ranking and setup invalidation check."""
    try:
        _refresh_signals()
        with _cache_lock:
            swing_count = len(_signal_cache["swing"])
            intraday_count = len(_signal_cache["intraday"])
        return _success({
            "message": "Re-ranking completed successfully",
            "qualified_swing_setups": swing_count,
            "qualified_intraday_setups": intraday_count,
            "timestamp": datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")
        })
    except Exception as exc:
        logger.exception("api_re_rank error")
        return _error(str(exc))


@app.route("/api/nifty50")
def api_nifty50():
    """GET /api/nifty50 — Nifty 50 spot price, trend, PCR, bias, gainers/losers."""
    try:
        if _nifty50_analysis is not None:
            try:
                data = _nifty50_analysis.get_full_analysis()
                return _success(data)
            except Exception as inner_exc:
                logger.warning("Nifty50Analysis.get_full_analysis() failed: %s", inner_exc)

        # Fallback: NSEFetcher
        if _nse_fetcher is not None:
            data = _nse_fetcher.get_nifty50_data()
            return _success(data)

        return _error("Nifty 50 analysis not available", 503)
    except Exception as exc:
        logger.exception("api_nifty50 error")
        return _error(str(exc))


@app.route("/api/nifty50/gainers-losers")
def api_nifty50_gainers_losers():
    """GET /api/nifty50/gainers-losers — Top 5 Nifty 50 gainers and losers."""
    try:
        if _nifty50_analysis is not None:
            try:
                data = _nifty50_analysis.get_gainers_losers(top_n=5)
                return _success(data)
            except Exception as inner_exc:
                logger.warning(
                    "Nifty50Analysis.get_gainers_losers() failed: %s", inner_exc
                )

        # Fallback: NSEFetcher components with live quotes
        if _nse_fetcher is not None:
            from data.nse_fetcher import NIFTY50_COMPONENTS
            quotes = []
            for sym in NIFTY50_COMPONENTS[:30]:  # Limit to avoid timeout
                try:
                    q = _nse_fetcher.get_stock_quote(sym)
                    if q:
                        quotes.append(q)
                except Exception:
                    pass
            if quotes:
                sorted_quotes = sorted(
                    quotes, key=lambda x: x.get("change_pct", 0), reverse=True
                )
                return _success({
                    "gainers": sorted_quotes[:5],
                    "losers": sorted_quotes[-5:][::-1],
                })

        return _error("Gainers/Losers data not available", 503)
    except Exception as exc:
        logger.exception("api_nifty50_gainers_losers error")
        return _error(str(exc))


# ---------------------------------------------------------------------------
# Portfolio routes
# ---------------------------------------------------------------------------

@app.route("/api/portfolio")
def api_portfolio():
    """GET /api/portfolio — Full paper portfolio overview."""
    try:
        if _paper_trading is None:
            return _error("PaperTradingEngine not available", 503)
        data = _paper_trading.get_portfolio()
        return _success(data)
    except Exception as exc:
        logger.exception("api_portfolio error")
        return _error(str(exc))


@app.route("/api/portfolio/positions")
def api_portfolio_positions():
    """GET /api/portfolio/positions — Open positions with live P&L."""
    try:
        if _paper_trading is None:
            return _error("PaperTradingEngine not available", 503)
        data = _paper_trading.get_open_positions()
        return _success(data)
    except Exception as exc:
        logger.exception("api_portfolio_positions error")
        return _error(str(exc))


@app.route("/api/portfolio/history")
def api_portfolio_history():
    """GET /api/portfolio/history — Closed trade history."""
    try:
        if _paper_trading is None:
            return _error("PaperTradingEngine not available", 503)
        data = _paper_trading.get_trade_history()
        return _success(data)
    except Exception as exc:
        logger.exception("api_portfolio_history error")
        return _error(str(exc))


@app.route("/api/portfolio/trade", methods=["POST"])
def api_portfolio_trade():
    """POST /api/portfolio/trade — Open a new paper trade.

    Body JSON:
        {
            "signal_id": str,
            "symbol":    str,
            "direction": "BUY" | "SELL",
            "entry":     float,
            "qty":       int
        }
    """
    try:
        if _paper_trading is None:
            return _error("PaperTradingEngine not available", 503)

        body = request.get_json(force=True, silent=True) or {}
        signal_id = body.get("signal_id", "")
        symbol = body.get("symbol", "")
        direction = body.get("direction", "BUY")
        entry = float(body.get("entry", 0))
        qty = int(body.get("qty", 0))

        if not symbol or entry <= 0 or qty <= 0:
            return _error("Invalid trade parameters. Provide symbol, entry > 0, qty > 0.", 400)

        result = _paper_trading.open_trade(
            signal_id=signal_id,
            symbol=symbol,
            direction=direction,
            entry_price=entry,
            quantity=qty,
        )
        return _success(result)
    except Exception as exc:
        logger.exception("api_portfolio_trade error")
        return _error(str(exc))


@app.route("/api/portfolio/close", methods=["POST"])
def api_portfolio_close():
    """POST /api/portfolio/close — Close an open paper trade.

    Body JSON:
        {
            "symbol":     str,
            "exit_price": float,
            "reason":     str   (optional)
        }
    """
    try:
        if _paper_trading is None:
            return _error("PaperTradingEngine not available", 503)

        body = request.get_json(force=True, silent=True) or {}
        symbol = body.get("symbol", "")
        exit_price = float(body.get("exit_price", 0))
        reason = body.get("reason", "Manual close")

        if not symbol or exit_price <= 0:
            return _error("Invalid close parameters. Provide symbol and exit_price > 0.", 400)

        result = _paper_trading.close_trade(
            symbol=symbol,
            exit_price=exit_price,
            reason=reason,
        )
        return _success(result)
    except Exception as exc:
        logger.exception("api_portfolio_close error")
        return _error(str(exc))


@app.route("/api/portfolio/stats")
def api_portfolio_stats():
    """GET /api/portfolio/stats — Portfolio performance statistics."""
    try:
        if _paper_trading is None:
            return _error("PaperTradingEngine not available", 503)
        data = _paper_trading.get_performance_stats()
        return _success(data)
    except Exception as exc:
        logger.exception("api_portfolio_stats error")
        return _error(str(exc))


# ---------------------------------------------------------------------------
# Stock detail
# ---------------------------------------------------------------------------

@app.route("/api/stock/<symbol>")
def api_stock_detail(symbol: str):
    """GET /api/stock/<symbol> — Full stock data: quote + technical + SMC + fundamentals."""
    try:
        if _nse_fetcher is None:
            return _error("NSEFetcher not available", 503)

        symbol = symbol.upper().strip()

        # 1. Live quote
        quote = _nse_fetcher.get_stock_quote(symbol)

        # 2. Historical OHLCV (3 months, daily)
        hist = _nse_fetcher.get_historical_data(symbol, period="3mo", interval="1d")

        # 3. Technical scores
        technical_score: float = 0.0
        technical_trend: str = "SIDEWAYS"
        support_resistance: Dict[str, Any] = {}
        if hist:
            try:
                import pandas as pd
                from analysis.technical import TechnicalAnalysis
                df = pd.DataFrame(hist)
                df.rename(
                    columns={
                        "open": "Open",
                        "high": "High",
                        "low": "Low",
                        "close": "Close",
                        "volume": "Volume",
                    },
                    inplace=True,
                )
                ta = TechnicalAnalysis(df)
                technical_score = ta.get_technical_score()
                technical_trend = ta.get_trend_direction()
                support_resistance = ta.get_support_resistance()
            except Exception as te:
                logger.warning("TechnicalAnalysis failed for %s: %s", symbol, te)

        # 4. SMC scores
        smc_score: float = 0.0
        smc_bias: str = "NEUTRAL"
        smc_details: Dict[str, Any] = {}
        if hist:
            try:
                import pandas as pd
                from analysis.smc_analysis import SMCAnalysis
                df = pd.DataFrame(hist)
                df.rename(
                    columns={
                        "open": "Open",
                        "high": "High",
                        "low": "Low",
                        "close": "Close",
                        "volume": "Volume",
                    },
                    inplace=True,
                )
                smc = SMCAnalysis(df)
                smc_score = smc.get_smc_score()
                smc_bias = smc.get_smc_bias()
                smc_details = {
                    "order_blocks": smc.find_order_blocks(lookback=20)[-5:],
                    "fair_value_gaps": smc.find_fair_value_gaps(lookback=15)[-5:],
                    "choch": smc.find_choch(),
                    "premium_discount": smc.find_premium_discount_zones(),
                }
            except Exception as se:
                logger.warning("SMCAnalysis failed for %s: %s", symbol, se)

        # 5. Corporate actions / fundamentals
        corp_actions: Dict[str, Any] = {}
        week52: Dict[str, Any] = {}
        try:
            corp_actions = _nse_fetcher.get_corporate_actions(symbol)
            week52 = _nse_fetcher.get_52_week_high_low(symbol)
        except Exception as ce:
            logger.warning("Corporate actions fetch failed for %s: %s", symbol, ce)

        # 6. Stock-specific news
        news: list = []
        if _news_fetcher is not None:
            try:
                news = _news_fetcher.get_stock_news(symbol)[:5]
            except Exception:
                pass

        return _success({
            "symbol": symbol,
            "quote": quote,
            "week52": week52,
            "technical": {
                "score": technical_score,
                "trend": technical_trend,
                "support_resistance": support_resistance,
            },
            "smc": {
                "score": smc_score,
                "bias": smc_bias,
                **smc_details,
            },
            "corporate_actions": corp_actions,
            "news": news,
        })
    except Exception as exc:
        logger.exception("api_stock_detail(%s) error", symbol)
        return _error(str(exc))


# ---------------------------------------------------------------------------
# IPO Endpoints (Mainboard NSE Only & Multi-Account Optimizer)
# ---------------------------------------------------------------------------

@app.route("/api/ipo/list", methods=["GET"])
def api_ipo_list() -> Any:
    """Return list of active and upcoming NSE Mainboard IPOs."""
    try:
        if _ipo_fetcher is None:
            return _service_unavailable("IPOFetcher")
        ipos = _ipo_fetcher.get_mainboard_ipos()
        return _success(ipos)
    except Exception as exc:
        logger.exception("api_ipo_list error")
        return _error(str(exc))


@app.route("/api/ipo/strategy", methods=["GET"])
def api_ipo_strategy() -> Any:
    """Return mathematical allotment optimization across 3 family accounts."""
    try:
        if _ipo_fetcher is None or _ipo_engine is None:
            return _service_unavailable("IPO Engine")
        ipos = _ipo_fetcher.get_mainboard_ipos()
        evaluations = _ipo_engine.evaluate_all_ipos(ipos)
        return _success(evaluations)
    except Exception as exc:
        logger.exception("api_ipo_strategy error")
        return _error(str(exc))


@app.route("/api/ipo/calculate", methods=["POST"])
def api_ipo_calculate() -> Any:
    """Calculate customized allotment probabilities for user-entered values."""
    try:
        if _ipo_engine is None:
            return _service_unavailable("IPO Engine")
        data = request.get_json(force=True, silent=True) or {}
        accounts = int(data.get("accounts", 3))
        retail_sub = float(data.get("retail_sub", 1.0))
        shni_sub = float(data.get("shni_sub", 1.0))
        gmp_pct = float(data.get("gmp_pct", 5.0))
        lot_size = int(data.get("lot_size", 10))
        price = float(data.get("price", 500))

        min_inv = price * lot_size
        p_retail_1 = 1.0 if retail_sub <= 1.0 else (1.0 / retail_sub)
        p_accounts = 1.0 if p_retail_1 >= 1.0 else (1.0 - ((1.0 - p_retail_1) ** accounts))
        p_shni = 1.0 if shni_sub <= 1.0 and shni_sub > 0 else (1.0 / shni_sub if shni_sub > 0 else 0.5)

        profit_lot = (price * (gmp_pct / 100.0)) * lot_size

        return _success({
            "accounts": accounts,
            "min_investment_1lot": min_inv,
            "total_capital_deployed": min_inv * accounts,
            "prob_1_account_pct": round(p_retail_1 * 100, 1),
            "prob_all_accounts_pct": round(p_accounts * 100, 1),
            "prob_shni_pct": round(p_shni * 100, 1),
            "profit_per_lot": round(profit_lot, 0),
            "recommendation": "RETAIL MULTI-ACCOUNT" if p_accounts > p_shni else "sHNI CATEGORY"
        })
    except Exception as exc:
        logger.exception("api_ipo_calculate error")
        return _error(str(exc))


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

def _start_background_thread() -> None:
    """Launch the signal-refresh daemon thread."""
    thread = threading.Thread(
        target=_background_refresh_loop,
        name="SignalRefreshThread",
        daemon=True,
    )
    thread.start()
    logger.info("Background signal-refresh thread started (interval: 5 min).")


if __name__ == "__main__":
    port = 5002
    now_ist = datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")
    logger.info("=" * 60)
    logger.info(" J1 Trader — Indian Stock Market Portal")
    logger.info(" Starting on  : http://0.0.0.0:%d", port)
    logger.info(" Startup time : %s", now_ist)
    logger.info("=" * 60)

    _start_background_thread()

    app.run(debug=True, port=port, host="0.0.0.0", use_reloader=False)
