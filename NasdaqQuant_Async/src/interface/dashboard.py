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
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(PROJECT_ROOT)

# 리팩토링된 모듈 임포트
from src.core.macro import get_detailed_macro_analysis
from src.core.valuation_engine import analyze_tech_valuation_full, analyze_tech_stock_data
from src.interface.charts import create_tech_valuation_chart
from src.utils.report_generator import generate_analyst_report
from src.utils.macro_report_generator import generate_macro_report
from src.indicators import calculate_indicators
from src.engine.optimizer import optimize_strategy_async
from src.engine.registry import get_registered_strategy, save_to_registry

# --- 페이지 설정 ---
st.set_page_config(page_title="Nasdaq Quant Master Ultimate", page_icon="💎", layout="wide")

# 고대비 가독성 CSS
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;700;800&display=swap');
    html, body, [class*="css"], p, li, span, label, h1, h2, h3, div { 
        font-family: 'Noto Sans KR', sans-serif !important; color: #000000 !important; 
    }
    .main, .stApp { background-color: #ffffff !important; }
    .section-header { 
        font-size: 32px; font-weight: 800; color: #003399 !important; 
        border-bottom: 5px solid #003399; padding-bottom: 12px; margin-top: 50px; margin-bottom: 30px; 
    }
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
    </style>
""", unsafe_allow_html=True)

# --- [Macro Section] ---
@st.cache_data(ttl=3600 * 12) # 12시간 동안 메모리 유지
def get_macro_data():
    return get_detailed_macro_analysis()

# --- [Macro Section] 10년 시계열 대형 차트 복구 ---
def plot_macro_full(df):
    plt.rcParams['font.family'] = 'Malgun Gothic'
    df_plot = df.tail(120) # 최근 10년
    fig, axes = plt.subplots(3, 1, figsize=(16, 22), facecolor='#ffffff')
    line_w = 4
    
    # 1. Monetary
    axes[0].plot(df_plot.index, df_plot['FedFunds'], label='기준 금리', color='#003399', linewidth=line_w)
    axes[0].plot(df_plot.index, df_plot['10Y_Treasury'], label='10년물 국채', color='#38A169', linewidth=line_w)
    axes[0].plot(df_plot.index, df_plot['Inflation_YoY'], label='물가(CPI)', color='#E53E3E', linestyle='--', linewidth=2.5)
    axes[0].set_title('🏦 통화 정책 및 물가 추이 (최근 10년)', fontsize=22, fontweight='bold', pad=20)
    axes[0].legend(loc='upper left', fontsize=13); axes[0].grid(True, alpha=0.3)
    
    # 2. Growth
    axes[1].fill_between(df_plot.index, df_plot['Profits_YoY'], color='#3182CE', alpha=0.2)
    axes[1].plot(df_plot.index, df_plot['Profits_YoY'], label='기업 이익 성장', color='#3182CE', linewidth=line_w)
    axes[1].axhline(0, color='black', linewidth=2)
    axes[1].set_title('🚀 실물 경기 성장 탄력 (Earnings)', fontsize=22, fontweight='bold', pad=20)
    axes[1].legend(loc='upper left', fontsize=13); axes[1].grid(True, alpha=0.3)
    
    # 3. Risk
    axes[2].plot(df_plot.index, df_plot['HY_Spread'], label='신용 스프레드', color='#1A202C', linewidth=line_w)
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
    # [차트 렌더링 추가]
    st.pyplot(plot_macro_full(macro_data))
    
    # [리포트 텍스트 출력]
    macro_report_txt = generate_macro_report(macro_data)
    st.markdown(f"<div class='report-box'>{macro_report_txt.replace('\n', '<br>')}</div>", unsafe_allow_html=True)
else:
    st.error("매크로 데이터를 불러올 수 없습니다. API 키와 네트워크 상태를 확인하세요.")

st.divider()

# 2. Stock Section
with st.sidebar:
    st.header("🔍 분석 타겟 설정")
    ticker_input = st.text_input("분석 티커 입력", value="NVDA").upper()
    run_btn = st.button("🚀 심층 분석 생성", type="primary", use_container_width=True)

if run_btn:
    try:
        with st.spinner(f"🕵️ {ticker_input} 분석 중..."):
            summary_data, recent_df = analyze_tech_stock_data(ticker_input)
            if summary_data is None:
                st.error("데이터 수집 혹은 분석 중 오류가 발생했습니다.")
                st.stop()
            
            val_data = analyze_tech_valuation_full(ticker_input)
            report_text = generate_analyst_report(ticker_input, val_data)
            fig = create_tech_valuation_chart(ticker_input, summary_data, recent_df)
            
            dna = get_registered_strategy(ticker_input)
            if not dna:
                df_p = yf.download(ticker_input, period="3y", interval="1d", progress=False)
                if isinstance(df_p.columns, pd.MultiIndex): df_p.columns = df_p.columns.get_level_values(0)
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                opt_res = loop.run_until_complete(optimize_strategy_async(calculate_indicators(df_p.copy()), {'LarryWilliamsVBO': [{'k': 0.6}]}))
                dna = opt_res[0]
                save_to_registry(ticker_input, dna)

            st.markdown(f"<div class='section-header'>2. {ticker_input} 심층 리포트 및 3단 가치 평가</div>", unsafe_allow_html=True)
            if fig: st.plotly_chart(fig, use_container_width=True)
            
            # 2. 핵심 요약 카드 (신호등 시스템 적용)
            m1, m2, m3 = st.columns(3)
            with m1: st.metric("지배적 평가지표", summary_data['dominant_metric'])
            with m2: st.metric("현재 Z-Score", f"{summary_data['z_score']:+.2f}σ")
            with m3: 
                erg_val = val_data['erg_ratio']
                if erg_val >= 999:
                    st.error("🚨 ERG: 측정 불가 (역성장)")
                else:
                    st.metric("ERG Ratio", f"{erg_val:.2f}")

            # 3. 긴급 경고 배너
            if val_data['erg_ratio'] >= 999:
                st.warning(f"⚠️ **{ticker_input} 분석 주의:** 현재 매출 성장률이 마이너스 혹은 정체되어 밸류에이션 정당성이 부족한 상태입니다. 하단 리포트의 리스크 섹션을 반드시 확인하세요.")

            # 4. 상세 리포트
            st.markdown(f"<div class='report-box'><b>[수석 애널리스트 심층 리포트]</b><br><br>{report_text.replace('\n', '<br>')}</div>", unsafe_allow_html=True)
            
            last_p = yf.Ticker(ticker_input).history(period="1d")['Close'].iloc[-1]
            st.success(f"🚀 **전략적 목표 가격: ${last_p * 1.02:,.2f} 이상 돌파 시 진입 권장**")

    except Exception as e:
        st.error(f"대시보드 렌더링 오류: {e}")