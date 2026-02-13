import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta

class TechValuationEngine:
    def __init__(self, ticker):
        self.ticker_symbol = ticker
        self.ticker = yf.Ticker(ticker)
        self.price_data = None
        self.financials = None
        
    def fetch_data(self):
        """재무제표 수집 및 TTM 변환 (안정성 강화 버전)"""
        try:
            hist = self.ticker.history(period="5y")
            if hist.empty: return None
            hist.reset_index(inplace=True)
            if hist['Date'].dt.tz is not None: hist['Date'] = hist['Date'].dt.tz_localize(None)
            self.price_data = hist
            
            q_inc = self.ticker.quarterly_income_stmt.T.sort_index()
            q_bal = self.ticker.quarterly_balance_sheet.T.sort_index()
            q_cf = self.ticker.quarterly_cashflow.T.sort_index()
            if q_inc.empty: return None
            
            fin_df = pd.DataFrame(index=q_inc.index)
            def get_col(df, keywords):
                for k in keywords: 
                    if k in df.columns: return df[k]
                return pd.Series(0, index=df.index)
                
            fin_df['Revenue'] = get_col(q_inc, ['Total Revenue', 'Revenue']).fillna(0)
            fin_df['EBITDA'] = get_col(q_inc, ['EBITDA', 'Normalized EBITDA']).fillna(0)
            fin_df['EBIT'] = get_col(q_inc, ['EBIT', 'Operating Income']).fillna(0)
            fin_df['Net Income'] = get_col(q_inc, ['Net Income']).fillna(0)
            fin_df['Total Debt'] = get_col(q_bal, ['Total Debt']).fillna(0)
            fin_df['Cash'] = get_col(q_bal, ['Cash And Cash Equivalents', 'Cash']).fillna(0)
            fin_df['CapEx'] = abs(get_col(q_cf, ['Capital Expenditure'])).fillna(0)
            fin_df['CFO'] = get_col(q_cf, ['Operating Cash Flow']).fillna(0)
            fin_df['SBC'] = get_col(q_cf, ['Stock Based Compensation']).fillna(0)
            
            for col in ['Revenue', 'EBITDA', 'EBIT', 'Net Income', 'CapEx', 'CFO', 'SBC']:
                fin_df[f'{col}_TTM'] = fin_df[col].rolling(window=4, min_periods=4).sum().fillna(0)
            
            fin_df['Rev_Growth'] = fin_df['Revenue_TTM'].pct_change(4).fillna(0)
            fin_df['FCF_TTM'] = fin_df['CFO_TTM'] - fin_df['CapEx_TTM']
            fin_df['Adj_FCF_TTM'] = fin_df['FCF_TTM'] - fin_df['SBC_TTM']
            
            fin_df.index = pd.to_datetime(fin_df.index).tz_localize(None) + pd.Timedelta(days=45)
            self.financials = fin_df
            return fin_df
        except: return None

    def compute_valuation_multiples(self):
        if self.financials is None: self.fetch_data()
        if self.financials is None or self.price_data is None: return pd.DataFrame()
        
        merged = pd.merge_asof(
            self.price_data.sort_values('Date'), 
            self.financials.resample('D').ffill(), 
            left_on='Date', right_index=True, direction='backward'
        ).ffill()
        
        shares = self.ticker.info.get('sharesOutstanding', 1)
        merged['Market_Cap'] = merged['Close'] * shares
        merged['EV'] = merged['Market_Cap'] + merged.get('Total Debt', 0) - merged.get('Cash', 0)
        
        merged['EV/Sales'] = merged['EV'] / merged['Revenue_TTM'].replace(0, np.nan)
        merged['EV/EBITDA'] = merged['EV'] / merged['EBITDA_TTM'].replace(0, np.nan)
        merged['EV/EBIT'] = merged['EV'] / merged['EBIT_TTM'].replace(0, np.nan)
        merged['P/FCF'] = merged['Market_Cap'] / merged['FCF_TTM'].replace(0, np.nan)
        
        merged.set_index('Date', inplace=True)
        return merged

    def select_best_metric(self, row):
        """[보고서 2.2] 최적 지표 선정 의사결정 트리"""
        rev = float(row.get('Revenue_TTM', 1) or 1)
        ebitda = float(row.get('EBITDA_TTM', 0) or 0)
        capex = float(row.get('CapEx_TTM', 0) or 0)
        growth = float(row.get('Rev_Growth', 0) or 0)
        fcf = float(row.get('FCF_TTM', 0) or 0)
        
        ebitda_margin = ebitda / rev if rev != 0 else 0
        capex_ratio = capex / rev if rev != 0 else 0
        fcf_margin = fcf / rev if rev != 0 else 0

        # 1. 적자 기업
        if ebitda <= 0: return "EV/Sales", float(row.get('EV/Sales', 0)), "EBITDA 적자"
        # 2. 초기 흑자
        if ebitda_margin < 0.05: return "EV/Sales", float(row.get('EV/Sales', 0)), "초기 마진 불안정"
        # 3. 자본 집약적
        if capex_ratio > 0.10: return "EV/EBIT", float(row.get('EV/EBIT', 0)), "자본집약적(High CapEx)"
        # 4. 성숙기
        if growth < 0.10 and fcf_margin > 0.20: return "P/FCF", float(row.get('P/FCF', 0)), "성숙기 현금창출"
        # 5. Default
        return "EV/EBITDA", float(row.get('EV/EBITDA', 0)), "표준 성장주"

def analyze_tech_valuation_full(ticker):
    """최종 분석 데이터를 딕셔너리로 취합 (Z-Score 포함)"""
    try:
        engine = TechValuationEngine(ticker)
        df = engine.compute_valuation_multiples()
        if df.empty: return None
        
        last = df.iloc[-1]
        m_name, m_val, m_reason = engine.select_best_metric(last)
        
        # Z-Score (최근 2년)
        recent = df[df.index >= (df.index.max() - timedelta(days=365*2))]
        if not recent.empty:
            m_series = recent[m_name].replace([np.inf, -np.inf], np.nan).dropna()
            z_score = (m_val - m_series.mean()) / m_series.std() if not m_series.empty else 0
        else:
            z_score = 0

        # Rule of 40 & ERG
        rev = float(last.get('Revenue_TTM', 0) or 0)
        growth = float(last.get('Rev_Growth', 0) or 0) * 100
        adj_fcf = float(last.get('Adj_FCF_TTM', 0) or 0)
        sbc = float(last.get('SBC_TTM', 0) or 0)
        
        margin = (adj_fcf / rev * 100) if rev != 0 else 0.0
        rule_of_40 = growth + margin
        erg_ratio = float(last.get('EV/Sales', 0)) / growth if growth > 0 else 999.0
        
        return {
            "ticker": ticker,
            "metric_name": m_name, "metric_value": m_val, "metric_reason": m_reason,
            "z_score": z_score,
            "rev_growth": growth, "adj_fcf_margin": margin, "rule_of_40": rule_of_40,
            "ev_sales": float(last.get('EV/Sales', 0)), "erg_ratio": erg_ratio,
            "sbc_ratio": (sbc / rev * 100) if rev != 0 else 0.0,
            "debt_ratio": float(engine.ticker.info.get('debtToEquity', 0) or 0)
        }
    except: return None
