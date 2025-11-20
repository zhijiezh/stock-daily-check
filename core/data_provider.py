import yfinance as yf
import pandas as pd

def get_stock_data(ticker: str, start_date: str = None, end_date: str = None, period: str = "max") -> pd.DataFrame:
    """
    Fetch historical stock data using yfinance.
    
    Args:
        ticker (str): Stock symbol (e.g., "TQQQ").
        start_date (str): Start date in "YYYY-MM-DD" format.
        end_date (str): End date in "YYYY-MM-DD" format.
        period (str): Period to fetch if dates are not provided (default "max").
        
    Returns:
        pd.DataFrame: DataFrame with Date index and columns [Open, High, Low, Close, Volume].
    """
    print(f"Fetching data for {ticker}...")
    if start_date and end_date:
        df = yf.download(ticker, start=start_date, end=end_date, progress=False)
    else:
        df = yf.download(ticker, period=period, progress=False)
        
    if df.empty:
        print(f"Warning: No data found for {ticker}")
        return df

    # Standardize columns
    # yfinance sometimes returns multi-level columns if multiple tickers, but here we assume one.
    if isinstance(df.columns, pd.MultiIndex):
        # Flatten multi-index columns if they exist (e.g. ('Close', 'TQQQ') -> 'Close')
        # Keep only the Price column names
        try:
            df.columns = df.columns.droplevel(1)
        except:
            pass
    
    return df

def get_current_price(ticker: str) -> float:
    """
    Get the latest available price for a ticker.
    """
    ticker_obj = yf.Ticker(ticker)
    # Try to get fast info first (faster)
    try:
        price = ticker_obj.fast_info['last_price']
        return price
    except:
        pass
        
    # Fallback to history
    df = ticker_obj.history(period="1d")
    if not df.empty:
        return df['Close'].iloc[-1]
    return 0.0

