import numpy as np
import pandas as pd

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def add_momentum_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    모멘텀 지표 계산 (Pandas Implementation)
    """
    close = df['Close']
    high = df['High']
    low = df['Low']

    # --- 1. RSI-2 (Connors) ---
    # Pandas rolling mean RSI is simple averaging, Wilder's smoothing is standard but Simple is ok for RSI-2
    df['rsi_2'] = calculate_rsi(close, period=2)
    df['sma_200'] = close.rolling(window=200).mean()

    # --- 2. Williams %R (14) ---
    hh = high.rolling(window=14).max()
    ll = low.rolling(window=14).min()
    df['willr_14'] = ((hh - close) / (hh - ll)) * -100

    # --- 3. Z-Score (Period 20) ---
    sma_20 = close.rolling(window=20).mean()
    std_20 = close.rolling(window=20).std()
    df['z_score'] = (close - sma_20) / std_20.replace(0, 0.0001)

    # --- 4. MA Envelopes (20, 5%) ---
    env_pct = 0.05
    df['ma_env_upper'] = sma_20 * (1 + env_pct)
    df['ma_env_lower'] = sma_20 * (1 - env_pct)

    return df