# 🏛️ Institutional Trading & Execution Guidelines (Jeevan Trader)

This workspace enforces institutional-grade quantitative discipline backed by a **365-Day Factor Audit across NSE stocks & 10-Year Macro/Crypto Patterns** (`trader-analyst/institutional_dna.json`), powered by the **Institutional Multi-Confluence Engine** (`trader-analyst/confluence_engine.py`).

---

## 🔬 The 8 Immutable Laws of Trading DNA (Baked into Every Signal)

### 1. The Open = Low Rule (99.47% Empirical Win Rate)
* When a stock's **Open is within 0.15% of its Day Low** at 9:20 AM (e.g. SBIN, L&T, BSE), institutional buying has overwhelmed all market sellers. 
* **Directive**: Prioritize Long setups on the first 5-minute VWAP pullback with SL anchored strictly below the Open.

### 2. The Open = High Rule (99.70% Dump Probability)
* When a stock's **Open is within 0.15% of its Day High** (e.g. INFY), institutions used the opening bell to dump inventory.
* **Directive**: **STRICTLY FORBIDDEN TO BUY.** Never catch this falling knife. Only evaluate Short setups or stay in cash.

### 3. Sector Confluence Gatekeeper
* **Never trade against the sector tide**: If Nifty IT is down, do not buy INFY, TCS, or HCLTech. If Nifty Metal/Realty/Banking is leading, focus 100% of capital there.
* 80% of individual stock breakout failures are caused by sector divergence.

### 4. Demand Dip Buying (Camarilla L3) > Late Breakouts
* Pre-calculate **Camarilla L3 Demand Pivots** before 9:15 AM (e.g. DLF at ₹689).
* Entering at institutional demand zones provides a tight 0.5% stop loss and massive 1:3.5+ Risk:Reward. Avoid buying at the top of multi-day resistance (e.g. ₹701).

### 5. Time-Window Execution Discipline
* **09:15 – 09:45 AM**: Observe opening volatility and identify Open=Low / Open=High candidates.
* **09:45 – 10:15 AM**: Prime entry window for morning swing & intraday momentum.
* **11:30 AM – 01:30 PM**: **NO NEW TRADES** (Midday chop & retail trap zone).
* **02:45 – 03:15 PM**: BTST (Buy Today, Sell Tomorrow) closing surge setups on delivery volume.
* **18:30 – 20:30 IST**: Peak Crypto/BTC Institutional Session (Wall Street / US ETF Open).

### 6. Crypto Institutional Personality (The Stop Hunt)
* Bitcoin liquidity mechanics: Whales routinely spike price past key levels to trigger clustered retail stops before making the actual move.
* Never enter market orders at CMP into momentum candles. Wait for the shakeout wick to reject, and enter with Limit orders (5x–10x max leverage).

### 7. Mandatory Corporate Earnings & Event Blacklist (HARD BLOCK)
* **NEVER recommend or enter a stock on the day of its quarterly earnings release (Q1/Q2/Q3/Q4) or Board Meeting.**
* Automated Gatekeeper: `EventsCalendar.is_earnings_or_event_today()` automatically checks the corporate calendar. If true, the stock is **100% BLOCKED**.
* Binary news whipsaws ignore technical chart patterns; trading them is gambling, not quantitative edge.

### 8. Universal Multi-Confluence Matrix & Strict "NO TRADE" Discipline
* **Every single recommendation must pass the 5-Pillar Confluence Engine (`trader-analyst/confluence_engine.py`)**:
  1. **Volume Profile & Order Flow**: POC, Value Area High (VAH), Value Area Low (VAL). Never enter in mid-range chop.
  2. **ICT / SMC Structure**: Order Blocks, Fair Value Gaps (FVG), Market Structure Shift (MSS/CHoCH), Liquidity Sweeps.
  3. **Institutional Footprint & Retail Traps**: Equal Highs/Lows stop hunts, false breakout traps.
  4. **Technical Indicators**: EMA 9/21/50/200 Stack, MACD momentum divergence, VWAP alignment.
  5. **Risk-to-Reward Footprint**: Tight Stop-Loss (<0.5% on stocks, <300 pts on BTC) anchored to structural boundaries, targeting $\ge 1:3.5$ R:R.
* **STRICT MANDATE**: If total confluence score is **< 85%**, the system MUST issue:
  > **"VERDICT: NO TRADE - CONDITIONS NOT MET (STAND ASIDE)"**
  No forced setups, no chasing, no guessing.

---

## Signal Delivery Protocol
Whenever Jeevan requests an entry, the system automatically checks these 8 laws before producing:
1. **Setup Pre-Alert**: Confluence score ($\ge 85\%$), Volume Profile level, SMC Liquidity Sweep, Event Calendar check.
2. **Order Ticket**: Exact Limit Entry, Stop Loss (anchored to structural pivot $\le 300$ pts on BTC), Target 1 ($\ge 1,000$ pts), Target 2.
3. **Active Trade Coaching**: Trailing SL to Entry at +1R to guarantee risk-free execution.
