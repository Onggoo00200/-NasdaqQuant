import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import asyncio
import yfinance as yf
import sys
import os
from datetime import datetime, timedelta

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.core.macro import get_detailed_macro_analysis
from src.core.valuation import TechValuationEngine, analyze_tech_valuation_full
from src.utils.report_generator import generate_analyst_report
from src.utils.macro_report_generator import generate_macro_report # 📜 에이전트 통합
from src.indicators import calculate_indicators
from src.engine.optimizer import optimize_strategy_async
from src.engine.registry import get_registered_strategy, save_to_registry

# --- 페이지 설정 ---
st.set_page_config(page_title="Nasdaq Quant AI Master Dashboard", page_icon="🏦", layout="wide")

# 가독성 및 고대비 CSS
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;700;800&display=swap');
    
    .main, .stApp { background-color: #ffffff !important; }
    html, body, [class*="css"], p, li, span, label, h1, h2, h3, div { 
        font-family: 'Noto Sans KR', sans-serif !important; color: #000000 !important; 
    }
    
    /* 섹션 헤더 스타일 */
    .section-header { 
        font-size: 32px; font-weight: 800; color: #003399 !important; 
        border-bottom: 5px solid #003399; padding-bottom: 12px; margin-top: 50px; margin-bottom: 30px; 
    }
    
    /* 리포트 박스 (풀와이드 및 가독성 최적화) */
    .report-box {
        background-color: #f8fafc;
        border: 2px solid #e1e4e8;
        padding: 40px;
        border-radius: 15px;
        line-height: 2.1;
        font-size: 18px;
        color: #000000 !important;
        margin-bottom: 40px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        white-space: pre-wrap;
    }
    
    /* 강조 메트릭 */
    [data-testid="stMetricValue"] { color: #003399 !important; font-weight: 800 !important; }
    </style>
""", unsafe_allow_html=True)

# --- [Macro Section] 10년 시계열 대형 차트 ---
def plot_macro_full(df):
    plt.rcParams['font.family'] = 'Malgun Gothic'
    df_plot = df.tail(120) # 최근 10년
    fig, axes = plt.subplots(3, 1, figsize=(16, 22), facecolor='#ffffff')
    
    # 1. Monetary
    axes[0].plot(df_plot.index, df_plot['FedFunds'], label='기준 금리', color='#003399', linewidth=4)
    axes[0].plot(df_plot.index, df_plot['10Y_Treasury'], label='10년물 국채', color='#38A169', linewidth=4)
    axes[0].plot(df_plot.index, df_plot['Inflation_YoY'], label='물가(CPI)', color='#E53E3E', linestyle='--', linewidth=2.5)
    axes[0].set_title('🏦 통화 정책 및 물가 추이 (최근 10년)', fontsize=22, fontweight='bold', pad=20)
    axes[0].legend(loc='upper left', fontsize=13); axes[0].grid(True, alpha=0.3)
    
    # 2. Growth
    axes[1].fill_between(df_plot.index, df_plot['Profits_YoY'], color='#3182CE', alpha=0.2)
    axes[1].plot(df_plot.index, df_plot['Profits_YoY'], label='기업 이익 성장', color='#3182CE', linewidth=4)
    axes[1].axhline(0, color='black', linewidth=2)
    axes[1].set_title('🚀 실물 경기 성장 탄력 (Earnings)', fontsize=22, fontweight='bold', pad=20)
    axes[1].legend(loc='upper left', fontsize=13); axes[1].grid(True, alpha=0.3)
    
    # 3. Risk
    axes[2].plot(df_plot.index, df_plot['HY_Spread'], label='신용 스프레드', color='#1A202C', linewidth=4)
    axes[2].axhline(5.0, color='#cc0000', linestyle='--', linewidth=2.5, label='위험 경계선')
    axes[2].set_title('⚠️ 금융 시장 리스크 스캐너 (Credit)', fontsize=22, fontweight='bold', pad=20)
    axes[2].legend(loc='upper left', fontsize=13); axes[2].grid(True, alpha=0.3)
    
    plt.tight_layout(pad=6.0)
    return fig

# --- Main UI ---
st.markdown("<h1 style='text-align:center; font-size:48px; font-weight:800;'>🏛️ Nasdaq Quant Master Dashboard</h1>", unsafe_allow_html=True)
st.divider()

# 1. Macro Section
st.markdown("<div class='section-header'>1. 🏛️ 매크로 퀀트 대시보드 해석 리포트</div>", unsafe_allow_html=True)

macro_data = get_detailed_macro_analysis()
if not macro_data.empty:
    # 차트 (상단 풀와이드)
    st.pyplot(plot_macro_full(macro_data))
    
    # 리포트 (하단 풀와이드)
    macro_report_txt = generate_macro_report(macro_data)
    st.markdown(f"<div class='report-box'>{macro_report_txt.replace('\n', '<br>')}</div>", unsafe_allow_html=True)
else:
    st.error("매크로 데이터를 로드할 수 없습니다.")

st.divider()

# 2. Stock Section
with st.sidebar:
    st.header("🔍 분석 타겟 설정")
    ticker_input = st.text_input("분석 티커 입력", value="NVDA").upper()
    run_btn = st.button("🚀 심층 리포트 생성", type="primary", use_container_width=True)

if run_btn:
    try:
        with st.spinner(f"🕵️ {ticker_input}의 주가 DNA와 재무를 대조 분석 중..."):
            # 밸류에이션 리포트
            val_data = analyze_tech_valuation_full(ticker_input)
            report_text = generate_analyst_report(ticker_input, val_data)
            
            # 가격 및 전략 데이터
            df_p = yf.download(ticker_input, period="3y", interval="1d", progress=False)
            if isinstance(df_p.columns, pd.MultiIndex): df_p.columns = df_p.columns.get_level_values(0)
            
            dna = get_registered_strategy(ticker_input)
            if not dna:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                opt_res = loop.run_until_complete(optimize_strategy_async(calculate_indicators(df_p.copy()), {'LarryWilliamsVBO': [{'k': 0.6}]}))
                dna = opt_res[0]
                save_to_registry(ticker_input, dna)

            # 리포트 출력
            st.markdown(f"<div class='section-header'>2. {ticker_input} 기업 펀더멘털 및 퀀트 가이드</div>", unsafe_allow_html=True)
            
            m1, m2, m3 = st.columns(3)
            with m1: st.metric("최적 전략", dna['strategy'])
            with m2: st.metric("연수익률 (CAGR)", f"{float(dna['cagr'])*100:.1f}%")
            with m3: st.metric("최대 낙폭", f"{float(dna['mdd'])*100:.1f}%")

            # 1,000자 리포트 전문 출력
            st.markdown(f"<div class='report-box'>{report_text.replace('\n', '<br>')}</div>", unsafe_allow_html=True)
            
            # 액션 플랜 가이드
            last_c, last_h, last_l = df_p['Close'].iloc[-1], df_p['High'].iloc[-1], df_p['Low'].iloc[-1]
            entry_p = last_c + (last_h - last_l) * 0.6
            st.success(f"🚀 **전략적 매수 진입가: ${entry_p:,.2f} 이상 돌파 시 (손절가 -10%)**")

    except Exception as e:
        st.error(f"리포트 생성 오류: {e}")
