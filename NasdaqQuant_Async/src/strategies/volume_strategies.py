import pandas as pd
import numpy as np
from scipy.signal import find_peaks, argrelextrema
from .base_strategy import Strategy

class VWAPMFI(Strategy):
    """
    5.1 VWAP + MFI
    - Setup: Close > Long Term MA (Trend)
    - Entry: Price pulls back to VWAP AND MFI < 40 Turn Up
    - Exit: MFI > 80 OR Price > VWAP Upper Band
    """
    def __init__(self):
        super().__init__("VWAPMFI")

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        signals = pd.Series(0, index=df.index)
        
        vwap = df['rolling_vwap_20']
        mfi = df['mfi_14']
        sma200 = df['Close'].rolling(window=200).mean()
        
        # MFI Turn Up: Yesterday < 40 AND Today > Yesterday
        mfi_turn_up = (mfi.shift(1) < 40) & (mfi > mfi.shift(1))
        
        # Pullback to VWAP: Low <= VWAP <= High (Touch) OR Close near VWAP (within 1%)
        near_vwap = (df['Close'] - vwap).abs() / vwap < 0.01
        
        # Entry
        entry_cond = (df['Close'] > sma200) & near_vwap & mfi_turn_up
        
        # Exit
        exit_cond = (mfi > 80)
        
        signals[entry_cond] = 1
        signals[exit_cond] = -1
        
        df['signal'] = signals
        return df

class AnchoredVWAPSupport(Strategy):
    """
    5.2 앵커드 VWAP 지지
    - Anchor: Significant Swing Lows (using scipy)
    - Entry: Price touches AVWAP and bounces
    - Exit: Close < AVWAP
    """
    def __init__(self):
        super().__init__("AnchoredVWAP")

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        signals = pd.Series(0, index=df.index)
        close = df['Close'].values
        
        # 1. Find Significant Lows (Anchors)
        # order=20 (local minima window 40 days)
        min_idxs = argrelextrema(close, np.less, order=20)[0]
        
        # AVWAP 계산은 Iterative할 수밖에 없음 (각 앵커마다 다르므로)
        # 여기서는 가장 최근의 'Major Low' 하나만 Anchor로 사용하여 벡터화 근사
        
        # 앵커 인덱스 매핑
        if len(min_idxs) > 0:
            last_anchor_idx = min_idxs[-1]
            if last_anchor_idx < len(df) - 1:
                # Calculate AVWAP from last_anchor_idx to end
                subset = df.iloc[last_anchor_idx:]
                cum_vol = subset['Volume'].cumsum()
                cum_pv = (subset['Close'] * subset['Volume']).cumsum()
                avwap_subset = cum_pv / cum_vol
                
                # 원본 df에 매핑 (인덱스 주의)
                df.loc[subset.index, 'avwap'] = avwap_subset
                
                # Entry: Low <= AVWAP <= Close (Intraday Touch & Bounce)
                avwap = df['avwap']
                entry_cond = (df['Low'] <= avwap) & (df['Close'] > avwap)
                
                # Exit: Close < AVWAP
                exit_cond = (df['Close'] < avwap)
                
                signals[entry_cond] = 1
                signals[exit_cond] = -1

        df['signal'] = signals
        return df

class OBVDivergence(Strategy):
    """
    5.3 OBV 다이버전스 (Bullish)
    - Logic: Price makes Lower Low, OBV makes Higher Low (Smart Money Accumulation)
    - Detection: Compare last two valleys using find_peaks (inverted)
    """
    def __init__(self):
        super().__init__("OBVDivergence")

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        signals = pd.Series(0, index=df.index)
        
        close = df['Close'].values
        obv = df['obv'].values
        
        # Find Valleys (Invert data to use find_peaks)
        # distance=20 (한 달에 한 번 정도의 저점)
        peaks_idx, _ = find_peaks(-close, distance=20)
        
        # 신호 생성용 배열
        divergence_detected = np.zeros(len(df), dtype=bool)
        
        if len(peaks_idx) >= 2:
            for i in range(1, len(peaks_idx)):
                curr_idx = peaks_idx[i]
                prev_idx = peaks_idx[i-1]
                
                p2 = close[curr_idx]
                p1 = close[prev_idx]
                
                o2 = obv[curr_idx]
                o1 = obv[prev_idx]
                
                # Bullish Divergence: Price Lower Low, OBV Higher Low
                if (p2 < p1) and (o2 > o1):
                    divergence_detected[curr_idx] = True
        
        # Entry
        signals[divergence_detected] = 1
        
        # Exit: OBV Trend Broken or SMA Crossover (Simple Exit for divergence trade)
        sma50 = df['Close'].rolling(window=50).mean()
        exit_cond = (df['Close'] < sma50)
        signals[exit_cond] = -1
        
        df['signal'] = signals
        return df
