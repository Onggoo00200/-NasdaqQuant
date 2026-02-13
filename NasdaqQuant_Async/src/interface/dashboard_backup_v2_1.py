import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import asyncio
import yfinance as yf
import sys
import os
from datetime import datetime

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.core.macro import get_detailed_macro_analysis
from src.core.valuation import TechValuationEngine, analyze_tech_valuation_full
from src.utils.report_generator import generate_analyst_report
from src.utils.macro_report_generator import generate_macro_report
from src.indicators import calculate_indicators
from src.engine.optimizer import optimize_strategy_async
from src.engine.registry import get_registered_strategy, save_to_registry

# --- 페이지 설정 ---
st.set_page_config(page_title="Nasdaq Quant Master V2.1", page_icon="🏦", layout="wide")

# 가독성 및 대비 CSS (검정 글씨 강제)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&family=Noto+Sans+KR:wght@300;400;700&display=swap');
    
    .main, .stApp { background-color: #ffffff !important; }
    html, body, [class*="css"], p, li, span, label, h1, h2, h3 { 
        font-family: 'Noto Sans KR', sans-serif !important; color: #000000 !important; 
    }
    
    /* 섹션 제목 - 선명하게 */
    .section-header { 
        font-size: 32px; font-weight: 800; color: #003399 !important; 
        border-bottom: 5px solid #003399; padding-bottom: 12px; margin-top: 50px; margin-bottom: 30px; 
    }
    
    /* 리포트 박스 (풀와이드 최적화) */
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
    }
    
    /* 액션 플랜 하이라이트 */
    .action-plan {
        background-color: #f0fdf4;
        border: 2px solid #166534;
        padding: 30px;
        border-radius: 12px;
        font-size: 20px;
        font-weight: 700;
        text-align: center;
        margin-top: 20px;
    }
    </style>
""", unsafe_allow_html=True)

# --- [Macro Section] 차트 크기 확대 및 스타일 개선 ---
def plot_large_macro(df):
    plt.rcParams['font.family'] = 'Malgun Gothic' # Windows 한글 폰트
    # 가로로 더 넓고 시원하게 크기 조절 (16x18)
    fig, axes = plt.subplots(3, 1, figsize=(16, 18), facecolor='#ffffff')
    
    line_width = 3.5
    title_size = 20
    
    # 1. Monetary Cycle
    axes[0].plot(df.index, df['FedFunds'], label='기준 금리', color='#003399', linewidth=line_width)
    axes[0].plot(df.index, df['10Y_Treasury'], label='10년물 국채', color='#38A169', linewidth=line_width)
    axes[0].plot(df.index, df['Inflation_YoY'], label='물가 (CPI)', color='#E53E3E', linestyle='--', linewidth=2)
    axes[0].set_title('🏦 통화 정책 및 인플레이션 사이클 (Monetary)', fontsize=title_size, fontweight='bold')
    axes[0].legend(loc='upper left', fontsize=12)
    axes[0].grid(True, alpha=0.3)
    
    # 2. Growth Engine
    axes[1].fill_between(df.index, df['Profits_YoY'], color='#3182CE', alpha=0.2)
    axes[1].plot(df.index, df['Profits_YoY'], label='기업 이익 성장(YoY)', color='#3182CE', linewidth=line_width)
    axes[1].axhline(0, color='black', linewidth=1.5)
    axes[1].set_title('🚀 실물 경기 성장 동력 (Earnings)', fontsize=title_size, fontweight='bold')
    axes[1].legend(loc='upper left', fontsize=12)
    axes[1].grid(True, alpha=0.3)
    
    # 3. Risk Scanner
    axes[2].plot(df.index, df['HY_Spread'], label='하이일드 스프레드', color='#1A202C', linewidth=line_width)
    axes[2].axhline(5.0, color='#E53E3E', linestyle='--', linewidth=2, label='위험 임계선(5%)')
    axes[2].set_title('⚠️ 금융 시장 신용 리스크 (Credit)', fontsize=title_size, fontweight='bold')
    axes[2].legend(loc='upper left', fontsize=12)
    axes[2].grid(True, alpha=0.3)
    
    plt.tight_layout(pad=4.0)
    return fig

# --- Main UI ---
st.markdown("<h1 style='text-align:center; font-size:48px; font-weight:800;'>🏛️ Nasdaq Quant Master Dashboard</h1>", unsafe_allow_html=True)
st.divider()

# 1. Macro Section (Full-Width Stacked)
st.markdown("<div class='section-title'>1. 글로벌 거시 경제 분석 및 차트</div>", unsafe_allow_html=True)

macro_data = get_detailed_macro_analysis()
if not macro_data.empty:
    # 차트를 상단에 풀와이드로 배치
    st.pyplot(plot_large_macro(macro_data))
    
    # 리포트를 차트 아래에 배치
    m_info = generate_macro_report(macro_data)
    st.markdown(f"<div class='report-box'><b>[매크로 전략 가이드]</b><br><br>{m_info.replace('\n', '<br>')}</div>", unsafe_allow_html=True)
else:
    st.error("매크로 데이터를 로드할 수 없습니다.")

st.divider()

# 2. Stock Section (Full-Width Stacked)
with st.sidebar:
    st.header("🔍 분석 대상 설정")
    ticker_input = st.text_input("분석 티커 (예: NVDA)", value="NVDA").upper()
    run_btn = st.button("🚀 심층 분석 시작", type="primary", use_container_width=True)

if run_btn:
    try:
        with st.spinner(f"🕵️ {ticker_input} 분석 중..."):
            val_data = analyze_tech_valuation_full(ticker_input)
            report_text = generate_analyst_report(ticker_input, val_data)
            df_p = yf.download(ticker_input, period="3y", interval="1d", progress=False)
            if isinstance(df_p.columns, pd.MultiIndex): df_p.columns = df_p.columns.get_level_values(0)
            
            dna = get_registered_strategy(ticker_input)
            if not dna:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                opt_res = loop.run_until_complete(optimize_strategy_async(calculate_indicators(df_p.copy()), {'LarryWilliamsVBO': [{'k': 0.6}]}))
                dna = opt_res[0]
                save_to_registry(ticker_input, dna)

            st.markdown(f"<div class='section-header'>2. {ticker_input} 심층 리포트 및 액션 플랜</div>", unsafe_allow_html=True)
            
            # 성과 지표 상단 배치
            col_m1, col_m2, col_m3 = st.columns(3)
            with col_m1: st.metric("최적 전략", dna['strategy'])
            with col_m2: st.metric("연수익률 (CAGR)", f"{float(dna['cagr'])*100:.1f}%")
            with col_m3: st.metric("최대 낙폭 (MDD)", f"{float(dna['mdd'])*100:.1f}%")

            # 리포트 박스 (풀와이드)
            st.markdown(f"<div class='report-box'><b>[전문 애널리스트 분석]</b><br><br>{report_text.replace('\n', '<br>')}</div>", unsafe_allow_html=True)
            
            # 액션 플랜 (맨 하단 강조)
            last_c, last_h, last_l = df_p['Close'].iloc[-1], df_p['High'].iloc[-1], df_p['Low'].iloc[-1]
            entry_p = last_c + (last_h - last_l) * 0.6
            st.markdown(f"""
            <div class='action-plan'>
                🚀 {ticker_input} 추천 매수 진입가: ${entry_p:,.2f} 이상 (VBO 돌파 시) <br>
                🛡️ 리스크 가이드: 진입 가격 대비 -10% 하락 시 기계적 손절 권장
            </div>
            """, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"리포트 생성 중 오류: {e}")
