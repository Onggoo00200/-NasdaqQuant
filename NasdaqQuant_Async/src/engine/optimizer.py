import asyncio
import pandas as pd
import numpy as np
from concurrent.futures import ProcessPoolExecutor
from typing import List, Dict, Any
import math

# 전략 클래스들 임포트
from src.strategies.trend_strategies import AdaptiveDonchian, SupertrendStrategy, IchimokuStrategy, LinRegSlopeStrategy
from src.strategies.volatility_strategies import TTMSqueeze, CrabelORB, LarryWilliamsVBO
from src.strategies.mean_reversion import ConnorsRSI2, WilliamsRZScore, MAEnvelopes
from src.strategies.volume_strategies import VWAPMFI, AnchoredVWAPSupport, OBVDivergence

# 전략 매핑
STRATEGY_MAP = {
    'AdaptiveDonchian': AdaptiveDonchian,
    'Supertrend': SupertrendStrategy,
    'Ichimoku': IchimokuStrategy,
    'LinRegSlope': LinRegSlopeStrategy,
    'TTMSqueeze': TTMSqueeze,
    'CrabelORB': CrabelORB,
    'LarryWilliamsVBO': LarryWilliamsVBO,
    'ConnorsRSI2': ConnorsRSI2,
    'WilliamsRZScore': WilliamsRZScore,
    'MAEnvelopes': MAEnvelopes,
    'VWAPMFI': VWAPMFI,
    'AnchoredVWAP': AnchoredVWAPSupport,
    'OBVDivergence': OBVDivergence
}

def backtest_engine(df: pd.DataFrame, strategy_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    [CPU-Bound] 단일 전략 시뮬레이션 및 성과 계산.
    ProcessPoolExecutor에서 실행됨.
    """
    try:
        # 1. 전략 인스턴스화
        strat_cls = STRATEGY_MAP.get(strategy_name)
        if not strat_cls:
            return {'error': f"Unknown strategy: {strategy_name}", 'status': 'failed'}
        
        if params:
            strategy = strat_cls(**params)
        else:
            strategy = strat_cls()
            
        # 2. 신호 생성
        # 데이터프레임 복사본 사용 (병렬 처리 안전성)
        sim_df = df.copy()
        sim_df = strategy.apply(sim_df)
        
        # 3. 포지션 및 수익률 계산
        # 1(Entry) -> 1, -1(Exit) -> 0
        signals = sim_df['signal'].replace(0, np.nan)
        signals = signals.replace(-1, 0)
        sim_df['position'] = signals.ffill().fillna(0)
        
        # 수익률: 익일 시가 진입 가정이 정확하나, 일봉 데이터상 Close-to-Close 계산 후 Position Shift
        # Position[t]가 1이면 t+1일 수익률을 가져감
        sim_df['daily_ret'] = sim_df['Close'].pct_change()
        sim_df['strategy_ret'] = sim_df['position'].shift(1) * sim_df['daily_ret']
        
        # 4. 성과 지표
        equity_curve = (1 + sim_df['strategy_ret'].fillna(0)).cumprod()
        
        if equity_curve.empty:
             return {'status': 'failed', 'error': 'No data'}

        total_return = equity_curve.iloc[-1] - 1
        
        # CAGR (연환산)
        days = (sim_df.index[-1] - sim_df.index[0]).days
        cagr = ((1 + total_return) ** (365 / max(days, 1))) - 1
        
        # MDD
        running_max = equity_curve.cummax()
        drawdown = (equity_curve - running_max) / running_max
        mdd = drawdown.min()
        
        # Trade Count (진입 횟수)
        # Position 0 -> 1 로 바뀔 때가 진입
        pos_diff = sim_df['position'].diff()
        trades = len(pos_diff[pos_diff == 1])
        
        return {
            'strategy': strategy_name,
            'params': params,
            'cagr': cagr,
            'mdd': mdd,
            'total_return': total_return,
            'num_trades': trades,
            'status': 'success'
        }
        
    except Exception as e:
        return {
            'strategy': strategy_name,
            'params': params,
            'error': str(e),
            'status': 'failed'
        }

def calculate_romad_score(result: Dict[str, Any], total_days: int) -> float:
    """
    RoMaD 기반 스코어링 + 거래 빈도 스타일 제약
    """
    if result.get('status') != 'success':
        return -999.0
        
    cagr = result['cagr']
    mdd = abs(result['mdd']) if result['mdd'] != 0 else 0.01
    trades = result['num_trades']
    
    # RoMaD (수익/리스크 비율)
    romad = cagr / mdd
    
    # 거래 빈도 계산 (주당 평균 거래 횟수)
    weeks = total_days / 7
    trades_per_week = trades / weeks if weeks > 0 else 0
    
    # Weights
    w1 = 0.7
    w2 = 0.3
    raw_score = (w1 * romad) + (w2 * math.log(max(1, trades)))
    
    # --- 스타일 제약 (Style Constraints) ---
    penalty = 1.0
    
    # 1. 과소 거래 페널티 (신뢰도 부족)
    if trades < 10: 
        penalty *= 0.3
    
    # 2. 과잉 거래 페널티 (사용자 요청: 주 4회 초과 금지)
    if trades_per_week > 4.0:
        # 주 4회를 넘어서면 점수를 대폭 삭감 (데일리 트레이딩 배제)
        penalty *= 0.1 
    
    return raw_score * penalty

async def optimize_strategy_async(df: pd.DataFrame, param_grid: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """
    [Main Orchestrator] 비동기 최적화 엔진
    """
    loop = asyncio.get_running_loop()
    tasks = []
    
    # 데이터 전체 일수 계산
    total_days = (df.index[-1] - df.index[0]).days
    
    # ProcessPoolExecutor로 병렬 처리
    with ProcessPoolExecutor() as pool:
        for strat_name, params_list in param_grid.items():
            for params in params_list:
                task = loop.run_in_executor(
                    pool,
                    backtest_engine,
                    df,
                    strat_name,
                    params
                )
                tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
    # 스코어링
    scored_results = []
    for res in results:
        score = calculate_romad_score(res, total_days)
        res['score'] = score
        scored_results.append(res)
        
    # 정렬 (높은 점수 순)
    scored_results.sort(key=lambda x: x['score'], reverse=True)
    
    return scored_results
