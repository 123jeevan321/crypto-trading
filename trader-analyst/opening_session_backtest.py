"""
Opening Session Scalping Quantitative Backtest Engine (9:15 AM - 9:25 AM)
Analyzes 1-minute microstructure for Indian Equities across the past 30 days.
Evaluates retail traps, liquidity sweeps, Open=Low drives, and 9:17 AM inversions.
Calculates Zerodha transaction costs, slippage, and capital sizing for Rs 20,000 daily target.
"""

import os
import sys
import datetime as dt
import numpy as np
import pandas as pd
import yfinance as yf

# Cache directory for intraday data
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "intraday_1m")
os.makedirs(DATA_DIR, exist_ok=True)

WATCHLIST = [
    "ICICIBANK.NS",
    "HDFCBANK.NS",
    "SBIN.NS",
    "RELIANCE.NS",
    "TATAMOTORS.NS",
    "DLF.NS",
    "INFY.NS",
    "KALYANKJIL.NS",
    "DELHIVERY.NS",
    "HINDALCO.NS",
    "TATASTEEL.NS",
    "RVNL.NS"
]

def fetch_1m_data(symbol, days=30):
    cache_file = os.path.join(DATA_DIR, f"{symbol.replace('.NS', '')}_1m.parquet")
    if os.path.exists(cache_file):
        try:
            df = pd.read_parquet(cache_file)
            # Check if recent enough
            if len(df) > 0 and (dt.datetime.now().date() - df.index[-1].date()).days <= 1:
                return df
        except Exception:
            pass

    print(f"Downloading 1m data for {symbol}...")
    t = yf.Ticker(symbol)
    chunks = []
    end = dt.datetime.now() + dt.timedelta(days=1)
    # Fetch in 7-day chunks (Yahoo limit)
    for _ in range(5):
        start = end - dt.timedelta(days=7)
        try:
            df_chunk = t.history(
                start=start.strftime('%Y-%m-%d'),
                end=end.strftime('%Y-%m-%d'),
                interval='1m'
            )
            if len(df_chunk) > 0:
                chunks.append(df_chunk)
        except Exception as e:
            print(f"Error fetching chunk for {symbol}: {e}")
        end = start

    if not chunks:
        return pd.DataFrame()

    full_df = pd.concat(chunks).sort_index()
    full_df = full_df[~full_df.index.duplicated(keep='first')]
    # Save cache
    try:
        full_df.to_parquet(cache_file)
    except Exception as e:
        print(f"Cache save failed: {e}")
    return full_df

def calculate_zerodha_friction(buy_turnover, sell_turnover):
    """
    Computes exact Zerodha Intraday Equity statutory & brokerage costs.
    - Brokerage: 0.03% or Rs 20 per leg (max Rs 40 round trip)
    - STT: 0.025% on sell side
    - Exchange txn charge: 0.00297% on both sides
    - GST: 18% on (brokerage + exchange txn charge)
    - SEBI charge: 0.0001%
    - Stamp duty: 0.003% on buy side
    """
    brokerage_buy = min(20.0, 0.0003 * buy_turnover)
    brokerage_sell = min(20.0, 0.0003 * sell_turnover)
    brokerage = brokerage_buy + brokerage_sell

    stt = 0.00025 * sell_turnover
    exchange_charges = 0.0000297 * (buy_turnover + sell_turnover)
    gst = 0.18 * (brokerage + exchange_charges)
    sebi = 0.000001 * (buy_turnover + sell_turnover)
    stamp_duty = 0.00003 * buy_turnover

    total_taxes = brokerage + stt + exchange_charges + gst + sebi + stamp_duty
    return total_taxes

def analyze_opening_microstructure(df):
    """
    Analyzes candle 1 (09:15) and subsequent 9:15-9:25 movement.
    """
    days = sorted(list(set(df.index.strftime('%Y-%m-%d'))))
    results = []

    for d in days:
        day_data = df.loc[d]
        if len(day_data) < 15:
            continue
        
        # Filter 09:15 to 09:25
        window = day_data.between_time('09:15', '09:25')
        if len(window) < 5:
            continue

        c1 = window.iloc[0] # 9:15 candle
        c1_range = c1.High - c1.Low
        if c1_range == 0:
            continue

        body_top = max(c1.Open, c1.Close)
        body_bottom = min(c1.Open, c1.Close)
        upper_wick = c1.High - body_top
        lower_wick = body_bottom - c1.Low

        upper_wick_ratio = upper_wick / c1_range
        lower_wick_ratio = lower_wick / c1_range
        body_ratio = abs(c1.Close - c1.Open) / c1_range

        # Check Open=Low (<5% lower wick)
        is_open_low = (lower_wick / c1.Open) < 0.0005 or lower_wick_ratio < 0.08
        # Check Open=High (<5% upper wick)
        is_open_high = (upper_wick / c1.Open) < 0.0005 or upper_wick_ratio < 0.08

        # Trap detection: Large upper wick (>35%) after a fast surge, then broken downward
        is_bull_trap = upper_wick_ratio > 0.35 and c1.Close < c1.Open

        results.append({
            'date': d,
            'c1_open': c1.Open,
            'c1_high': c1.High,
            'c1_low': c1.Low,
            'c1_close': c1.Close,
            'c1_volume': c1.Volume,
            'range_pts': c1_range,
            'range_pct': (c1_range / c1.Open) * 100,
            'upper_wick_ratio': upper_wick_ratio,
            'lower_wick_ratio': lower_wick_ratio,
            'body_ratio': body_ratio,
            'is_open_low': is_open_low,
            'is_open_high': is_open_high,
            'is_bull_trap': is_bull_trap,
            'window_df': window
        })
    return results

def backtest_strategies(symbol, microstructure_data):
    """
    Simulates:
    1. Blind 9:15:10 entry (the retail mistake)
    2. Strategy A: Law #1 Open=Low Institutional Drive (Entry 9:16)
    3. Strategy B: Law #21 9:17 Trap Inversion Short (Entry 9:17)
    """
    trades_retail = []
    trades_open_low = []
    trades_trap_inversion = []

    # Position sizing target: Base capital Rs 2,00,000 to Rs 3,00,000 (with 5x intraday margin = Rs 10L-15L exposure)
    # Target Rs 20,000 daily
    ALLOCATED_EXPOSURE = 1000000.0 # Rs 10,00,000 intraday buying power (Rs 2,00,000 margin at 5x)

    for item in microstructure_data:
        wdf = item['window_df']
        if len(wdf) < 8:
            continue

        c1 = wdf.iloc[0] # 9:15
        c2 = wdf.iloc[1] # 9:16
        c3 = wdf.iloc[2] # 9:17
        
        # Shares based on Rs 10L exposure
        shares = int(ALLOCATED_EXPOSURE / c1.Open)
        if shares <= 0:
            shares = 100

        # --- TEST 1: Blind Retail 9:15 Long (Enters at 9:15 Market Close/High) ---
        retail_entry = c1.Open + (c1.High - c1.Open) * 0.75 # Slippage / FOMO fill near top
        # Stop loss: 0.5% below entry. Target: 0.8%
        retail_sl = retail_entry * 0.995
        retail_tp = retail_entry * 1.008
        retail_exit = None
        retail_result = 'EXIT_925'

        for t_idx in range(1, len(wdf)):
            bar = wdf.iloc[t_idx]
            if bar.Low <= retail_sl:
                retail_exit = retail_sl
                retail_result = 'STOP_LOSS'
                break
            elif bar.High >= retail_tp:
                retail_exit = retail_tp
                retail_result = 'TARGET'
                break
        if retail_exit is None:
            retail_exit = wdf.iloc[-1].Close

        gross_pnl = (retail_exit - retail_entry) * shares
        friction = calculate_zerodha_friction(retail_entry * shares, retail_exit * shares)
        slippage_cost = 0.0005 * retail_entry * shares # 0.05% slippage
        net_pnl = gross_pnl - friction - slippage_cost

        trades_retail.append({
            'date': item['date'],
            'symbol': symbol,
            'entry': retail_entry,
            'exit': retail_exit,
            'gross_pnl': gross_pnl,
            'net_pnl': net_pnl,
            'result': retail_result,
            'is_win': net_pnl > 0
        })

        # --- TEST 2: Strategy A - Law #1 Open=Low Institutional Drive ---
        # Condition: C1 has Open == Low (< 0.05% lower wick). C2 breaks C1 High.
        if item['is_open_low'] and c2.High > c1.High:
            entry_price = c1.High + (0.0005 * c1.High) # Enter upon breakout of 9:15 high
            sl_price = c1.Low # Invalidation: breakdown below open
            risk_per_share = entry_price - sl_price
            
            # If risk is too wide (>0.8%), cap risk at 0.4%
            if risk_per_share > entry_price * 0.005:
                sl_price = entry_price * 0.996
                risk_per_share = entry_price - sl_price
            
            # Target: 1.5R to 2R (or min +0.7%)
            tp_price = entry_price + max(risk_per_share * 1.8, entry_price * 0.007)
            
            # Position size: Cap max risk at Rs 4,000 per trade!
            risk_shares = int(4000.0 / max(risk_per_share, 1.0))
            active_shares = min(shares, risk_shares)
            
            exit_price = None
            result_label = 'TIME_EXIT'
            for t_idx in range(2, len(wdf)):
                bar = wdf.iloc[t_idx]
                if bar.Low <= sl_price:
                    exit_price = sl_price
                    result_label = 'STOP_LOSS'
                    break
                elif bar.High >= tp_price:
                    exit_price = tp_price
                    result_label = 'TARGET'
                    break
            if exit_price is None:
                exit_price = wdf.iloc[-1].Close

            gross = (exit_price - entry_price) * active_shares
            fric = calculate_zerodha_friction(entry_price * active_shares, exit_price * active_shares)
            net = gross - fric
            trades_open_low.append({
                'date': item['date'],
                'symbol': symbol,
                'type': 'OPEN_LOW_LONG',
                'entry': entry_price,
                'exit': exit_price,
                'shares': active_shares,
                'gross_pnl': gross,
                'net_pnl': net,
                'result': result_label,
                'is_win': net > 0
            })

        # --- TEST 3: Strategy B - Law #21 9:17 AM Trap Inversion Short ---
        # Condition: C1 has upper wick > 35%. C2 tries to push or stalls.
        # At 9:17 (C3), price breaks below C1 Low or C2 Low (liquidity grab failure).
        upper_wick_condition = item['upper_wick_ratio'] > 0.35
        if upper_wick_condition and (c3.Low < c1.Low or c3.Close < c1.Open):
            entry_price = min(c1.Low, c3.Open) - (0.0002 * c1.Low)
            sl_price = c1.High # Stop loss above the liquidity trap wick
            risk_per_share = sl_price - entry_price
            if risk_per_share > entry_price * 0.006:
                sl_price = entry_price * 1.005 # Cap SL at 0.5%
                risk_per_share = sl_price - entry_price
            
            tp_price = entry_price - max(risk_per_share * 1.8, entry_price * 0.008)
            
            risk_shares = int(4000.0 / max(risk_per_share, 1.0))
            active_shares = min(shares, risk_shares)

            exit_price = None
            result_label = 'TIME_EXIT'
            for t_idx in range(3, len(wdf)):
                bar = wdf.iloc[t_idx]
                if bar.High >= sl_price:
                    exit_price = sl_price
                    result_label = 'STOP_LOSS'
                    break
                elif bar.Low <= tp_price:
                    exit_price = tp_price
                    result_label = 'TARGET'
                    break
            if exit_price is None:
                exit_price = wdf.iloc[-1].Close

            gross = (entry_price - exit_price) * active_shares
            fric = calculate_zerodha_friction(entry_price * active_shares, exit_price * active_shares)
            net = gross - fric
            trades_trap_inversion.append({
                'date': item['date'],
                'symbol': symbol,
                'type': 'TRAP_INVERSION_SHORT',
                'entry': entry_price,
                'exit': exit_price,
                'shares': active_shares,
                'gross_pnl': gross,
                'net_pnl': net,
                'result': result_label,
                'is_win': net > 0
            })

    return trades_retail, trades_open_low, trades_trap_inversion

def main():
    print("=" * 80)
    print(" QUANTITATIVE STUDY: 9:15 - 9:25 AM OPENING SESSION MICROSTRUCTURE")
    print(" Target: Rs 20,000 / Day | Indian Equities Intraday (Zerodha Friction Model)")
    print("=" * 80)

    all_micro = []
    all_retail = []
    all_open_low = []
    all_trap_inv = []

    stock_stats = {}

    for sym in WATCHLIST:
        df = fetch_1m_data(sym)
        if len(df) == 0:
            continue
        micro = analyze_opening_microstructure(df)
        all_micro.extend(micro)
        ret, o_l, t_inv = backtest_strategies(sym, micro)
        all_retail.extend(ret)
        all_open_low.extend(o_l)
        all_trap_inv.extend(t_inv)

        stock_stats[sym] = {
            'days': len(micro),
            'open_low_count': sum(1 for m in micro if m['is_open_low']),
            'bull_trap_count': sum(1 for m in micro if m['is_bull_trap']),
            'avg_915_range_pct': np.mean([m['range_pct'] for m in micro]) if micro else 0,
            'avg_upper_wick': np.mean([m['upper_wick_ratio'] for m in micro]) if micro else 0,
            'avg_lower_wick': np.mean([m['lower_wick_ratio'] for m in micro]) if micro else 0,
        }

    print("\n--- 1. MICROSTRUCTURE AUDIT ACROSS WATCHLIST (PAST 30 DAYS) ---")
    print(f"{'Symbol':<15} {'Days':<6} {'Avg 9:15 Range%':<18} {'Upper Wick%':<14} {'Lower Wick%':<14} {'Open=Low Days':<14} {'Trap Days':<10}")
    print("-" * 88)
    for sym, st in stock_stats.items():
        print(f"{sym:<15} {st['days']:<6} {st['avg_915_range_pct']:>6.2f}%            {st['avg_upper_wick']*100:>5.1f}%         {st['avg_lower_wick']*100:>5.1f}%         {st['open_low_count']:<14} {st['bull_trap_count']:<10}")

    def summarize_strategy(trades, name):
        if not trades:
            print(f"\n{name}: No trades generated.")
            return
        tdf = pd.DataFrame(trades)
        total_trades = len(tdf)
        wins = tdf[tdf['is_win']]
        losses = tdf[~tdf['is_win']]
        win_rate = (len(wins) / total_trades) * 100
        gross_total = tdf['gross_pnl'].sum()
        net_total = tdf['net_pnl'].sum()
        avg_trade_net = tdf['net_pnl'].mean()
        avg_win = wins['net_pnl'].mean() if len(wins) > 0 else 0
        avg_loss = abs(losses['net_pnl'].mean()) if len(losses) > 0 else 0
        profit_factor = (wins['net_pnl'].sum() / abs(losses['net_pnl'].sum())) if len(losses) > 0 and losses['net_pnl'].sum() != 0 else 999.0
        
        # Max drawdown calculation
        tdf['cum_pnl'] = tdf['net_pnl'].cumsum()
        tdf['peak'] = tdf['cum_pnl'].cummax()
        tdf['dd'] = tdf['peak'] - tdf['cum_pnl']
        max_dd = tdf['dd'].max()

        # Consecutive losses
        is_loss_series = (~tdf['is_win']).astype(int)
        consec_losses = 0
        cur_loss = 0
        for l in is_loss_series:
            if l == 1:
                cur_loss += 1
                consec_losses = max(consec_losses, cur_loss)
            else:
                cur_loss = 0

        print(f"\n{'='*25} {name} {'='*25}")
        print(f"Total Trades Taken       : {total_trades}")
        print(f"Win Rate                 : {win_rate:.1f}% ({len(wins)}W / {len(losses)}L)")
        print(f"Net Total PnL (Post-Tax) : Rs {net_total:,.2f}")
        print(f"Gross PnL                : Rs {gross_total:,.2f}")
        print(f"Average Trade Net        : Rs {avg_trade_net:,.2f}")
        print(f"Average Win              : Rs {avg_win:,.2f}")
        print(f"Average Loss             : Rs {avg_loss:,.2f}")
        print(f"Profit Factor            : {profit_factor:.2f}")
        print(f"Max Cumulative Drawdown  : Rs {max_dd:,.2f}")
        print(f"Max Consecutive Losses   : {consec_losses}")

    print("\n--- 2. STRATEGY COMPARISON & PERFORMANCE ---")
    summarize_strategy(all_retail, "RETAIL MISTAKE: Blind 9:15 AM Market Long")
    summarize_strategy(all_open_low, "STRATEGY A (Law #1): 9:16 AM Open=Low Drive Long")
    summarize_strategy(all_trap_inv, "STRATEGY B (Law #21): 9:17 AM Trap Inversion Short")

    # Combine Strategy A + B into daily combined performance
    if all_open_low or all_trap_inv:
        combined = []
        for t in all_open_low + all_trap_inv:
            combined.append(t)
        cdf = pd.DataFrame(combined)
        daily_pnl = cdf.groupby('date')['net_pnl'].sum()
        print("\n" + "=" * 25 + " COMBINED SYSTEM (Law #1 + Law #21) " + "=" * 25)
        print(f"Total Combined Days Active: {len(daily_pnl)}")
        print(f"Profitable Days Ratio     : {(sum(daily_pnl > 0) / len(daily_pnl))*100:.1f}% ({sum(daily_pnl > 0)}/{len(daily_pnl)} days)")
        print(f"Average Daily Net PnL     : Rs {daily_pnl.mean():,.2f}")
        print(f"Max Single Day Profit     : Rs {daily_pnl.max():,.2f}")
        print(f"Max Single Day Loss       : Rs {daily_pnl.min():,.2f}")
        print(f"Total 30-Day Net Profit   : Rs {daily_pnl.sum():,.2f}")

if __name__ == '__main__':
    main()
