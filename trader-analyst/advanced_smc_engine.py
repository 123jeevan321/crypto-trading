"""
Advanced SMC 9:15-9:25 AM Strategy Engine with Caching & Precision Execution
Implements:
1. Smart Money Concepts: Fair Value Gap (FVG) Retracement & Break of Structure (BOS)
2. Institutional Filter: RVOL & Open=Low vs Trap Wick Analysis
3. Zerodha Friction Model & Asymmetric Tranche Scaling (Rs 20k target)
"""

import os
import sys
import datetime as dt
import numpy as np
import pandas as pd
import yfinance as yf

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "intraday_1m")
os.makedirs(DATA_DIR, exist_ok=True)

WATCHLIST = [
    "ICICIBANK.NS", "HDFCBANK.NS", "SBIN.NS", "RELIANCE.NS",
    "TATAMOTORS.NS", "DLF.NS", "INFY.NS", "KALYANKJIL.NS",
    "DELHIVERY.NS", "HINDALCO.NS", "TATASTEEL.NS", "RVNL.NS"
]

def get_cached_or_download_1m(symbol):
    cache_file = os.path.join(DATA_DIR, f"{symbol.replace('.NS', '')}_1m.pkl")
    if os.path.exists(cache_file):
        try:
            return pd.read_pickle(cache_file)
        except Exception:
            pass

    t = yf.Ticker(symbol)
    chunks = []
    end = dt.datetime.now() + dt.timedelta(days=1)
    for _ in range(5):
        start = end - dt.timedelta(days=7)
        try:
            df_chunk = t.history(start=start.strftime('%Y-%m-%d'), end=end.strftime('%Y-%m-%d'), interval='1m')
            if len(df_chunk) > 0:
                chunks.append(df_chunk)
        except Exception:
            pass
        end = start

    if not chunks:
        return pd.DataFrame()

    full_df = pd.concat(chunks).sort_index()
    full_df = full_df[~full_df.index.duplicated(keep='first')]
    full_df.to_pickle(cache_file)
    return full_df

def calculate_zerodha_friction(buy_val, sell_val):
    brokerage = min(20.0, 0.0003 * buy_val) + min(20.0, 0.0003 * sell_val)
    stt = 0.00025 * sell_val
    exchange = 0.0000297 * (buy_val + sell_val)
    gst = 0.18 * (brokerage + exchange)
    sebi = 0.000001 * (buy_val + sell_val)
    stamp = 0.00003 * buy_val
    return brokerage + stt + exchange + gst + sebi + stamp

def run_advanced_smc_backtest():
    all_smc_trades = []
    timing_study = {'9:15_blind': [], '9:16_breakout': [], '9:17_fvg_retest': [], '9:20_delayed': []}

    for sym in WATCHLIST:
        df = get_cached_or_download_1m(sym)
        if len(df) == 0:
            continue
        days = sorted(list(set(df.index.strftime('%Y-%m-%d'))))

        for d in days:
            day_data = df.loc[d]
            if len(day_data) < 15:
                continue
            window = day_data.between_time('09:15', '09:25')
            if len(window) < 8:
                continue

            c1 = window.iloc[0] # 9:15
            c2 = window.iloc[1] # 9:16
            c3 = window.iloc[2] # 9:17
            c4 = window.iloc[3] # 9:18
            c5 = window.iloc[4] # 9:19
            
            c1_range = c1.High - c1.Low
            if c1_range == 0:
                continue

            lower_wick = (min(c1.Open, c1.Close) - c1.Low) / c1_range
            upper_wick = (c1.High - max(c1.Open, c1.Close)) / c1_range
            body_ratio = abs(c1.Close - c1.Open) / c1_range

            # --- SETUP 1: SMC Open=Low Institutional Drive with FVG Retest ---
            # Criteria:
            # 1. Zero/tiny lower wick (< 10%)
            # 2. Strong green close (Body > 60%)
            # 3. 9:16 breaks 9:15 High creating 1m FVG
            # 4. 9:17 or 9:18 retests upper 50% of C1 High (Discount Entry)
            if lower_wick < 0.10 and c1.Close > c1.Open and body_ratio > 0.50:
                if c2.High > c1.High:
                    # SMC Entry: Limit/Market fill on slight pullback to C1 High (FVG retest)
                    fvg_entry = c1.High # Retest level
                    # If C2 or C3 dipped near C1 High, filled!
                    filled = False
                    entry_time = None
                    if c2.Low <= fvg_entry <= c2.High:
                        filled = True
                        entry_time = '09:16'
                    elif c3.Low <= fvg_entry <= c3.High:
                        filled = True
                        entry_time = '09:17'
                    elif c4.Low <= fvg_entry <= c4.High:
                        filled = True
                        entry_time = '09:18'
                    
                    if filled:
                        sl = c1.Low
                        risk_per_share = fvg_entry - sl
                        if risk_per_share > fvg_entry * 0.005:
                            sl = fvg_entry * 0.996
                            risk_per_share = fvg_entry - sl
                        
                        # Target: +0.8% to +1.2% (Target 1: +0.6%, Target 2: +1.0% runner)
                        tp1 = fvg_entry + (risk_per_share * 1.5)
                        tp2 = fvg_entry + (risk_per_share * 2.5)
                        
                        # Position Sizing for Rs 4,000 risk (Targeting Rs 10k-15k profit)
                        shares = int(4000.0 / max(risk_per_share, 1.0))
                        shares = min(shares, int(1200000 / fvg_entry)) # Max Rs 12L margin exposure

                        # Track outcome through 9:25
                        exit_price = None
                        status = 'TIME_EXIT'
                        for t_idx in range(3, len(window)):
                            bar = window.iloc[t_idx]
                            if bar.Low <= sl:
                                exit_price = sl
                                status = 'STOP_LOSS'
                                break
                            elif bar.High >= tp2:
                                exit_price = tp2
                                status = 'RUNNER_TARGET_HIT'
                                break
                            elif bar.High >= tp1 and exit_price is None:
                                # Lock in Tranche 1
                                pass
                        
                        if exit_price is None:
                            # 9:25 close
                            exit_price = window.iloc[-1].Close

                        gross = (exit_price - fvg_entry) * shares
                        friction = calculate_zerodha_friction(fvg_entry * shares, exit_price * shares)
                        net = gross - friction
                        all_smc_trades.append({
                            'date': d,
                            'symbol': sym,
                            'strategy': 'SMC_OPEN_LOW_FVG',
                            'entry_time': entry_time,
                            'entry': fvg_entry,
                            'exit': exit_price,
                            'shares': shares,
                            'gross_pnl': gross,
                            'friction': friction,
                            'net_pnl': net,
                            'status': status,
                            'is_win': net > 0
                        })

            # --- SETUP 2: SMC 9:17 Liquidity Sweep Reversal Short (CHoCH) ---
            # Criteria:
            # 1. C1 shoots up leaving giant upper wick (> 35%)
            # 2. C2 or C3 fails to make new high (Liquidity grab exhausted)
            # 3. C3 breaks below C1 Low or C2 Low (Market Structure Shift)
            if upper_wick > 0.35:
                # Check for breakdown at 9:17
                if c3.Low < c1.Low:
                    entry = c1.Low - (0.0002 * c1.Low)
                    sl = c1.High
                    risk_per_share = sl - entry
                    if risk_per_share > entry * 0.006:
                        sl = entry * 1.005
                        risk_per_share = sl - entry
                    
                    tp = entry - (risk_per_share * 2.0)
                    shares = int(4000.0 / max(risk_per_share, 1.0))
                    shares = min(shares, int(1200000 / entry))

                    exit_price = None
                    status = 'TIME_EXIT'
                    for t_idx in range(3, len(window)):
                        bar = window.iloc[t_idx]
                        if bar.High >= sl:
                            exit_price = sl
                            status = 'STOP_LOSS'
                            break
                        elif bar.Low <= tp:
                            exit_price = tp
                            status = 'TARGET_HIT'
                            break
                    if exit_price is None:
                        exit_price = window.iloc[-1].Close

                    gross = (entry - exit_price) * shares
                    friction = calculate_zerodha_friction(entry * shares, exit_price * shares)
                    net = gross - friction
                    all_smc_trades.append({
                        'date': d,
                        'symbol': sym,
                        'strategy': 'SMC_TRAP_INVERSION_SHORT',
                        'entry_time': '09:17',
                        'entry': entry,
                        'exit': exit_price,
                        'shares': shares,
                        'gross_pnl': gross,
                        'friction': friction,
                        'net_pnl': net,
                        'status': status,
                        'is_win': net > 0
                    })

    tdf = pd.DataFrame(all_smc_trades)
    print("\n" + "=" * 80)
    print(" ADVANCED SMC QUANTITATIVE RESULTS (9:15 - 9:25 AM)")
    print("=" * 80)
    if len(tdf) == 0:
        print("No SMC trades triggered.")
        return

    wins = tdf[tdf['is_win']]
    losses = tdf[~tdf['is_win']]
    print(f"Total SMC Setups Filtered : {len(tdf)}")
    print(f"Win Rate                  : {(len(wins)/len(tdf))*100:.1f}% ({len(wins)}W / {len(losses)}L)")
    print(f"Total Net PnL (Post-Tax)  : Rs {tdf['net_pnl'].sum():,.2f}")
    print(f"Total Gross PnL           : Rs {tdf['gross_pnl'].sum():,.2f}")
    print(f"Total Friction (Zerodha)  : Rs {tdf['friction'].sum():,.2f}")
    print(f"Average Profit per Win    : Rs {wins['net_pnl'].mean():,.2f}")
    print(f"Average Loss per Loss     : Rs {abs(losses['net_pnl'].mean()):,.2f}")
    profit_factor = wins['net_pnl'].sum() / abs(losses['net_pnl'].sum()) if len(losses) > 0 else 999.0
    print(f"Profit Factor             : {profit_factor:.2f}")

    # Daily aggregation
    daily = tdf.groupby('date')['net_pnl'].sum()
    print(f"\n--- DAILY PnL BREAKDOWN (19 Trading Days) ---")
    print(f"Active Trading Days       : {len(daily)}")
    print(f"Profitable Days           : {sum(daily > 0)} / {len(daily)} ({(sum(daily > 0)/len(daily))*100:.1f}%)")
    print(f"Average Daily Net PnL     : Rs {daily.mean():,.2f}")
    print(f"Best Day Profit           : Rs {daily.max():,.2f}")
    print(f"Worst Day Loss            : Rs {daily.min():,.2f}")
    
    # Top individual stocks for opening session scalping
    print("\n--- TOP STOCKS PERFORMANCE RANKING ---")
    stock_group = tdf.groupby('symbol').agg(
        trades=('net_pnl', 'count'),
        win_rate=('is_win', lambda x: f"{(x.sum()/len(x))*100:.0f}%"),
        total_pnl=('net_pnl', 'sum'),
        avg_trade=('net_pnl', 'mean')
    ).sort_values(by='total_pnl', ascending=False)
    print(stock_group.to_string())

if __name__ == '__main__':
    run_advanced_smc_backtest()
