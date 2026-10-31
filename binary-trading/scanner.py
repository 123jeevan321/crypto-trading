"""Quotex 20-Pair Live Signal Scanner & Decision Engine.

Scans the top 20 currency pairs, evaluates the 5 institutional binary strategies,
and produces ranked CALL / PUT recommendations with 80%–95%+ confluence ratings.
Provides direct helper functions for on-demand manual trading calls.
"""

import concurrent.futures
import sys
import time
from config import QUOTEX_PAIRS, MIN_PAYOUT_THRESHOLD
from forex_sessions import get_current_sessions
from market_data import analyze_market_snapshot
from news_calendar import check_current_news_status
from strategies import analyze_confluence


def scan_single_pair(pair_config, news_status=None):
    """Fetches snapshot and analyzes confluence for a single pair."""
    try:
        news = news_status or check_current_news_status()
        data = analyze_market_snapshot(pair_config)
        if not data:
            return None
        return analyze_confluence(data, news)
    except Exception:
        return None


def run_full_market_scan(limit=20):
    """Scans all eligible Quotex pairs in parallel and ranks them by signal quality."""
    start_time = time.time()
    session_info = get_current_sessions()
    news_status = check_current_news_status()

    eligible_pairs = [p for p in QUOTEX_PAIRS if p["payout"] >= MIN_PAYOUT_THRESHOLD][:limit]

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        future_to_pair = {
            executor.submit(scan_single_pair, p, news_status): p
            for p in eligible_pairs
        }
        for future in concurrent.futures.as_completed(future_to_pair):
            res = future.result()
            if res:
                results.append(res)

    actionable = [r for r in results if r["signal"] in ("CALL", "PUT")]
    neutral = [r for r in results if r["signal"] not in ("CALL", "PUT")]

    actionable.sort(key=lambda x: (x["confidence_pct"], x["payout"]), reverse=True)
    neutral.sort(key=lambda x: x["payout"], reverse=True)

    ranked_signals = actionable + neutral
    elapsed = round(time.time() - start_time, 2)

    return {
        "scan_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "scan_duration_sec": elapsed,
        "total_pairs_scanned": len(ranked_signals),
        "actionable_signals_count": len(actionable),
        "session": session_info,
        "news": news_status,
        "signals": ranked_signals
    }


def get_best_signal():
    """Returns the single highest-probability actionable trade right now."""
    scan = run_full_market_scan(20)
    signals = scan["signals"]
    actionable = [s for s in signals if s["signal"] in ("CALL", "PUT")]
    if actionable:
        return {
            "status": "FOUND",
            "best_trade": actionable[0],
            "session": scan["session"]
        }
    return {
        "status": "NO_CLEAR_SIGNAL",
        "message": "Market is currently consolidating or neutral across pairs. Wait for next 5m candle close.",
        "top_pairs_monitored": [s["symbol"] for s in signals[:5]],
        "session": scan["session"]
    }


def check_pair_signal(symbol):
    """Analyzes a specific currency pair requested by the user."""
    target_symbol = symbol.strip().upper().replace("_", "/").replace("-", "/")
    if "/" not in target_symbol and len(target_symbol) == 6:
        target_symbol = target_symbol[:3] + "/" + target_symbol[3:]

    pair_cfg = next((p for p in QUOTEX_PAIRS if p["symbol"] == target_symbol), None)
    if not pair_cfg:
        # Default lookup with yahoo ticker
        pair_cfg = {
            "symbol": target_symbol,
            "ticker": f"{target_symbol.replace('/', '')}=X",
            "payout": 85,
            "category": "Custom"
        }

    return scan_single_pair(pair_cfg)


if __name__ == "__main__":
    import json
    if len(sys.argv) > 1:
        pair_input = sys.argv[1]
        res = check_pair_signal(pair_input)
        print(json.dumps(res, indent=2))
    else:
        best = get_best_signal()
        print(json.dumps(best, indent=2))
