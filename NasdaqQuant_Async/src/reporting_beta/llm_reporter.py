import os
import google.generativeai as genai
from dotenv import load_dotenv
from .context import BetaReportContext

# 환경 변수 로드 (.env 파일 지원)
load_dotenv()

class LLMReporter:
    def __init__(self):
        # 환경 변수에서 API 키 로드
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            print("WARNING: GOOGLE_API_KEY가 설정되지 않았습니다. 기본 텍스트 모드로 동작합니다.")
            self.enabled = False
        else:
            genai.configure(api_key=api_key)
            # 가장 표준적인 모델명 사용
            self.model = genai.GenerativeModel('gemini-flash-latest')
            self.enabled = True

    async def write_report(self, context: BetaReportContext):
        """
        전문적인 투자 내러티브를 생성합니다.
        """
        if not self.enabled:
            return "LLM 연동이 비활성화되어 기본 데이터만 제공합니다."

        prompt = f"""
역할: 당신은 20년 경력의 월가 수석 퀀트 애널리스트입니다.
작업: 아래 제공된 '전문적인 데이터 분석 인사이트'를 바탕으로, 투자자에게 보내는 부드러우면서도 날카로운 투자 서신(Letter) 형식의 리포트를 작성하세요.

[분석 대상 종목: {context.ticker}]

[분석 엔진 도출 인사이트]
1. 가치와 가격의 괴리: {context.insights.get('valuation_divergence', '데이터 없음')}
2. 수익의 질적 측면: {context.insights.get('profit_quality', '데이터 없음')}
3. 재무 및 리스크 요인: {context.insights.get('risk_factor', '데이터 없음')}
4. 외부 검증(ChoiceStock) 결과: {context.insights.get('cross_check', '데이터 없음')}

[핵심 수치 정보]
- Rule of 40: {context.valuation_metrics.get('rule_of_40', 0):.1f}%
- Z-Score: {context.valuation_metrics.get('z_score', 0):.2f}

[작성 지침]
- 단순 수치 나열을 지양하고, 지표들 간의 인과관계와 서사를 중심으로 서술하세요.
- 첫 문장은 종목에 대한 강렬한 한 줄 평으로 시작하세요.
- 말투는 전문적이고 신뢰감 있는 한국어를 사용하세요.
- '결론 및 투자 전략' 섹션을 마지막에 포함하세요.
"""
        try:
            # 동기 방식으로 호출 (테스트 환경 안정성 확보)
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"LLM 생성 중 오류 발생: {str(e)}"
