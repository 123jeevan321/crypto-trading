#!/usr/bin/env python3
"""Quotex Binary Options Signal Server & Terminal.

Serves the real-time 20-pair scanner dashboard and REST API endpoints:
- GET / -> Serves interactive signal terminal dashboard
- GET /api/scan -> Returns real-time 5-strategy confluence scan on 20 pairs
- GET /api/sessions -> Returns live Forex session clock and overlap recommendations
"""

import http.server
import json
import os
import socketserver
from urllib.parse import urlparse

from forex_sessions import get_current_sessions
from scanner import run_full_market_scan

PORT = 8085
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_HTML = os.path.join(BASE_DIR, "index.html")

# In-memory cache to maintain high responsiveness
CACHE_DATA = None
CACHE_TIME = 0
CACHE_DURATION_SEC = 5


class BinaryTradingServerHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        global CACHE_DATA, CACHE_TIME
        parsed = urlparse(self.path)

        if parsed.path in ("/", "/index.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            with open(INDEX_HTML, "rb") as f:
                self.wfile.write(f.read())
            return

        if parsed.path == "/api/scan":
            now = os.times().elapsed
            if CACHE_DATA is None or (now - CACHE_TIME) > CACHE_DURATION_SEC:
                CACHE_DATA = run_full_market_scan(20)
                CACHE_TIME = now
            self.send_json(CACHE_DATA)
            return

        if parsed.path == "/api/sessions":
            self.send_json(get_current_sessions())
            return

        super().do_GET()

    def send_json(self, data, status_code=200):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))


def main():
    print("================================================================")
    print("  Quotex Binary Options Confluence Terminal (20 Pairs)")
    print(f"  Live Signal Scanner & Session Clock Active")
    print(f"  URL: http://127.0.0.1:{PORT}")
    print("================================================================")
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", PORT), BinaryTradingServerHandler) as server:
        server.serve_forever()


if __name__ == "__main__":
    main()
