import numpy as np
import pandas as pd

def add_volatility_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    변동성 지표 계산 (Pandas Implementation)
    """
    high = df['High']
    low = df['Low']
    close = df['Close']
    open_p = df['Open']
    
    # --- ATR Calculation (Common) ---
    period = 14
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr_14 = tr.rolling(window=14).mean()
    atr_20 = tr.rolling(window=20).mean()
    
    df['atr_14'] = atr_14

    # --- 1. TTM Squeeze ---
    # Bollinger Bands (20, 2.0)
    bb_mid = close.rolling(window=20).mean()
    bb_std = close.rolling(window=20).std()
    bb_upper = bb_mid + (2.0 * bb_std)
    bb_lower = bb_mid - (2.0 * bb_std)
    
    # Keltner Channels (20, 1.5 ATR)
    kc_upper = bb_mid + (1.5 * atr_20)
    kc_lower = bb_mid - (1.5 * atr_20)
    
    df['ttm_squeeze_on'] = (bb_upper < kc_upper) & (bb_lower > kc_lower)
    df['ttm_mom'] = close - close.ewm(span=20, adjust=False).mean()

    # --- 2. Crabel Stretch (ORB) ---
    ho = (high - open_p).abs()
    ol = (open_p - low).abs()
    noise = np.minimum(ho, ol)
    df['crabel_stretch'] = noise.rolling(window=10).mean()

    # --- 3. Larry Williams VBO ---
    df['prev_range'] = (high - low).shift(1)

    return df