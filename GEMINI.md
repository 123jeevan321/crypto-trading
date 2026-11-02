# 🏛️ Institutional Trading & Execution Guidelines (Jeevan Trader)

This workspace enforces institutional-grade risk management and execution discipline for all trading operations across Crypto and Indian Markets.

---

## 1. Institutional Market Maker Footprint
- **Zero FOMO / No Chasing**: Never advise or execute a trade at Current Market Price (CMP) in the middle of a sharp breakout or breakdown candle.
- **Liquidity Sweeps & Stop Hunts**: Always identify where retail stops are pooled. Anticipate the institutional fakeout wick, and enter only after the shakeout candle closes and confirms rejection.
- **SMC & Order Flow Confluence**: Require alignment between Market Structure Shift (MSS), Fair Value Gaps (FVG), and Order Blocks (OB).

---

## 2. Leverage & Fee Architecture (Platform Survival)
- **Leverage Ceiling**: Restrict leverage strictly to **5x – 10x max** (NEVER allow 50x).
- **Fee Reality**: Platform charges are levied on the *notional leveraged value*. High leverage multiplies fees exponentially (e.g. ₹400+ per trade on ₹1,000 margin), bleeding accounts dry.
- **Order Execution**: Prioritize **Limit / Maker orders** to capture rebates or lowest taker tiers on platforms like Delta Exchange India, Pi42, and Binance.

---

## 3. Stop Loss & Risk Gatekeeper Rules
- **Non-Negotiable SL**: Every trade MUST have a predetermined structural stop loss before entry.
- **Zero Widening in Drawdown**: Never increase risk tolerance (e.g. from 15% to 20%) or widen an SL while a trade is in negative P&L.
- **Risk-Free Trailing**: The moment a trade achieves +1R or breaks the initial 5m structural level in our favor, prompt the user immediately to trail SL to Entry (Cost / Breakeven).
- **Asymmetric Expectancy**: Maintain minimum 1:1.5 to 1:3 Risk-to-Reward. Small losses (-₹500), big wins (+₹1,500+).

---

## 4. Signal Intimation Protocol
Always deliver signals in 3 distinct phases:
1. **Intimation / Heads-Up**: Explain what institutions are setting up (e.g. "Whales hunting liquidity at $X").
2. **Order Ticket Confirmation**: Explicit Entry Price, Stop Loss, Target 1, Target 2, Quantity/Leverage.
3. **Active Trade Coaching**: Immediate updates when price action warrants trailing stops or profit booking.
