import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def fetch_data(ticker, period="3y", interval="1d"):
    """
    yfinance로 데이터를 가져오고 정제합니다.
    """
    stock = yf.Ticker(ticker)
    df = stock.history(period=period, interval=interval)
    
    if df.empty:
        return df

    # 결측치 처리 (앞의 값으로 채움)
    df = df.ffill()
    
    return df

def add_indicators(df):
    """
    다양한 기술적 보조지표를 추가합니다. (Pandas 직접 구현)
    """
    if df.empty:
        return df

    # 1. 이동평균선 (SMA)
    df['MA5'] = df['Close'].rolling(window=5).mean()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA60'] = df['Close'].rolling(window=60).mean()
    df['MA120'] = df['Close'].rolling(window=120).mean()

    # 2. RSI (14)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))

    # 3. Bollinger Bands (20, 2)
    df['BB_Mid'] = df['MA20']
    std = df['Close'].rolling(window=20).std()
    df['BB_Upper'] = df['BB_Mid'] + (std * 2)
    df['BB_Lower'] = df['BB_Mid'] - (std * 2)

    # 4. MACD (12, 26, 9)
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']

    # 5. Stochastic Oscillator (14, 3)
    low_14 = df['Low'].rolling(window=14).min()
    high_14 = df['High'].rolling(window=14).max()
    df['Stoch_K'] = 100 * ((df['Close'] - low_14) / (high_14 - low_14))
    df['Stoch_D'] = df['Stoch_K'].rolling(window=3).mean()

    # 6. ATR (Average True Range, 14)
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    df['ATR'] = true_range.rolling(window=14).mean()

    # 7. OBV (On-Balance Volume)
    df['OBV'] = (np.sign(df['Close'].diff()) * df['Volume']).fillna(0).cumsum()

    return df

if __name__ == "__main__":
    test_ticker = "AAPL"
    print(f"Fetching 3y data for {test_ticker}...")
    data = fetch_data(test_ticker)
    data = add_indicators(data)
    
    print("\n[Available Indicators]")
    print(data.columns.tolist())
    
    print("\n[Recent Data Sample]")
    print(data[['Close', 'MACD', 'Stoch_K', 'ATR', 'OBV']].tail())