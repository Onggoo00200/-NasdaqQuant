import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

class TechValuationEngine:
    def __init__(self, ticker):
        self.ticker_symbol = ticker.upper().strip()
        self.ticker = yf.Ticker(self.ticker_symbol)
        self.price_data = None
        self.financials = None

    def fetch_data(self):
        """재무제표 수집 및 TTM 변환 (안정성 강화)"""
        try:
            # 1. 주가 데이터 수집
            hist = self.ticker.history(period="5y")
            if hist.empty: return None
            
            # 인덱스를 컬럼으로 빼고 강제로 datetime 변환
            hist.reset_index(inplace=True)
            hist['Date'] = pd.to_datetime(hist['Date']).dt.tz_localize(None)
            self.price_data = hist

            # 2. 분기 재무제표
            q_inc = self.ticker.quarterly_income_stmt.T.sort_index()
            q_bal = self.ticker.quarterly_balance_sheet.T.sort_index()
            q_cf = self.ticker.quarterly_cashflow.T.sort_index()
            if q_inc.empty: return None

            # 재무 데이터 인덱스도 강제 datetime 변환
            for df in [q_inc, q_bal, q_cf]:
                df.index = pd.to_datetime(df.index).tz_localize(None)

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
            fin_df['Shares'] = get_col(q_bal, ['Share Issued', 'Ordinary Shares Number']).fillna(0)
            fin_df['CapEx'] = abs(get_col(q_cf, ['Capital Expenditure'])).fillna(0)
            fin_df['CFO'] = get_col(q_cf, ['Operating Cash Flow']).fillna(0)
            fin_df['SBC'] = get_col(q_cf, ['Stock Based Compensation']).fillna(0)

            for col in ['Revenue', 'EBITDA', 'EBIT', 'Net Income', 'CapEx', 'CFO', 'SBC']:
                fin_df[f'{col}_TTM'] = fin_df[col].rolling(window=4, min_periods=1).sum().fillna(0)

            fin_df['Rev_Growth'] = fin_df['Revenue_TTM'].pct_change(4).fillna(0)
            fin_df['FCF_TTM'] = fin_df['CFO_TTM'] - fin_df['CapEx_TTM']
            fin_df['Adj_FCF_TTM'] = fin_df['FCF_TTM'] - fin_df['SBC_TTM']

            # 공시 시차 반영
            fin_df.index = fin_df.index + pd.Timedelta(days=45)
            self.financials = fin_df
            return fin_df
        except Exception as e:
            print(f"Fetch Error: {e}")
            return None

    def compute_valuation_multiples(self):
        if self.financials is None: self.fetch_data()
        if self.financials is None or self.price_data is None: return pd.DataFrame()

        # 시점 정렬 병합
        merged = pd.merge_asof(
            self.price_data.sort_values('Date'),
            self.financials.resample('D').ffill(),
            left_on='Date', right_index=True, direction='backward'
        ).ffill()

        # Market Cap 및 EV 계산
        shares = self.ticker.info.get('sharesOutstanding', 1) or 1
        merged['Market_Cap'] = merged['Close'] * shares
        merged['EV'] = merged['Market_Cap'] + merged.get('Total Debt', 0) - merged.get('Cash', 0)

        # 멀티플 계산
        merged['EV/Sales'] = merged['EV'] / merged['Revenue_TTM'].replace(0, np.nan)
        merged['EV/EBITDA'] = merged['EV'] / merged['EBITDA_TTM'].replace(0, np.nan)
        merged['EV/EBIT'] = merged['EV'] / merged['EBIT_TTM'].replace(0, np.nan)
        merged['PER'] = merged['Market_Cap'] / merged['Net Income_TTM'].replace(0, np.nan)
        merged['P/FCF'] = merged['Market_Cap'] / merged['FCF_TTM'].replace(0, np.nan)

        merged.set_index('Date', inplace=True)
        # 인덱스가 확실히 DatetimeIndex인지 보장
        merged.index = pd.to_datetime(merged.index)
        return merged

def select_best_metric(row):
    rev = float(row.get('Revenue_TTM', 1) or 1)
    ebitda = float(row.get('EBITDA_TTM', 0) or 0)
    capex = float(row.get('CapEx_TTM', 0) or 0)
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
        if df.empty: return None
        last = df.iloc[-1]
        m_name, m_val, m_reason = engine.select_best_metric(last)
        
        # 역사적 Z-Score (최근 2년)
        recent = df[df.index >= (df.index.max() - timedelta(days=365*2))]
        if not recent.empty:
            m_series = recent[m_name].replace([np.inf, -np.inf], np.nan).dropna()
            z_score = (m_val - m_series.mean()) / m_series.std() if not m_series.empty else 0
        else: z_score = 0

        rev = float(last.get('Revenue_TTM', 0) or 0)
        growth = float(last.get('Rev_Growth', 0) or 0) * 100
        return {
            "rev_growth": growth, 
            "adj_fcf_margin": (float(last.get('Adj_FCF_TTM', 0))/rev*100) if rev != 0 else 0,
            "rule_of_40": growth + ((float(last.get('Adj_FCF_TTM', 0))/rev*100) if rev != 0 else 0),
            "ev_sales": float(last.get('EV/Sales', 0)), 
            "erg_ratio": float(last.get('EV/Sales', 0)) / growth if growth > 0 else 999.0,
            "sbc_ratio": (float(last.get('SBC_TTM', 0)) / rev * 100) if rev != 0 else 0.0,
            "debt_ratio": float(engine.ticker.info.get('debtToEquity', 0) or 0),
            "z_score": z_score, "metric_name": m_name, "metric_value": m_val, "metric_reason": m_reason
        }
    except: return None

def analyze_tech_stock(ticker):
    engine = TechValuationEngine(ticker)
    df = engine.compute_valuation_multiples()
    if df.empty: return None, None
    
    # 지표 선정 값 컬럼 추가
    def _get_val(row): 
        _, val, _ = engine.select_best_metric(row)
        return val
    df['Selected_Value'] = df.apply(_get_val, axis=1)
    
    # 최근 3년 필터링 (인덱스가 Datetime임을 보장했으므로 이제 안전함)
    cutoff = df.index.max() - timedelta(days=365 * 3)
    recent = df[df.index >= cutoff].copy()
    
    m_name, _, _ = engine.select_best_metric(df.iloc[-1])
    m_series = recent['Selected_Value'].replace([np.inf, -np.inf], np.nan).dropna()
    mean_v, std_v = m_series.mean(), m_series.std()
    recent['Z_Score'] = (recent['Selected_Value'] - mean_v) / (std_v if std_v > 0 else 1)

    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.08,
                        subplot_titles=(f"Historical Valuation Band ({m_name})", "Z-Score Trend", "Rule of 40"))
    fig.add_trace(go.Scatter(x=recent.index, y=recent['Selected_Value'], name=m_name, line=dict(color='black', width=2)), row=1, col=1)
    
    colors = np.where(recent['Z_Score'] > 0, '#ef4444', '#3b82f6')
    fig.add_trace(go.Bar(x=recent.index, y=recent['Z_Score'], name="Z-Score", marker_color=colors), row=2, col=1)
    
    r40 = (recent['Rev_Growth'] * 100) + ((recent['FCF_TTM'] / recent['Revenue_TTM'].replace(0,1)) * 100)
    fig.add_trace(go.Scatter(x=recent.index, y=r40, name="Rule 40", fill='tozeroy', line_color='purple'), row=3, col=1)
    
    fig.update_layout(height=900, template="plotly_white", showlegend=False)
    return {}, fig
