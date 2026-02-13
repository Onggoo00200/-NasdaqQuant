import asyncio
import pandas as pd
import yfinance as yf
import sys
import os

# 현재 디렉토리를 경로에 추가하여 src 모듈 인식
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.indicators import calculate_indicators
from src.engine.optimizer import optimize_strategy_async

# 테스트할 종목 리스트
TICKERS = ["QQQ", "TQQQ", "NVDA", "TSLA", "AAPL"]

# 최적화할 파라미터 그리드
PARAM_GRID = {
    'AdaptiveDonchian': [{}], 
    'Supertrend': [{}],
    'Ichimoku': [{}],
    'LinRegSlope': [{'threshold': 0.2}, {'threshold': 0.3}],
    'TTMSqueeze': [{}],
    'CrabelORB': [{}],
    'LarryWilliamsVBO': [{'k': 0.5}, {'k': 0.4}, {'k': 0.6}],
    'ConnorsRSI2': [{'rsi_limit': 5}, {'rsi_limit': 10}],
    'WilliamsRZScore': [{}],
    'MAEnvelopes': [{}],
    'VWAPMFI': [{}],
    'AnchoredVWAP': [{}],
    'OBVDivergence': [{}]
}

async def process_ticker(ticker):
    """단일 종목 처리 파이프라인"""
    print(f"[{ticker}] 데이터 다운로드 중...")
    try:
        # 1. 데이터 다운로드 (스윙 트레이딩을 위해 3년치 일봉 데이터 수집)
        df = yf.download(ticker, period="3y", interval="1d", progress=False)
        
        if df.empty:
            print(f"[{ticker}] 데이터 없음.")
            return None
        
        # yfinance 최신 버전 MultiIndex 컬럼 처리
        if isinstance(df.columns, pd.MultiIndex):
             # ('Close', 'AAPL') -> 'Close'
             df.columns = df.columns.get_level_values(0)

        # 2. 지표 계산
        df = calculate_indicators(df)
        
        # 3. 전략 최적화
        results = await optimize_strategy_async(df, PARAM_GRID)
        
        if not results:
            print(f"[{ticker}] 유효한 전략 결과 없음.")
            return None
            
        best = results[0] # 1위 전략
        
        return {
            'Ticker': ticker,
            'Best Strategy': best['strategy'],
            'Params': str(best['params']),
            'CAGR': f"{best['cagr']*100:.2f}%",
            'MDD': f"{best['mdd']*100:.2f}%",
            'Trades': best['num_trades'],
            'RoMaD Score': f"{best['score']:.4f}"
        }
        
    except Exception as e:
        print(f"[{ticker}] 처리 중 오류: {e}")
        import traceback
        traceback.print_exc()
        return None

async def main():
    print(f"🚀 NasdaqQuant_Async 시스템 가동... (대상: {len(TICKERS)}종목)")
    
    tasks = [process_ticker(ticker) for ticker in TICKERS]
    results = await asyncio.gather(*tasks)
    
    # 결과 정리 및 출력
    final_results = [r for r in results if r is not None]
    
    if final_results:
        df_res = pd.DataFrame(final_results)
        print("\n📊 [최적화 결과 리포트]")
        try:
            print(df_res.to_markdown(index=False))
        except ImportError:
            print(df_res.to_string(index=False))
    else:
        print("결과가 없습니다.")

if __name__ == "__main__":
    # Windows asyncio 정책 설정 (ProactorEventLoop 권장)
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
