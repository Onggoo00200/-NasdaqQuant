import asyncio
from typing import Optional
import yfinance as yf
import pandas as pd
from .context import BetaReportContext
from src.core.choicestock_api import ChoiceStockScraper
from src.core.valuation_engine import analyze_tech_valuation_full

class DataAggregator:
    def __init__(self, ticker: str):
        self.ticker = ticker.upper()
        self.context = BetaReportContext(ticker=self.ticker)

    async def collect_all(self):
        print(f"[Beta-Aggregator] {self.ticker} 데이터 통합 수집 시작...")
        
        loop = asyncio.get_event_loop()
        
        # 1. 기초 퀀트 데이터 (Z-score, R40 등)
        val_data = await loop.run_in_executor(None, analyze_tech_valuation_full, self.ticker)
        if val_data:
            self.context.valuation_metrics = val_data

        # 2. ChoiceStock 데이터 (우선순위 활용을 위해 먼저 수집)
        cs_data = await loop.run_in_executor(None, self._fetch_choicestock)
        if cs_data:
            self.context.choice_stock_data = cs_data

        # 3. 테크 특화 재무 데이터 수집 (CS 데이터를 활용할 수 있도록 전달)
        tech_stats = await loop.run_in_executor(None, self._fetch_tech_specifics, cs_data)
        self.context.metadata.update(tech_stats)
            
        return self.context

    def _fetch_tech_specifics(self, cs_data=None):
        """
        [데이터 우선순위 및 단위 보정 엔진]
        모든 Margin 지표는 0~100 사이의 숫자로 통일합니다.
        """
        try:
            t = yf.Ticker(self.ticker)
            info = t.info
            rev_total = info.get("totalRevenue", 1)
            
            def get_standardized_metric(yf_key, cs_label, raw_label, is_cf=False):
                val = None
                # 1. yfinance info 시도
                yf_val = info.get(yf_key)
                if yf_val is not None and yf_val != 0:
                    # yfinance의 margin은 소수점(0.1)이므로 100을 곱함
                    if 'Margin' in yf_key or 'Margins' in yf_key:
                        val = yf_val * 100
                    elif 'Cashflow' in yf_key or 'Flow' in yf_key:
                        # 절대 수치는 매출로 나눠서 마진화
                        val = (yf_val / rev_total * 100) if rev_total > 0 else 0
                    else:
                        val = yf_val
                
                # 2. ChoiceStock/Raw 시도 (yf_val이 없거나 0인 경우)
                if val is None or val == 0:
                    try:
                        # Raw TTM 계산 (가장 정확한 백업)
                        df_raw = t.quarterly_cashflow if is_cf else t.quarterly_financials
                        if df_raw is not None and raw_label in df_raw.index:
                            raw_ttm = df_raw.loc[raw_label].iloc[:4].sum()
                            rev_ttm = t.quarterly_financials.loc['Total Revenue'].iloc[:4].sum()
                            val = (raw_ttm / rev_ttm * 100) if rev_ttm > 0 else 0
                    except: pass

                return val

            # 지표 산출
            op_margin = get_standardized_metric("operatingMargins", "영업이익", "Operating Income")
            cfo_margin = get_standardized_metric("operatingCashflow", "영업활동", "Operating Cash Flow", is_cf=True)
            rnd_val = get_standardized_metric("rnd_ratio", "연구개발", "Research And Development") # 임의 키

            # R&D는 수치가 없는 경우가 많으므로 직접 계산 보강
            if rnd_val is None or rnd_val == 0:
                try:
                    rnd_ttm = t.quarterly_financials.loc['Research And Development'].iloc[:4].sum()
                    rev_ttm = t.quarterly_financials.loc['Total Revenue'].iloc[:4].sum()
                    rnd_val = (rnd_ttm / rev_ttm * 100) if rev_ttm > 0 else 0
                except: rnd_val = 0

            return {
                "rnd_ratio": rnd_val,
                "gross_margin": info.get("grossMargins", 0) * 100,
                "operating_margin": op_margin if op_margin is not None else 0,
                "cfo_margin": cfo_margin if cfo_margin is not None else 0,
                "fcf_yield": (info.get("freeCashflow", 0) / info.get("marketCap", 1) * 100) if info.get("marketCap") else 0
            }
        except Exception as e:
            print(f"[Aggregator] Unit Correction Error: {e}")
            return {}

    def _fetch_choicestock(self):
        try:
            scraper = ChoiceStockScraper()
            return scraper.get_financial_data(self.ticker)
        except:
            return None