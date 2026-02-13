from .context import BetaReportContext
import pandas as pd
import numpy as np

class QuantLogic:
    def analyze(self, context: BetaReportContext):
        """
        [Professional Quant Analysis with Score Breakdown]
        각 분석 항목의 점수와 산출 근거를 상세히 기록합니다.
        """
        i = context.insights
        v = context.valuation_metrics
        m = context.metadata
        
        breakdown = {}
        
        # 기본 수치 로드
        rev_g = v.get('rev_growth', 0)
        fcf_m = v.get('adj_fcf_margin', 0)
        cfo_m = v.get('cfo_margin', fcf_m + 5) 
        op_m = m.get('operating_margin', 1) 
        
        # 1. 성장성 점수 (Growth Score) - Max 25
        growth_score = min(25, max(0, rev_g * 0.5))
        breakdown['Growth'] = {
            "score": growth_score,
            "max": 25,
            "reason": f"매출 성장률 {rev_g:.1f}% 기록. " + 
                      ("폭발적 성장이 점수를 견인함" if rev_g > 30 else "완만한 성장세 유지")
        }

        # 2. 수익의 질 (Profit Quality Score) - Max 25
        # 영업이익 대비 영업현금흐름(CFO) 비율 평가
        cfo_m = m.get('cfo_margin')
        
        if cfo_m is None or op_m is None or op_m == 0:
            profit_score = 0
            reason = "데이터 부족: 현금흐름(CFO) 또는 영업이익 지표를 찾을 수 없음"
        else:
            cash_ratio = cfo_m / op_m
            # 현금 전환 비율이 0.8 이상이면 만점
            profit_score = min(25, max(0, cash_ratio * 20)) 
            reason = f"이익의 현금 전환 비율 {cash_ratio:.2f}배. " + \
                     ("수익의 질이 우수함" if cash_ratio > 0.8 else "장부상 이익 대비 현금 흐름 확인 필요")

        breakdown['Profit Quality'] = {
            "score": profit_score,
            "max": 25,
            "reason": reason
        }

        # 3. 기술 투자 효율성 (Tech Efficiency) - Max 25
        rnd_r = m.get('rnd_ratio', 0)
        rnd_eff = rev_g / (rnd_r if rnd_r > 0 else 1)
        tech_score = min(25, max(0, rnd_eff * 5))
        breakdown['Tech Efficiency'] = {
            "score": tech_score,
            "max": 25,
            "reason": f"R&D 투자 대비 매출 기여도 {rnd_eff:.2f}. " +
                      ("투자 효율이 매우 뛰어남" if rnd_eff > 2 else "기술 투자 대비 가시적 성과 대기 중")
        }

        # 4. 가격 매력도 (Valuation Attraction) - Max 25
        z_score = v.get('z_score', 0)
        val_score = min(25, max(0, (1 - z_score) * 12.5))
        breakdown['Valuation'] = {
            "score": val_score,
            "max": 25,
            "reason": f"역사적 주가 위치(Z-Score) {z_score:.2f}. " +
                      ("과거 대비 저평가 구간" if z_score < 0 else "과거 대비 프리미엄 거래 중")
        }

        # 최종 점수 통합
        total_score = sum(item['score'] for item in breakdown.values())
        i['final_quant_score'] = f"{total_score:.1f}/100"
        i['score_breakdown'] = breakdown
        
        # 기존 인사이트 요약도 유지 (LLM용)
        i['strategic_summary'] = f"{breakdown['Growth']['reason']}, {breakdown['Valuation']['reason']}."
        
        return context