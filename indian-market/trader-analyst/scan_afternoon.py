import yfinance as yf

tickers = [
    'ICICIBANK.NS', 'BSE.NS', 'DLF.NS', 'KALYANKJIL.NS', 
    'SBIN.NS', 'HDFCBANK.NS', 'TATASTEEL.NS', 'RELIANCE.NS', 'RVNL.NS', 'DELHIVERY.NS'
]

print(f"{'Ticker':<14} {'CMP':<8} {'VWAP':<8} {'Day %':<8} {'5m Vol':<8} {'Status'}")
print("-" * 65)

for t in tickers:
    try:
        d = yf.Ticker(t).history(period='1d', interval='5m')
        if not d.empty:
            c = float(d['Close'].iloc[-1])
            o = float(d['Open'].iloc[0])
            h = float(d['High'].max())
            l = float(d['Low'].min())
            pct = ((c - o) / o) * 100
            vwap = float((d['Close'] * d['Volume']).sum() / d['Volume'].sum())
            v_last = int(d['Volume'].iloc[-1])
            
            if c >= h * 0.995:
                status = "BREAKOUT (AT HIGH)"
            elif c > vwap:
                status = "ABOVE VWAP (BULL)"
            else:
                status = "BELOW VWAP (WEAK)"
                
            print(f"{t:<14} {c:<8.2f} {vwap:<8.2f} {pct:<+8.2f} {v_last:<8} {status}")
    except Exception as e:
        print(f"Error {t}: {e}")
