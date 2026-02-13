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
from src.utils.macro_report_generator import generate_macro_report
from src.indicators import calculate_indicators
from src.engine.optimizer import optimize_strategy_async
from src.engine.registry import get_registered_strategy, save_to_registry

# --- 페이지 설정 ---
st.set_page_config(page_title="Nasdaq Quant Master 5Y-Focus", page_icon="📈", layout="wide")

# 가독성 및 대비 CSS
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&family=Noto+Sans+KR:wght@300;400;700&display=swap');
    .main, .stApp { background-color: #ffffff !important; }
    html, body, [class*="css"], p, li, span, label, h1, h2, h3 { 
        font-family: 'Noto Sans KR', sans-serif !important; color: #000000 !important; 
    }
    .section-header { 
        font-size: 32px; font-weight: 800; color: #003399 !important; 
        border-bottom: 5px solid #003399; padding-bottom: 12px; margin-top: 50px; margin-bottom: 30px; 
    }
    .report-box {
        background-color: #fcfcfc;
        border: 2px solid #e1e4e8;
        padding: 40px;
        border-radius: 15px;
        line-height: 2.1;
        font-size: 18px;
        color: #000000 !important;
        margin-bottom: 40px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
    }
    </style>
""", unsafe_allow_html=True)

# --- [Macro Section] 최근 10년 집중 시각화 ---
def plot_10y_macro(df):
    plt.rcParams['font.family'] = 'Malgun Gothic'
    
    # 최근 10년(약 120개월) 데이터로 필터링
    df_10y = df.tail(120) 
    
    fig, axes = plt.subplots(3, 1, figsize=(16, 20), facecolor='#ffffff')
    line_width = 3.5 # 데이터가 많아지므로 선 굵기 소폭 조정
    title_size = 22
    
    # 1. Monetary Cycle
    axes[0].plot(df_10y.index, df_10y['FedFunds'], label='기준 금리', color='#003399', linewidth=line_width)
    axes[0].plot(df_10y.index, df_10y['10Y_Treasury'], label='10년물 국채', color='#38A169', linewidth=line_width)
    axes[0].plot(df_10y.index, df_10y['Inflation_YoY'], label='물가 (CPI)', color='#E53E3E', linestyle='--', linewidth=2)
    axes[0].set_title('🏦 최근 10년 통화 정책 및 물가 추이', fontsize=title_size, fontweight='bold')
    axes[0].legend(loc='upper left', fontsize=13)
    axes[0].grid(True, alpha=0.3)
    
    # 2. Growth Engine
    axes[1].fill_between(df_10y.index, df_10y['Profits_YoY'], color='#3182CE', alpha=0.2)
    axes[1].plot(df_10y.index, df_10y['Profits_YoY'], label='기업 이익 성장', color='#3182CE', linewidth=line_width)
    axes[1].axhline(0, color='black', linewidth=1.5)
    axes[1].set_title('🚀 최근 10년 실물 경기 성장 탄력', fontsize=title_size, fontweight='bold')
    axes[1].legend(loc='upper left', fontsize=13)
    axes[1].grid(True, alpha=0.3)
    
    # 3. Risk Scanner
    axes[2].plot(df_10y.index, df_10y['HY_Spread'], label='신용 스프레드', color='#1A202C', linewidth=line_width)
    axes[2].axhline(5.0, color='#E53E3E', linestyle='--', linewidth=2, label='위험 경계선(5%)')
    axes[2].set_title('⚠️ 최근 10년 금융 시장 스트레스 지수', fontsize=title_size, fontweight='bold')
    axes[2].legend(loc='upper left', fontsize=13)
    axes[2].grid(True, alpha=0.3)
    
    plt.tight_layout(pad=5.0)
    return fig

# --- Main UI ---
st.markdown("<h1 style='text-align:center; font-size:48px; font-weight:800;'>🏛️ Nasdaq Quant Master Dashboard</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center; color:#666;'>최근 10개년 거시 경제 사이클 분석 모드 활성화</p>", unsafe_allow_html=True)
st.divider()

# 1. Macro Section
st.markdown("<div class='section-title'>1. 글로벌 거시 경제 리포트 (최근 10년 데이터)</div>", unsafe_allow_html=True)

macro_data = get_detailed_macro_analysis()
if not macro_data.empty:
    # 차트 상단 배치 (10년 데이터)
    st.pyplot(plot_10y_macro(macro_data))
    
    # 상세 리포트 하단 배치
    m_info = generate_macro_report(macro_data)
    st.markdown(f"<div class='report-box'><b>[매크로 전략 심층 리포트]</b><br><br>{m_info.replace('\n', '<br>')}</div>", unsafe_allow_html=True)
else:
    st.error("매크로 데이터를 로드할 수 없습니다.")

st.divider()

# 2. Stock Section
with st.sidebar:
    st.header("🔍 분석 설정")
    ticker_input = st.text_input("기업 티커", value="NVDA").upper()
    run_btn = st.button("🚀 심층 분석 생성", type="primary", use_container_width=True)

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

            st.markdown(f"<div class='section-header'>2. {ticker_input} 전문 투자 리포트</div>", unsafe_allow_html=True)
            
            # 성과 카드
            st.metric("최적 전략", dna['strategy'])
            
            # 리포트 전문
            st.markdown(f"<div class='report-box'><b>[수석 애널리스트 펀더멘털 진단]</b><br><br>{report_text.replace('\n', '<br>')}</div>", unsafe_allow_html=True)
            
            # 최종 가이드 강조
            last_c, last_h, last_l = df_p['Close'].iloc[-1], df_p['High'].iloc[-1], df_p['Low'].iloc[-1]
            entry_p = last_c + (last_h - last_l) * 0.6
            st.success(f"🚀 **금일 추천 진입 가격: ${entry_p:,.2f} 이상 돌파 시 (손절가 -10%)**")

    except Exception as e:
        st.error(f"오류: {e}")