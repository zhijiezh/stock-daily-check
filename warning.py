from datetime import datetime, timedelta
import yfinance as yf

def rule_price_increase(stock_data, ticker):
    """Rule 2: 25-50% increase in 1 to 3 weeks."""
    period_returns = stock_data['Close'][ticker].pct_change(periods=5).iloc[-1]  # 1-week return
    return 0.25 <= period_returns <= 0.50

def rule_largest_gain(stock_data, ticker):
    """Rule 3: Largest single-day gain since rise began."""
    daily_gains = stock_data['Close'][ticker].pct_change()
    max_gain = daily_gains.max()
    recent_gain = daily_gains.iloc[-1]
    return recent_gain == max_gain

def rule_accelerating_growth(stock_data, ticker):
    """Rule 6: 6-10 days of accelerating growth, with only about 2 days of decline."""
    recent_data = stock_data['Close'][ticker].iloc[-10:]
    up_days = recent_data.pct_change() > 0
    return up_days.sum() >= 8

def rule_falling_below_ma(stock_data, ticker):
    """Rule 10: Falling below 50-day MA on largest volume."""
    ma50 = stock_data['Close'][ticker].rolling(window=50).mean().iloc[-1]
    max_volume = stock_data['Volume'][ticker].max()
    recent_volume = stock_data['Volume'][ticker].iloc[-1]
    current_price = stock_data['Close'][ticker].iloc[-1]
    return current_price < ma50 and recent_volume == max_volume

def stock_warning_system(tickers, date, rules):
    warnings = {}
    end_date = datetime.strptime(date, '%Y-%m-%d') + timedelta(days=1)  # To include the end date in the fetch
    start_date = end_date - timedelta(days=365)
    for ticker in tickers:
        data = yf.download(ticker, start=start_date, end=date)
        for rule in rules:
            if rule(data, ticker):
                warnings.setdefault(ticker, []).append(rule.__name__)
    return warnings

if __name__ == '__main__':
    # Define your rules
    warning_rules = [rule_price_increase, rule_largest_gain, rule_accelerating_growth, rule_falling_below_ma]  # Add other rule functions here

    # List of tickers and a specific date
    tickers = ['AAPL', 'MSFT', 'SAVE']
    # tickers = nasdaq_tickers
    date = '2025-01-03'  # Replace with your date

    # Get warnings 
    warnings = stock_warning_system(tickers, date, warning_rules)
    print("Warnings:", warnings)