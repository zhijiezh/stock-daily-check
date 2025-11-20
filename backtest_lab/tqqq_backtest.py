import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import sys
import os
import math

# Add project root to path to import core modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.data_provider import get_stock_data

class TQQQStrategy:
    def __init__(self, 
                 initial_cash=100000, 
                 base_invest_ratio=0.01, # Invest 1% of peak cash per period
                 profit_target_multiple=3.0, 
                 rebalance_threshold=0.60, 
                 rebalance_target=0.40):
        
        self.cash = initial_cash
        self.initial_cash = initial_cash
        self.peak_cash = initial_cash
        self.shares = 0
        self.portfolio_value = initial_cash
        self.equity_curve = []
        self.history = []
        
        # Strategy Parameters
        self.base_invest_ratio = base_invest_ratio
        self.profit_target_multiple = profit_target_multiple
        self.rebalance_threshold = rebalance_threshold
        self.rebalance_target = rebalance_target
        
        # Holdings tracking: List of {'price': float, 'shares': float, 'tp_price': float}
        self.lots = []
        
        # Stats
        self.max_equity = initial_cash
        self.current_drawdown = 0.0

    def calculate_drawdown_multiplier(self, drawdown_pct):
        # "随回撤提升的倍率"
        # Rule: 1 + (Drawdown_PCT * 2)
        # Example: 
        # 0% DD -> 1.0x
        # 20% DD -> 1.4x
        # 50% DD -> 2.0x
        # This is a conservative interpretation. Aggressive could be exponential.
        return 1 + (drawdown_pct * 2)

    def run(self, price_data: pd.DataFrame, invest_period_days=20):
        """
        Run the simulation.
        price_data: DataFrame with 'Close' and 'High' columns (daily).
        invest_period_days: How often to invest (e.g. 20 days ~ monthly).
        """
        print(f"Starting simulation on {len(price_data)} trading days...")
        
        days_counter = 0
        
        for date, row in price_data.iterrows():
            price = row['Close']
            # High is safer for TP, but data might have splits/issues. 
            # Using Close for TP is safer for backtest to avoid "ghost" spikes.
            # But strategy says "挂出的卖单", implying limit orders. Limit orders get filled at High.
            # Let's use High for checking TP hit, but execute at TP Price.
            high = row['High'] 
            
            # 1. Update Portfolio Value (Mark to Market)
            stock_value = self.shares * price
            self.portfolio_value = self.cash + stock_value
            
            # Update Peak Stats & Drawdown
            if self.cash > self.peak_cash:
                self.peak_cash = self.cash
            
            is_new_high = False
            if self.portfolio_value > self.max_equity:
                self.max_equity = self.portfolio_value
                self.current_drawdown = 0.0
                is_new_high = True
            else:
                if self.max_equity > 0:
                    self.current_drawdown = (self.max_equity - self.portfolio_value) / self.max_equity
                else:
                    self.current_drawdown = 0.0

            # 2. Check Take Profit (TP) for individual lots
            remaining_lots = []
            for lot in self.lots:
                # If High price crossed our TP target
                if high >= lot['tp_price']:
                    # Sell this lot
                    # Logic: We sell at TP price (Limit Order filled)
                    sell_price = lot['tp_price']
                    proceeds = lot['shares'] * sell_price
                    
                    self.cash += proceeds
                    self.shares -= lot['shares']
                    
                    # Log trade
                    self.history.append({
                        'date': date,
                        'action': 'SELL_TP',
                        'price': sell_price,
                        'shares': lot['shares'],
                        'value': proceeds,
                        'reason': f"Hit TP (Entry: {lot['price']:.2f})"
                    })
                else:
                    remaining_lots.append(lot)
            self.lots = remaining_lots
            
            # Recalculate stock value after TP sales
            stock_value = self.shares * price
            self.portfolio_value = self.cash + stock_value

            # 3. Regular Investment (Buy) - "每个周期...买入"
            days_counter += 1
            if days_counter >= invest_period_days:
                days_counter = 0
                
                # Calculate Buy Amount
                # "最大持有过的现金数 × 系数 × 随回撤提升的倍率"
                dd_mult = self.calculate_drawdown_multiplier(self.current_drawdown)
                buy_amount = self.peak_cash * self.base_invest_ratio * dd_mult
                
                # Check if we have enough cash
                if self.cash >= buy_amount:
                    shares_to_buy = buy_amount / price
                    self.cash -= buy_amount
                    self.shares += shares_to_buy
                    
                    self.lots.append({
                        'price': price,
                        'shares': shares_to_buy,
                        'tp_price': price * self.profit_target_multiple
                    })
                    
                    self.history.append({
                        'date': date,
                        'action': 'BUY_DCA',
                        'price': price,
                        'shares': shares_to_buy,
                        'value': buy_amount,
                        'reason': f"Periodic (DD:{self.current_drawdown:.1%}, M:{dd_mult:.1f})"
                    })
            
            # 4. Rebalancing Logic (Sell on Highs)
            # "如果达到新高，且仓位高于60%，则提前清理挂出的卖单，减仓至40%"
            current_allocation = stock_value / self.portfolio_value if self.portfolio_value > 0 else 0
            
            if is_new_high and current_allocation > self.rebalance_threshold:
                target_equity = self.portfolio_value * self.rebalance_target
                target_stock_val = target_equity
                
                # Amount to sell to reach 40% allocation
                sell_amount = stock_value - target_stock_val
                
                if sell_amount > 0:
                    shares_to_sell = sell_amount / price
                    
                    self.cash += sell_amount
                    self.shares -= shares_to_sell
                    
                    # FIFO Removal from lots
                    # We just remove shares from the front of the list (oldest lots)
                    shares_removed = 0
                    new_lots = []
                    for lot in self.lots:
                        if shares_removed >= shares_to_sell:
                            new_lots.append(lot)
                            continue
                            
                        shares_in_lot = lot['shares']
                        needed = shares_to_sell - shares_removed
                        
                        if shares_in_lot > needed:
                            # Partial reduce
                            lot['shares'] -= needed
                            shares_removed += needed
                            new_lots.append(lot)
                        else:
                            # Full consume
                            shares_removed += shares_in_lot
                            # Lot dropped
                    
                    self.lots = new_lots
                    
                    self.history.append({
                        'date': date,
                        'action': 'SELL_REBAL',
                        'price': price,
                        'shares': shares_to_sell,
                        'value': sell_amount,
                        'reason': f"ATH Rebalance (Alloc: {current_allocation:.1%})"
                    })

            # Record daily stats
            self.equity_curve.append({
                'Date': date,
                'Equity': self.portfolio_value,
                'Cash': self.cash,
                'StockValue': stock_value,
                'Drawdown': self.current_drawdown,
                'Allocation': current_allocation,
                'Price': price
            })

        return pd.DataFrame(self.equity_curve).set_index('Date')

if __name__ == "__main__":
    # --- CONFIGURATION ---
    TICKER = "TQQQ"
    START_DATE = "2011-01-01" # TQQQ inception was 2010-02
    INITIAL_CASH = 100_000
    INVEST_RATIO = 0.01 # 1% of peak cash
    INVEST_PERIOD = 20  # ~1 month
    
    print(f"Fetching data for {TICKER}...")
    df = get_stock_data(TICKER, start_date=START_DATE)
    
    if df.empty:
        print("No data fetched. Check your internet connection or ticker symbol.")
        sys.exit(1)
        
    strategy = TQQQStrategy(
        initial_cash=INITIAL_CASH,
        base_invest_ratio=INVEST_RATIO,
        rebalance_threshold=0.60,
        rebalance_target=0.40
    )
    
    results = strategy.run(df, invest_period_days=INVEST_PERIOD)
    
    # --- METRICS ---
    final_equity = results['Equity'].iloc[-1]
    total_return = (final_equity - INITIAL_CASH) / INITIAL_CASH
    cagr = (final_equity / INITIAL_CASH) ** (365 / (results.index[-1] - results.index[0]).days) - 1
    max_dd = results['Drawdown'].max()
    
    print("\n" + "=" * 50)
    print(f"  STRATEGY RESULTS: {TICKER}")
    print("=" * 50)
    print(f"Period:       {results.index[0].date()} -> {results.index[-1].date()}")
    print(f"Initial Cash: ${INITIAL_CASH:,.2f}")
    print(f"Final Equity: ${final_equity:,.2f}")
    print(f"Total Return: {total_return * 100:,.2f}%")
    print(f"CAGR:         {cagr * 100:.2f}%")
    print(f"Max Drawdown: {max_dd * 100:.2f}%")
    print("-" * 50)
    
    # --- PLOTTING ---
    # Use a nice style
    plt.style.use('ggplot')
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 12), sharex=True)
    
    # 1. Equity Curve (Log Scale)
    ax1.plot(results.index, results['Equity'], label='Portfolio Value', color='blue', linewidth=1.5)
    ax1.set_yscale('log')
    ax1.set_title(f'{TICKER} Strategy Equity (Log Scale)')
    ax1.set_ylabel('Value ($)')
    ax1.legend(loc='upper left')
    ax1.grid(True, which="both", ls="-", alpha=0.2)
    
    # 2. Drawdown
    ax2.fill_between(results.index, -results['Drawdown'], 0, color='red', alpha=0.3)
    ax2.plot(results.index, -results['Drawdown'], color='red', linewidth=1)
    ax2.set_title('Strategy Drawdown')
    ax2.set_ylabel('Drawdown %')
    ax2.set_ylim(bottom=-1.0, top=0.05) # Fix y-axis for clearer view
    
    # 3. Cash vs Stock Allocation
    ax3.stackplot(results.index, results['Cash'], results['StockValue'], labels=['Cash', 'Stock'], alpha=0.6, colors=['green', 'orange'])
    ax3.set_title('Asset Allocation')
    ax3.set_ylabel('Value ($)')
    ax3.legend(loc='upper left')
    
    plt.tight_layout()
    output_file = 'backtest_results.png'
    plt.savefig(output_file)
    print(f"\nPlot saved to: {os.path.abspath(output_file)}")
    print("You can open this image to view the performance.")

