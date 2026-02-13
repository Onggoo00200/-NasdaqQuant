import pandas as pd
import numpy as np
from datetime import timedelta
from src.core.data_fetcher import TechValuationEngine

def select_best_metric(row):
    rev = float(row.get('Revenue_TTM', 1) or 1)
    ebitda = float(row.get('EBITDA_TTM', 0) or 0)
    capex = float(row.get('CapEx_TTM', 0) or 0)
    growth = float(row.get('Rev_Growth', 0) or 0)
    
    if ebitda <= 0: return "EV/Sales", float(row.get('EV/Sales', 0)), "EBITDA 적자"
    if (ebitda / rev) < 0.05: return "EV/Sales", float(row.get('EV/Sales', 0)), "초기 마진 불안정"
    if (capex / rev) > 0.10: 
        if float(row.get('EBIT_TTM', 0)) > 0: return "EV/EBIT", float(row.get('EV/EBIT', 0)), "자본집약적"
        else: return "EV/EBITDA", float(row.get('EV/EBITDA', 0)), "EBIT 적자 차선책"
    return "EV/EBITDA", float(row.get('EV/EBITDA', 0)), "표준 성장 모델"

def analyze_tech_valuation_full(ticker):
    try:
        engine = TechValuationEngine(ticker)
        df = engine.compute_valuation_multiples()
        if df is None or df.empty: return None
        
        last = df.iloc[-1]
        m_name, m_val, m_reason = select_best_metric(last)
        
        recent = df[df.index >= (df.index.max() - timedelta(days=365*2))]
        if not recent.empty:
            m_series = recent[m_name].replace([np.inf, -np.inf], np.nan).dropna()
            z_score = (m_val - m_series.mean()) / m_series.std() if not m_series.empty else 0
        else: z_score = 0

        rev = float(last.get('Revenue_TTM', 0) or 1)
        growth = float(last.get('Rev_Growth', 0) or 0) * 100
        # SBC 차감 Adjusted FCF 마진
        adj_fcf_margin = (float(last.get('Adj_FCF_TTM', 0)) / rev) * 100
        cfo_margin = (float(last.get('CFO_TTM', 0)) / rev) * 100
        
        return {
            "ticker": ticker,
            "rev_growth": growth, 
            "adj_fcf_margin": adj_fcf_margin,
            "cfo_margin": cfo_margin,
            "rule_of_40": growth + adj_fcf_margin,
            "ev_sales": float(last.get('EV/Sales', 0)), 
            "erg_ratio": float(last.get('EV/Sales', 0)) / growth if growth > 0 else 999.0,
            "sbc_ratio": (float(last.get('SBC_TTM', 0)) / rev * 100),
            "debt_ratio": float(engine.ticker.info.get('debtToEquity', 0) or 0),
            "z_score": z_score, "metric_name": m_name, "metric_value": m_val, "metric_reason": m_reason
        }
    except Exception: return None

def analyze_tech_stock_data(ticker):
    engine = TechValuationEngine(ticker)
    df = engine.compute_valuation_multiples()
    if df is None or df.empty: return None, None

    def _get_val(row): 
        _, val, _ = select_best_metric(row)
        return val
    df['Selected_Value'] = df.apply(_get_val, axis=1)
    
    cutoff = df.index.max() - timedelta(days=365 * 3)
    recent_df = df[df.index >= cutoff].copy()
    if recent_df.empty: return None, None

    m_name, _, _ = select_best_metric(df.iloc[-1])
    m_series = recent_df['Selected_Value'].replace([np.inf, -np.inf], np.nan).dropna()
    mean_val, std_val = m_series.mean(), m_series.std()
    
    recent_df['Z_Score'] = (recent_df['Selected_Value'] - mean_val) / (std_val if std_val > 0 else 1)
    # 시각화용 Rule of 40 시계열 교정
    recent_df['Hist_Rule40'] = (recent_df['Rev_Growth'] * 100) + ((recent_df['FCF_TTM'] / recent_df['Revenue_TTM'].replace(0,1)) * 100)
    
    latest = df.iloc[-1]
    rev = float(latest.get('Revenue_TTM', 1))
    growth = float(latest.get('Rev_Growth', 0)) * 100
    fcf_m = (float(latest.get('FCF_TTM', 0)) / rev) * 100

    summary_data = {
        "ticker": ticker, "dominant_metric": m_name, "mean_val": mean_val, "std_val": std_val,
        "z_score": recent_df['Z_Score'].iloc[-1], "rev_growth": growth, "rule_of_40": growth + fcf_m
    }
    return summary_data, recent_df