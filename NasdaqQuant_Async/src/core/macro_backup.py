import pandas as pd
import numpy as np
from fredapi import Fred
from datetime import datetime, timedelta
from src.utils.config import FRED_API_KEY

# 분석할 지표 정의 (Series ID 매핑)
INDICATORS = {
    'FedFunds': 'FEDFUNDS',       # 기준금리
    '10Y_Treasury': 'GS10',       # 10년물 국채금리
    '2Y_Treasury': 'GS2',         # 2년물 국채금리
    'Real_Rate_10Y': 'DFII10',    # 10년물 실질금리
    'M2_Liquidity': 'M2SL',       # M2 통화량
    'Corp_Profits': 'CPATAX',     # 기업 세후 이익
    'CPI': 'CPIAUCSL',            # 소비자 물가지수
    'HY_Spread': 'BAMLH0A0HYM2',  # 하이일드 스프레드
    'VIX': 'VIXCLS'               # 공포 지수
}

def fetch_fred_data(start_date='2000-01-01'):
    fred = Fred(api_key=FRED_API_KEY)
    df = pd.DataFrame()
    for name, series_id in INDICATORS.items():
        try:
            series = fred.get_series(series_id, observation_start=start_date)
            series.name = name
            if df.empty:
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
    
    return df_eng.dropna()

def determine_regime(row):
    """
    [보고서 로직] 우라카미 구니오 4계절 이론 기반 국면 판별
    """
    # 1. 금리 추세 확인 (기준금리 0.5% 초과 여부 - 단순화)
    rate_trend = 'UP' if row['FedFunds'] > 0.5 else 'LOW'
    
    # 2. 기업 이익 추세
    earnings_trend = 'GROWTH' if row['Profits_YoY'] > 0 else 'DECLINE'
    
    # 3. 리스크 상태 (하이일드 스프레드 Z-Score 기준)
    risk_status = 'RISK_OFF' if row['HY_Z'] > 1.0 else 'RISK_ON'
    
    # --- 국면 매핑 로직 ---
    if risk_status == 'RISK_OFF':
        return 'Panic/Crisis (Winter)'
    
    if earnings_trend == 'DECLINE' and rate_trend == 'LOW':
        return 'Financial Market (Spring)' # 금융 장세
        
    elif earnings_trend == 'GROWTH' and row['Inflation_YoY'] < 4.0:
        return 'Earnings Market (Summer)' # 실적 장세
        
    elif row['Inflation_YoY'] > 3.0 and rate_trend == 'UP':
        return 'Reverse Financial (Autumn)' # 역금융 장세
        
    else:
        return 'Transition/Uncertain'

def get_detailed_macro_analysis():
    """
    전체 파이프라인을 실행하여 현재 시장 국면 정보를 반환하는 마스터 함수
    """
    raw_data = fetch_fred_data()
    processed_data = feature_engineering(raw_data)
    processed_data['Regime'] = processed_data.apply(determine_regime, axis=1)
    
    return processed_data

if __name__ == "__main__":
    print("Running Global Macro Analysis...")
    analysis_df = get_detailed_macro_analysis()
    last_regime = analysis_df['Regime'].iloc[-1]
    print(f"\n[Latest Market Status]: {last_regime}")
    print(analysis_df[['Regime', 'Inflation_YoY', 'Profits_YoY', 'HY_Z']].tail())
