import sys
import os
import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf
import numpy as np

# Add project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.indicators import TechnicalIndicators

def get_4h_data_custom(ticker, start_date, end_date):
    """
    Fetch hourly data and resample to 4H.
    Since yfinance '1h' only allows last 730 days, 2024 Mar-May is within range (as of late 2025).
    Note: User is in late 2025. March 2024 is ~1.5 years ago. It IS within 730 days.
    """
    print(f"Fetching 1h data for {ticker} ({start_date} to {end_date})...")
    df = yf.download(ticker, start=start_date, end=end_date, interval="1h", progress=False)
    
    if df.empty:
        print("No data found.")
        return df
        
    # Flatten columns
    if isinstance(df.columns, pd.MultiIndex):
        try:
            df.columns = df.columns.droplevel(1)
        except:
            pass
            
    logic = {
        'Open': 'first',
        'High': 'max',
        'Low': 'min',
        'Close': 'last',
        'Volume': 'sum'
    }
    
    df_4h = df.resample('4h').agg(logic).dropna()
    return df_4h

def run_complex_strategy(df):
    """
    Complex Logic:
    1. Wait for '抄底' (DXDX) signal.
    2. Once '抄底' appears, enter 'MONITORING' mode.
    3. Buy when Price > Yellow Ladder Top (A1).
    4. Sell when Price < Blue Ladder Bottom (B).
    """
    # Calculate Indicators
    df = TechnicalIndicators.add_ladder_indicator(df, n1=26, n2=89)
    df = TechnicalIndicators.add_bottom_fishing_indicator(df)
    
    cash = 100000
    shares = 0
    trades = []
    equity = []
    
    # States: 'NEUTRAL', 'BOTTOM_SEEN', 'INVESTED'
    state = 'NEUTRAL'
    bottom_seen_price = 0
    
    # We might want to expire the 'BOTTOM_SEEN' signal if price makes a new low?
    # Or just keep it valid until we buy.
    # Let's say valid until a Buy happens or price drops significantly below the bottom signal low (Stop Loss logic on signal).
    # For now, keep simple: Valid until Buy.
    
    for date, row in df.iterrows():
        price = row['Close']
        
        # Check Indicators
        is_bottom = row['bottom_fishing_signal'] == 1
        above_yellow = price > row['ladder_yellow_top']
        below_blue = price < row['ladder_blue_bottom']
        
        if state == 'NEUTRAL':
            if is_bottom:
                state = 'BOTTOM_SEEN'
                bottom_seen_price = price
                trades.append({'date': date, 'action': 'SIGNAL', 'price': price, 'type': 'Bottom Found'})
        
        elif state == 'BOTTOM_SEEN':
            # We have seen a bottom, waiting for Yellow Breakout
            
            # If another bottom signal comes, update reference? (Optional)
            if is_bottom:
                 trades.append({'date': date, 'action': 'SIGNAL', 'price': price, 'type': 'Bottom Again'})
            
            if above_yellow:
                # BUY!
                shares = cash / price
                cash = 0
                state = 'INVESTED'
                trades.append({'date': date, 'action': 'BUY', 'price': price, 'type': 'Yellow Breakout'})
        
        elif state == 'INVESTED':
            # Sell logic
            if below_blue:
                # SELL!
                cash = shares * price
                shares = 0
                state = 'NEUTRAL' # Reset to Neutral, need new Bottom signal to enter again? 
                # User query implies: "抄底...再有超过黄色梯子". 
                # Usually after selling, we might just trade the Ladder (Trend)?
                # Or strictly need a new Bottom signal?
                # Let's assume strict: Need new Bottom to restart the cycle. 
                # Or maybe just Neutral -> Yellow Breakout is enough in Bull market?
                # User said: "本来就是要先有抄底...再有超过黄色梯子". implied dependency.
                trades.append({'date': date, 'action': 'SELL', 'price': price, 'type': 'Blue Breakdown'})
                
        # Record Equity
        curr_val = cash + (shares * price)
        equity.append(curr_val)
        
    df['Equity'] = equity
    return df, trades

if __name__ == "__main__":
    TICKER = "TQQQ"
    # Focus on March - May 2024
    # Note: 2024 is last year.
    START = "2024-03-01"
    END = "2024-06-01"
    
    df_4h = get_4h_data_custom(TICKER, START, END)
    
    if df_4h.empty:
        sys.exit(1)
        
    print(f"Bars: {len(df_4h)}")
    
    df_res, trades = run_complex_strategy(df_4h)
    
    # Stats
    print("\nTrades Log:")
    for t in trades:
        print(f"{t['date']} | {t['action']:<6} @ ${t['price']:.2f} ({t['type']})")

    # Plot
    plt.figure(figsize=(14, 8))
    plt.plot(df_res.index, df_res['Close'], 'k', alpha=0.6, label='Price')
    
    # Plot Ladders
    plt.plot(df_res.index, df_res['ladder_blue_bottom'], 'b--', alpha=0.3, label='Blue Bottom')
    plt.plot(df_res.index, df_res['ladder_yellow_top'], 'orange', linestyle=':', alpha=0.8, linewidth=2, label='Yellow Top (Trigger)')
    
    # Plot Events
    for t in trades:
        if t['action'] == 'SIGNAL':
            plt.scatter(t['date'], t['price'], color='purple', marker='*', s=200, label='Bottom Signal' if 'Bottom Signal' not in plt.gca().get_legend_handles_labels()[1] else "")
            plt.text(t['date'], t['price']*0.98, '抄底', color='purple', fontsize=10)
        elif t['action'] == 'BUY':
            plt.scatter(t['date'], t['price'], color='g', marker='^', s=150, label='BUY')
        elif t['action'] == 'SELL':
            plt.scatter(t['date'], t['price'], color='r', marker='v', s=150, label='SELL')

    plt.title(f"{TICKER} Complex Strategy (Mar-May 2024)")
    plt.legend()
    plt.grid(True)
    plt.savefig("march_may_backtest.png")
    print("\nSaved to march_may_backtest.png")

