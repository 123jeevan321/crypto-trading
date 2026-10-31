# Binary Trading Keyword Protocol

## Trigger Keyword: `"binary trading entry"`

Whenever the user prompts with:
```text
binary trading entry
```

### Protocol Checklist:
1. **Analyze Live Markets**:
   - Run multi-pair scan on the top 20 Quotex currency pairs.
   - Calculate live SMC (Liquidity Sweeps, Order Blocks, Fair Value Gaps).
   - Calculate 5-Strategy Confluence (EMA 20/50, RSI 14, Bollinger Bands, MACD).
   - Check IST Session Risk Window.

2. **Strict Output Rules**:
   - **RULE 1 - NO FORCED TRADES**: If confluence is below 88% or market is in a dangerous/choppy zone, DO NOT recommend a trade. Explicitly state:
     > **"NO ENTRY RIGHT NOW. MARKET IS CHOPPY / DANGEROUS. WAIT."**
   - **RULE 2 - EXACTLY ONE TRADE**: Never offer Option 1 and Option 2. Provide strictly the single highest-probability setup.
   - **RULE 3 - CANDLE 00-SECOND EXECUTION**: Explicitly specify:
     - Pair (e.g., `GBP/USD (OTC)`)
     - Payout (e.g., `88%`)
     - Direction (`CALL ⬆️` or `PUT ⬇️`)
     - Recommended Expiry (`5 Minutes`)
     - Wait for the current candle to close and enter at `:00` seconds of the new candle!
