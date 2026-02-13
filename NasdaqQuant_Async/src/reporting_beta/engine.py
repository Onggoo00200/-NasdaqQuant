import asyncio
import sys
import io

# 한글 깨짐 방지: 표준 출력을 UTF-8로 설정
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from .aggregator import DataAggregator
from .quant_logic import QuantLogic
from .llm_reporter import LLMReporter

class BetaReportingEngine:
    def __init__(self):
        self.quant_logic = QuantLogic()
        self.llm_reporter = LLMReporter()

    async def generate_markdown_report(self, ticker: str):
        # 1. 데이터 수집
        aggregator = DataAggregator(ticker)
        context = await aggregator.collect_all()
        
        # 2. 알고리즘 기반 인사이트 해석 (고도화된 로직)
        context = self.quant_logic.analyze(context)
        
        # 3. LLM을 통한 내러티브 생성
        narrative = await self.llm_reporter.write_report(context)
        
        # 4. 최종 리포트 조립
        breakdown = context.insights.get('score_breakdown', {})
        breakdown_text = ""
        for label, data in breakdown.items():
            breakdown_text += f"- **{label}**: {data['score']:.1f}/{data['max']} ({data['reason']})\n"

        report = f"""
# [Beta] {ticker} Investment Narrative Report
---
## 🖋 Analyst Narrative
{narrative}

---
## 🎯 Alpha Score Breakdown (산출 근거)
{breakdown_text}
### 🏆 Total Alpha Score: {context.insights.get('final_quant_score', '0.0/100')}

---
## 📊 Deep Tech Analysis (Quant Insights)
- **Summary:** {context.insights.get('strategic_summary', 'N/A')}
- **Growth Quality:** {context.insights.get('growth_quality', 'N/A')}
- **Profit Trust:** {context.insights.get('profit_trust', 'N/A')}

---
## 📉 Core Metrics
- **Z-Score (Valuation):** {context.valuation_metrics.get('z_score', 0):.2f}
- **Rule of 40 (Growth):** {context.valuation_metrics.get('rule_of_40', 0):.1f}%
- **Gross Margin:** {context.metadata.get('gross_margin', 0):.1f}%
- **R&D Ratio:** {context.metadata.get('rnd_ratio', 0):.1f}%

*본 리포트는 퀀트 알고리즘의 상세 근거를 바탕으로 자동 생성되었습니다.*
"""
        return report

async def test_beta_report(ticker="NVDA"):
    engine = BetaReportingEngine()
    report = await engine.generate_markdown_report(ticker)
    
    # 파일로 저장 (한글 깨짐 방지)
    filename = f"report_{ticker}.md"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(report)
    
    print(f"\n✅ 리포트가 성공적으로 생성되었습니다: {filename}")
    print("-" * 50)
    print(report)

if __name__ == "__main__":
    asyncio.run(test_beta_report())
