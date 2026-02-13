import pandas as pd
import numpy as np
from .base_strategy import Strategy

class AdaptiveDonchian(Strategy):
    """
    2.1 적응형 돈치안 채널 브레이크아웃
    - Entry: 20일 신고가 (donchian_upper_20 돌파)
    - Exit: 10일 신저가 (donchian_lower_10 이탈)
    """
    def __init__(self):
        super().__init__("AdaptiveDonchian")

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        signals = pd.Series(0, index=df.index)
        
        # Long Entry: Close > Previous Donchian Upper (20)
        # (주의: donchian_upper_20은 오늘을 포함할 수 있으므로 shift(1)된 값과 비교하거나, 
        # indicators에서 이미 shift된 값을 썼는지 확인. 여기서는 indicators 로직상 오늘 포함이므로 shift(1) 필요)
        entry_cond = df['Close'] > df['donchian_upper_20'].shift(1)
        
        # Long Exit: Close < Previous Donchian Lower (10)
        exit_cond = df['Close'] < df['donchian_lower_10'].shift(1)
        
        signals[entry_cond] = 1
        signals[exit_cond] = -1
        
        df['signal'] = signals
        return df

class SupertrendStrategy(Strategy):
    """
    2.2 ATR 변동성 스케일링 슈퍼트렌드
    - Entry: Supertrend Signal 1 (Green)
    - Exit: Supertrend Signal -1 (Red)
    - Mult: 3.5 (Nasdaq Optimized)
    """
    def __init__(self):
        super().__init__("Supertrend")

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        signals = pd.Series(0, index=df.index)
        
        # supertrend_signal: 1(Up), -1(Down)
        # 상태가 변하는 지점(Diff != 0)을 진입/청산 포인트로 잡음
        
        # 1로 변하는 순간 (매수)
        entry_cond = (df['supertrend_signal'] == 1) & (df['supertrend_signal'].shift(1) == -1)
        
        # -1로 변하는 순간 (매도)
        exit_cond = (df['supertrend_signal'] == -1) & (df['supertrend_signal'].shift(1) == 1)
        
        signals[entry_cond] = 1
        signals[exit_cond] = -1
        
        df['signal'] = signals
        return df

class IchimokuStrategy(Strategy):
    """
    2.3 이치모쿠 균형표 구름대 돌파 (Nasdaq Optimized)
    - Entry: Price > Cloud (Span A & B) AND Tenkan > Kijun (Golden Cross)
    - Exit: Price < Kijun
    """
    def __init__(self):
        super().__init__("Ichimoku")

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        signals = pd.Series(0, index=df.index)
        
        close = df['Close']
        span_a = df['ichi_senkou_a']
        span_b = df['ichi_senkou_b']
        tenkan = df['ichi_tenkan']
        kijun = df['ichi_kijun']
        
        # Cloud Top/Bottom
        cloud_top = np.maximum(span_a, span_b)
        cloud_bottom = np.minimum(span_a, span_b)
        
        # Entry: Close > Cloud Top AND Tenkan > Kijun
        entry_cond = (close > cloud_top) & (tenkan > kijun)
        
        # Exit: Close < Kijun OR Close < Cloud Bottom (구름대 진입/이탈)
        # 보고서: Price < Kijun
        exit_cond = (close < kijun)
        
        signals[entry_cond] = 1
        signals[exit_cond] = -1
        
        df['signal'] = signals
        return df

class LinRegSlopeStrategy(Strategy):
    """
    2.4 정규화 선형 회귀 기울기
    - Entry: Norm Slope > 0.2 (Threshold) AND R^2 > 0.8 (Filter)
    - Exit: Norm Slope < 0
    """
    def __init__(self, threshold=0.2, r2_filter=0.8):
        super().__init__("LinRegSlope")
        self.threshold = threshold
        self.r2_filter = r2_filter

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        signals = pd.Series(0, index=df.index)
        
        slope = df['norm_slope']
        r2 = df['r_squared']
        
        # Entry
        entry_cond = (slope > self.threshold) & (r2 > self.r2_filter)
        
        # Exit
        exit_cond = (slope < 0)
        
        signals[entry_cond] = 1
        signals[exit_cond] = -1
        
        df['signal'] = signals
        return df
