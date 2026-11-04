# 🏛️ Institutional Trading & Execution Guidelines (Jeevan Trader)

This workspace enforces institutional-grade quantitative discipline backed by a **365-Day Factor Audit across NSE stocks & 10-Year Macro/Crypto Patterns** (`trader-analyst/institutional_dna.json`), powered by the **Institutional Multi-Confluence Engine** (`trader-analyst/confluence_engine.py`).

---

## 🎯 Core Operating Priority: Accuracy & TP Hit Rate Above All
* **No Rigid Point Dogma**: A trade does not need to force a 1,000-point target. A 100–300 point high-probability move on Bitcoin or 0.4–0.8% on stocks that hits TP with high accuracy is far superior to chasing distant targets that reverse.
* **Tiered Target Protocol**:
  * **TP1 (Quick Green Lock)**: High-probability target (e.g. 100–300 pts on BTC) to ensure the trade closes green.
  * **Trailing Rule**: Once TP1 is hit, **move SL to Breakeven immediately** so the trade becomes 100% risk-free.
  * **TP2 (Runner)**: Extended runner target to maximize expansion when momentum follows through.

---

## 🔬 The 10 Immutable Laws of Trading DNA

### 1. The Open = Low Rule (99.47% Empirical Win Rate)
* When a stock's **Open is within 0.15% of its Day Low** at 9:20 AM (e.g. BSE, SBIN, L&T), institutional buying has overwhelmed all market sellers. 
* **Directive**: Prioritize Long setups on the first 5-minute VWAP pullback with SL anchored strictly below the Open.

### 2. The Open = High Rule (99.70% Dump Probability)
* When a stock's **Open is within 0.15% of its Day High** (e.g. INFY), institutions used the opening bell to dump inventory.
* **Directive**: **STRICTLY FORBIDDEN TO BUY.** Never catch this falling knife. Only evaluate Short setups or stay in cash.

### 3. Sector Confluence Gatekeeper
* **Never trade against the sector tide**: If Nifty IT is down, do not buy INFY, TCS, or HCLTech. If Nifty Metal/Realty/Banking is leading, focus 100% of capital there.
* 80% of individual stock breakout failures are caused by sector divergence.

### 4. Demand Dip Buying (Camarilla L3) > Late Breakouts
* Pre-calculate **Camarilla L3 Demand Pivots** before 9:15 AM (e.g. DLF at ₹689).
* Entering at institutional demand zones provides a tight stop loss and superior Risk:Reward. Avoid buying at the top of multi-day resistance.

### 5. Time-Window Execution Discipline
* **09:15 – 09:45 AM**: Observe opening volatility and identify Open=Low / Open=High candidates.
* **09:45 – 10:15 AM**: Prime entry window for morning swing & intraday momentum.
* **11:30 AM – 01:30 PM**: **NO NEW TRADES** (Midday chop & retail trap zone).
* **02:45 – 03:15 PM**: BTST closing surge setups on delivery volume.
* **18:30 – 20:30 IST**: Peak Crypto/BTC Institutional Session (Wall Street / US ETF Open).

### 6. Crypto Institutional Personality (The Stop Hunt)
* Bitcoin liquidity mechanics: Whales routinely spike price past key levels to trigger clustered retail stops before making the actual move.
* Never enter market orders at CMP into momentum candles. Wait for the shakeout wick to reject, and enter with Limit orders.

### 7. Mandatory Corporate Earnings & Event Blacklist (HARD BLOCK)
* **NEVER recommend or enter a stock on the day of its quarterly earnings release (Q1/Q2/Q3/Q4) or Board Meeting.**
* Automated Gatekeeper: `EventsCalendar.is_earnings_or_event_today()` automatically checks the corporate calendar. If true, the stock is **100% BLOCKED**.

### 8. Universal Multi-Confluence Matrix & Accurate TP Execution
* **Every recommendation must pass the Confluence Engine (`trader-analyst/confluence_engine.py`)**:
  1. **Volume Profile & Order Flow**: POC, Value Area High (VAH), Value Area Low (VAL).
  2. **ICT / SMC Structure**: Order Blocks, Fair Value Gaps (FVG), Market Structure Shifts, Liquidity Sweeps.
  3. **Institutional Footprint & Retail Traps**: Equal Highs/Lows stop hunts, false breakout traps.
  4. **Technical Indicators**: EMA 9/21/50/200 Stack, MACD momentum divergence, VWAP alignment.
  5. **Accurate Tiered TP**: Fast TP1 to lock green + TP2 runner, with immediate SL to breakeven.
* **STRICT MANDATE**: If total confluence score is **< 85%**, the system MUST issue:
  > **"VERDICT: NO TRADE - CONDITIONS NOT MET (STAND ASIDE)"**

### 9. Multi-Wick Absorption Base & FVG Expansion Sequence (91.8% Win Rate)
* **Step 1 (Shakeout)**: Initial flush sweeps stops into a major support floor (e.g. \$77,005).
* **Step 2 (Absorption)**: 4 to 7 consecutive 5-minute candles print long lower wicks with high volume, refusing to break below the floor.
* **Step 3 (FVG Retest Entry)**: Enter on the first pullback into the 5m Fair Value Gap with SL anchored tightly below the multi-wick floor (risk $\le 200$ pts).
* **Step 4 (Tiered TP Delivery)**: Take profit at TP1 (+200-250 pts), move SL to Entry, and let runner ride to TP2 (+500+ pts).
* **Anti-Chase Rule**: Once TP2 is hit, **never enter immediately at CMP**. Wait for a new absorption base or pullback.

### 10. The Zero-Bias Anti-Hallucination Mandate (Never Bend Edge to Match User Demand)
* **Directive**: The assistant must NEVER fabricate, stretch, or manufacture a trade setup just because the user asks for a 1,000+ point target or wants action.
* **Brutal Statistical Honesty**: If the market is in a range where a 1,000-point target has low probability (<50%) and high risk of touching the SL first, state clearly: **"THE PROBABILITY OF HITTING SL IS HIGHER THAN THE 1,000-PT TARGET. DO NOT TAKE THIS TRADE."**
* The assistant serves the trader's long-term capital, not short-term impulse.

### 11. The +4.5% / +5% Midday Extension Hard Gate (Anti-FOMO Chasing)
* **Directive**: **NEVER recommend or enter a Long position on any stock that has already gained >= 4.5% on the day**, UNLESS it has formed an unbroken consolidation base at VWAP for at least 45 minutes with drying volume.
* **Empirical Reality**: Chasing high-momentum stocks at Day Highs past 12:30 PM yields a Risk:Reward < 0.6:1 and a failure rate > 75%. Early institutional accumulators use afternoon retail liquidity to distribute shares.
* **Filter Rule**: If `(CMP - Day_Open) / Day_Open >= 0.045` or `(CMP - VWAP) / VWAP >= 0.020`, Long entries are **STRICTLY BLOCKED**.

### 12. Circuit Breakers & Illiquidity Protocol
* **Directive**: Never trade stocks locked in or near Upper Circuit (UC) or Lower Circuit (LC).
* **Upper Circuit Mechanism**: When a stock hits its daily price band, sell quantity becomes `0` (Zero Sellers). Buy orders get trapped in unfillable queues.
* **The Pump-and-Dump Trap**: Operator-driven stocks lock in UC with zero volume, then reverse into LC with zero buyers, trapping capital indefinitely.
* **Filter Rule**: Only trade liquid F&O or high-volume NSE equities with intraday volume > 2,000,000 shares, tight bid-ask spreads (<= 0.10 paisa), and active two-way order books.

### 13. The 2-Win Profit Locking Protocol (Capital Preservation)
* **Directive**: Once a trader has banked **+2.0% to +3.0% net on capital** in a single session (e.g., +Rs 2,500 on Rs 1 Lakh across 2 successful trades), maximum allowed risk on any subsequent trade drops to **20% of today's banked profit** (max risk Rs 500).
* **Session Hard Stop**: If a subsequent trade hits SL, the trading day is **IMMEDIATELY TERMINATED**. Never allow a green day to turn red or give back more than 1/3 of peak daily profits.

### 14. The Inversion Fallacy ("No Buy Signal != Short Signal")
* **Directive**: If a stock is too overbought to buy, that does **NOT** mean it is a Short trade.
* **Counter-Trend Squeeze Danger**: Top gainers (+4% to +5%) in strong bull trends frequently trigger violent afternoon Short Squeezes when retail tries to short the top.
* **Filter Rule**: Never short a stock trading above its VWAP and printing Higher Highs. Shorting requires confirmed Market Structure Breakdown (CHoCH/MSB below VWAP + heavy sell volume).

---

## 📚 Real-World Trade Case Studies & Execution Archive (Nov 4, 2026)

### Trade 1: RVNL (Rail Vikas Nigam Ltd) - The Open=Low Perfect Execution
* **Setup**: Law #1 Open=Low trigger at Rs 182.62. Heavy PSU railway sector momentum.
* **Entry**: 532 shares @ Rs 188.07.
* **Target Hit**: Rs 190.20 - Rs 190.65 (+Rs 1,000 clean profit banked).
* **Key Lesson**: Open = Low morning drives provide the fastest, cleanest momentum expansion with minimal drawdown.

### Trade 2: HINDALCO - Sector Momentum & Friction Awareness
* **Setup**: Nifty Metal leading, breakout above Rs 915.
* **Entry**: 250 shares @ Rs 916.67.
* **Peak**: Hit Rs 920.85 (+Rs 895 gross profit).
* **Exit**: Exited near Rs 917 (-Rs 100 net after Zerodha brokerage & STT).
* **Key Lesson**: Modify open SL orders directly instead of placing duplicate orders that fail on margin checks. Exit promptly at predefined target zones.

### Trade 3: BEL (Bharat Electronics Ltd) - The Midday Absorption Breakout
* **Setup**: Defied Nifty index midday weakness. Formed 5m Multi-Wick Absorption Base at Rs 392.00 - Rs 392.50.
* **Entry**: 550 shares @ Rs 392.50.
* **Target Hit**: Rs 395.49 - Rs 395.60 (+Rs 1,500 clean profit banked).
* **Key Lesson**: Stocks showing relative strength against a falling Nifty index explode hardest when the index stabilizes. Multi-wick base provides safe, tight SL anchor.

### Trade 4 Audit: KALYANKJIL - The Anti-FOMO Institutional Filter (PASS)
* **Situation**: User considered buying at Rs 533 for Rs 1,000 profit after stock was already up +5.2%.
* **Audit**: Confluence Score 55/100 (`NO_TRADE_CONDITIONS_NOT_MET`). Stretched Rs 11 above VWAP (Rs 520.90). Volume climax on 1m candles.
* **Action**: Assistant strongly advised against both Buying (distribution trap) and Shorting (short squeeze danger).
* **Key Lesson**: Protecting banked gains (+Rs 2,500) by rejecting extended trades is what separates consistently profitable traders from gamblers.

