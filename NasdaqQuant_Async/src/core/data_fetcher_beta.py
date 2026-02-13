import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(PROJECT_ROOT)

from src.core.choicestock_api import ChoiceStockScraper

class BetaTechValuationEngine:
    def __init__(self, ticker):
        self.ticker_symbol = ticker.upper().strip()
        self.ticker = yf.Ticker(self.ticker_symbol)
        self.scraper = ChoiceStockScraper()
        
    def generate_final_report(self):
        print(f"[{self.ticker_symbol}] 정밀 하이브리드 리포트 생성 중...\n")
        
        try:
            # 1. 주가 및 SBC
            hist = self.ticker.history(period="1d")
            last_price = hist['Close'].iloc[-1]
            
            yf_cf = self.ticker.quarterly_cashflow.T
            yf_cf.index = pd.to_datetime(yf_cf.index)
            sbc_ttm = yf_cf.get('Stock Based Compensation', pd.Series(0, index=yf_cf.index)).tail(4).sum()
            
            # 2. ChoiceStock
            raw_fin = self.scraper.get_financial_data(self.ticker_symbol)
            if not raw_fin: return

            def process_cs(df):
                df = df.set_index(df.columns[0]).T
                new_index = [pd.to_datetime("20" + d, format="%Y.%m.%d", errors='coerce') for d in df.index]
                df.index = new_index
                df = df.sort_index()
                for col in df.columns:
                    df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce')
                return df.fillna(0) * 1_000_000

            inc = process_cs(raw_fin.get('income_statement'))
            cf = process_cs(raw_fin.get('cash_flow'))
            
            # 항목 추출 도우미 (에러 방지)
            def get_safe_val(df, kw):
                filtered = df.filter(like=kw)
                if not filtered.empty: return filtered.iloc[-1, 0]
                return 0

            rev_ttm = get_safe_val(inc, '매출액')
            ebitda_ttm = get_safe_val(inc, 'EBITDA')
            net_inc_ttm = get_safe_val(inc, '순이익') # 지배지분순이익 대신 포괄적인 '순이익' 사용
            cfo_ttm = get_safe_val(cf, '영업활동현금흐름')
            capex_ttm = abs(get_safe_val(cf, '자본지출'))
            fcf_ttm = cfo_ttm - capex_ttm
            
            # 성장률
            rev_series = inc.filter(like='매출액').iloc[:, 0]
            growth = (rev_series.iloc[-1] / rev_series.iloc[-5] - 1) * 100 if len(rev_series) > 5 else 0
            
            # 3. 지표 산출
            shares = self.ticker.info.get('sharesOutstanding', 1)
            mkt_cap = last_price * shares
            ev_ebitda = mkt_cap / ebitda_ttm if ebitda_ttm > 0 else 0
            fcf_m = (fcf_ttm / rev_ttm) * 100 if rev_ttm > 0 else 0
            rule_of_40 = growth + fcf_m
            sbc_ratio = (sbc_ttm / rev_ttm) * 100 if rev_ttm > 0 else 0
            
            print(f"========================================")
            print(f"   💎 {self.ticker_symbol} 테크 퀀트 정밀 리포트 (BETA)")
            print(f"========================================")
            print(f"기준일: {inc.index[-1].date()}")
            print(f"시가 총액: ${mkt_cap/1e12:.2f}T")
            print(f"----------------------------------------")
            print(f"1. 성장 및 수익 효율성")
            print(f"   ▶ 매출 성장률(YoY): {growth:.1f}%")
            print(f"   ▶ FCF 마진율: {fcf_m:.1f}%")
            print(f"   ▶ Rule of 40 점수: {rule_of_40:.1f}")
            print(f"   ▶ SBC 비중: {sbc_ratio:.1f}%")
            print(f"----------------------------------------")
            print(f"2. 밸류에이션 지표")
            print(f"   ▶ EV/Sales: {mkt_cap/rev_ttm if rev_ttm > 0 else 0:.2f}x")
            print(f"   ▶ EV/EBITDA: {ev_ebitda:.2f}x")
            print(f"   ▶ PER: {mkt_cap/net_inc_ttm if net_inc_ttm > 0 else 0:.2f}x")
            print(f"========================================\n")
            
        except Exception as e:
            print(f"리포트 생성 실패: {e}")

if __name__ == "__main__":
    BetaTechValuationEngine("NVDA").generate_final_report()