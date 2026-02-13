import pandas as pd
import numpy as np
from fredapi import Fred
from datetime import datetime, timedelta
import os
from src.utils.config import FRED_API_KEY, BASE_DIR

# 캐시 파일 경로 설정
CACHE_DIR = os.path.join(BASE_DIR, "data")
CACHE_FILE = os.path.join(CACHE_DIR, "macro_daily_cache.pkl")

# 분석할 지표 정의
INDICATORS = {
    'FedFunds': 'FEDFUNDS',
    '10Y_Treasury': 'GS10',
    '2Y_Treasury': 'GS2',
    'Real_Rate_10Y': 'DFII10',
    'M2_Liquidity': 'M2SL',
    'Corp_Profits': 'CPATAX',
    'CPI': 'CPIAUCSL',
    'HY_Spread': 'BAMLH0A0HYM2',
    'VIX': 'VIXCLS'
}

def fetch_fred_data(start_date='2000-01-01'):
    fred = Fred(api_key=FRED_API_KEY)
    df = None
    for name, series_id in INDICATORS.items():
        try:
            series = fred.get_series(series_id, observation_start=start_date)
            series.name = name
            if df is None:
                df = series.to_frame()
            else:
                df = pd.merge(df, series, left_index=True, right_index=True, how='outer')
        except Exception as e:
            print(f"Error fetching {name}: {e}")
    return df.resample('ME').last().ffill()

def feature_engineering(df):
    df_eng = df.copy()
    df_eng['Yield_Curve'] = df_eng['10Y_Treasury'] - df_eng['2Y_Treasury']
    df_eng['Inflation_YoY'] = df_eng['CPI'].pct_change(12) * 100
    df_eng['M2_YoY'] = df_eng['M2_Liquidity'].pct_change(12) * 100
    df_eng['Profits_YoY'] = df_eng['Corp_Profits'].pct_change(12) * 100
    
    window = 24
    df_eng['HY_Z'] = (df_eng['HY_Spread'] - df_eng['HY_Spread'].rolling(window).mean()) / df_eng['HY_Spread'].rolling(window).std()
    df_eng['VIX_Z'] = (df_eng['VIX'] - df_eng['VIX'].rolling(window).mean()) / df_eng['VIX'].rolling(window).std()
    
    df_eng['Real_Rate_Calc'] = df_eng['10Y_Treasury'] - df_eng['Inflation_YoY']
    df_eng['Real_Rate_10Y'] = df_eng['Real_Rate_10Y'].fillna(df_eng['Real_Rate_Calc'])
    
    essential_cols = ['FedFunds', '10Y_Treasury', 'CPI', 'HY_Spread']
    df_eng = df_eng.ffill().bfill()
    return df_eng.dropna(subset=essential_cols)

def determine_regime(row):
    fed = row.get('FedFunds', 0); profits = row.get('Profits_YoY', 0)
    inflation = row.get('Inflation_YoY', 0); hy_z = row.get('HY_Z', 0)
    rate_trend = 'UP' if fed > 0.5 else 'LOW'
    earnings_trend = 'GROWTH' if profits > 0 else 'DECLINE'
    risk_status = 'RISK_OFF' if hy_z > 1.0 else 'RISK_ON'
    
    if risk_status == 'RISK_OFF': return 'Panic/Crisis (Winter)'
    if earnings_trend == 'DECLINE' and rate_trend == 'LOW': return 'Financial Market (Spring)'
    elif earnings_trend == 'GROWTH' and inflation < 4.0: return 'Earnings Market (Summer)'
    elif inflation > 3.0 and rate_trend == 'UP': return 'Reverse Financial (Autumn)'
    else: return 'Transition/Uncertain'

def get_detailed_macro_analysis():
    """
    일일 캐싱 로직이 적용된 마스터 함수.
    하루에 한 번만 FRED API를 호출하고 나머지는 로컬 파일에서 읽어옵니다.
    """
    # 1. 캐시 확인
    if os.path.exists(CACHE_FILE):
        file_time = datetime.fromtimestamp(os.path.getmtime(CACHE_FILE))
        if file_time.date() == datetime.now().date():
            print("[Macro] 오늘자 캐시 데이터를 로드합니다.")
            return pd.read_pickle(CACHE_FILE)

    # 2. 신규 수집 (캐시가 없거나 어제 데이터인 경우)
    print("[Macro] 오늘 첫 접속입니다. FRED API에서 신규 데이터를 수집합니다...")
    try:
        raw_data = fetch_fred_data()
        if raw_data is None or raw_data.empty: return pd.DataFrame()
        
        processed_data = feature_engineering(raw_data)
        if processed_data.empty: return pd.DataFrame()
        
        processed_data['Regime'] = processed_data.apply(determine_regime, axis=1)
        
        # 3. 캐시 저장
        os.makedirs(CACHE_DIR, exist_ok=True)
        processed_data.to_pickle(CACHE_FILE)
        return processed_data
    except Exception as e:
        print(f"Macro Logic Error: {e}")
        return pd.DataFrame()
