import pandas as pd
import numpy as np
from .base_strategy import Strategy

class ConnorsRSI2(Strategy):
    """
    4.1 코너스 RSI-2
    - Filter: Close > SMA 200 (Long Term Uptrend)
    - Entry: RSI(2) < 5 (Deep Oversold)
    - Exit: Close > SMA 5 (Mean Reversion)
    """
    def __init__(self, rsi_limit=5):
        super().__init__("ConnorsRSI2")
        self.rsi_limit = rsi_limit

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        signals = pd.Series(0, index=df.index)
        
        # Indicators
        rsi2 = df['rsi_2']
        sma200 = df['sma_200']
        sma5 = df['Close'].rolling(window=5).mean() # 여기서 계산 (Indicator에 없으면)
        
        # Entry: Close > SMA200 AND RSI2 < Limit
        entry_cond = (df['Close'] > sma200) & (rsi2 < self.rsi_limit)
        
        # Exit: Close > SMA5
        exit_cond = (df['Close'] > sma5)
        
        signals[entry_cond] = 1
        signals[exit_cond] = -1
        
        df['signal'] = signals
        return df

class WilliamsRZScore(Strategy):
    """
    4.2 윌리엄스 %R + Z-Score 엔벨로프
    - Entry: Z-Score < -2.0 AND Williams %R < -80
    - Exit: Z-Score > 0 OR Williams %R > -20
    """
    def __init__(self):
        super().__init__("WilliamsRZScore")

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        signals = pd.Series(0, index=df.index)
        
        z = df['z_score']
        wr = df['willr_14']
        
        # Entry
        entry_cond = (z < -2.0) & (wr < -80)
        
        # Exit
        exit_cond = (z > 0) | (wr > -20)
        
        signals[entry_cond] = 1
        signals[exit_cond] = -1
        
        df['signal'] = signals
        return df

class MAEnvelopes(Strategy):
    """
    4.3 이동평균 엔벨로프 역추세
    - Entry: Price < Lower Envelope (5% below SMA 20)
    - Exit: Price > SMA 20
    """
    def __init__(self):
        super().__init__("MAEnvelopes")

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        signals = pd.Series(0, index=df.index)
        
        lower = df['ma_env_lower']
        # mid = sma 20
        mid = df['ma_env_upper'] / 1.05 # 역산 or Indicator에서 가져오기
        # Indicator.py에서 sma_20을 따로 저장 안했으면 다시 계산
        sma20 = df['Close'].rolling(window=20).mean()
        
        entry_cond = df['Close'] < lower
        exit_cond = df['Close'] > sma20
        
        signals[entry_cond] = 1
        signals[exit_cond] = -1
        
        df['signal'] = signals
        return df
