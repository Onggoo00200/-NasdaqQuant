import pandas as pd
from .trend import add_trend_indicators
from .volatility import add_volatility_indicators
from .momentum import add_momentum_indicators
from .volume import add_volume_indicators

def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    모든 기술적 지표를 한 번에 계산하여 DataFrame에 추가하는 마스터 함수.
    NasdaqQuant_Async 프로젝트의 핵심 전처리 단계.
    
    Args:
        df (pd.DataFrame): OHLCV 데이터 (Open, High, Low, Close, Volume 필수)
    
    Returns:
        pd.DataFrame: 지표가 추가된 DataFrame
    """
    # 데이터 유효성 체크
    required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
    if not all(col in df.columns for col in required_cols):
        raise ValueError(f"Input DataFrame must contain: {required_cols}")

    # 1. Trend
    df = add_trend_indicators(df)
    
    # 2. Volatility
    df = add_volatility_indicators(df)
    
    # 3. Momentum
    df = add_momentum_indicators(df)
    
    # 4. Volume
    df = add_volume_indicators(df)
    
    # 결측치 처리 (지표 계산 초기에 발생하는 NaN)
    # 전략에 따라 dropna()를 할지 0으로 채울지 결정해야 하나,
    # 여기서는 앞부분 데이터를 날리는 것이 안전함 (Backtesting 시)
    # df.dropna(inplace=True) -> 호출하는 쪽에서 결정하도록 주석 처리
    
    return df
