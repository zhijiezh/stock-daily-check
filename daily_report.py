# import
import pandas as pd
from datetime import datetime, timedelta

from utils import recommended_pe_ratio
from warning import rule_price_increase, rule_largest_gain, rule_accelerating_growth, rule_falling_below_ma, stock_warning_system
from earning import upcoming_earnings
import trade_decision as td
import yfinance as yf

def get_stock_info_on_date(tickers, short_window, long_window, rsi_buy_signal, rsi_sell_signal, rsi_window, date=datetime.today().strftime("%Y-%m-%d"), history_days=600, long_term_ma=200):
    print("Today is " + date)
    end_date = datetime.strptime(date, '%Y-%m-%d') + timedelta(days=1)  # To include the end date in the fetch
    start_date = end_date - timedelta(days=history_days)

    # market_index = yf.Ticker("^GSPC")  # S&P 500 Index
    # market_data = market_index.history(start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'))
    # market_signal = get_market_exit_signal(market_data, long_term_ma)
    # print(market_signal)

    data = {'Company Code': [], 'Date': [], 'Daily Price': [], 'Recommendation': [],'60 DAY RSI':[], 'P/E Ratio': [], 'Recommended PE':[], 'Category': [],'Dividend Yield': [], 'Market Cap': [], 'Earnings Growth': [], 'One Year Target': [], 'Analyst Buy': [], 'Analyst Hold': [], 'Analyst Sell': []}
    
    for ticker in tickers:
        stock = yf.Ticker(ticker)
        hist_data = stock.history(start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'))
        if hist_data.empty:
            continue  # Skip if no data for the given date range
        
        last_date = hist_data.index[-1].strftime('%Y-%m-%d')  # Last date in the historical data
        daily_price = hist_data['Close'].iloc[-1]  # Last close price
        # Apply buy/sell signal functions (as previously defined)
        risk_buy_signal, buy_data = td.check_buy_signal(hist_data, short_window=short_window, long_window=long_window, rsi_buy_signal=rsi_buy_signal, rsi_window=rsi_window)
        buy_signal, _ = td.check_buy_signal(hist_data, short_window=short_window, long_window=long_window, rsi_buy_signal=rsi_buy_signal, rsi_window=rsi_window)
        sell_signal, _ = td.check_sell_signal(hist_data, short_window=short_window, long_window=long_window, rsi_sell_signal=rsi_sell_signal, rsi_window=rsi_window)
        recommendation = 'BUY' if buy_signal else 'SELL' if sell_signal else 'RISK BUY' if risk_buy_signal else None

        if recommendation:
            pe_ratio = stock.info.get('trailingPE', 'N/A')
            category = stock.info.get('sector', 'N/A')
            dividend_yield = stock.info.get('dividendYield', 'N/A') * 100 if stock.info.get('dividendYield') is not None else 'N/A'
            market_cap = stock.info.get('marketCap', 'N/A')
            earnings_growth = stock.info.get('earningsGrowth', 'N/A')
            one_year_target = stock.info.get('targetMeanPrice')
            analyst_buy_ratings = stock.info.get('buyRatingCount')
            analyst_hold_ratings = stock.info.get('holdRatingCount')
            analyst_sell_ratings = stock.info.get('sellRatingCount')
            data['Company Code'].append(ticker)
            data['Recommendation'].append(recommendation)
            data['60 DAY RSI'].append(buy_data['RSI'].iloc[-1])
            data['P/E Ratio'].append(pe_ratio)
            data['Category'].append(category)
            data['Dividend Yield'].append(dividend_yield)
            data['Market Cap'].append(market_cap)
            data['Earnings Growth'].append(earnings_growth)
            data['Recommended PE'].append(recommended_pe_ratio(category))
            data['One Year Target'].append(one_year_target)
            data['Analyst Buy'].append(analyst_buy_ratings)
            data['Analyst Hold'].append(analyst_hold_ratings)
            data['Analyst Sell'].append(analyst_sell_ratings)
            data['Date'].append(last_date)
            data['Daily Price'].append(daily_price)

    return pd.DataFrame(data)

def every_day_printer(tickers, date=datetime.today().strftime("%Y-%m-%d")):
    # Build up the report as a list of strings
    report_lines = []
    
    report_lines.append(f"Analysis Date: {date}\n")
    report_lines.append("Tickers:\n")
    report_lines.append(f"{tickers}\n\n")

    # Get stock table (assumes get_stock_info_on_date returns a DataFrame)
    stock_table = get_stock_info_on_date(
        tickers,
        date=date,
        short_window=td.SHORT_WINDOW,
        long_window=td.LONG_WINDOW,
        rsi_buy_signal=td.RSI_BUY_SIGNAL,
        rsi_sell_signal=td.RSI_SELL_SIGNAL,
        rsi_window=td.RSI_WINDOW
    )
    report_lines.append("Stock Table:\n")
    report_lines.append(stock_table.to_string() + "\n\n")

    # Optionally set pandas display options
    pd.set_option('display.max_rows', None)
    # Instead of displaying, we include the string output in the report
    # (If display() is needed for interactive work, you can call it separately.)

    # Process warning rules
    warning_rules = [rule_price_increase, rule_largest_gain, rule_accelerating_growth, rule_falling_below_ma]
    warnings = stock_warning_system(tickers, date, warning_rules)
    report_lines.append("Warnings:\n")
    report_lines.append(f"{warnings}\n\n")

    # Append stocks with upcoming earnings
    report_lines.append("Stocks with Upcoming Earnings:\n")
    stocks_with_upcoming_earnings = upcoming_earnings(tickers, date)
    for ticker, earnings_date in stocks_with_upcoming_earnings:
        report_lines.append(f"{ticker}: Earnings on {earnings_date}\n")
    
    report_lines.append("\n***************************************************************************************************\n\n")

    # Join the lines into a single string and return it
    return "".join(report_lines)

def append_to_report_file(content, filename = "stock_analysis_results.txt" ):
    with open(filename, 'a') as file:
        file.write(content)