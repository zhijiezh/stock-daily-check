from utils import calculate_moving_average, calculate_rsi

# Constants to be tuned
SHORT_WINDOW = 5
LONG_WINDOW = 60
RSI_BUY_SIGNAL = 45
RSI_SELL_SIGNAL = 70
RSI_WINDOW = 60

def get_market_exit_signal(index_data, long_term_ma):
    index_data['Long_Term_MA'] = index_data['Close'].rolling(window=long_term_ma).mean()
    if index_data['Close'].iloc[-1] < index_data['Long_Term_MA'].iloc[-1]:
        return "Exit Market"
    return "Stay"
def check_buy_signal(stock_data, short_window, long_window, rsi_buy_signal, rsi_window):
    stock_data['Short_MA'] = calculate_moving_average(stock_data, short_window)
    stock_data['Long_MA'] = calculate_moving_average(stock_data, long_window)
    stock_data['RSI'] = calculate_rsi(stock_data, rsi_window)
    stock_data['Volume_MA'] = stock_data['Volume'].rolling(window=short_window).mean()

    # Check the latest data point for buy signal
    buy_signal = (stock_data['Short_MA'].iloc[-1] < stock_data['Long_MA'].iloc[-1]) and \
                 (stock_data['RSI'].iloc[-1] < rsi_buy_signal) and \
                 (stock_data['Volume'].iloc[-1] > stock_data['Volume_MA'].iloc[-1])
    return buy_signal, stock_data

def check_sell_signal(stock_data, short_window, long_window, rsi_sell_signal, rsi_window):
    stock_data['Short_MA'] = calculate_moving_average(stock_data, short_window)
    stock_data['Long_MA'] = calculate_moving_average(stock_data, long_window)
    stock_data['RSI'] = calculate_rsi(stock_data, rsi_window)
    stock_data['Volume_MA'] = stock_data['Volume'].rolling(window=short_window).mean()

    # Check the latest data point for sell signal
    sell_signal = (stock_data['Short_MA'].iloc[-1] > stock_data['Long_MA'].iloc[-1]) and \
                  (stock_data['RSI'].iloc[-1] > rsi_sell_signal) and \
                  (stock_data['Volume'].iloc[-1] > stock_data['Volume_MA'].iloc[-1])
    return sell_signal, stock_data

def decide_trade(stock_data, short_window, long_window, rsi_buy_signal, rsi_sell_signal, rsi_window):
    print("short_window: ", short_window)
    print("long_window: ", long_window)
    print("rsi_buy_signal: ", rsi_buy_signal)
    print("rsi_sell_signal: ", rsi_sell_signal)
    print("rsi_window: ", rsi_window)
    stock_data['Short_MA'] = calculate_moving_average(stock_data, short_window)
    stock_data['Long_MA'] = calculate_moving_average(stock_data, long_window)
    stock_data['RSI'] = calculate_rsi(stock_data, rsi_window)
    stock_data['Volume_MA'] = stock_data['Volume_Series'].rolling(window=short_window).mean()

    buy_signals = ((stock_data['Short_MA'] < stock_data['Long_MA']) & (stock_data['RSI'] < rsi_buy_signal)) & (stock_data['Volume_Series'] > stock_data['Volume_MA'])
    sell_signals = ((stock_data['Short_MA'] > stock_data['Long_MA']) & (stock_data['RSI'] > rsi_sell_signal)) & (stock_data['Volume_Series'] > stock_data['Volume_MA'])
    
    return buy_signals, sell_signals