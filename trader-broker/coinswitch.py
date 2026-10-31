#!/usr/bin/env python3
"""CoinSwitch Pro Official REST API Connector using Ed25519 Cryptography.

Authenticates using CoinSwitch PRO's exact Ed25519 public-key signature standard:
- Public Key (API Key): Hex-encoded Ed25519 public key.
- Private Key (Secret Key): Hex-encoded Ed25519 secret key.
- Message = METHOD + decoded_path + epoch.
- Headers: X-AUTH-APIKEY, X-AUTH-SIGNATURE, X-AUTH-EPOCH.
"""
import json
import os
import time
import urllib.parse
import urllib.request
from cryptography.hazmat.primitives.asymmetric import ed25519

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


def sign_request(api_key, secret_key_hex, method, path, params=None):
    """Signs request using official CoinSwitch Pro Ed25519 specification."""
    method = method.upper()
    if params:
        sep = "&" if "?" in path else "?"
        path = path + sep + urllib.parse.urlencode(params)

    decoded_path = urllib.parse.unquote_plus(path)
    epoch = str(int(time.time() * 1000))

    message = f"{method}{decoded_path}{epoch}"

    private_key = ed25519.Ed25519PrivateKey.from_private_bytes(bytes.fromhex(secret_key_hex))
    signature = private_key.sign(message.encode("utf-8")).hex()

    headers = {
        "Content-Type": "application/json",
        "X-AUTH-APIKEY": api_key,
        "X-AUTH-SIGNATURE": signature,
        "X-AUTH-EPOCH": epoch,
        "User-Agent": "AntigravityTrader/2.0"
    }

    return headers, path


def send_coinswitch_request(method, endpoint, params=None, data=None):
    """Sends authenticated REST request to CoinSwitch Pro API."""
    creds = load_env()
    api_key = creds["API_KEY"]
    secret_key = creds["SECRET_KEY"]
    base_url = creds["BASE_URL"].rstrip("/")

    if not api_key:
        return {"status": "error", "message": "Missing CoinSwitch API Key."}
    if not secret_key:
        return {"status": "error", "message": "Missing CoinSwitch Secret Key."}

    headers, signed_path = sign_request(api_key, secret_key, method, endpoint, params)
    full_url = base_url + signed_path

    payload_bytes = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(full_url, data=payload_bytes, headers=headers, method=method)

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
    """Run diagnostics to verify real CoinSwitch Pro credentials."""
    creds = load_env()
    print("==================================================")
    print(" CoinSwitch Pro Ed25519 API Connection Test")
    print("==================================================")
    print(f" API Key Loaded:    {creds['API_KEY'][:6]}...{creds['API_KEY'][-6:]}")
    print(f" Secret Key Loaded: {creds['SECRET_KEY'][:6]}...{creds['SECRET_KEY'][-6:]}")
    print(f" Base URL:          {creds['BASE_URL']}")

    print("\nPinging CoinSwitch Pro /trade/api/v2/user/portfolio...")
    res = get_real_portfolio()
    print("Response:")
    print(json.dumps(res, indent=2))
    return res


if __name__ == "__main__":
    test_connection()
