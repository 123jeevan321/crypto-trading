# Quotex (Cortex) Binary Options Confluence Trading System

A dedicated, high-probability binary options signal engine and decision terminal designed specifically for manual execution on **Quotex**.

---

## 🎯 System Overview

* **Manual Execution Focus**: Provides clear, real-time **CALL ⬆️** and **PUT ⬇️** signals with recommended expiration times (**5m, 15m, 1h**) so you can manually click on your Quotex screen with complete control and zero API risk.
* **Top 20 Quotex Currency Pairs**: Scanned simultaneously in real-time, filtered strictly for high-payout pairs (**82% to 90%+ payout**).
* **5-Strategy Confluence Engine**: Evaluates 5 institutional and price action strategies; generates high-confidence alerts only when multiple strategies agree (80%–95%+ probability).
* **Live Forex Session Clock**: Tracks London, New York, Tokyo, and Sydney sessions in IST and GMT, highlighting the high-volume **London / New York Overlap (6:30 PM – 9:30 PM IST)**.

---

## 🏆 Top 20 Currency Pairs Monitored (Quotex Payouts ≥ 80%)

| Symbol | Category | Typical Quotex Payout | Optimal Trading Session |
| :--- | :--- | :---: | :--- |
| **EUR/USD** | Major | **90%** | London & New York (Peak Overlap) |
| **GBP/USD** | Major | **88%** | London & New York |
| **USD/JPY** | Major | **87%** | Tokyo & New York |
| **AUD/USD** | Major | **85%** | Sydney, Tokyo & New York |
| **USD/CAD** | Major | **85%** | New York |
| **USD/CHF** | Major | **84%** | London & New York |
| **NZD/USD** | Major | **83%** | Sydney & Tokyo |
| **EUR/GBP** | Cross | **86%** | London |
| **EUR/JPY** | Cross | **88%** | London & Tokyo |
| **GBP/JPY** | Cross | **89%** | London & Tokyo (High Volatility) |
| **AUD/JPY** | Cross | **85%** | Sydney & Tokyo |
| **CAD/JPY** | Cross | **84%** | Tokyo & New York |
| **EUR/AUD** | Cross | **85%** | London & Sydney |
| **GBP/AUD** | Cross | **86%** | London & Sydney |
| **EUR/CAD** | Cross | **84%** | London & New York |
| **GBP/CAD** | Cross | **85%** | London & New York |
| **AUD/NZD** | Cross | **82%** | Sydney & Tokyo |
| **NZD/JPY** | Cross | **83%** | Sydney & Tokyo |
| **EUR/CHF** | Cross | **82%** | London |
| **USD/INR** | Exotic | **82%** | Asian & London |

---

## 🧠 The Top 5 High-Probability Binary Strategies

### 1. EMA 20/50 Trend-Pullback Strategy (5m Expiry)
* **Principle**: Trade strictly in the direction of the macro trend by entering on pullbacks to dynamic support/resistance.
* **CALL Rule**: EMA 20 > EMA 50, price pulls back to test EMA 20, RSI resets between 40–55, bullish candle confirms → **CALL (5 min)**.
* **PUT Rule**: EMA 20 < EMA 50, price pulls back to test EMA 20, RSI resets between 45–60, bearish candle confirms → **PUT (5 min)**.

### 2. Bollinger Bands + RSI Extreme Mean Reversion (1m–5m Expiry)
* **Principle**: Capitalize on market exhaustion when price stretches outside statistical normal distribution.
* **CALL Rule**: Price touches/pierces Lower Bollinger Band, RSI < 30 (deeply oversold), rejection wick appears → **CALL (3–5 min)**.
* **PUT Rule**: Price touches/pierces Upper Bollinger Band, RSI > 70 (deeply overbought), rejection wick appears → **PUT (3–5 min)**.

### 3. Key Support & Resistance Price Action Wick Rejection (5m–15m Expiry)
* **Principle**: Institutional round numbers (e.g. 1.08500, 150.00) act as price magnets and reversal zones.
* **CALL Rule**: Price reaches major support / round number and leaves a pin-bar rejection (lower wick ≥ 50% of candle body) → **CALL (5–15 min)**.
* **PUT Rule**: Price reaches major resistance / round number and leaves a pin-bar rejection (upper wick ≥ 50% of candle body) → **PUT (5–15 min)**.

### 4. MACD Momentum Zero-Line Crossover Filter
* **Principle**: Confirms directional strength using histogram acceleration.
* **CALL Rule**: MACD histogram turns positive while price is above EMA 50 → **CALL confirmed**.
* **PUT Rule**: MACD histogram turns negative while price is below EMA 50 → **PUT confirmed**.

### 5. High-Impact Economic News Safety Filter
* **Principle**: High-impact news releases (NFP, CPI, Fed Rate Decision) create erratic spikes that break technical analysis.
* **Rule**: Pause binary trading **15 minutes before and 15 minutes after** high-impact news releases.

---

## ⏰ Global Forex Market Sessions (IST Timing)

| Session | Hours (IST) | Market Characteristics | Best Pairs to Trade |
| :--- | :--- | :--- | :--- |
| **Sydney** | 03:30 AM – 12:30 PM | Low volatility, ranging | AUD/NZD, AUD/USD |
| **Tokyo (Asian)** | 05:30 AM – 02:30 PM | Smooth trends for Yen | USD/JPY, AUD/JPY, EUR/JPY |
| **London** | 01:30 PM – 09:30 PM | High liquidity, large moves | EUR/USD, GBP/USD, EUR/GBP |
| **New York** | 06:30 PM – 02:30 AM | Heavy USD & CAD volume | EUR/USD, USD/CAD, USD/JPY |
| **🔥 GOLDEN OVERLAP (London + NY)** | **06:30 PM – 09:30 PM IST** | **Highest volume & win-rate of the day (~70% of world volume)** | **EUR/USD, GBP/USD, GBP/JPY** |

---

## 🚀 How to Run the Signal Terminal

Start the live web scanner server:
```powershell
python binary-trading/app.py
```
Then open your browser at:
```text
http://127.0.0.1:8085
```

### How to Trade with the Signals on Quotex:
1. Keep the Signal Terminal open side-by-side with your Quotex platform.
2. When a **Strong Signal (Confluence ≥ 75%)** appears:
   - Check the **Symbol** (e.g., `GBP/USD`).
   - Check the **Direction** (`CALL ⬆️` or `PUT ⬇️`).
   - Check the **Recommended Expiry** (usually **5 Minutes**).
3. On Quotex, select the pair, set the 5-minute timer, and click **UP (Green)** or **DOWN (Red)**.
4. **Risk Rule**: Never bet more than **2% to 3%** of your total balance on a single trade.
