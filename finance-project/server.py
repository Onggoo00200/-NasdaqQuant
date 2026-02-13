from mcp.server.fastmcp import FastMCP
import threading
import uuid
import time
import json
import os
import pandas as pd
import numpy as np
import yfinance as yf
from fredapi import Fred
from datetime import datetime, timedelta
import random

# 기존 NasdaqQuant_Async 모듈 경로 추가
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "NasdaqQuant_Async"))
from src.indicators import calculate_indicators
from src.engine.optimizer import backtest_engine, calculate_romad_score

# FastMCP 서버 인스턴스
mcp = FastMCP("Nasdaq-Master-Agent")

JOBS = {}
REGISTRY_FILE = "strategy_registry.json"
FRED_API_KEY = "3662881107b1dc7e444adf1dcc698477"

# --- [Core] Strategy Registry System ---
def load_registry():
    if os.path.exists(REGISTRY_FILE):
        try:
            with open(REGISTRY_FILE, 'r', encoding='utf-8') as f: return json.load(f)
        except: return {}
    return {}

def save_to_registry(ticker, strategy_data):
    registry = load_registry()
    registry[ticker.upper()] = {**strategy_data, "updated_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    with open(REGISTRY_FILE, 'w', encoding='utf-8') as f: json.dump(registry, f, indent=2, ensure_ascii=False)

def get_registered_strategy(ticker):
    return load_registry().get(ticker.upper())

# --- [Advanced] Genetic Alpha Search Engine ---
class GeneticAlphaSearch:
    def __init__(self, df, population_size=10, generations=3):
        self.df = df
        self.pop_size = population_size
        self.total_days = (df.index[-1] - df.index[0]).days
        self.gene_pool = {
            'LarryWilliamsVBO': {'k': [0.4, 0.5, 0.6, 0.7, 0.8]},
            'ConnorsRSI2': {'rsi_limit': [5, 10, 15, 20]},
            'Supertrend': {'multiplier': [3.0, 3.5, 4.0]},
            'LinRegSlope': {'threshold': [0.1, 0.2, 0.3]}
        }
    def evolve(self):
        best_res, best_score = None, -999
        for _ in range(20):
            strat = random.choice(list(self.gene_pool.keys()))
            params = {k: random.choice(v) for k, v in self.gene_pool[strat].items()}
            res = backtest_engine(self.df, strat, params)
            score = calculate_romad_score(res, self.total_days)
            if score > best_score: best_score, best_res = score, res
        return best_res, best_score

# --- [Core] Tech Valuation Engine ---
class TechValuationEngine:
    def __init__(self, ticker):
        self.ticker_symbol = ticker
        self.ticker = yf.Ticker(ticker)
        self.price_data, self.financials = None, None
    def fetch_data(self):
        try:
            hist = self.ticker.history(period="5y")
            if hist.empty: return None
            hist.reset_index(inplace=True)
            if hist['Date'].dt.tz is not None: hist['Date'] = hist['Date'].dt.tz_localize(None)
            self.price_data = hist
            q_inc = self.ticker.quarterly_income_stmt.T.sort_index()
            q_bal = self.ticker.quarterly_balance_sheet.T.sort_index()
            q_cf = self.ticker.quarterly_cashflow.T.sort_index()
            fin_df = pd.DataFrame(index=q_inc.index)
            def get_col(df, keywords):
                for k in keywords: 
                    if k in df.columns: return df[k]
                return pd.Series(0, index=df.index)
            fin_df['Revenue'] = get_col(q_inc, ['Total Revenue', 'Revenue'])
            fin_df['EBITDA'] = get_col(q_inc, ['EBITDA', 'Normalized EBITDA'])
            fin_df['EBIT'] = get_col(q_inc, ['EBIT', 'Operating Income'])
            fin_df['Net Income'] = get_col(q_inc, ['Net Income'])
            fin_df['Total Debt'] = get_col(q_bal, ['Total Debt'])
            fin_df['Cash'] = get_col(q_bal, ['Cash And Cash Equivalents', 'Cash'])
            fin_df['Shares'] = get_col(q_bal, ['Share Issued', 'Ordinary Shares Number'])
            fin_df['CapEx'] = abs(get_col(q_cf, ['Capital Expenditure']))
            fin_df['CFO'] = get_col(q_cf, ['Operating Cash Flow'])
            fin_df['SBC'] = get_col(q_cf, ['Stock Based Compensation'])
            for col in ['Revenue', 'EBITDA', 'EBIT', 'Net Income', 'CapEx', 'CFO', 'SBC']:
                fin_df[f'{col}_TTM'] = fin_df[col].rolling(window=4, min_periods=1).sum()
            fin_df['Rev_Growth'] = fin_df['Revenue_TTM'].pct_change(4)
            fin_df['FCF_TTM'] = fin_df['CFO_TTM'] - fin_df['CapEx_TTM']
            fin_df['Adj_FCF_TTM'] = fin_df['FCF_TTM'] - fin_df['SBC_TTM']
            fin_df.index = pd.to_datetime(fin_df.index).tz_localize(None) + pd.Timedelta(days=45)
            self.financials = fin_df
            return fin_df
        except: return None
    def compute_valuation_multiples(self):
        if self.financials is None: self.fetch_data()
        if self.financials is None or self.price_data is None: return pd.DataFrame()
        merged = pd.merge_asof(self.price_data.sort_values('Date'), self.financials.resample('D').ffill(), left_on='Date', right_index=True, direction='backward').ffill()
        if 'Shares' not in merged.columns or merged['Shares'].iloc[-1] == 0:
            merged['Shares'] = self.ticker.info.get('sharesOutstanding', 1)
        merged['Market_Cap'] = merged['Close'] * merged['Shares']
        merged['EV'] = merged['Market_Cap'] + merged['Total Debt'] - merged['Cash']
        merged['EV/Sales'] = merged['EV'] / merged['Revenue_TTM']
        merged['EV/EBITDA'] = merged['EV'] / merged['EBITDA_TTM']
        merged['EV/EBIT'] = merged['EV'] / merged['EBIT_TTM']
        merged['PER'] = merged['Market_Cap'] / merged['Net Income_TTM']
        merged['P/FCF'] = merged['Market_Cap'] / merged['FCF_TTM']
        return merged.dropna(subset=['Revenue_TTM'])
    def select_best_metric(self, row):
        rev, ebitda, capex = row.get('Revenue_TTM', 1), row.get('EBITDA_TTM', 0), row.get('CapEx_TTM', 0)
        if ebitda <= 0 or (ebitda/rev) < 0.05: return "EV/Sales", row.get('EV/Sales'), "초기/적자 기업"
        if (capex/rev) > 0.10: return "EV/EBIT", row.get('EV/EBIT'), "자본집약적"
        if row.get('Rev_Growth', 0) < 0.10 and (row.get('FCF_TTM', 0)/rev) > 0.20: return "P/FCF", row.get('P/FCF'), "성숙기 현금창출"
        return "EV/EBITDA", row.get('EV/EBITDA'), "표준 성장주"

# --- Helper Functions ---
def format_number(val):
    if val is None or pd.isna(val): return "N/A"
    try:
        val = float(val)
        if abs(val) >= 1e9: return f"{val/1e9:.2f}B"
        elif abs(val) >= 1e6: return f"{val/1e6:.2f}M"
        return f"{val:,.2f}"
    except: return str(val)

# --- MCP Tools & Exported Functions ---

@mcp.tool()
def get_market_regime() -> str:
    """FRED 데이터를 분석하여 현재 시장 국면을 판단합니다."""
    try:
        fred = Fred(api_key=FRED_API_KEY)
        indpro = fred.get_series('INDPRO')
        cpi = fred.get_series('CPIAUCSL')
        vix = fred.get_series('VIXCLS')
        growth = indpro.pct_change(12).rolling(3).mean()
        inflation = cpi.pct_change(12).rolling(3).mean()
        dg, di = growth.iloc[-1] - growth.iloc[-4], inflation.iloc[-1] - inflation.iloc[-4]
        regime = "RECOVERY"
        if dg > 0 and di < 0: regime = "RECOVERY (회복기)"
        elif dg > 0 and di > 0: regime = "OVERHEAT (과열기)"
        elif dg < 0 and di > 0: regime = "STAGFLATION (스태그플레이션)"
        elif dg < 0 and di < 0: regime = "REFLATION (리플레이션)"
        cvix = vix.iloc[-1]
        if cvix > 30: regime = "PANIC (패닉)"
        return f"🌐 [매크로 국면]\n- 상태: {regime}\n- 성장모멘텀: {dg*100:.2f}%\n- 물가모멘텀: {di*100:.2f}%\n- VIX: {cvix:.2f}"
    except Exception as e: return f"매크로 분석 오류: {str(e)}"

@mcp.tool()
def analyze_tech_valuation(ticker: str) -> str:
    """[최종판] 테크 기업 종합 밸류에이션 분석"""
    engine = TechValuationEngine(ticker)
    df = engine.compute_valuation_multiples()
    if df.empty: return "데이터 부족"
    last = df.iloc[-1]
    m_name, m_val, reason = engine.select_best_metric(last)
    recent = df[df['Date'] >= (df['Date'].max() - timedelta(days=365*2))]
    m_series = recent[m_name].replace([np.inf, -np.inf], np.nan).dropna()
    mean_val, std_val = m_series.mean(), m_series.std()
    z = (m_val - mean_val) / std_val if std_val > 0 else 0
    rev, growth = last.get('Revenue_TTM', 0), last.get('Rev_Growth', 0) * 100
    adj_fcf = last.get('Adj_FCF_TTM', 0)
    r40 = growth + (adj_fcf / rev * 100 if rev else 0)
    erg = last.get('EV/Sales', 0) / growth if growth > 0 else 999
    return f"📊 [{ticker} Valuation]\n1. 지표: {m_name} ({reason})\n2. 현재: {m_val:.2f}x (Z:{z:.2f})\n3. Rule of 40: {r40:.1f}점\n4. ERG: {erg:.2f}\n5. 매출: {format_number(rev)} | Adj-FCF: {format_number(adj_fcf)}"

def _full_optimization_worker(job_id: str, ticker: str):
    try:
        df = yf.download(ticker, period="3y", interval="1d", progress=False)
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df = calculate_indicators(df)
        best_res, best_score = None, -999
        from server import PARAM_GRID
        for s, p_list in PARAM_GRID.items():
            for p in p_list:
                res = backtest_engine(df, s, p)
                score = calculate_romad_score(res, (df.index[-1]-df.index[0]).days)
                if score > best_score: best_score, best_res = score, res
        JOBS[job_id] = {"status": "completed", "result": {**best_res, "score": best_score}}
    except Exception as e: JOBS[job_id] = {"status": "error", "error_msg": str(e)}

@mcp.tool()
def get_optimized_strategy(ticker: str) -> str:
    job_id = str(uuid.uuid4())
    JOBS[job_id] = {"status": "running", "submitted_at": time.time()}
    threading.Thread(target=_full_optimization_worker, args=(job_id, ticker), daemon=True).start()
    return f"Job ID: {job_id}"

@mcp.tool()
def check_backtest_status(job_id: str) -> str:
    job = JOBS.get(job_id)
    if not job: return "ID 없음"
    if job["status"] == "completed": return json.dumps(job["result"], default=str)
    return "진행 중"

PARAM_GRID = {'LarryWilliamsVBO': [{'k': 0.5}, {'k': 0.6}], 'ConnorsRSI2': [{'rsi_limit': 5}, {'rsi_limit': 10}]}

if __name__ == "__main__": mcp.run()
