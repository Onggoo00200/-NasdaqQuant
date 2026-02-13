from dataclasses import dataclass, field
from typing import Dict, Any, Optional
import pandas as pd

@dataclass
class BetaReportContext:
    """
    베타 리포트 생성을 위한 통합 데이터 컨텍스트.
    모든 모듈의 데이터가 이 곳으로 집결되지만, 기존 모듈과는 독립적으로 존재합니다.
    """
    ticker: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # [1] 정량 데이터 (from yfinance / internal engine)
    price_df: Optional[pd.DataFrame] = None
    valuation_metrics: Dict[str, Any] = field(default_factory=dict) # Z-score, Rule of 40 등
    
    # [2] 정성 데이터 (from ChoiceStock)
    choice_stock_data: Dict[str, Any] = field(default_factory=dict) # 스크래핑된 원본/가공 데이터
    
    # [3] 전략 분석 데이터 (from Backtester/Optimizer)
    best_strategy_results: Dict[str, Any] = field(default_factory=dict)
    
    # [4] 해석된 인사이트 (Translator가 채울 공간)
    insights: Dict[str, str] = field(default_factory=dict)
