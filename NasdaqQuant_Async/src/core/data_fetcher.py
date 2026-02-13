import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import sys
from src.core.choicestock_api import ChoiceStockScraper

class TechValuationEngine:
    def __init__(self, ticker):
        self.ticker_symbol = ticker.upper().strip()
        self.ticker = yf.Ticker(self.ticker_symbol)
        self.price_data = None
        self.financials = None
        self.scraper = ChoiceStockScraper()
        
    def fetch_data(self):
        """
        [정식 하이브리드 엔진]
        - 재무: 초이스스탁 (이미 TTM 처리된 고품질 데이터)
        - 주가/SBC/주식수: 야후 파이낸스 (실시간 데이터)
        """
        print(f"[{self.ticker_symbol}] 초이스스탁 하이브리드 분석 파이프라인 가동...")
        try:
            # 1. 주가 데이터 (yfinance)
            self.price_data = self.ticker.history(period="5y")
            if self.price_data.empty: return None
            self.price_data.reset_index(inplace=True)
            self.price_data['Date'] = pd.to_datetime(self.price_data['Date']).dt.tz_localize(None)
            
            # 2. SBC 데이터 확보 (yfinance)
            yf_cf = self.ticker.quarterly_cashflow.T
            yf_cf.index = pd.to_datetime(yf_cf.index)
            if yf_cf.index.tz is not None: yf_cf.index = yf_cf.index.tz_localize(None)
            sbc_series = yf_cf.get('Stock Based Compensation', pd.Series(0, index=yf_cf.index))
            
            # 3. 초이스스탁 정밀 스크래핑
            raw_fin = self.scraper.get_financial_data(self.ticker_symbol)
            if not raw_fin:
                print(f"[{self.ticker_symbol}] 초이스스탁 수집 실패. 백업 로직으로 전환.")
                return self._fetch_data_yf_backup()

            def process_cs_data(df):
                if df is None or df.empty: return pd.DataFrame()
                df = df.set_index(df.columns[0]).T
                # 날짜 보정: '25.10.26' -> '2025-10-26'
                new_index = [pd.to_datetime("20" + d, format="%Y.%m.%d", errors='coerce') for d in df.index]
                df.index = new_index
                df = df.sort_index()
                # 수치화 및 단위 보정 (100만 -> 1)
                for col in df.columns:
                    df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce')
                return df.fillna(0) * 1_000_000

            q_inc = process_cs_data(raw_fin.get('income_statement'))
            q_cf = process_cs_data(raw_fin.get('cash_flow'))
            
            # 4. 데이터 병합
            combined = pd.merge(q_inc, q_cf, left_index=True, right_index=True, how='outer').ffill().fillna(0)
            
            # 유연한 키워드 매핑
            def get_val(df, kw):
                filtered = df.filter(like=kw)
                return filtered.iloc[:, 0] if not filtered.empty else pd.Series(0, index=df.index)

            fin_df = pd.DataFrame(index=combined.index)
            # 초이스스탁은 이미 TTM이므로 TTM 컬럼에 바로 할당
            fin_df['Revenue_TTM'] = get_val(combined, '매출액')
            fin_df['EBITDA_TTM'] = get_val(combined, 'EBITDA')
            fin_df['EBIT_TTM'] = get_val(combined, '영업이익')
            fin_df['Net Income_TTM'] = get_val(combined, '순이익')
            fin_df['CFO_TTM'] = get_val(combined, '영업활동현금흐름')
            fin_df['CapEx_TTM'] = abs(get_val(combined, '자본지출'))
            fin_df['SBC_TTM'] = sbc_series.reindex(fin_df.index, method='nearest').fillna(0).rolling(4, min_periods=1).sum()
            
            # 성장률 및 FCF (이미 TTM이므로 4칸 전과 비교)
            fin_df['Rev_Growth'] = fin_df['Revenue_TTM'].pct_change(4)
            fin_df['FCF_TTM'] = fin_df['CFO_TTM'] - fin_df['CapEx_TTM']
            fin_df['Adj_FCF_TTM'] = fin_df['FCF_TTM'] - fin_df['SBC_TTM']
            
            # 5. 공시 시차 45일 반영
            fin_df.index = fin_df.index + pd.Timedelta(days=45)
            self.financials = fin_df.dropna(subset=['Revenue_TTM'])
            return self.financials
            
        except Exception as e:
            print(f"[HYBRID] Critical Error: {e}")
            return self._fetch_data_yf_backup()

    def _fetch_data_yf_backup(self):
        """초이스스탁 실패 시의 yfinance 전용 백업 로직"""
        try:
            q_inc = self.ticker.quarterly_income_stmt.T.sort_index()
            q_cf = self.ticker.quarterly_cashflow.T.sort_index()
            if q_inc.empty: return None
            
            q_inc.index = pd.to_datetime(q_inc.index).tz_localize(None)
            q_cf.index = pd.to_datetime(q_cf.index).tz_localize(None)
            
            fin_df = pd.DataFrame(index=q_inc.index)
            def get_col(df, kw):
                for k in kw:
                    if k in df.columns: return df[k]
                return pd.Series(0, index=df.index)

            fin_df['Revenue'] = get_col(q_inc, ['Total Revenue', 'Revenue'])
            fin_df['EBITDA'] = get_col(q_inc, ['EBITDA', 'Normalized EBITDA'])
            fin_df['EBIT'] = get_col(q_inc, ['EBIT', 'Operating Income'])
            fin_df['Net Income'] = get_col(q_inc, ['Net Income'])
            fin_df['CFO'] = get_col(q_cf, ['Operating Cash Flow'])
            fin_df['CapEx'] = abs(get_col(q_cf, ['Capital Expenditure']))
            fin_df['SBC'] = get_col(q_cf, ['Stock Based Compensation'])
            
            for col in fin_df.columns:
                fin_df[f'{col}_TTM'] = fin_df[col].rolling(window=4, min_periods=4).sum()
            
            fin_df['Rev_Growth'] = fin_df['Revenue_TTM'].pct_change(4)
            fin_df['FCF_TTM'] = fin_df['CFO_TTM'] - fin_df['CapEx_TTM']
            fin_df['Adj_FCF_TTM'] = fin_df['FCF_TTM'] - fin_df['SBC_TTM']
            
            fin_df.index = fin_df.index + pd.Timedelta(days=45)
            self.financials = fin_df.dropna(subset=['Revenue_TTM'])
            return self.financials
        except: return None

    def compute_valuation_multiples(self):
        if self.financials is None: self.fetch_data()
        if self.financials is None or self.price_data is None or self.financials.empty: return pd.DataFrame()
        
        daily_fin = self.financials.resample('D').ffill()
        merged = pd.merge_asof(self.price_data.sort_values('Date'), daily_fin, left_on='Date', right_index=True, direction='backward').ffill()
        
        # 실시간 발행주식수 (yfinance)
        shares = self.ticker.info.get('sharesOutstanding', 1)
        merged['Market_Cap'] = merged['Close'] * shares
        # EV 약식 계산 (시총 + 부채 - 현금)
        debt = self.ticker.info.get('totalDebt', 0)
        cash = self.ticker.info.get('totalCash', 0)
        merged['EV'] = merged['Market_Cap'] + debt - cash
        
        # 멀티플 산출
        merged['EV/Sales'] = merged['EV'] / merged['Revenue_TTM'].replace(0, np.nan)
        merged['EV/EBITDA'] = merged['EV'] / merged['EBITDA_TTM'].replace(0, np.nan)
        merged['PER'] = merged['Market_Cap'] / merged['Net Income_TTM'].replace(0, np.nan)
        merged['P/FCF'] = merged['Market_Cap'] / merged['FCF_TTM'].replace(0, np.nan)
        
        merged.set_index('Date', inplace=True)
        return merged
