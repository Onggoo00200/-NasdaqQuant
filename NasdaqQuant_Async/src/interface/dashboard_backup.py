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
st.set_page_config(page_title="Nasdaq Quant Master UI", page_icon="📈", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;700&display=swap');
    html, body, [class*="css"], p, li, span, label, h1, h2, h3 { font-family: 'Noto Sans KR', sans-serif !important; color: #000000 !important; }
    .main, .stApp { background-color: #ffffff !important; }
    .report-box { background-color: #f8fafc; border: 1px solid #cbd5e1; padding: 25px; border-radius: 12px; color: #000000 !important; line-height: 1.8; }
    .section-title { font-size: 24px; font-weight: 700; color: #003399; border-left: 6px solid #003399; padding-left: 15px; margin-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

# --- [Macro Section] ---
def get_macro_data():
    return get_detailed_macro_analysis()

def plot_macro_dashboard(df):
    fig, axes = plt.subplots(3, 1, figsize=(12, 18), sharex=True)
    sns.set_style("whitegrid")
    axes[0].plot(df.index, df['FedFunds'], label='Fed Funds Rate', color='blue', linewidth=2)
    axes[0].plot(df.index, df['10Y_Treasury'], label='10Y Treasury', color='green', linewidth=2)
    axes[0].plot(df.index, df['Inflation_YoY'], label='CPI YoY', color='red', linestyle='--')
    axes[0].set_title('Monetary Cycle', fontsize=14, fontweight='bold')
    axes[0].legend()
    axes[1].plot(df.index, df['M2_YoY'], label='M2 YoY', color='purple')
    axes[1].plot(df.index, df['Profits_YoY'], label='Profits YoY', color='orange')
    axes[1].axhline(0, color='black', linewidth=1)
    axes[1].set_title('Growth Engine', fontsize=14, fontweight='bold')
    axes[1].legend()
    axes[2].plot(df.index, df['HY_Spread'], label='HY Spread', color='black')
    axes[2].axhline(5.0, color='red', linestyle='--')
    axes[2].set_title('Risk Indicators', fontsize=14, fontweight='bold')
    axes[2].legend()
    plt.tight_layout()
    return fig

# --- Main UI ---
st.title("🚀 Nasdaq Quant Master: 통합 대시보드")
st.divider()

st.markdown("<div class='section-title'>1. 글로벌 거시 경제 매크로 진단 및 전략 리포트</div>", unsafe_allow_html=True)

macro_data = get_macro_data()
if not macro_data.empty:
    macro_report_txt = generate_macro_report(macro_data)
    
    # 딕셔너리로 들어올 경우를 대비한 안전장치
    if isinstance(macro_report_txt, dict):
        macro_report_txt = str(macro_report_txt)
    
    col_m1, col_m2 = st.columns([1.2, 1])
    with col_m1:
        st.markdown(f"<div class='report-box'>{macro_report_txt.replace('\n', '<br>')}</div>", unsafe_allow_html=True)
    with col_m2:
        st.pyplot(plot_macro_dashboard(macro_data))
else:
    st.error("데이터 로딩 실패")

st.divider()

# 2. 사이드바 및 기업 분석 (기존 유지)
with st.sidebar:
    st.header("🔍 기업 분석 설정")
    ticker_input = st.text_input("분석 티커", value="NVDA").upper()
    run_btn = st.button("심층 분석 리포트 생성", type="primary", use_container_width=True)

if run_btn:
    try:
        with st.spinner(f"🕵️ {ticker_input} 분석 중..."):
            val_data = analyze_tech_valuation_full(ticker_input)
            report_text = generate_analyst_report(ticker_input, val_data)
            df_p = yf.download(ticker_input, period="3y", interval="1d", progress=False)
            if isinstance(df_p.columns, pd.MultiIndex): df_p.columns = df_p.columns.get_level_values(0)
            
            dna = get_registered_strategy(ticker_input)
            if not dna:
                processed_df = calculate_indicators(df_p.copy())
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                opt_res = loop.run_until_complete(optimize_strategy_async(processed_df, {'LarryWilliamsVBO': [{'k': 0.6}]}))
                dna = opt_res[0]
                save_to_registry(ticker_input, dna)

            st.markdown(f"<div class='section-title'>2. {ticker_input} 심층 리포트 및 전략</div>", unsafe_allow_html=True)
            c_r1, c_r2 = st.columns([1.5, 1])
            with c_r1:
                st.markdown(f"<div class='report-box'>{report_text.replace('\n', '<br>')}</div>", unsafe_allow_html=True)
            with c_r2:
                st.metric("추천 전략", dna['strategy'])
                st.metric("연수익률", f"{float(dna['cagr'])*100:.1f}%")
                st.metric("최대 낙폭", f"{float(dna['mdd'])*100:.1f}%")
    except Exception as e:
        st.error(f"오류: {e}")
