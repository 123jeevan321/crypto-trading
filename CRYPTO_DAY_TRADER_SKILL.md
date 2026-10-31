---
name: crypto-day-trader
description: 11 tools for 24/7 Bitcoin and Crypto day trading. Scans breakouts, checks live news, times bar-by-bar entries, plans stop/target exits, runs 10,000 Monte Carlo replays, enforces risk/budget limits, manages paper/demo tickets, and tracks live price alerts.
---

# Crypto Day Trader Skill (Bitcoin & 24/7 Crypto Market)

This skill provides an automated and guided day-trading system adapted for the **24/7 Cryptocurrency Market (Bitcoin `BTC-USD`, `ETH-USD`, `SOL-USD`, etc.)**, built upon the open-source Trader Skill v2 engine.

All code and data are preserved in the repository at:
`C:\Users\jeeva\.gemini\antigravity\scratch\trading-skill` on branch **`crypto-market`**.

---

## 1. System Architecture: How It Actually Works

### The Frontend (UI) vs. Backend
- **Backend**: Plain Python standard library scripts (`entry.py`, `exit.py`, `size.py`, `check.py`, `ticket.py`, `timemachine.py`, `alerts.py`, `news.py`, `scan.py`). Reads free live public data from Yahoo Finance 5-minute / 1-minute chart feeds and SEC EDGAR.
- **Frontend / UI**:
  - **In Agent Chat (Gemini / Claude / Antigravity)**: The chat acts as your trading terminal. When you ask to scan or trade, the agent executes the Python scripts, formats tables, plots ASCII band charts, and shows you approval tickets.
  - **In Terminal**: You can run each Python script directly from PowerShell or Bash.
  - **Your Exchange App (e.g. CoinSwitch, Binance, Delta)**: The Python scripts do **not** create a duplicate exchange website. Instead, they interact with trading accounts in one of two ways:
    1. **Paper Trading Simulation (Default & Active)**: Completely local. Simulated orders and fills are tracked in `trader/orders.json` and `trader/portfolio.json`. Zero real money risk.
    2. **Real Exchange / Demo API (Testnet / Live)**: When you are ready, you plug in your Exchange API Key & Secret (such as CoinSwitch Pro API, Binance Testnet, or Alpaca Crypto Sandbox). The script sends REST API orders to the real exchange on your behalf—**only after you type "yes" in the chat**.

---

## 2. Crypto Adaptations (Completed on Branch `crypto-market`)

| Feature | Original US Stock Behavior | Crypto Market Adaptation |
| :--- | :--- | :--- |
| **Trading Hours** | 9:30 AM – 4:00 PM ET (Closed weekends & NYSE holidays) | **24/7/365 Non-stop** (Active on Saturday & Sunday) |
| **Session Anchor** | 9:30 AM ET Daily Open | **00:00 UTC Daily Open** (Global standard used by Binance & TradingView) |
| **Opening Range (ORB)** | 9:30 – 9:45 AM ET (15 min) | **00:00 – 00:15 UTC** (First 3 five-minute bars of the UTC day) |
| **Position Sizing** | Integer shares only (floor) | **Fractional units** (e.g. `0.0485 BTC` to 4 decimal places) |
| **Risk Enforcement** | Blocks trades outside NYSE hours | Enforces max loss ($50), position cap (75%), and reward:risk (2.0+) 24/7 |
| **Time Machine Replay**| 78 bars/day (6.5 hrs) | **288 bars/day (24 hrs)** using Bitcoin's own 60-day 5-min history |

---

## 3. The 11 Tools & How to Run the Pipeline

### Step 1: Scan for Setups
```bash
# Scan daily setups (20d breakouts, bull flags, oversold bounces) on top cryptos:
python trader-scanner/scan.py daily --symbols BTC-USD,ETH-USD,SOL-USD --min-volume 0

# Check opening-range breakouts (ORB) on 5m bars:
python trader-scanner/scan.py orb --min-volume 0
```

### Step 2: Breaking News
```bash
# Pull real-time headlines and sentiment tags for Bitcoin:
python trader-news/news.py --tickers BTC-USD --hours 12
```

### Step 3: Bar-by-Bar Entry Trigger
```bash
# Check if Bitcoin triggered an Opening Range Breakout today:
python trader-entry/entry.py check BTC --write
# Writes: trader/entry.json (Status: TRIGGERED or WAITING)
```

### Step 4: Plan Exit (Stop Loss & Target)
```bash
# Calculate opening-range midpoint stop and 2R take-profit:
python trader-exit/exit.py plan --from trader/entry.json --write
# Writes: trader/plan.json
```

### Step 5: Time Machine Monte Carlo Replay
```bash
# Replay 10,000 sessions drawn from BTC's own 60-day history:
python trader-timemachine/timemachine.py run --write
# Outputs target vs stop probabilities and historical hit rates
```

### Step 6: Budget & Position Sizing
```bash
# Size position to your account budget ($5,000) and max loss ($50):
python trader-budget/size.py --budget 5000 --write
# Writes: trader/orders.json (Fractional BTC bracket order)
```

### Step 7: Risk Manager Verification
```bash
# Audit order against max loss, position cap, and reward:risk:
python trader-risk/check.py
# Outputs: PASS or BLOCK
```

### Step 8: Order Ticket Approval
```bash
# Display human-readable ticket waiting for your 'yes':
python trader-broker/ticket.py show

# Record explicit user approval:
python trader-broker/ticket.py approve --index 1 --reply "yes"
```

### Step 9: Price Alerts & Exit Tracking
```bash
# Arm alerts for stop loss, target, and session close:
python trader-alerts/alerts.py add --from-plan

# Check live prices against active alerts:
python trader-alerts/alerts.py check
```

---

## 4. Benchmark Live Test Data (Recorded Saturday Oct 31, 2026)

- **Asset**: Bitcoin (`BTC-USD`) at **$77,250.62**
- **00:00 UTC Opening Range**: High $77,223.38 / Low $77,114.76
- **Entry Trigger**: 00:15 UTC bar closed above range high at **$77,250.62**
- **Stop Loss**: $77,169.07 (Opening-range midpoint, $81.55 risk per BTC)
- **Take Profit (2R)**: $77,413.72 (+$163.10 gain per BTC)
- **Position Size**: `0.0485 BTC` ($3,746.66 cost, capped at 75% budget)
- **Max Loss at Stop**: Exactly **$3.96** (Well inside $50 max loss limit)
- **Time Machine Replay**: 30.6% target hit, 69.3% stop hit on 2R ratio

---

## 5. Git Repository & Continuity

- **Local Path**: `C:\Users\jeeva\.gemini\antigravity\scratch\trading-skill`
- **Active Branch**: `crypto-market`
- **Clean Main Branch**: `main` remains intact with original US equities code.
- **To resume in a new chat**: Set the workspace to `C:\Users\jeeva\.gemini\antigravity\scratch\trading-skill`, checkout `crypto-market`, and paste this skill document.
