#!/usr/bin/env python3
"""CoinSwitch Pro Crypto Futures & Scalper Terminal Backend Server.

Supports 10x-100x Leverage, INR Wallet, Real Exchange Brokerage Fee Deductions (0.05% + 18% GST),
Dynamic Real-Time Tick Streaming, and Draggable On-Chart TP/SL Lines.
Zero external dependencies (uses standard library).
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
USD_INR_RATE = 85.0

# CoinSwitch Pro Fee Structure: 0.05% Taker Fee + 18% GST on Fee
FEE_RATE = 0.0005
GST_RATE = 0.18


def get_live_price(symbol="BTC-USD"):
    """Fetch live market price from public crypto feed."""
    url = "https://query2.finance.yahoo.com/v8/finance/chart/BTC-USD?interval=1m&range=1d"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode())
        meta = data["chart"]["result"][0]["meta"]
        return float(meta.get("regularMarketPrice", 77156.00))
    except Exception:
        return 77156.00


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

        if parsed.path == "/api/order":
            self.handle_order(req_data)
        elif parsed.path == "/api/update_bracket":
            self.handle_update_bracket(req_data)
        elif parsed.path == "/api/flatten":
            self.handle_flatten(req_data)
        elif parsed.path == "/api/reset":
            self.handle_reset()
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
        portfolio = read_json_file(
            os.path.join(TRADER_DIR, "portfolio.json"),
            {"currency": "INR", "cash_inr": 10000.0, "positions": []}
        )

        positions = portfolio.get("positions", [])
        enhanced_positions = []
        for p in positions:
            side = p.get("side", "LONG").upper()
            entry = float(p.get("entry_price", live_price))
            margin = float(p.get("margin_inr", 0.0))
            lev = float(p.get("leverage", 25))
            exposure = margin * lev

            if side == "LONG":
                pct_move = (live_price - entry) / entry if entry > 0 else 0
            else:
                pct_move = (entry - live_price) / entry if entry > 0 else 0

            gross_pnl = round(pct_move * exposure, 2)
            # Estimated roundtrip fee (entry + exit with GST)
            total_fee = float(p.get("total_fee_inr", round(exposure * FEE_RATE * 2 * (1 + GST_RATE), 2)))
            net_pnl = round(gross_pnl - (total_fee / 2), 2)  # half fee deducted at entry, half remaining
            roi_pct = round((net_pnl / margin) * 100, 2) if margin > 0 else 0

            p_copy = dict(p)
            p_copy["mark_price"] = live_price
            p_copy["gross_pnl_inr"] = gross_pnl
            p_copy["net_pnl_inr"] = net_pnl
            p_copy["roi_pct"] = roi_pct
            enhanced_positions.append(p_copy)

        self.send_json({
            "status": "ok",
            "price_usd": live_price,
            "spot_price_usd": round(live_price - 50.0, 2),  # typical spot vs futures spread
            "usd_inr_rate": USD_INR_RATE,
            "price_inr": round(live_price * USD_INR_RATE, 2),
            "cash_inr": float(portfolio.get("cash_inr", 10000.0)),
            "positions": enhanced_positions
        })

    def handle_order(self, req):
        symbol = req.get("symbol", "BTC/USDT")
        side = req.get("side", "LONG").upper()
        margin_inr = float(req.get("margin_inr", 5000.0))
        leverage = int(req.get("leverage", 25))
        entry_price = float(req.get("entry_price", get_live_price()))
        points_target = float(req.get("points_target", 400))
        points_stop = float(req.get("points_stop", 160))

        portfolio_path = os.path.join(TRADER_DIR, "portfolio.json")
        portfolio = read_json_file(portfolio_path, {"currency": "INR", "cash_inr": 10000.0, "positions": []})
        current_cash = float(portfolio.get("cash_inr", 10000.0))

        exposure_inr = round(margin_inr * leverage, 2)
        # Entry Fee: 0.05% + 18% GST
        entry_fee_inr = round(exposure_inr * FEE_RATE * (1 + GST_RATE), 2)
        roundtrip_fee_inr = round(entry_fee_inr * 2, 2)

        total_entry_deduction = round(margin_inr + entry_fee_inr, 2)
        if total_entry_deduction > current_cash:
            self.send_json({
                "status": "error",
                "message": f"Insufficient margin: Available ₹{current_cash:,.2f}, need ₹{total_entry_deduction:,.2f} (including ₹{entry_fee_inr:.2f} exchange fee + GST)"
            }, 400)
            return

        if side == "LONG":
            tp_price = round(entry_price + points_target, 2)
            sl_price = round(entry_price - points_stop, 2)
            liq_price = round(entry_price * (1 - (1.0 / leverage) * 0.90), 2)
        else:
            tp_price = round(entry_price - points_target, 2)
            sl_price = round(entry_price + points_stop, 2)
            liq_price = round(entry_price * (1 + (1.0 / leverage) * 0.90), 2)

        est_profit_inr = round((points_target / entry_price) * exposure_inr - roundtrip_fee_inr, 2)
        est_loss_inr = round((points_stop / entry_price) * exposure_inr + roundtrip_fee_inr, 2)

        # Deduct margin AND entry fee from cash
        portfolio["cash_inr"] = round(current_cash - total_entry_deduction, 2)
        position_record = {
            "id": f"SCALP-{len(portfolio.get('positions', [])) + 1}",
            "symbol": symbol,
            "side": side,
            "margin_inr": margin_inr,
            "leverage": leverage,
            "exposure_inr": exposure_inr,
            "entry_price": entry_price,
            "tp_price": tp_price,
            "sl_price": sl_price,
            "liq_price": liq_price,
            "points_target": points_target,
            "points_stop": points_stop,
            "entry_fee_inr": entry_fee_inr,
            "total_fee_inr": roundtrip_fee_inr,
            "est_profit_inr": est_profit_inr,
            "est_loss_inr": est_loss_inr
        }
        portfolio.setdefault("positions", []).append(position_record)
        write_json_file(portfolio_path, portfolio)

        self.send_json({
            "status": "ok",
            "position": position_record,
            "new_cash_inr": portfolio["cash_inr"],
            "fee_deducted_inr": entry_fee_inr
        })

    def handle_update_bracket(self, req):
        """Update TP / SL prices when user drags lines on chart."""
        pos_id = req.get("id")
        tp_price = float(req.get("tp_price", 0))
        sl_price = float(req.get("sl_price", 0))

        portfolio_path = os.path.join(TRADER_DIR, "portfolio.json")
        portfolio = read_json_file(portfolio_path, {"currency": "INR", "cash_inr": 10000.0, "positions": []})

        found = False
        for p in portfolio.get("positions", []):
            if p.get("id") == pos_id or pos_id is None:
                if tp_price > 0:
                    p["tp_price"] = tp_price
                    p["points_target"] = round(abs(tp_price - p["entry_price"]), 2)
                if sl_price > 0:
                    p["sl_price"] = sl_price
                    p["points_stop"] = round(abs(p["entry_price"] - sl_price), 2)

                exposure = p["exposure_inr"]
                entry = p["entry_price"]
                p["est_profit_inr"] = round((p["points_target"] / entry) * exposure, 2)
                p["est_loss_inr"] = round((p["points_stop"] / entry) * exposure, 2)
                found = True
                break

        if found:
            write_json_file(portfolio_path, portfolio)
            self.send_json({"status": "ok", "positions": portfolio["positions"]})
        else:
            self.send_json({"status": "error", "message": "Position not found"}, 404)

    def handle_flatten(self, req):
        pos_id = req.get("id")
        live_price = get_live_price("BTC-USD")
        portfolio_path = os.path.join(TRADER_DIR, "portfolio.json")
        portfolio = read_json_file(portfolio_path, {"currency": "INR", "cash_inr": 10000.0, "positions": []})

        positions = portfolio.get("positions", [])
        new_positions = []
        total_net_pnl = 0.0
        cash_return = 0.0

        for p in positions:
            if pos_id is None or p.get("id") == pos_id:
                side = p.get("side", "LONG").upper()
                entry = float(p.get("entry_price", live_price))
                margin = float(p.get("margin_inr", 0.0))
                lev = float(p.get("leverage", 25))
                exposure = margin * lev

                if side == "LONG":
                    pct_move = (live_price - entry) / entry if entry > 0 else 0
                else:
                    pct_move = (entry - live_price) / entry if entry > 0 else 0

                gross_pnl = round(pct_move * exposure, 2)
                # Exit Fee: 0.05% + 18% GST
                exit_fee_inr = round(exposure * FEE_RATE * (1 + GST_RATE), 2)
                net_pnl = gross_pnl - exit_fee_inr

                total_net_pnl += net_pnl
                cash_return += max(0.0, margin + net_pnl)
            else:
                new_positions.append(p)

        portfolio["cash_inr"] = round(portfolio.get("cash_inr", 0.0) + cash_return, 2)
        portfolio["positions"] = new_positions
        write_json_file(portfolio_path, portfolio)

        self.send_json({
            "status": "ok",
            "realized_pnl_inr": total_net_pnl,
            "new_cash_inr": portfolio["cash_inr"],
            "exit_price": live_price
        })

    def handle_reset(self):
        portfolio_path = os.path.join(TRADER_DIR, "portfolio.json")
        data = {"currency": "INR", "cash_inr": 10000.0, "initial_capital_inr": 10000.0, "positions": []}
        write_json_file(portfolio_path, data)
        self.send_json({"status": "ok", "cash_inr": 10000.0})


def main():
    print("================================================================")
    print("  CoinSwitch Pro - Crypto Futures & Scalper Terminal (INR)")
    print(f"  Available Margin: INR 10,000.00 | Leverage: 10x - 100x")
    print(f"  URL: http://127.0.0.1:{PORT}")
    print("================================================================")
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", PORT), TradingServerHandler) as server:
        server.serve_forever()


if __name__ == "__main__":
    main()
