import numpy as np
import pandas as pd

def add_volume_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    거래량 지표 계산 (Pandas Implementation)
    """
    high = df['High']
    low = df['Low']
    close = df['Close']
    volume = df['Volume']
    
    tp = (high + low + close) / 3

    # --- 1. VWAP (Rolling 20 Days) ---
    tp_v = tp * volume
    df['rolling_vwap_20'] = tp_v.rolling(window=20).sum() / volume.rolling(window=20).sum()

    # --- 2. MFI (14) ---
    # MFI is RSI of Volume-Weighted Price
    # Money Flow = TP * Volume
    # Positive Flow: if TP > Prev TP
    # Negative Flow: if TP < Prev TP
    mf = tp * volume
    positive_flow = np.where(tp > tp.shift(1), mf, 0)
    negative_flow = np.where(tp < tp.shift(1), mf, 0)
    
    pos_mf_sum = pd.Series(positive_flow).rolling(window=14).sum()
    neg_mf_sum = pd.Series(negative_flow).rolling(window=14).sum()
    
    mfi = 100 - (100 / (1 + (pos_mf_sum / neg_mf_sum)))
    df['mfi_14'] = mfi.values

    # --- 3. OBV ---
    # OBV = Cumulative Sum of Volume * Direction
    direction = np.sign(close.diff()).fillna(0)
    df['obv'] = (direction * volume).cumsum()

    return df