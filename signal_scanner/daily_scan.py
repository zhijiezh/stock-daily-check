import sys
import os
import json
import pandas as pd
import yfinance as yf
from datetime import datetime
import argparse

# Add project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.indicators import TechnicalIndicators

def load_config():
    try:
        with open('config/watchlist.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("Config file not found. Using default TQQQ.")
        return {"watchlist": ["TQQQ"], "settings": {}}

def get_data(ticker, period="1y", interval="1d"):
    try:
        df = yf.download(ticker, period=period, interval=interval, progress=False)
        if df.empty:
            return None
        
        # Clean MultiIndex
        if isinstance(df.columns, pd.MultiIndex):
            try:
                df.columns = df.columns.droplevel(1)
            except:
                pass
        return df
    except Exception as e:
        print(f"Error fetching {ticker}: {e}")
        return None

def scan_ticker(ticker, settings):
    # 1. Fetch Data
    # We need enough history for Ladder (89) and MACD
    df = get_data(ticker, period="2y", interval="1d")
    if df is None:
        return None

    # 2. Calculate Indicators
    df = TechnicalIndicators.add_ladder_indicator(df, n1=settings.get('ladder_n1', 26), n2=settings.get('ladder_n2', 89))
    # Use Strict Bottom Fishing
    df = TechnicalIndicators.add_bottom_fishing_indicator(df)

    # 3. Analyze Latest Candle
    last_row = df.iloc[-1]
    prev_row = df.iloc[-2]
    
    date_str = df.index[-1].strftime('%Y-%m-%d')
    
    price = last_row['Close']
    
    # Signals
    signals = []
    
    # -- Bottom Fishing --
    if last_row['bottom_fishing_signal'] == 1:
        signals.append("🚨 抄底信号 (Bottom Fishing) Triggered!")
    
    # -- Ladder Analysis --
    # Blue Ladder (Short Term)
    blue_top = last_row['ladder_blue_top']
    blue_bottom = last_row['ladder_blue_bottom']
    
    # Yellow Ladder (Long Term)
    yellow_top = last_row['ladder_yellow_top']
    yellow_bottom = last_row['ladder_yellow_bottom']
    
    # Breakout: Price crossed above Blue Top TODAY
    if prev_row['Close'] <= prev_row['ladder_blue_top'] and price > blue_top:
        signals.append("🚀 突破蓝梯子 (Blue Breakout)")
        
    # Breakdown: Price crossed below Blue Bottom TODAY
    if prev_row['Close'] >= prev_row['ladder_blue_bottom'] and price < blue_bottom:
        signals.append("🔻 跌破蓝梯子 (Blue Breakdown)")
        
    # Trend Status
    trend = "Neutral"
    if price > yellow_top:
        trend = "Bullish (Above Yellow)"
    elif price < yellow_bottom:
        trend = "Bearish (Below Yellow)"
        
    # Position inside Blue Ladder?
    in_blue_ladder = blue_bottom <= price <= blue_top
    
    return {
        "ticker": ticker,
        "date": date_str,
        "price": price,
        "change_pct": (price - prev_row['Close']) / prev_row['Close'] * 100,
        "trend": trend,
        "signals": signals,
        "ladder_status": "In Channel" if in_blue_ladder else ("Above" if price > blue_top else "Below")
    }

def main():
    config = load_config()
    watchlist = config.get('watchlist', [])
    settings = config.get('settings', {})
    
    print(f"🔍 Scanning {len(watchlist)} tickers for {datetime.now().strftime('%Y-%m-%d')}...")
    print("-" * 60)
    
    results = []
    for ticker in watchlist:
        print(f"Processing {ticker}...", end="\r")
        res = scan_ticker(ticker, settings)
        if res:
            results.append(res)
            
    print("\n" + "=" * 60)
    print(f"  DAILY SCAN REPORT")
    print("=" * 60)
    
    # 1. Priority: Signals
    has_signals = False
    for res in results:
        if res['signals']:
            has_signals = True
            print(f"\n🔥 {res['ticker']} (${res['price']:.2f}) {res['change_pct']:+.2f}%")
            for sig in res['signals']:
                print(f"   {sig}")
            print(f"   Trend: {res['trend']}")
            
    if not has_signals:
        print("\nNo Actionable Signals Today.")
        
    print("-" * 60)
    print("watchlist Status:")
    # Simple table
    print(f"{'Ticker':<8} {'Price':<10} {'Trend':<20} {'Ladder Pos':<15}")
    for res in results:
        print(f"{res['ticker']:<8} ${res['price']:<9.2f} {res['trend']:<20} {res['ladder_status']:<15}")
        
if __name__ == "__main__":
    main()

