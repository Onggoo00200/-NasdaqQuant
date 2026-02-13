from abc import ABC, abstractmethod
import pandas as pd
import numpy as np

class Strategy(ABC):
    """
    모든 퀀트 전략의 기본이 되는 추상 클래스.
    """
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        데이터프레임에 진입/청산 신호(Signal)를 생성하여 반환.
        
        Args:
            df (pd.DataFrame): 지표가 계산된 데이터
            
        Returns:
            pd.DataFrame: 'signal' 컬럼(1: Long, -1: Short/Exit, 0: Neutral)이 추가된 데이터
        """
        pass
    
    def generate_position(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Signal을 기반으로 실제 포지션(Position) 상태를 생성.
        1: 보유 중, 0: 미보유
        (여기서는 Long Only 전략을 가정)
        """
        # signal: 1 (진입), -1 (청산)
        # position: 현재 보유 상태
        df['position'] = 0
        
        # 벡터화된 포지션 계산을 위해 numpy where 사용 불가 (이전 상태 의존)
        # 반복문 최소화를 위해 signal이 0이 아닌 지점만 찾아서 fillna로 채움
        
        # 1. 신호가 있는 곳만 추출
        # 진입(1) -> 1, 청산(-1) -> 0 (포지션 없으므로)
        temp_pos = df['signal'].replace(0, np.nan)
        
        # 2. -1(청산)을 0으로 변환 (보유량 0)
        temp_pos = temp_pos.replace(-1, 0)
        
        # 3. 앞의 상태를 유지 (ffill)
        df['position'] = temp_pos.ffill().fillna(0)
        
        return df
