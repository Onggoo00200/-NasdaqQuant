import streamlit as st
import pandas as pd
import asyncio
import yfinance as yf
import os
import sys
import numpy as np
import altair as alt
from datetime import datetime, timedelta
import json

# 프로젝트 루트를 경로에 추가
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# 리팩토링된 모듈들 임포트
from src.indicators import calculate_indicators
from src.engine.optimizer import optimize_strategy_async
from src.engine.registry import get_registered_strategy, save_to_registry
from src.core.macro import get_detailed_macro_logic
from src.core.valuation import analyze_tech_valuation_full, TechValuationEngine
from src.utils.config import PARAM_GRID

# --- 설정 ---
st.set_page_config(page_title="Nasdaq Quant Master [PRO]", page_icon="⚖️", layout="wide")

# 가독성 디자인 CSS
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;700&display=swap');
    html, body, [class*="css"], p, li, span, label, h1, h2, h3 { 
        font-family: 'Noto Sans KR', sans-serif !important; color: #000000 !important; 
    }
    .main, .stApp { background-color: #ffffff !important; }
    .report-box {
        background-color: #f8fafc !important;
        border: 1px solid #cbd5e1;
        border-left: 8px solid #003399;
        padding: 30px;
        border-radius: 12px;
        line-height: 2.0;
        font-size: 16px;
        color: #000000 !important;
        margin-bottom: 25px;
        white-space: pre-wrap;
    }
    .section-header { 
        font-size: 28px; font-weight: 800; color: #003399 !important; 
        border-bottom: 4px solid #003399; padding-bottom: 10px; margin-top: 40px; margin-bottom: 25px; 
    }
    [data-testid="stMetricValue"] { color: #003399 !important; font-weight: 800 !important; }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 1. GLOBAL MACRO INTEL
# ---------------------------------------------------------
st.markdown("<h1 style='text-align:center;'>🚀 Nasdaq Quant Master Dashboard</h1>", unsafe_allow_html=True)
st.divider()

intel = get_detailed_macro_logic()

if "error" not in intel:
    st.markdown("<div class='section-header'>1. 글로벌 거시 경제 및 리스크 분석</div>", unsafe_allow_html=True)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("실물 경기 모멘텀", f"{intel['dg']:+.2f}%")
    m2.metric("장단기 금리차", f"{intel['yield']:.2f}%p", delta="Inverted" if intel['yield'] < 0 else "Normal")
    m3.metric("신용 위험 (Credit)", f"{intel['credit']:.2f}")
    m4.metric("시장 변동성 (VIX)", f"{intel['vix']:.2f}")

    col_l, col_r = st.columns([1.3, 1])
    with col_l:
        st.markdown(f"### 🏛️ 현재 국면: <span style='color:#003399;'>{intel['regime']}</span>", unsafe_allow_html=True)
        st.markdown(f"<div class='report-box' style='padding:20px; font-size:15px;'>{intel['regime']} 구간에서는 성장주와 기술주의 멀티플 확장이 역사적으로 시장 수익률을 상회했습니다.</div>", unsafe_allow_html=True)
    with col_r:
        st.line_chart(intel['chart_data'])

st.markdown("---")

# ---------------------------------------------------------
# 2. TICKER ANALYSIS
# ---------------------------------------------------------
with st.sidebar:
    st.header("🔍 기업 심층 분석")
    ticker = st.text_input("티커 입력", value="NVDA").upper()
    run_btn = st.button("🚀 심층 리포트 생성", type="primary", use_container_width=True)

if run_btn:
    try:
        with st.spinner(f"🕵️ {ticker} 분석 중..."):
            df_p = yf.download(ticker, period="3y", interval="1d", progress=False)
            if isinstance(df_p.columns, pd.MultiIndex): df_p.columns = df_p.columns.get_level_values(0)
            
            # 리팩토링된 클래스 사용
            engine = TechValuationEngine(ticker)
            fin_df = engine.fetch_data()
            val = analyze_tech_valuation_full(ticker)
            
            # 최적화 로직
            dna = get_registered_strategy(ticker)
            if not dna:
                processed_df = calculate_indicators(df_p.copy())
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                opt_res = loop.run_until_complete(optimize_strategy_async(processed_df, PARAM_GRID))
                best = opt_res[0]
                save_to_registry(ticker, {"strategy": best['strategy'], "params": best['params'], "cagr": best['cagr'], "mdd": best['mdd'], "score": best['score']})
                dna = get_registered_strategy(ticker)

            st.markdown(f"## 📈 {ticker} 심층 투자 분석 리포트")
            
            # 섹션 2: 펀더멘털
            st.markdown("<div class='section-header'>2. 기업 펀더멘털 및 가치 평가</div>", unsafe_allow_html=True)
            st.markdown(f"""
            <div class='report-box'>
            <b>[수익성 및 성장성 진단]</b>
            - Rule of 40: {val['rule_of_40']:.1f}점 (SBC 보정 후)
            - ERG Ratio: {val['erg_ratio']:.2f} (성장성 대비 가치)
            - 부채비율: {val['debt_ratio']:.1f}%
            </div>
            """, unsafe_allow_html=True)
            
            # 섹션 3: 액션 플랜
            st.markdown("<div class='section-header'>3. 🏁 최종 투자 판단</div>", unsafe_allow_html=True)
            l_c, l_h, l_l = df_p['Close'].iloc[-1], df_p['High'].iloc[-1], df_p['Low'].iloc[-1]
            entry_p = l_c + (l_h - l_l) * 0.6
            st.success(f"🚀 **권장 진입가: ${entry_p:,.2f} 이상** | **전략: {dna['strategy']}**")

    except Exception as e:
        st.error(f"오류: {e}")
