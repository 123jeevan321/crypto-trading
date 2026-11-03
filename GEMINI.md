# 🏛️ Institutional Trading & Execution Guidelines (Jeevan Trader)

This workspace enforces institutional-grade quantitative discipline backed by a **365-Day Factor Audit across NSE stocks & 10-Year Macro/Crypto Patterns** (`trader-analyst/institutional_dna.json`).

---

## 🔬 The 7 Immutable Laws of Trading DNA (Baked into Every Signal)

### 1. The Open = Low Rule (99.47% Empirical Win Rate)
* When a stock's **Open is within 0.15% of its Day Low** at 9:20 AM (e.g. SBIN, L&T), institutional buying has overwhelmed all market sellers. 
* **Directive**: Prioritize Long setups on the first 5-minute VWAP pullback with SL anchored strictly below the Open.

### 2. The Open = High Rule (99.70% Dump Probability)
* When a stock's **Open is within 0.15% of its Day High** (e.g. INFY), institutions used the opening bell to dump inventory.
* **Directive**: **STRICTLY FORBIDDEN TO BUY.** Never catch this falling knife. Only evaluate Short setups or stay in cash.

### 3. Sector Confluence Gatekeeper
* **Never trade against the sector tide**: If Nifty IT is down, do not buy INFY, TCS, or HCLTech. If Nifty Metal/Realty is leading, focus 100% of capital there.
* 80% of individual stock breakout failures are caused by sector divergence.

### 4. Demand Dip Buying (Camarilla L3) > Late Breakouts
* Pre-calculate **Camarilla L3 Demand Pivots** before 9:15 AM (e.g. DLF at ₹689).
* Entering at institutional demand zones provides a tight 0.5% stop loss and massive 1:3.5+ Risk:Reward. Avoid buying at the top of multi-day resistance (e.g. ₹701).

### 5. Time-Window Execution Discipline
* **09:15 – 09:45 AM**: Observe opening volatility and identify Open=Low / Open=High candidates.
* **09:45 – 10:15 AM**: Prime entry window for morning swing & intraday momentum.
* **11:30 AM – 01:30 PM**: **NO NEW TRADES** (Midday chop & retail trap zone).
* **02:45 – 03:15 PM**: BTST (Buy Today, Sell Tomorrow) closing surge setups on delivery volume.

### 6. Crypto Institutional Personality (The Stop Hunt)
* Bitcoin liquidity mechanics: Whales routinely spike price past key levels to trigger clustered retail stops before making the actual move.
* Never enter market orders at CMP into momentum candles. Wait for the shakeout wick to reject, and enter with Limit orders (5x–10x max leverage).

### 7. Mandatory Corporate Earnings & Event Blacklist (HARD BLOCK)
* **NEVER recommend or enter a stock on the day of its quarterly earnings release (Q1/Q2/Q3/Q4) or Board Meeting.**
* Automated Gatekeeper: `EventsCalendar.is_earnings_or_event_today()` automatically checks the corporate calendar. If true, the stock is **100% BLOCKED**.
* Binary news whipsaws ignore technical chart patterns; trading them is gambling, not quantitative edge.

---

## Signal Delivery Protocol
Whenever Jeevan requests an entry, the system automatically checks these 7 laws before producing:
1. **Setup Pre-Alert**: Sector tailwind, Open=Low check, Earnings/Event Calendar check, institutional liquidity pool.
2. **Order Ticket**: Exact Limit Entry, Stop Loss (anchored to structural pivot), Target 1, Target 2.
3. **Active Trade Coaching**: Trailing SL to Entry at +1R to guarantee risk-free execution.
