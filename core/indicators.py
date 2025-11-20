import pandas as pd
import numpy as np
from scipy.signal import argrelextrema

def calculate_ema(series, span):
    return series.ewm(span=span, adjust=False).mean()

def bars_last(condition_series):
    res = np.full(len(condition_series), np.nan)
    last_idx = -1
    vals = condition_series.values
    for i in range(len(vals)):
        if vals[i]:
            last_idx = i
        if last_idx != -1:
            res[i] = i - last_idx
    return pd.Series(res, index=condition_series.index)

class TechnicalIndicators:
    
    @staticmethod
    def add_ladder_indicator(df: pd.DataFrame, n1=26, n2=89):
        df = df.copy()
        df['ladder_blue_top'] = calculate_ema(df['High'], n1) 
        df['ladder_blue_bottom'] = calculate_ema(df['Low'], n1) 
        df['ladder_yellow_top'] = calculate_ema(df['High'], n2) 
        df['ladder_yellow_bottom'] = calculate_ema(df['Low'], n2) 
        
        conditions = [
            (df['Close'] > df['ladder_blue_top']),
            (df['Close'] < df['ladder_blue_bottom'])
        ]
        choices = [1, -1]
        df['ladder_signal'] = np.select(conditions, choices, default=0)
        return df

    @staticmethod
    def add_bottom_fishing_indicator(df: pd.DataFrame):
        """Strict Implementation returning DataFrame"""
        return TechnicalIndicators._add_strict_bottom_fishing(df)

    @staticmethod
    def add_relaxed_bottom_signal(df: pd.DataFrame, lookback=30):
        df = df.copy()
        
        ema12 = df['Close'].ewm(span=12, adjust=False).mean()
        ema26 = df['Close'].ewm(span=26, adjust=False).mean()
        df['DIF'] = ema12 - ema26
        df['DEA'] = df['DIF'].ewm(span=9, adjust=False).mean()
        df['MACD'] = (df['DIF'] - df['DEA']) * 2
        
        signals = np.zeros(len(df))
        
        lows = df['Low'].values
        difs = df['DIF'].values
        macds = df['MACD'].values
        
        llv_price = df['Low'].rolling(window=lookback).min()
        llv_dif = df['DIF'].rolling(window=lookback).min()
        
        for i in range(lookback, len(df)):
            curr_low = lows[i]
            curr_dif = difs[i]
            
            # Using iloc for access inside loop is slow but safer if index is not int
            # Here we use array access (lows[i]) which is fine.
            # llv_price is a Series, so we need iloc or values
            
            lowest_p = llv_price.iloc[i]
            lowest_d = llv_dif.iloc[i]
            
            is_price_low = curr_low <= (lowest_p * 1.01)
            
            # Relaxed logic: Price is low, but DIF is NOT at its low
            # lowest_d is the min DIF in window.
            # If curr_dif > lowest_d * 0.95 (meaning it's higher/less negative)
            
            # Wait, if DIF is negative (-2), and curr is -1.5.
            # -1.5 > -2.0 is True.
            # But we want "Significant" divergence.
            
            is_divergence = is_price_low and (curr_dif > lowest_d + 0.05) # Add absolute buffer
            
            momentum_improving = macds[i] > macds[i-1]
            
            if is_divergence and momentum_improving and difs[i] < 0:
                signals[i] = 1
                
        df['bottom_fishing_signal'] = signals
        return df

    @staticmethod
    def _add_strict_bottom_fishing(df: pd.DataFrame):
        df = df.copy()
        ema12 = df['Close'].ewm(span=12, adjust=False).mean()
        ema26 = df['Close'].ewm(span=26, adjust=False).mean()
        df['DIF'] = ema12 - ema26
        df['DEA'] = df['DIF'].ewm(span=9, adjust=False).mean()
        df['MACD'] = (df['DIF'] - df['DEA']) * 2
        
        d = df['DIF'].values
        m = df['MACD'].values
        close = df['Close'].values
        
        ref_m = np.roll(m, 1); ref_m[0] = 0 
        cond_turn_green = (ref_m >= 0) & (m < 0)
        cond_turn_red = (ref_m <= 0) & (m > 0)
        n1_series = bars_last(pd.Series(cond_turn_green))
        mm1_series = bars_last(pd.Series(cond_turn_red))
        
        signals = np.zeros(len(df))
        ccc_arr = np.zeros(len(df), dtype=bool)
        jjj_arr = np.zeros(len(df), dtype=bool)
        
        for i in range(1, len(df)):
            n1 = n1_series.iloc[i]
            mm1 = mm1_series.iloc[i]
            if np.isnan(n1) or np.isnan(mm1): continue
            n1 = int(n1); mm1 = int(mm1)
            
            cc1 = np.min(close[max(0, i-n1):i+1])
            difl1 = np.min(d[max(0, i-n1):i+1])
            
            idx_prev = i - (mm1 + 1)
            if idx_prev < 0: 
                ccc_arr[i] = False; continue
            
            n1_prev = int(n1_series.iloc[idx_prev]) if not np.isnan(n1_series.iloc[idx_prev]) else 0
            cc2 = np.min(close[max(0, idx_prev-n1_prev):idx_prev+1])
            difl2 = np.min(d[max(0, idx_prev-n1_prev):idx_prev+1])
            
            idx_prev2 = idx_prev - (int(mm1_series.iloc[idx_prev]) + 1) if not np.isnan(mm1_series.iloc[idx_prev]) else -1
            if idx_prev2 >= 0:
                n1_prev2 = int(n1_series.iloc[idx_prev2]) if not np.isnan(n1_series.iloc[idx_prev2]) else 0
                cc3 = np.min(close[max(0, idx_prev2-n1_prev2):idx_prev2+1])
                difl3 = np.min(d[max(0, idx_prev2-n1_prev2):idx_prev2+1])
            else:
                cc3 = np.inf; difl3 = -np.inf

            is_green = (ref_m[i] < 0) & (d[i] < 0)
            aaa = (cc1 < cc2) and (difl1 > difl2) and is_green
            bbb = (cc1 < cc3) and (difl1 < difl2) and (difl1 > difl3) and is_green
            ccc = (aaa or bbb) and (d[i] < 0)
            ccc_arr[i] = ccc
            
            jjj = ccc_arr[i-1] and (abs(d[i-1]) >= (abs(d[i]) * 1.01))
            dxdx = (not jjj_arr[i-1]) and jjj
            jjj_arr[i] = jjj
            
            if dxdx: signals[i] = 1
            
        df['bottom_fishing_signal'] = signals
        return df
