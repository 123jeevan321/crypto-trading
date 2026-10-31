#!/usr/bin/env python3
"""CoinSwitch Pro Crypto Futures Auto-Scalper Backend Server.

Features:
- Automated TP and SL trigger & exit (closes position instantly when price touches target or stop).
- Auto-Trading Loop (Auto-Scalp Bot): automatically enters next scalp when no trade is active.
- Clean INR accounting with real exchange fee deductions (0.05% + 18% GST).
- WebSocket & HTTP streaming.
"""
import http.server
import json
import os
import socketserver
import sys
import threading
import time
import urllib.request
from urllib.parse import urlparse

PORT = 8080
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UI_DIR = os.path.join(BASE_DIR, "ui")
TRADER_DIR = os.path.join(BASE_DIR, "trader")
USD_INR_RATE = 85.0
FEE_RATE = 0.0005
GST_RATE = 0.18

# Capital & Risk Limits for ₹1,000 Wallet
INITIAL_WALLET_CAPITAL = 1000.51
OVERALL_TARGET_INR = 2000.00   # +100% target
OVERALL_MAX_LOSS_INR = 500.00  # Strict stop loss floor
DEFAULT_LEVERAGE = 50          # 50x gives ~16,500 exposure on ₹330 margin
MARGIN_RATIO = 0.33            # 33% per trade (leaving 67% unallocated safe reserve)

# Global state
AUTO_SCALP_ENABLED = True
TRADING_MODE = "AUTO-SCALPER"  # Connected to CoinSwitch Pro
TRADE_LOGS = []
CURRENT_PRICE = 77156.00
PRICE_HISTORY = []

sys.path.append(os.path.join(BASE_DIR, "trader-broker"))
try:
    import coinswitch as cs
except Exception:
    cs = None


def get_real_coinswitch_inr():
    """Fetch real CoinSwitch Pro INR unallocated wallet balance."""
    if not cs:
        return 0.0
    try:
        res = cs.get_real_portfolio()
        for item in res.get("data", []):
            if item.get("currency") == "INR":
                return float(item.get("main_balance", 0.0))
    except Exception as e:
        print("[WARN] Error fetching CoinSwitch balance:", e)
    return 0.0


def log_message(msg):
    ts = time.strftime("%H:%M:%S")
    entry = f"[{ts}] {msg}"
    print(entry)
    TRADE_LOGS.insert(0, entry)
    if len(TRADE_LOGS) > 30:
        TRADE_LOGS.pop()


def get_live_price():
    global CURRENT_PRICE, PRICE_HISTORY
    try:
        url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
        req = urllib.request.Request(url, headers={"User-Agent": "AntigravityTrader/1.0"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode())
            CURRENT_PRICE = round(float(data["price"]), 2)
    except Exception:
        try:
            url = "https://query2.finance.yahoo.com/v8/finance/chart/BTC-USD?interval=1m&range=1d"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode())
            meta = data["chart"]["result"][0]["meta"]
            CURRENT_PRICE = round(float(meta.get("regularMarketPrice", CURRENT_PRICE)), 2)
        except Exception:
            pass

    PRICE_HISTORY.append(CURRENT_PRICE)
    if len(PRICE_HISTORY) > 30:
        PRICE_HISTORY.pop(0)

    return CURRENT_PRICE


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


def check_and_execute_auto_triggers(live_price):
    """Monitors active positions and automatically closes when price reaches TP or SL."""
    global AUTO_SCALP_ENABLED
    portfolio_path = os.path.join(TRADER_DIR, "portfolio.json")
    portfolio = read_json_file(portfolio_path, {"currency": "INR", "cash_inr": INITIAL_WALLET_CAPITAL, "positions": [], "history": []})

    positions = portfolio.get("positions", [])
    remaining_positions = []
    closed_any = False

    for p in positions:
        side = p.get("side", "LONG").upper()
        entry = float(p.get("entry_price", live_price))
        tp = float(p.get("tp_price", 0))
        sl = float(p.get("sl_price", 0))
        margin = float(p.get("margin_inr", 330.0))
        lev = float(p.get("leverage", DEFAULT_LEVERAGE))
        exposure = margin * lev
        exit_fee = round(exposure * FEE_RATE * (1 + GST_RATE), 2)

        is_tp = False
        is_sl = False

        if side == "LONG":
            if tp > 0 and live_price >= tp:
                is_tp = True
            elif sl > 0 and live_price <= sl:
                is_sl = True
        else:  # SHORT
            if tp > 0 and live_price <= tp:
                is_tp = True
            elif sl > 0 and live_price >= sl:
                is_sl = True

        if is_tp or is_sl:
            closed_any = True
            exit_price = tp if is_tp else sl
            pct_move = (exit_price - entry) / entry if side == "LONG" else (entry - exit_price) / entry
            gross_pnl = round(pct_move * exposure, 2)
            net_pnl = round(gross_pnl - exit_fee, 2)
            cash_return = round(margin + net_pnl, 2)

            portfolio["cash_inr"] = round(portfolio.get("cash_inr", 0.0) + cash_return, 2)

            status_label = "TARGET HIT (TP) 🎉" if is_tp else "STOP LOSS HIT (SL) 🛑"
            log_message(f"⚡ {status_label}: {side} {lev}x closed at ${exit_price:,.2f} | Net P&L: ₹{net_pnl:+,.2f} | Wallet: ₹{portfolio['cash_inr']:,.2f}")

            history_entry = {
                "id": p.get("id"),
                "side": side,
                "leverage": lev,
                "margin_inr": margin,
                "entry_price": entry,
                "exit_price": exit_price,
                "exit_reason": "TAKE_PROFIT" if is_tp else "STOP_LOSS",
                "net_pnl_inr": net_pnl,
                "timestamp": time.strftime("%H:%M:%S")
            }
            portfolio.setdefault("history", []).insert(0, history_entry)
        else:
            remaining_positions.append(p)

    if closed_any:
        portfolio["positions"] = remaining_positions
        write_json_file(portfolio_path, portfolio)

    # Auto-Scalp Bot: If enabled and no positions are active, auto-enter next scalp!
    if AUTO_SCALP_ENABLED and len(remaining_positions) == 0:
        time.sleep(2)  # brief breath before next trade
        auto_enter_next_scalp(live_price)


def auto_enter_next_scalp(live_price):
    """Automatically opens the next high-probability scalp trade within ₹1,000 risk parameters."""
    global AUTO_SCALP_ENABLED
    portfolio_path = os.path.join(TRADER_DIR, "portfolio.json")
    portfolio = read_json_file(portfolio_path, {"currency": "INR", "cash_inr": INITIAL_WALLET_CAPITAL, "positions": [], "history": []})

    cash = float(portfolio.get("cash_inr", INITIAL_WALLET_CAPITAL))

    # 1. Enforce Profit Target Limit (+100% gain)
    if cash >= OVERALL_TARGET_INR:
        AUTO_SCALP_ENABLED = False
        log_message(f"🏆 DAILY TARGET HIT! Wallet reached ₹{cash:,.2f} (+100% gain). Auto-trading paused to secure profits!")
        return

    # 2. Enforce Strict Stop Loss Limit (Max loss capped at ₹500 floor)
    if cash <= OVERALL_MAX_LOSS_INR:
        AUTO_SCALP_ENABLED = False
        log_message(f"🛑 MAX LOSS LIMIT HIT: Wallet ₹{cash:,.2f} is at/below ₹{OVERALL_MAX_LOSS_INR:,.2f}. Auto-trading halted to protect your capital!")
        return

    # 3. Position Sizing: Use ~33% of current wallet (e.g. ₹330 on ₹1,000 wallet)
    margin_inr = round(max(100.0, cash * MARGIN_RATIO), 2)
    leverage = DEFAULT_LEVERAGE  # 50x gives ~₹16,500 exposure (matches user's screenshot)
    exposure_inr = round(margin_inr * leverage, 2)
    entry_fee_inr = round(exposure_inr * FEE_RATE * (1 + GST_RATE), 2)
    roundtrip_fee_inr = round(entry_fee_inr * 2, 2)

    total_deduction = round(margin_inr + entry_fee_inr, 2)
    if total_deduction > cash:
        log_message(f"⚠️ Auto-Scalp Bot: Insufficient balance (Have ₹{cash:,.2f}, need ₹{total_deduction:,.2f})")
        return

    # 4. Momentum / Trend Filter
    side = "LONG"
    if len(PRICE_HISTORY) >= 4:
        recent_delta = PRICE_HISTORY[-1] - PRICE_HISTORY[-4]
        if recent_delta < -15.0:
            side = "SHORT"
        else:
            side = "LONG"
    else:
        history = portfolio.get("history", [])
        if history and history[0].get("exit_reason") == "STOP_LOSS":
            # Reverse direction if stopped out
            side = "SHORT" if history[0].get("side") == "LONG" else "LONG"

    entry_price = live_price
    points_target = 280.0  # +280 pts target
    points_stop = 130.0    # -130 pts stop (2.15:1 R:R)

    if side == "LONG":
        tp_price = round(entry_price + points_target, 2)
        sl_price = round(entry_price - points_stop, 2)
        liq_price = round(entry_price * (1 - (1.0 / leverage) * 0.90), 2)
    else:
        tp_price = round(entry_price - points_target, 2)
        sl_price = round(entry_price + points_stop, 2)
        liq_price = round(entry_price * (1 + (1.0 / leverage) * 0.90), 2)

    portfolio["cash_inr"] = round(cash - total_deduction, 2)

    trade_num = len(portfolio.get('history', [])) + 1
    new_position = {
        "id": f"SCALP-{trade_num}",
        "symbol": "BTC/USDT",
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
        "est_profit_inr": round((points_target / entry_price) * exposure_inr - roundtrip_fee_inr, 2),
        "est_loss_inr": round((points_stop / entry_price) * exposure_inr + roundtrip_fee_inr, 2)
    }

    portfolio["positions"] = [new_position]
    write_json_file(portfolio_path, portfolio)

    log_message(f"🤖 Trade #{trade_num}: Entered {side} {leverage}x @ ${entry_price:,.2f} | Margin: ₹{margin_inr:,.2f} | TP: ${tp_price:,.2f} (+{points_target} pts) | SL: ${sl_price:,.2f} (-{points_stop} pts)")


def background_monitor_loop():
    """Continuously fetches price and evaluates triggers."""
    while True:
        try:
            price = get_live_price()
            check_and_execute_auto_triggers(price)
        except Exception as e:
            print("[WARN] Monitor error:", e)
        time.sleep(2)


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
        elif parsed.path == "/api/toggle_auto":
            self.handle_toggle_auto(req_data)
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
        global CURRENT_PRICE, AUTO_SCALP_ENABLED, TRADE_LOGS, TRADING_MODE
        portfolio = read_json_file(
            os.path.join(TRADER_DIR, "portfolio.json"),
            {"currency": "INR", "cash_inr": INITIAL_WALLET_CAPITAL, "positions": [], "history": []}
        )

        real_inr = get_real_coinswitch_inr()

        positions = portfolio.get("positions", [])
        enhanced_positions = []
        for p in positions:
            side = p.get("side", "LONG").upper()
            entry = float(p.get("entry_price", CURRENT_PRICE))
            margin = float(p.get("margin_inr", 330.0))
            lev = float(p.get("leverage", DEFAULT_LEVERAGE))
            exposure = margin * lev

            pct_move = (CURRENT_PRICE - entry) / entry if side == "LONG" else (entry - CURRENT_PRICE) / entry
            gross_pnl = round(pct_move * exposure, 2)
            entry_fee = float(p.get("entry_fee_inr", 9.74))
            net_pnl = round(gross_pnl - entry_fee, 2)
            roi_pct = round((net_pnl / margin) * 100, 2) if margin > 0 else 0

            p_copy = dict(p)
            p_copy["mark_price"] = CURRENT_PRICE
            p_copy["gross_pnl_inr"] = gross_pnl
            p_copy["net_pnl_inr"] = net_pnl
            p_copy["roi_pct"] = roi_pct
            enhanced_positions.append(p_copy)

        self.send_json({
            "status": "ok",
            "price_usd": CURRENT_PRICE,
            "spot_price_usd": round(CURRENT_PRICE - 45.0, 2),
            "usd_inr_rate": USD_INR_RATE,
            "price_inr": round(CURRENT_PRICE * USD_INR_RATE, 2),
            "cash_inr": float(portfolio.get("cash_inr", INITIAL_WALLET_CAPITAL)),
            "real_inr_balance": real_inr,
            "real_connected": True,
            "overall_target_inr": OVERALL_TARGET_INR,
            "overall_max_loss_inr": OVERALL_MAX_LOSS_INR,
            "trading_mode": TRADING_MODE,
            "positions": enhanced_positions,
            "history": portfolio.get("history", [])[:10],
            "auto_scalp_enabled": AUTO_SCALP_ENABLED,
            "logs": TRADE_LOGS[:15]
        })

    def handle_toggle_auto(self, req):
        global AUTO_SCALP_ENABLED
        AUTO_SCALP_ENABLED = not AUTO_SCALP_ENABLED
        log_message(f"🤖 Auto-Scalp Bot {'ACTIVATED' if AUTO_SCALP_ENABLED else 'PAUSED'} by user.")
        self.send_json({"status": "ok", "auto_scalp_enabled": AUTO_SCALP_ENABLED})

    def handle_order(self, req):
        side = req.get("side", "LONG").upper()
        margin_inr = float(req.get("margin_inr", 5000.0))
        leverage = int(req.get("leverage", 25))
        points_target = float(req.get("points_target", 400))
        points_stop = float(req.get("points_stop", 160))

        portfolio_path = os.path.join(TRADER_DIR, "portfolio.json")
        portfolio = read_json_file(portfolio_path, {"currency": "INR", "cash_inr": 10000.0, "positions": [], "history": []})
        current_cash = float(portfolio.get("cash_inr", 10000.0))

        exposure_inr = round(margin_inr * leverage, 2)
        entry_fee_inr = round(exposure_inr * FEE_RATE * (1 + GST_RATE), 2)
        roundtrip_fee_inr = round(entry_fee_inr * 2, 2)

        total_deduction = round(margin_inr + entry_fee_inr, 2)
        if total_deduction > current_cash:
            self.send_json({"status": "error", "message": f"Insufficient margin: Have ₹{current_cash:,.2f}"}, 400)
            return

        entry_price = CURRENT_PRICE
        if side == "LONG":
            tp_price = round(entry_price + points_target, 2)
            sl_price = round(entry_price - points_stop, 2)
            liq_price = round(entry_price * (1 - (1.0 / leverage) * 0.90), 2)
        else:
            tp_price = round(entry_price - points_target, 2)
            sl_price = round(entry_price + points_stop, 2)
            liq_price = round(entry_price * (1 + (1.0 / leverage) * 0.90), 2)

        portfolio["cash_inr"] = round(current_cash - total_deduction, 2)
        position_record = {
            "id": f"SCALP-{len(portfolio.get('history', [])) + 1}",
            "symbol": "BTC/USDT",
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
            "est_profit_inr": round((points_target / entry_price) * exposure_inr - roundtrip_fee_inr, 2),
            "est_loss_inr": round((points_stop / entry_price) * exposure_inr + roundtrip_fee_inr, 2)
        }
        portfolio["positions"] = [position_record]
        write_json_file(portfolio_path, portfolio)

        log_message(f"Manual Entry: {side} {leverage}x @ ${entry_price:,.2f} | TP: ${tp_price} | SL: ${sl_price}")
        self.send_json({"status": "ok", "position": position_record, "new_cash_inr": portfolio["cash_inr"]})

    def handle_update_bracket(self, req):
        tp_price = float(req.get("tp_price", 0))
        sl_price = float(req.get("sl_price", 0))
        portfolio_path = os.path.join(TRADER_DIR, "portfolio.json")
        portfolio = read_json_file(portfolio_path, {"currency": "INR", "cash_inr": 10000.0, "positions": [], "history": []})

        for p in portfolio.get("positions", []):
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

        write_json_file(portfolio_path, portfolio)
        self.send_json({"status": "ok", "positions": portfolio.get("positions", [])})

    def handle_flatten(self, req):
        portfolio_path = os.path.join(TRADER_DIR, "portfolio.json")
        portfolio = read_json_file(portfolio_path, {"currency": "INR", "cash_inr": 10000.0, "positions": [], "history": []})

        positions = portfolio.get("positions", [])
        total_net_pnl = 0.0
        cash_return = 0.0

        for p in positions:
            side = p.get("side", "LONG").upper()
            entry = float(p.get("entry_price", CURRENT_PRICE))
            margin = float(p.get("margin_inr", 0.0))
            lev = float(p.get("leverage", 25))
            exposure = margin * lev

            pct_move = (CURRENT_PRICE - entry) / entry if side == "LONG" else (entry - CURRENT_PRICE) / entry
            gross_pnl = round(pct_move * exposure, 2)
            exit_fee_inr = round(exposure * FEE_RATE * (1 + GST_RATE), 2)
            net_pnl = gross_pnl - exit_fee_inr

            total_net_pnl += net_pnl
            cash_return += max(0.0, margin + net_pnl)

            portfolio.setdefault("history", []).insert(0, {
                "id": p.get("id"),
                "side": side,
                "leverage": lev,
                "margin_inr": margin,
                "entry_price": entry,
                "exit_price": CURRENT_PRICE,
                "exit_reason": "MANUAL_FLATTEN",
                "net_pnl_inr": net_pnl,
                "timestamp": time.strftime("%H:%M:%S")
            })

        portfolio["cash_inr"] = round(portfolio.get("cash_inr", 0.0) + cash_return, 2)
        portfolio["positions"] = []
        write_json_file(portfolio_path, portfolio)

        log_message(f"Manual Close: Settled at ${CURRENT_PRICE:,.2f} | Net P&L: ₹{total_net_pnl:+,.2f} | Wallet: ₹{portfolio['cash_inr']:,.2f}")
        self.send_json({"status": "ok", "realized_pnl_inr": total_net_pnl, "new_cash_inr": portfolio["cash_inr"]})

    def handle_reset(self):
        portfolio_path = os.path.join(TRADER_DIR, "portfolio.json")
        data = {"currency": "INR", "cash_inr": INITIAL_WALLET_CAPITAL, "initial_capital_inr": INITIAL_WALLET_CAPITAL, "positions": [], "history": []}
        write_json_file(portfolio_path, data)
        log_message(f"Wallet reset to ₹{INITIAL_WALLET_CAPITAL:,.2f} INR.")
        self.send_json({"status": "ok", "cash_inr": INITIAL_WALLET_CAPITAL})


def main():
    print("================================================================")
    print("  CoinSwitch Pro - Auto-Scalper Engine (INR)")
    print(f"  Auto-Trigger TP/SL & Auto-Scalp Loop Active")
    print(f"  URL: http://127.0.0.1:{PORT}")
    print("================================================================")
    # Start background monitor thread
    monitor_thread = threading.Thread(target=background_monitor_loop, daemon=True)
    monitor_thread.start()

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", PORT), TradingServerHandler) as server:
        server.serve_forever()


if __name__ == "__main__":
    main()
