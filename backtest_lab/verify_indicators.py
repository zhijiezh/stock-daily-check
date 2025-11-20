
import sys
import os
import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(''), '..')))

from core.indicators import TechnicalIndicators
from core.data_provider import get_stock_data

# 1. Get Data
ticker = "TQQQ"
print(f"Fetching data for {ticker}...")
# Get last 2 years to check recent signals
df = get_stock_data(ticker, start_date="2023-01-01")

# 2. Calculate Indicators
print("Calculating indicators...")
df = TechnicalIndicators.add_ladder_indicator(df)
df = TechnicalIndicators.add_bottom_fishing_indicator(df)

# 3. Plotting
print("Plotting...")

# Create figure
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 12), sharex=True, height_ratios=[3, 1])

# Plot 1: Price + Ladder
ax1.plot(df.index, df['Close'], label='Close', color='black', alpha=0.6, linewidth=1)

# Blue Ladder (A/B)
ax1.plot(df.index, df['ladder_blue_top'], label='Blue Top (EMA26 H)', color='blue', linestyle='--', linewidth=1)
ax1.plot(df.index, df['ladder_blue_bottom'], label='Blue Bottom (EMA26 L)', color='blue', linestyle='--', linewidth=1)
ax1.fill_between(df.index, df['ladder_blue_top'], df['ladder_blue_bottom'], color='blue', alpha=0.1)

# Yellow Ladder (A1/B1)
ax1.plot(df.index, df['ladder_yellow_top'], label='Yellow Top (EMA89 H)', color='orange', linestyle=':', linewidth=1)
ax1.plot(df.index, df['ladder_yellow_bottom'], label='Yellow Bottom (EMA89 L)', color='orange', linestyle=':', linewidth=1)
ax1.fill_between(df.index, df['ladder_yellow_top'], df['ladder_yellow_bottom'], color='orange', alpha=0.1)

# Plot Bottom Fishing Signals
# Find where signal == 1
signals = df[df['bottom_fishing_signal'] == 1]
if not signals.empty:
    print(f"Found {len(signals)} '抄底' signals:")
    print(signals.index)
    # Plot markers
    ax1.scatter(signals.index, signals['Low'] * 0.95, marker='^', color='red', s=100, label='Buy Signal (DXDX)', zorder=5)
    for idx, row in signals.iterrows():
        ax1.text(idx, row['Low'] * 0.94, '抄底', color='red', fontsize=12, ha='center')
else:
    print("No '抄底' signals found in this period.")

ax1.set_title(f'{ticker} Price with Ladder & Bottom Fishing Indicators')
ax1.legend()
ax1.grid(True)

# Plot 2: MACD (Underlying logic for Bottom Fishing)
ax2.plot(df.index, df['DIF'], label='DIF', color='black')
ax2.plot(df.index, df['DEA'], label='DEA', color='orange')
ax2.bar(df.index, df['MACD'], label='MACD Bar', color='gray', alpha=0.5)
ax2.set_title('MACD (Underlying)')
ax2.legend()
ax2.grid(True)

plt.tight_layout()
output_path = "indicator_check.png"
plt.savefig(output_path)
print(f"Chart saved to {output_path}")

