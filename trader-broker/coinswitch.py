#!/usr/bin/env python3
"""CoinSwitch Pro Official REST API Connector.

Handles authentication (HMAC-SHA256), portfolio fetching,
futures margin tracking, and bracket order execution.
Zero external dependencies (uses standard library urllib, hmac, hashlib).
"""
import hashlib
import hmac
import json
import os
import time
import urllib.parse
import urllib.request

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(BASE_DIR, ".env")


def load_env():
    """Load API credentials from local .env file."""
    creds = {
        "API_KEY": os.environ.get("COINSWITCH_API_KEY", ""),
        "SECRET_KEY": os.environ.get("COINSWITCH_SECRET_KEY", ""),
        "BASE_URL": os.environ.get("COINSWITCH_BASE_URL", "https://coinswitch.co")
    }
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip("'\"")
                    if k == "COINSWITCH_API_KEY":
                        creds["API_KEY"] = v
                    elif k == "COINSWITCH_SECRET_KEY":
                        creds["SECRET_KEY"] = v
                    elif k == "COINSWITCH_BASE_URL":
                        creds["BASE_URL"] = v
    return creds


def sign_request(secret_key, method, path, payload_str, timestamp):
    """Generates CoinSwitch Pro HMAC-SHA256 request signature."""
    # Message format: method + path + payload + timestamp
    message = f"{method.upper()}{path}{payload_str}{timestamp}"
    signature = hmac.new(
        secret_key.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    return signature


def send_coinswitch_request(method, endpoint, params=None, data=None):
    """Sends authenticated REST request to CoinSwitch Pro API."""
    creds = load_env()
    api_key = creds["API_KEY"]
    secret_key = creds["SECRET_KEY"]
    base_url = creds["BASE_URL"].rstrip("/")

    if not api_key:
        return {"status": "error", "message": "Missing CoinSwitch API Key. Check your .env file."}
    if not secret_key:
        return {"status": "error", "message": "Missing CoinSwitch Secret Key. CoinSwitch requires both API Key and Secret Key for signature."}

    path = endpoint
    query_str = ""
    if params:
        query_str = "?" + urllib.parse.urlencode(params)
        path += query_str

    full_url = base_url + path
    payload_str = json.dumps(data) if data is not None else ""
    timestamp = str(int(time.time() * 1000))

    signature = sign_request(secret_key, method, endpoint, payload_str, timestamp)

    headers = {
        "Content-Type": "application/json",
        "X-AUTH-APIKEY": api_key,
        "X-AUTH-SIGNATURE": signature,
        "X-AUTH-TIMESTAMP": timestamp,
        "User-Agent": "AntigravityTrader/2.0"
    }

    req_data = payload_str.encode("utf-8") if payload_str else None
    req = urllib.request.Request(full_url, data=req_data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp_body = resp.read().decode("utf-8")
            return json.loads(resp_body)
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8") if e.fp else ""
        try:
            return json.loads(err_body)
        except Exception:
            return {"status": "error", "code": e.code, "message": f"HTTP {e.code}: {err_body}"}
    except Exception as ex:
        return {"status": "error", "message": f"Network error: {str(ex)}"}


def get_real_portfolio():
    """Fetch real user wallet balances from CoinSwitch Pro."""
    return send_coinswitch_request("GET", "/trade/api/v2/user/portfolio")


def get_open_futures():
    """Fetch live open futures positions."""
    return send_coinswitch_request("GET", "/trade/api/v2/futures/positions")


def test_connection():
    """Quick diagnostics to verify API credentials."""
    creds = load_env()
    print("==================================================")
    print(" CoinSwitch Pro API Credentials Verification")
    print("==================================================")
    print(f" API Key Loaded:    {creds['API_KEY'][:6]}...{creds['API_KEY'][-6:] if len(creds['API_KEY']) > 12 else ''}")
    print(f" Secret Key Loaded: {'[PRESENT]' if creds['SECRET_KEY'] else '[MISSING - Needed for HMAC]'}")
    print(f" Base URL:          {creds['BASE_URL']}")

    if not creds["SECRET_KEY"]:
        print("\n[NOTE] CoinSwitch requires the Secret Key to sign requests.")
        print("Please copy the Secret Key from CoinSwitch Pro API settings.")
        return False

    print("\nPinging CoinSwitch Pro user portfolio...")
    res = get_real_portfolio()
    print("Response:", json.dumps(res, indent=2))
    return res.get("status") == "success" or res.get("code") == 200


if __name__ == "__main__":
    test_connection()
