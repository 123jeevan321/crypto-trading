"""Live Order Flow, Volume Delta & Footprint Engine.

Computes real-time institutional order flow metrics:
1. Aggressive Market Buyers vs Aggressive Market Sellers (Delta)
2. Cumulative Volume Delta (CVD)
3. Order Book Liquidity Depth (Bids vs Asks Imbalance)
4. Institutional Absorption & Delta Divergence Detection
"""

import json
import urllib.request


def get_order_flow_delta(symbol="BTCUSDT", limit=500):
    """Calculates live order flow delta from raw tick-by-tick aggregated trades."""
    # Format symbol for Binance
    clean_sym = symbol.replace("/", "").replace("-", "").upper()
    if clean_sym in ("BTCUSD", "BTC"):
        clean_sym = "BTCUSDT"
    elif clean_sym in ("ETHUSD", "ETH"):
        clean_sym = "ETHUSDT"

    url = f"https://api.binance.com/api/v3/aggTrades?symbol={clean_sym}&limit={limit}"
    req = urllib.request.Request(url, headers={"User-Agent": "AntigravityOrderFlow/1.0"})

    try:
        with urllib.request.urlopen(req, timeout=4) as resp:
            trades = json.loads(resp.read().decode("utf-8"))

        buy_vol = sum(float(t["q"]) for t in trades if not t["m"])
        sell_vol = sum(float(t["q"]) for t in trades if t["m"])
        total_vol = buy_vol + sell_vol

        delta = buy_vol - sell_vol
        buy_pct = round((buy_vol / total_vol) * 100, 1) if total_vol > 0 else 50.0
        sell_pct = round(100.0 - buy_pct, 1)

        # Price movement over these trades
        first_price = float(trades[0]["p"])
        last_price = float(trades[-1]["p"])
        price_change_pct = ((last_price - first_price) / first_price) * 100

        # Absorption / Delta Divergence Check:
        # If price drops but buyers are aggressively hitting market (> 55%) -> Absorption!
        # If price rises but sellers are aggressively dumping (> 55%) -> Exhaustion!
        if price_change_pct < -0.05 and buy_pct > 58.0:
            flow_condition = "BULLISH_ABSORPTION"
            flow_label = "[ABSORPTION DETECTED]: Passive buyers absorbing market sells (Strong Reversal Up!)"
            bias = "CALL"
        elif price_change_pct > 0.05 and sell_pct > 58.0:
            flow_condition = "BEARISH_EXHAUSTION"
            flow_label = "[EXHAUSTION DETECTED]: Passive sellers absorbing market buys (Strong Reversal Down!)"
            bias = "PUT"
        elif buy_pct >= 56.0:
            flow_condition = "AGGRESSIVE_BUYING"
            flow_label = "[AGGRESSIVE BUYERS IN CONTROL]: High market buy delta"
            bias = "CALL"
        elif sell_pct >= 56.0:
            flow_condition = "AGGRESSIVE_SELLING"
            flow_label = "[AGGRESSIVE SELLERS IN CONTROL]: High market sell delta"
            bias = "PUT"
        else:
            flow_condition = "BALANCED"
            flow_label = "[EQUILIBRIUM]: Balanced buyer/seller delta"
            bias = "NEUTRAL"

        return {
            "symbol": clean_sym,
            "trades_count": len(trades),
            "last_price": last_price,
            "price_change_pct": round(price_change_pct, 3),
            "aggressive_buy_vol": round(buy_vol, 4),
            "aggressive_sell_vol": round(sell_vol, 4),
            "buy_pct": buy_pct,
            "sell_pct": sell_pct,
            "volume_delta": round(delta, 4),
            "flow_condition": flow_condition,
            "flow_label": flow_label,
            "flow_bias": bias
        }
    except Exception as e:
        return {
            "symbol": clean_sym,
            "error": str(e),
            "flow_bias": "NEUTRAL"
        }


def get_orderbook_liquidity_depth(symbol="BTCUSDT", limit=50):
    """Calculates live order book depth and bid/ask wall imbalance."""
    clean_sym = symbol.replace("/", "").replace("-", "").upper()
    if clean_sym in ("BTCUSD", "BTC"):
        clean_sym = "BTCUSDT"

    url = f"https://api.binance.com/api/v3/depth?symbol={clean_sym}&limit={limit}"
    req = urllib.request.Request(url, headers={"User-Agent": "AntigravityOrderFlow/1.0"})

    try:
        with urllib.request.urlopen(req, timeout=4) as resp:
            ob = json.loads(resp.read().decode("utf-8"))

        bid_qty = sum(float(b[1]) for b in ob.get("bids", []))
        ask_qty = sum(float(a[1]) for a in ob.get("asks", []))
        total = bid_qty + ask_qty

        bid_pct = round((bid_qty / total) * 100, 1) if total > 0 else 50.0
        ask_pct = round(100.0 - bid_pct, 1)

        return {
            "symbol": clean_sym,
            "total_bid_liquidity": round(bid_qty, 2),
            "total_ask_liquidity": round(ask_qty, 2),
            "bid_ratio_pct": bid_pct,
            "ask_ratio_pct": ask_pct,
            "book_pressure": "BULLISH_SUPPORT" if bid_pct > 58 else ("BEARISH_RESISTANCE" if ask_pct > 58 else "BALANCED")
        }
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    import json
    delta_info = get_order_flow_delta("BTCUSDT")
    book_info = get_orderbook_liquidity_depth("BTCUSDT")
    print("=== LIVE ORDER FLOW DELTA ===")
    print(json.dumps(delta_info, indent=2))
    print("=== LIVE ORDER BOOK DEPTH ===")
    print(json.dumps(book_info, indent=2))
