from data_loader import fetch_data, add_indicators
from strategy_engine import Backtester, RSIStrategy

def test_rsi_strategy():
    ticker = "ALAB"
    print(f"--- [Test] Running Backtest for {ticker} (RSI 30/70) ---")

    # 1. 데이터 가져오기
    print("1. Fetching data...")
    df = fetch_data(ticker) # 기본값 3년치 사용
    
    if df.empty:
        print(f"Error: No data found for {ticker}.")
        return

    df = add_indicators(df)
    
    # 2. 현재 데이터 요약 (에이전트의 '시장 요약' 기능 시뮬레이션)
    last_price = df['Close'].iloc[-1]
    last_rsi = df['RSI'].iloc[-1]
    print(f"   Current Price: ${last_price:.2f}")
    print(f"   Current RSI: {last_rsi:.2f}")

    # 3. 전략 설정 (RSI 30 이하 매수, 70 이상 매도)
    strategy = RSIStrategy(lower=30, upper=70)
    
    # 4. 백테스트 실행
    print("2. Executing strategy...")
    engine = Backtester(initial_capital=10_000) # 자본금 $10,000 가정
    results = engine.run(df, strategy)
    
    # 5. 결과 리포트
    print("\n[Backtest Report]")
    print(f"Strategy: RSI (Lower 30 / Upper 70)")
    print(f"Period: {results['total_trades']} trades executed")
    print(f"Win Rate: {results['win_rate']*100:.2f}%")
    print(f"Total Return: {results['total_return']*100:.2f}%")
    print(f"MDD (Max Drawdown): {results['mdd']*100:.2f}%")
    print(f"Final Capital: ${results['final_equity']:,.2f}")
    
    # 6. 결과 해석 (에이전트 행동 지침 시뮬레이션)
    if results['mdd'] < -0.20:
        print("\n⚠️ WARNING: This strategy has a high risk (MDD < -20%).")
    else:
        print("\n✅ Risk Check: MDD is within acceptable range.")

if __name__ == "__main__":
    test_rsi_strategy()