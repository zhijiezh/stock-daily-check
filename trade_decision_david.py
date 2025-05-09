import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Constants
SHORT_WINDOW = 30
LONG_WINDOW = 60
RSI_BUY_SIGNAL = 40
RSI_SELL_SIGNAL = 50
RSI_WINDOW = 30

# 1. DEMA Calculation
def calculate_dema_David(series: pd.Series, window: int) -> pd.Series:
    ema = series.ewm(span=window, adjust=False).mean()
    ema_of_ema = ema.ewm(span=window, adjust=False).mean()
    return 2 * ema - ema_of_ema

# 2. RSI Calculation
def calculate_rsi_David(prices: pd.Series, window: int) -> pd.Series:
    """
    Wilder’s RSI:
    1. 计算价格差 delta
    2. 分别用 EMA(alpha=1/window) 对 gain 和 loss 做平滑
    3. 计算 RS = EMA_gain / EMA_loss
    4. RSI = 100 – 100 / (1 + RS)
    """
    delta = prices.diff()

    # 分离涨跌
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    # Wilder 的 EMA 平滑：alpha = 1/window
    ema_gain = gain.ewm(alpha=1/window, adjust=False, min_periods=window).mean()
    ema_loss = loss.ewm(alpha=1/window, adjust=False, min_periods=window).mean()

    rs = ema_gain / ema_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# 3. Signal Generation
def decide_trade_David(stock_data: pd.DataFrame,
                       short_window: int, long_window: int,
                       rsi_buy: float, rsi_sell: float,
                       rsi_window: int):
    df = stock_data.copy()
    
    # 1. 指标计算
    df['DEMA_Short'] = calculate_dema_David(df['Close'], short_window)
    df['DEMA_Long']  = calculate_dema_David(df['Close'], long_window)
    df['RSI']      = calculate_rsi_David(df['Close'], rsi_window)
    df['RSI_prev'] = df['RSI'].shift(1)
    
    # 2. 提取为 numpy 数组，避免索引对齐问题
    close_arr    = df['Close'].to_numpy().ravel()
    dema_arr     = df['DEMA_Short'].to_numpy().ravel()
    rsi_arr      = df['RSI'].to_numpy().ravel()
    rsi_prev_arr = df['RSI_prev'].to_numpy().ravel()
    # print(close_arr.dtypes)
    # print(dema_arr.dtypes)
    # print(rsi_arr.dtypes)
    # print(rsi_prev_arr.dtypes)
    
    # 3. 构造布尔数组
    buy_arr = ((rsi_prev_arr < rsi_buy) & (rsi_arr >= rsi_buy) & (close_arr > dema_arr))
    sell_arr = ((rsi_prev_arr > rsi_sell) & (rsi_arr <= rsi_sell) & (close_arr < dema_arr))
    
    # 4. 稳健信号
    robust_buy_arr  = buy_arr  & (df['DEMA_Short'].to_numpy() > df['DEMA_Long'].to_numpy())
    robust_sell_arr = sell_arr & (df['DEMA_Short'].to_numpy() < df['DEMA_Long'].to_numpy())
    
    # 5. 转回 pd.Series，保持与 df 相同的索引
    buy_signal   = pd.Series(buy_arr,   index=df.index)
    sell_signal  = pd.Series(sell_arr,  index=df.index)
    robust_buy   = pd.Series(robust_buy_arr,  index=df.index)
    robust_sell  = pd.Series(robust_sell_arr, index=df.index)
    
    return buy_signal, sell_signal, robust_buy, robust_sell, df







