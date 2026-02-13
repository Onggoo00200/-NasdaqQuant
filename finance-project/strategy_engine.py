from abc import ABC, abstractmethod
import pandas as pd
import numpy as np

class Strategy(ABC):
    """
    모든 전략의 기본이 되는 추상 클래스
    """
    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        """
        데이터프레임을 받아 매수(1), 매도(-1), 관망(0) 시그널 시리즈를 반환해야 함.
        """
        pass

class GoldenCrossStrategy(Strategy):
    def __init__(self, short_window=5, long_window=20):
        self.short_window = short_window
        self.long_window = long_window

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        # 데이터 로더에서 이미 MA 컬럼이 생성되었다고 가정하거나, 없으면 계산
        # 안전을 위해 컬럼 확인 후 계산
        close = df['Close']
        ma_short = df.get(f'MA{self.short_window}', close.rolling(window=self.short_window).mean())
        ma_long = df.get(f'MA{self.long_window}', close.rolling(window=self.long_window).mean())
        
        signals = pd.Series(0, index=df.index)
        
        # 골든크로스: 단기 이평선이 장기 이평선보다 높을 때 매수 상태 유지 (Trend Following)
        # 1: 매수 유지, 0: 매도/관망
        # 여기서는 간단히 Cross 조건보다는 상태 기반(Position) 시그널 생성
        signals[ma_short > ma_long] = 1
        signals[ma_short <= ma_long] = 0 # 데드크로스 시 청산
        
        return signals

class RSIStrategy(Strategy):
    def __init__(self, lower=30, upper=70):
        self.lower = lower
        self.upper = upper

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        # RSI 컬럼이 없으면 직접 계산하지 않고 에러 처리 또는 0 반환 (데이터 로더 의존)
        if 'RSI' not in df.columns:
            raise ValueError("RSI column is missing. Please run add_indicators() first.")
        
        rsi = df['RSI']
        signals = pd.Series(0, index=df.index)
        
        # Mean Reversion 전략
        # RSI < lower (과매도) -> 매수
        # RSI > upper (과매수) -> 매도 (청산)
        # 그 외 구간 -> 기존 포지션 유지 (이 부분은 백테스터 로직에 따라 다르지만, 여기선 간단히 시그널만 정의)
        
        # 벡터 연산으로 신호 생성 (1: 매수 진입, -1: 매도 청산, 0: 유지)
        # 하지만 Backtester가 1(보유) vs 0(미보유)를 원하므로 상태를 추적해야 함.
        # 벡터화된 상태 유지를 위해 numpy where 사용 불가 (이전 상태 의존). 
        # Pandas 로직으로 '진입'과 '청산' 이벤트만 마킹 후 ffill로 채움.
        
        buy_signal = (rsi < self.lower)
        sell_signal = (rsi > self.upper)
        
        # 시그널 통합
        # 1: 매수, -1: 매도, NaN: 변화 없음
        temp_signals = pd.Series(np.nan, index=df.index)
        temp_signals[buy_signal] = 1
        temp_signals[sell_signal] = 0 # 0은 포지션 없음
        
        # 앞의 신호를 채워서 현재 상태(Position) 결정
        signals = temp_signals.ffill().fillna(0)
        
        return signals

class CompositeStrategy(Strategy):
    def __init__(self, strategies: list, mode='AND'):
        self.strategies = strategies
        self.mode = mode.upper()

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        if not self.strategies:
            return pd.Series(0, index=df.index)
        
        # 각 전략의 시그널 수집 (DataFrame 형태)
        signals_df = pd.DataFrame({
            f'strat_{i}': s.generate_signals(df) 
            for i, s in enumerate(self.strategies)
        })
        
        if self.mode == 'AND':
            # 모든 전략이 1(매수)일 때만 최종 1
            final_signal = signals_df.all(axis=1).astype(int)
        elif self.mode == 'OR':
            # 하나라도 1이면 최종 1
            final_signal = signals_df.any(axis=1).astype(int)
        else:
            raise ValueError(f"Unsupported mode: {self.mode}")
            
        return final_signal

class Backtester:
    def __init__(self, initial_capital=1_000_000):
        self.initial_capital = initial_capital
        
    def run(self, df: pd.DataFrame, strategy: Strategy):
        """
        벡터 연산 기반 백테스팅 실행
        """
        # 원본 데이터 보존을 위해 복사
        backtest_df = df.copy()
        
        # 1. 전략 시그널 생성 (0: 관망, 1: 보유)
        backtest_df['signal'] = strategy.generate_signals(backtest_df)
        
        # 2. 포지션 설정 (Look-ahead Bias 방지)
        # 당일(t)의 신호 보고, 익일(t+1) 시가(Open)에 진입/청산
        # position[t] = signal[t-1]
        backtest_df['position'] = backtest_df['signal'].shift(1).fillna(0)
        
        # 3. 수익률 계산 (Open-to-Open Return)
        # t일 Open에 진입해서 t+1일 Open까지 보유했을 때의 수익률
        # Return[t] = (Open[t+1] - Open[t]) / Open[t]
        # Strategy Return[t] = Position[t] * Return[t]
        backtest_df['open_return'] = backtest_df['Open'].pct_change().shift(-1) # 한 칸 당겨서 t일의 수익률로 매칭
        backtest_df['strategy_return'] = backtest_df['position'] * backtest_df['open_return']
        
        # 결측치 제거 (첫날, 마지막날 등)
        backtest_df.dropna(subset=['strategy_return'], inplace=True)
        
        # 4. 성과 지표 계산
        
        # 누적 수익률 곡선 (Equity Curve)
        backtest_df['equity_curve'] = (1 + backtest_df['strategy_return']).cumprod()
        
        # 총 수익률
        total_return = backtest_df['equity_curve'].iloc[-1] - 1
        
        # MDD (Maximum Drawdown)
        running_max = backtest_df['equity_curve'].cummax()
        drawdown = (backtest_df['equity_curve'] - running_max) / running_max
        mdd = drawdown.min()
        
        # 승률 (Win Rate) 계산 - 거래(Trade) 단위
        # 포지션이 0 -> 1 로 바뀌는 구간(진입)부터 1 -> 0 (청산)까지를 하나의 거래로 간주
        backtest_df['trade_id'] = (backtest_df['position'].diff() != 0).cumsum()
        # 포지션을 보유하고 있는 구간(1)만 필터링하여 trade_id별로 그룹화
        trades = backtest_df[backtest_df['position'] == 1].groupby('trade_id')['strategy_return'].apply(lambda x: (1 + x).prod() - 1)
        
        win_count = (trades > 0).sum()
        total_trades = len(trades)
        win_rate = win_count / total_trades if total_trades > 0 else 0.0

        return {
            "total_return": total_return,
            "mdd": mdd,
            "win_rate": win_rate,
            "total_trades": total_trades,
            "final_equity": self.initial_capital * (1 + total_return),
            "equity_curve": backtest_df['equity_curve'] # 시각화를 위해 필요 시 사용
        }

if __name__ == "__main__":
    # 간단 테스트
    from data_loader import fetch_data, add_indicators
    
    ticker = "AAPL"
    print(f"Running backtest for {ticker}...")
    
    df = fetch_data(ticker)
    df = add_indicators(df)
    
    # 전략 설정: 골든크로스와 RSI 과매도를 동시에 만족할 때 매수 (Composite AND)
    strat_gc = GoldenCrossStrategy()
    strat_rsi = RSIStrategy(lower=40, upper=80) # 테스트를 위해 범위 조정
    composite_strat = CompositeStrategy([strat_gc, strat_rsi], mode='AND')
    
    engine = Backtester()
    results = engine.run(df, composite_strat)
    
    print("\n[Backtest Results]")
    print(f"Total Return: {results['total_return']*100:.2f}%")
    print(f"MDD: {results['mdd']*100:.2f}%")
    print(f"Win Rate: {results['win_rate']*100:.2f}% ({int(results['win_rate'] * results['total_trades'])}/{results['total_trades']})")
    print(f"Final Capital: ${results['final_equity']:,.2f}")
