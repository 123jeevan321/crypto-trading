"""Quotex 20-Pair Live Signal Scanner.

Scans the top 20 currency pairs, evaluates the 5 institutional binary strategies,
and produces ranked CALL / PUT recommendations with 80%–95%+ confluence ratings.
"""

import concurrent.futures
import time
from config import QUOTEX_PAIRS, MIN_PAYOUT_THRESHOLD
from forex_sessions import get_current_sessions
from market_data import analyze_market_snapshot
from news_calendar import check_current_news_status
from strategies import analyze_confluence


def scan_single_pair(pair_config, news_status):
    """Fetches snapshot and analyzes confluence for a single pair."""
    try:
        data = analyze_market_snapshot(pair_config)
        if not data:
            return None
        return analyze_confluence(data, news_status)
    except Exception as e:
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

    # Sort results: First by CALL/PUT signals (excluding Neutral), then by Confidence %, then by Payout %
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


if __name__ == "__main__":
    import json
    report = run_full_market_scan(5)
    print(json.dumps(report, indent=2))
