def generate_analyst_report(ticker, val_data):
    """
    valuation.py의 결과 딕셔너리를 받아 리포트 생성.
    ERG 999(역성장)에 대한 전문적인 예외 처리 포함.
    """
    if not val_data:
        return "데이터를 분석할 수 없습니다."

    ticker = ticker.upper()
    m_name = val_data['metric_name']
    m_val = round(val_data['metric_value'], 1)
    m_reason = val_data['metric_reason']
    z_score = round(val_data['z_score'], 1)
    erg = val_data['erg_ratio']
    r40 = round(val_data['rule_of_40'], 1)
    sbc = round(val_data['sbc_ratio'], 1)
    growth = round(val_data['rev_growth'], 1)
    debt = round(val_data['debt_ratio'], 1)

    # 1. 투자 등급 및 ERG 상태 진단
    rating = "중립 (Hold)"
    erg_status_text = ""
    
    if erg >= 999:
        rating = "주의 (Caution)"
        erg_status_text = f"현재 {ticker}는 매출 역성장(YoY {growth}%) 구간에 진입하여 성장 가치 대비 주가를 측정하는 ERG Ratio 산출이 무의미(Meaningless)합니다. "
        erg_status_text += "이는 현재 주가가 실질적 성장이 아닌 시장의 기대감이나 다른 내러티브에 의해 지탱되고 있음을 시사하므로 매우 보수적인 접근이 필요합니다."
    else:
        erg = round(erg, 2)
        if erg < 0.35 and z_score < -0.5: rating = "매수 (Buy)"
        elif erg > 0.6 or z_score > 1.5: rating = "매도 (Sell)"
        
        erg_status_text = f"현재 {ticker}의 ERG Ratio는 {erg}로, "
        if rating == "매수 (Buy)":
            erg_status_text += "성장성 대비 주가가 역사적 저점 부근에 있어 가격 매력도가 매우 높은 구간입니다."
        elif rating == "매도 (Sell)":
            erg_status_text += "성장 가치에 비해 주가가 과도하게 프리미엄을 받고 있어 하락 리스크가 큰 구간입니다."
        else:
            erg_status_text += "성장성과 주가가 균형을 이루고 있는 적정 가치 구간입니다."

    # 2. 리포트 본문
    report = f"""
## 📊 {ticker} 전문 투자 리포트 (Fundamental Insight)

### 1. 투자 요약 (Executive Summary)
- **종합 등급:** **{rating}**
- **가격 매력도:** {erg_status_text}

### 2. 밸류에이션 프레임워크
- **적용 지표:** {m_name} ({m_val}x)
- **선정 근거:** {m_reason}

### 3. 성장과 효율성의 균형 (Growth vs. Efficiency)
- **Rule of 40 점수:** {r40}점
- **분석:** 매출 성장률 {growth}%와 FCF 마진을 결합한 수치입니다. 40점 미만의 경우 성장의 질적 개선이 요구되는 단계로 해석합니다.
- **현금 흐름의 질:** 매출 대비 **SBC(주식보상비용)** 비율이 {sbc}%입니다. 이는 실제 현금 유출을 수반하지 않으나 주주 가치를 희석시키는 요소이므로 조정 현금흐름 관점에서 유의깊게 보아야 합니다.

### 4. 역사적 위치 및 리스크
- **밸류에이션 밴드:** 현재 Z-Score는 {z_score}입니다. 지난 2년 평균 대비 {'저평가' if z_score < 0 else '고평가'} 국면에 위치합니다.
- **주요 리스크:** 부채비율 {debt}% 및 현재의 성장 둔화 추세를 고려할 때, 향후 실적 가시성이 확보될 때까지 리스크 관리가 최우선입니다.
    """
    return report