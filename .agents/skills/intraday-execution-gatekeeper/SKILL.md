---
name: intraday-execution-gatekeeper
description: >-
  Strict institutional pre-flight checklist and risk gatekeeper before suggesting or executing any intraday stock trade on the Indian market (NSE/BSE). Enforces Open=Low/Open=High rules, +4.5% extension anti-chase gates, Upper Circuit trap filters, and capital preservation protocols.
---

# 🛡️ Intraday Execution Gatekeeper & Pre-Flight Checklist

Before suggesting or approving ANY intraday trade to the trader, this gatekeeper skill MUST be fully executed and verified.

---

## 🚦 Phase 1: Hard Disqualification Filters (Instant Rejection)

If ANY of the following 5 conditions are met, the setup is **INSTANTLY REJECTED (`NO TRADE`)**:

1. **The +4.5% Extension Filter (Law #11)**:
   * Is the stock already up $\ge 4.5\%$ from today's open?
   * Is CMP $> 2.0\%$ above its intraday VWAP?
   * *If YES $\rightarrow$ REJECT. Never chase Day Highs during afternoon sessions.*
2. **The Open = High Filter (Law #2)**:
   * Is Open within 0.15% of Day High?
   * *If YES $\rightarrow$ REJECT Longs. Institutions sold the open.*
3. **The Circuit Breaker Filter (Law #12)**:
   * Is the stock trading near or at Upper Circuit (Zero Sellers) or Lower Circuit (Zero Buyers)?
   * *If YES $\rightarrow$ REJECT. Illiquid trap with zero exit ability.*
4. **Earnings / Board Meeting Filter (Law #7)**:
   * Does the company have Q1/Q2/Q3/Q4 results or corporate actions today?
   * *If YES $\rightarrow$ REJECT. Binary gambling risk.*
5. **Session Time Cutoff (Law #5)**:
   * Is current time past 14:45 IST?
   * *If YES $\rightarrow$ REJECT new MIS positions (broker auto square-off at 15:15 IST).*

---

## 🎯 Phase 2: The Multi-Confluence Engine ($\ge 85\%$ Score Required)

Run `trader-analyst/confluence_engine.py` or verify:
* **Order Flow & VWAP**: Is price resting on or retesting VWAP / POC support?
* **Market Structure**: Is there a 5-minute Multi-Wick Absorption Base (Law #9) or Fair Value Gap (FVG)?
* **Sector Confirmation (Law #3)**: Is the stock's parent index (Nifty Metal, Nifty Realty, etc.) trading green and outperforming?
* **Risk:Reward Calculation**: Is the potential gain at least **2x to 3x** the risk to structural SL?

---

## 🔒 Phase 3: The Capital Preservation Protocol (Law #13)

* **If the trader is already in profit (+2% to +3% on capital today)**:
  * Maximum allowable risk on any new trade is strictly **20% of today's banked profit**.
  * Never gamble banked profits on low-conviction ideas.
* **The Inversion Fallacy (Law #14)**:
  * Never short an overbought stock just because it cannot be bought. Shorting requires confirmed structural breakdown below VWAP.

---

## 📖 Battle-Tested Blueprint Archive

* **RVNL**: Open=Low (+1.8% intraday, +₹1,000 profit).
* **BEL**: Midday absorption base at ₹392.50 (+₹1,500 profit at ₹395.50 target).
* **KALYANKJIL**: Avoided +5.2% trap at ₹533 (protected ₹2,500 banked gain).
