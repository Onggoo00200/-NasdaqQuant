import pandas as pd
import numpy as np

class MacroChartAgent:
    def __init__(self, df):
        """
        초기화: 전처리된 FRED 데이터프레임을 입력받습니다.
        df: plot_dashboard 함수에 들어가는 데이터와 동일해야 합니다.
        """
        self.df = df
        self.latest = df.iloc[-1] # 가장 최근 데이터
        self.prev = df.iloc[-2] if len(df) > 1 else df.iloc[-1] # 직전 데이터 (추세 확인용)
        # 6개월 전 데이터 (중기 추세 확인용)
        self.prev_6m = df.iloc[-6] if len(df) > 6 else df.iloc[0]
        self.timestamp = df.index[-1].strftime('%Y-%m-%d')

    def analyze_panel_1_monetary(self):
        """
        [Panel 1] 금리와 인플레이션 해석
        보고서 3.1(금리) & 4.2(국면 탐지) 논리 적용
        """
        fed_rate = self.latest['FedFunds']
        treasury_10y = self.latest['10Y_Treasury']
        cpi = self.latest.get('Inflation_YoY', self.latest.get('CPI', 0))
        
        # 논리 1: 실질 금리 (Real Interest Rate) - 유동성 비용 측정
        real_rate_proxy = fed_rate - cpi
        
        # 논리 2: 수익률 곡선 (Yield Curve) - 경기 침체 선행 지표
        is_inverted = treasury_10y < fed_rate
        
        analysis = f"**[Panel 1: 통화 사이클(Monetary Cycle) 진단]**\n"
        analysis += f"- 기준금리: {fed_rate:.2f}% | 10년물 국채: {treasury_10y:.2f}% | CPI: {cpi:.2f}%\n"
        
        # 실질 금리 해석
        if real_rate_proxy > 0:
            analysis += f"  -> [긴축 환경]: 실질 금리가 플러스({real_rate_proxy:.2f}%)입니다. 연준의 긴축 강도가 높아 자산 밸류에이션 확장이 제한적입니다.\n"
        else:
            analysis += f"  -> [완화 환경]: 실질 금리가 마이너스({real_rate_proxy:.2f}%)입니다. 현금의 구매력이 떨어지므로 인플레이션 헷지를 위한 자산(기술주 등) 선호가 강해집니다.\n"
            
        # 수익률 곡선 해석
        if is_inverted:
            analysis += f"  -> [⚠️ 경기 침체 경고]: 장단기 금리가 역전되었습니다(Spread: {treasury_10y - fed_rate:.2f}%p). 채권 시장은 향후 '금리 인하'와 '경기 둔화'를 강력하게 선반영하고 있습니다.\n"
        else:
            analysis += "  -> [정상 곡선]: 장단기 금리가 정상 배열 상태입니다. 당장 임박한 경기 침체 신호는 없습니다.\n"
        
        return analysis

    def analyze_panel_2_growth(self):
        """
        [Panel 2] 유동성과 기업 이익 해석
        보고서 2.1(4계절 이론) & 3.2(유동성) 논리 적용
        """
        m2_yoy = self.latest.get('M2_YoY', self.latest.get('M2_Liquidity', 0))
        profit_yoy = self.latest.get('Profits_YoY', self.latest.get('Corp_Profits', 0))
        
        analysis = f"\n**[Panel 2: 성장 동력(Growth Engine) 분석]**\n"
        analysis += f"- M2 유동성 증감률: {m2_yoy:.2f}% | 기업이익 증감률: {profit_yoy:.2f}%\n"
        
        # 보고서 2.1: 우라카미 구니오의 4계절 국면 판별 상세 로직
        if profit_yoy > 0 and profit_yoy > m2_yoy:
            analysis += "  -> **[☀️ 실적 장세 (Summer)]**: 유동성(M2)보다 '기업 실적'이 시장 상승을 주도하고 있습니다.\n"
            analysis += "     주가의 상승 동력이 '꿈'에서 '숫자(이익)'로 이동했습니다. 펀더멘털이 가장 견고한 시기입니다.\n"
            
        elif m2_yoy > 0 and profit_yoy < 0:
            analysis += "  -> **[🌱 금융 장세 (Spring)]**: 기업 실적은 마이너스지만, 풍부한 유동성(M2 증가)이 주가를 밀어올리고 있습니다.\n"
            analysis += "     전형적인 '유동성 랠리' 구간으로, 적자 성장주가 높은 멀티플을 받는 경향이 있습니다.\n"
            
        elif m2_yoy < 0 and profit_yoy > 0:
            analysis += "  -> **[🍂 역금융 장세 (Autumn)]**: 실적은 여전히 좋으나, 유동성이 축소(M2 감소)되고 있습니다.\n"
            analysis += "     금리 상승으로 인한 '멀티플 축소(De-rating)'가 발생하므로 밸류에이션 부담이 큰 주식은 주의해야 합니다.\n"
            
        elif m2_yoy < 0 and profit_yoy < 0:
            analysis += "  -> **[❄️ 역실적 장세 (Winter)]**: 유동성과 실적이 모두 위축되는 '복합 불황' 구간입니다.\n"
            analysis += "     주식 시장의 하락 압력이 가장 크며, 보수적인 자산 배분이 필수적입니다.\n"
        
        else:
            analysis += "  -> [전환기]: 유동성과 실적 지표가 혼재되어 있어 추세 전환을 모색하는 구간입니다.\n"
            
        return analysis

    def analyze_panel_3_risk(self):
        """
        [Panel 3] 리스크 지표 해석
        보고서 3.4(하이일드 스프레드 & RORO) 논리 적용
        """
        hy_spread = self.latest.get('HY_Spread', 0)
        # 추세 확인: 현재 스프레드가 6개월 전보다 확대되었는가?
        prev_hy = self.prev_6m.get('HY_Spread', 0)
        spread_widening = hy_spread > prev_hy
        
        threshold_critical = 5.0
        threshold_warning = 4.0
        
        analysis = f"\n**[Panel 3: 신용 리스크(Risk Indicators) 정밀 점검]**\n"
        analysis += f"- 하이일드 스프레드: {hy_spread:.2f}% (6개월 전: {prev_hy:.2f}%)\n"
        
        if hy_spread > threshold_critical:
            analysis += "  -> **[🚨 CRITICAL WARNING]**: 스프레드가 임계치(5.0%)를 돌파했습니다. 시스템 리스크가 고조되는 'Risk-Off' 국면입니다.\n"
            analysis += "     주식 시장과의 역상관관계가 극대화되므로, 주식 비중을 축소하고 현금/국채를 확보하는 방어 전략이 시급합니다.\n"
            
        elif hy_spread > threshold_warning or spread_widening:
            analysis += "  -> **[⚠️ Caution]**: 아직 위기 단계는 아니나, 신용 스프레드가 확대 추세에 있습니다. 기업들의 자금 조달 비용이 증가하고 있어 한계 기업(좀비 기업)의 파산 위험이 커집니다.\n"
            
        else:
            analysis += "  -> **[✅ Stable]**: 스프레드가 안정적인 낮은 수준을 유지하고 있습니다. 투자자들의 위험 선호 심리(Risk-On)가 살아있어 주식 투자에 우호적인 환경입니다.\n"
            
        return analysis

    def generate_nasdaq_strategy(self):
        """
        종합 나스닥 전략 제언
        보고서 6장: 매크로 국면과 나스닥 펀더멘털 분석의 통합 전략
        """
        profit_yoy = self.latest.get('Profits_YoY', 0)
        hy_spread = self.latest.get('HY_Spread', 0)
        fed_trend = "UP" if self.latest['FedFunds'] >= self.prev['FedFunds'] else "DOWN"
        
        strategy = "**[종합: 나스닥 펀더멘털 투자 전략 (Action Plan)]**\n"
        
        if hy_spread > 5.0:
            strategy += "❄️ **[국면: 역실적장세/위기]**\n"
            strategy += "   - **핵심 지표:** 현금 보유량(Cash Burn Rate), 유동비율\n"
            strategy += "   - **Action:** 펀더멘털보다 생존이 우선입니다. 부채가 많거나 추가 자금 조달이 필요한 적자 기술주는 즉시 매도하십시오.\n"
            strategy += "     현금 흐름이 확실한 독점적 빅테크(Big Tech)로 포트폴리오를 압축하거나 현금 비중을 극대화해야 합니다.\n"
            
        elif profit_yoy < 0 and fed_trend == "DOWN":
            strategy += "🌱 **[국면: 금융장세 (Spring)]**\n"
            strategy += "   - **핵심 지표:** 매출 성장률(Revenue Growth), PSR\n"
            strategy += "   - **Action:** 유동성이 공급되고 할인율이 낮아지는 시기입니다. 현재 적자라도 성장성이 높은 기업(High Beta)이 가장 높은 수익률을 줍니다.\n"
            strategy += "     전통적 밸류에이션(PER)을 무시하고 과감하게 성장주 비중을 확대하십시오.\n"
            
        elif profit_yoy > 0 and hy_spread < 4.0:
            strategy += "☀️ **[국면: 실적장세 (Summer)]**\n"
            strategy += "   - **핵심 지표:** EPS 성장률, Rule of 40, PEG Ratio\n"
            strategy += "   - **Action:** 단순 기대감이 아닌 '숫자'가 중요합니다. 매출과 이익이 동반 성장하는 우량 기술주(Quality Tech)를 매수하십시오.\n"
            strategy += "     'Rule of 40' 점수가 높고 실적 서프라이즈를 기록하는 기업이 주도주가 됩니다.\n"
            
        elif profit_yoy > 0 and fed_trend == "UP":
            strategy += "🍂 **[국면: 역금융장세 (Autumn)]**\n"
            strategy += "   - **핵심 지표:** P/FCF(잉여현금흐름), 배당 수익률\n"
            strategy += "   - **Action:** 금리 상승으로 멀티플이 축소되는 시기입니다. 듀레이션이 긴 고성장주는 피해야 합니다.\n"
            strategy += "     밸류에이션이 낮고 현금 창출력이 뛰어난 '가치 기술주' 위주로 방어적인 포트폴리오를 구축하십시오.\n"
            
        else:
            strategy += "🌫️ **[국면: 전환기 (Transition)]**\n"
            strategy += "   - 지표들이 혼재되어 있습니다. 매크로 방향성이 명확해질 때까지 보수적으로 접근하며 개별 기업의 이슈에 집중하십시오.\n"
            
        return strategy

def generate_macro_report(macro_data):
    """
    대시보드 통합용 리포트 생성 함수
    """
    if macro_data is None or macro_data.empty:
        return "매크로 데이터를 분석할 수 없습니다."
    
    agent = MacroChartAgent(macro_data)
    
    report = f"### 🏛️ 매크로 퀀트 대시보드 해석 리포트 ({agent.timestamp})\n\n"
    report += agent.analyze_panel_1_monetary() + "\n"
    report += agent.analyze_panel_2_growth() + "\n"
    report += agent.analyze_panel_3_risk() + "\n"
    report += "---\n"
    report += agent.generate_nasdaq_strategy()
    
    return report
