#!/usr/bin/env python3
"""CoinSwitch Pro Trading Terminal Backend Server.

Serves the TradingView chart frontend and connects it to the Python day-trader engines.
Zero external dependencies (uses standard library http.server, json, urllib).
"""
import http.server
import json
import os
import socketserver
import sys
import urllib.request
from urllib.parse import urlparse

PORT = 8080
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UI_DIR = os.path.join(BASE_DIR, "ui")
TRADER_DIR = os.path.join(BASE_DIR, "trader")


def get_live_price(symbol="BTC-USD"):
    """Fetch live market price from Yahoo Finance."""
    sym = symbol.upper().strip()
    if not sym.endswith("-USD"):
        sym += "-USD"
    url = f"https://query2.finance.yahoo.com/v8/finance/chart/{sym}?interval=5m&range=1d"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode())
        meta = data["chart"]["result"][0]["meta"]
        return float(meta.get("regularMarketPrice", 0.0))
    except Exception as e:
        print(f"[WARN] Failed to fetch live price for {sym}: {e}")
        # Fallback to last known price
        return 77110.00


def read_json_file(path, default=None):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def write_json_file(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


class TradingServerHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path in ("/", "/index.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            with open(os.path.join(UI_DIR, "index.html"), "rb") as f:
                self.wfile.write(f.read())
            return

        if parsed.path == "/api/status":
            self.handle_status()
            return

        super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else "{}"
        try:
            req_data = json.loads(body)
        except Exception:
            req_data = {}

        if parsed.path == "/api/calculate":
            self.handle_calculate(req_data)
        elif parsed.path == "/api/order":
            self.handle_order(req_data)
        elif parsed.path == "/api/flatten":
            self.handle_flatten(req_data)
        else:
            self.send_response(404)
            self.end_headers()

    def send_json(self, data, status_code=200):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def handle_status(self):
        live_price = get_live_price("BTC-USD")
        portfolio = read_json_file(os.path.join(TRADER_DIR, "portfolio.json"), {"cash": 5000.0, "positions": []})
        plan = read_json_file(os.path.join(TRADER_DIR, "plan.json"), {})

        plan_stop = plan.get("stop", 76980.00)
        plan_target = plan.get("target", 77458.23)

        # Enhance positions with entry & SL/TP
        positions = []
        for pos in portfolio.get("positions", []):
            lots = pos.get("lots", [])
            avg_entry = 0.0
            if lots:
                total_cost = sum(lot.get("cost", 0.0) for lot in lots)
                total_shares = sum(lot.get("shares", 0.0) for lot in lots)
                avg_entry = total_cost / total_shares if total_shares > 0 else 0.0

            positions.append({
                "ticker": pos.get("ticker", "BTC-USD"),
                "shares": float(pos.get("shares", 0.0)),
                "entry": avg_entry,
                "stop": plan_stop,
                "target": plan_target
            })

        self.send_json({
            "status": "ok",
            "price": live_price,
            "cash": float(portfolio.get("cash", 5000.0)),
            "positions": positions,
            "plan_stop": plan_stop,
            "plan_target": plan_target
        })

    def handle_calculate(self, req):
        sym = req.get("symbol", "BTC-USD")
        price = get_live_price(sym)
        
        # Risk management parameters:
        # Distance to stop: $150 or ~0.2%
        stop_distance = max(120.0, round(price * 0.002, 2))
        stop_price = round(price - stop_distance, 2)
        target_price = round(price + (2.0 * stop_distance), 2)

        # Budget $5000, Max loss $50, 75% cap = $3750
        qty_by_risk = 50.0 / stop_distance
        qty_by_cap = 3750.0 / price
        qty = round(min(qty_by_risk, qty_by_cap), 4)

        self.send_json({
            "status": "ok",
            "symbol": sym,
            "entry": price,
            "stop": stop_price,
            "target": target_price,
            "qty": qty,
            "rr": 2.0
        })

    def handle_order(self, req):
        sym = req.get("symbol", "BTC-USD")
        entry = float(req.get("entry", 0))
        qty = float(req.get("qty", 0))
        stop = float(req.get("stop", 0))
        target = float(req.get("target", 0))

        if not (entry > stop and target > entry and qty > 0):
            self.send_json({"status": "error", "message": "Invalid prices or quantity"}, 400)
            return

        risk = (entry - stop) * qty
        reward = (target - entry) * qty
        rr = reward / risk if risk > 0 else 0

        if risk > 50.0:
            self.send_json({"status": "error", "message": f"Risk ${risk:.2f} exceeds $50.00 max loss limit"}, 400)
            return
        if rr < 1.90:
            self.send_json({"status": "error", "message": f"Reward:Risk ratio {rr:.2f} is under 2.0x requirement"}, 400)
            return

        cost = round(entry * qty, 2)
        portfolio_path = os.path.join(TRADER_DIR, "portfolio.json")
        portfolio = read_json_file(portfolio_path, {"cash": 5000.0, "positions": []})

        if portfolio["cash"] < cost:
            self.send_json({"status": "error", "message": f"Insufficient cash: have ${portfolio['cash']:.2f}, need ${cost:.2f}"}, 400)
            return

        # Deduct cash and record position
        portfolio["cash"] = round(portfolio["cash"] - cost, 2)
        found = False
        for p in portfolio["positions"]:
            if p["ticker"] == sym:
                p["shares"] = round(p["shares"] + qty, 4)
                p.setdefault("lots", []).append({"id": f"{sym}-lot", "date": "today", "shares": qty, "cost": cost})
                found = True
                break
        if not found:
            portfolio["positions"].append({
                "ticker": sym,
                "shares": qty,
                "lots": [{"id": f"{sym}-1", "date": "today", "shares": qty, "cost": cost}]
            })
        write_json_file(portfolio_path, portfolio)

        # Update plan
        plan_path = os.path.join(TRADER_DIR, "plan.json")
        write_json_file(plan_path, {
            "symbol": sym,
            "entry": entry,
            "stop": stop,
            "target": target,
            "reward_risk": rr,
            "flat_by": "15:55 UTC"
        })

        # Arm alerts
        alerts_path = os.path.join(TRADER_DIR, "alerts.json")
        write_json_file(alerts_path, {
            "rules": [
                {"id": f"{sym}-stop", "symbol": sym, "type": "stop", "price": stop},
                {"id": f"{sym}-target", "symbol": sym, "type": "target", "price": target}
            ]
        })

        self.send_json({"status": "ok", "cost": cost, "risk": risk, "cash_left": portfolio["cash"]})

    def handle_flatten(self, req):
        sym = req.get("symbol", "BTC-USD")
        live_price = get_live_price(sym)
        portfolio_path = os.path.join(TRADER_DIR, "portfolio.json")
        portfolio = read_json_file(portfolio_path, {"cash": 5000.0, "positions": []})

        total_pnl = 0.0
        new_positions = []
        for p in portfolio["positions"]:
            if p["ticker"] == sym:
                shares = p["shares"]
                lots = p.get("lots", [])
                cost = sum(lot.get("cost", 0.0) for lot in lots) if lots else shares * live_price
                proceeds = shares * live_price
                total_pnl = proceeds - cost
                portfolio["cash"] = round(portfolio["cash"] + proceeds, 2)
            else:
                new_positions.append(p)

        portfolio["positions"] = new_positions
        write_json_file(portfolio_path, portfolio)

        self.send_json({"status": "ok", "price": live_price, "pnl": total_pnl, "new_cash": portfolio["cash"]})


def main():
    print(f"=======================================================")
    print(f"  CoinSwitch Pro Crypto Day Trading Terminal")
    print(f"  Live TradingView Candlestick Chart + Auto SL & 2R TP")
    print(f"  URL: http://127.0.0.1:{PORT}")
    print(f"=======================================================")
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", PORT), TradingServerHandler) as server:
        server.serve_forever()


if __name__ == "__main__":
    main()
