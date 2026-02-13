import pandas as pd
import numpy as np
from .base_strategy import Strategy

class TTMSqueeze(Strategy):
    """
    3.1 TTM 스퀴즈
    - Setup: Squeeze On (BB inside KC)
    - Entry: Squeeze Off (BB expands) AND Momentum > 0
    - Exit: Momentum decreases (2 bars) or turns negative
    """
    def __init__(self):
        super().__init__("TTMSqueeze")

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        signals = pd.Series(0, index=df.index)
        
        sqz_on = df['ttm_squeeze_on']
        mom = df['ttm_mom']
        
        # Entry: 
        # 1. 어제까지 Squeeze On이었다가 오늘 Off됨 (확장)
        # 2. Momentum > 0 (상승 방향)
        fired = (~sqz_on) & (sqz_on.shift(1))
        entry_cond = fired & (mom > 0)
        
        # Exit:
        # 1. Momentum < 0 (하락 반전) OR
        # 2. Momentum decreasing for 2 bars (힘 빠짐) -> 너무 민감할 수 있으므로 Negative 전환만 사용하거나 선택.
        # 보고서: "모멘텀 히스토그램이 2봉 연속 하락하거나 반대 방향으로 전환될 때"
        mom_decreasing = (mom < mom.shift(1)) & (mom.shift(1) < mom.shift(2))
        exit_cond = (mom < 0) | (mom_decreasing & (mom > 0))
        
        signals[entry_cond] = 1
        signals[exit_cond] = -1
        
        df['signal'] = signals
        return df

class CrabelORB(Strategy):
    """
    3.2 토비 크라벨의 ORB와 스트레치
    - Entry: Close > Open + Stretch (일봉상 당일 돌파 마감 간주)
    - Exit: Close < Open - Stretch (손절) OR Daily Close (여기선 다음날 시가 청산 가정)
    - 일봉 데이터 한계: 장중 돌파 여부를 알 수 없음. 
      -> Close가 Open + Stretch보다 높으면 '장중 돌파했다'고 가정하고 진입(1). 
      -> 다음날 시가(Open)에 청산(-1)하는 데이 트레이딩 로직으로 구현.
    """
    def __init__(self):
        super().__init__("CrabelORB")

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        signals = pd.Series(0, index=df.index)
        
        open_p = df['Open']
        stretch = df['crabel_stretch'] # Multiplier 1.0 (Indicators에서 이미 계산됨? 확인 필요. Indicators에선 Raw Mean만 있음)
        # 보고서엔 Multiplier 언급 없으나 보통 1.5~2.0 사용. 여기선 1.5 적용
        threshold = stretch * 1.5
        
        # Entry Condition (장중 돌파 가정: High > Open + Threshold)
        # 하지만 백테스트의 정확성을 위해 Close > Open + Threshold인 날 매수했다고 가정 (확실한 추세일)
        entry_cond = df['High'] > (open_p + threshold)
        
        # Exit: 데이 트레이딩이므로 당일 종가 청산이 원칙.
        # 시스템상 당일 1 -> 익일 0(청산) 처리 필요.
        # Backtester가 1이면 보유, 0이면 미보유이므로,
        # 이 전략은 진입 조건 만족 시 1을 주고, 그 다음날 무조건 -1을 주어야 함.
        # 하지만 벡터화 로직상 매일매일 독립적 판단이 어려움.
        # 대안: 조건 만족일 = 1. 다음날 = -1.
        
        signals[entry_cond] = 1
        # 진입 다음날 무조건 청산 신호
        # (shift(1)이 True면 어제 진입했으므로 오늘 청산)
        exit_cond = entry_cond.shift(1).fillna(False)
        signals[exit_cond] = -1
        
        # 만약 오늘 또 진입 조건이면? -> 1 (보유 연장 or 재진입)
        # 우선순위: 청산 후 재진입 가능. 1이 덮어쓰도록 순서 조정
        signals[exit_cond] = -1
        signals[entry_cond] = 1
        
        df['signal'] = signals
        return df

class LarryWilliamsVBO(Strategy):
    """
    3.3 래리 윌리엄스 VBO
    - Entry: Price > Open + (k * Prev Range)
    - k = 0.5
    - Exit: Next Open (Day Trading) or Swing
    """
    def __init__(self, k=0.5):
        super().__init__("LarryWilliamsVBO")
        self.k = k

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        signals = pd.Series(0, index=df.index)
        
        open_p = df['Open']
        prev_range = df['prev_range']
        
        # Entry Trigger Price
        trigger = open_p + (self.k * prev_range)
        
        # High가 Trigger보다 높으면 장중 진입 발생
        entry_cond = df['High'] > trigger
        
        # Exit: ORB와 마찬가지로 1일 보유 후 청산 (Swing 변형 가능)
        signals[entry_cond.shift(1).fillna(False)] = -1 # 어제 진입했으면 오늘 청산
        signals[entry_cond] = 1 # 오늘 진입
        
        df['signal'] = signals
        return df
