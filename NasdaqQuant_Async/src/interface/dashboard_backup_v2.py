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
st.set_page_config(page_title="Nasdaq Quant Master V2", page_icon="🏦", layout="wide")

# 가시성 극대화를 위한 CSS 커스텀
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&family=Noto+Sans+KR:wght@300;400;700&display=swap');
    
    .main, .stApp { background-color: #fcfcfc !important; }
    html, body, [class*="css"], p, li, span, label, h1, h2, h3 { 
        font-family: 'Noto Sans KR', sans-serif !important; color: #111111 !important; 
    }
    
    /* 카드형 섹션 */
    .dashboard-card {
        background-color: #ffffff;
        padding: 30px;
        border-radius: 15px;
        border: 1px solid #e1e4e8;
        box-shadow: 0 4px 20px rgba(0,0,0,0.05);
        margin-bottom: 25px;
    }
    
    /* 헤더 포인트 */
    .section-title { 
        font-size: 30px; font-weight: 800; color: #003399 !important; 
        border-bottom: 4px solid #003399; padding-bottom: 12px; margin-bottom: 30px; 
    }
    
    /* 리포트 박스 (가독성 강화) */
    .report-box {
        background-color: #ffffff;
        border: 2px solid #003399;
        padding: 30px;
        border-radius: 15px;
        line-height: 2.0;
        font-size: 17px;
        color: #000000 !important;
    }
    
    /* 강조 메트릭 */
    [data-testid="stMetricValue"] { color: #003399 !important; font-weight: 800 !important; font-size: 32px !important; }
    
    /* 액션 플랜 하이라이트 */
    .action-plan {
        background-color: #f0fdf4;
        border-left: 10px solid #166534;
        padding: 25px;
        border-radius: 10px;
        font-size: 18px;
        font-weight: 700;
    }
    </style>
""", unsafe_allow_html=True)

# --- [Macro Section] 시각화 개선 ---
def plot_modern_macro(df):
    plt.rcParams['font.family'] = 'Malgun Gothic' # 한글 폰트 대응
    fig, axes = plt.subplots(3, 1, figsize=(14, 20), facecolor='#ffffff')
    
    # 공통 스타일
    line_width = 3
    title_size = 18
    label_size = 12
    
    # 1. Monetary Cycle
    axes[0].plot(df.index, df['FedFunds'], label='기준 금리', color='#003399', linewidth=line_width)
    axes[0].plot(df.index, df['10Y_Treasury'], label='10년물 금리', color='#38A169', linewidth=line_width)
    axes[0].plot(df.index, df['Inflation_YoY'], label='물가 (CPI)', color='#E53E3E', linestyle='--', linewidth=2)
    axes[0].set_title('🏦 통화 정책 및 물가 사이클', fontsize=title_size, fontweight='bold', pad=20)
    axes[0].legend(fontsize=label_size)
    axes[0].grid(True, alpha=0.3)
    
    # 2. Growth Engine
    axes[1].fill_between(df.index, df['Profits_YoY'], color='#3182CE', alpha=0.15)
    axes[1].plot(df.index, df['Profits_YoY'], label='기업 이익 성장', color='#3182CE', linewidth=line_width)
    axes[1].plot(df.index, df['M2_YoY'], label='유동성 (M2)', color='#805AD5', linewidth=line_width, linestyle=':')
    axes[1].axhline(0, color='#1A202C', linewidth=1.5)
    axes[1].set_title('🚀 경제 성장 동력 및 유동성', fontsize=title_size, fontweight='bold', pad=20)
    axes[1].legend(fontsize=label_size)
    axes[1].grid(True, alpha=0.3)
    
    # 3. Risk Assessment
    axes[2].plot(df.index, df['HY_Spread'], label='하이일드 스프레드', color='#1A202C', linewidth=line_width)
    axes[2].axhline(5.0, color='#E53E3E', linestyle='--', label='위험 임계치 (5%)')
    axes[2].set_title('⚠️ 금융 시스템 리스크 스캐너', fontsize=title_size, fontweight='bold', pad=20)
    axes[2].legend(fontsize=label_size)
    axes[2].grid(True, alpha=0.3)
    
    plt.tight_layout(pad=5.0)
    return fig

# --- Main UI Logic ---
st.markdown("<h1 style='text-align:center; font-size:48px; margin-bottom:0;'>🏛️ Nasdaq Quant Master Dashboard</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center; font-size:20px; color:#666;'>실시간 거시 경제 진단 및 AI 기업 가치 평가 시스템</p>", unsafe_allow_html=True)
st.divider()

# 1. Macro Section
st.markdown("<div class='section-title'>1. 글로벌 거시 경제 리포트</div>", unsafe_allow_html=True)

macro_data = get_detailed_macro_analysis()
if not macro_data.empty:
    m_info = generate_macro_report(macro_data)
    
    # 레이아웃 재배치 (차트와 리포트를 더 크게)
    m_col_left, m_col_right = st.columns([1.1, 1])
    
    with m_col_left:
        st.markdown(f"<div class='report-box'>{m_info.replace('\n', '<br>')}</div>", unsafe_allow_html=True)
        
    with m_col_right:
        st.markdown("### 📊 매크로 추세 시각화")
        st.pyplot(plot_modern_macro(macro_data))
else:
    st.error("데이터 로딩 중...")

st.divider()

# 2. Stock Section
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2620/2620582.png", width=100)
    st.header("🔍 분석 타겟")
    ticker_input = st.text_input("종목 티커", value="NVDA").upper()
    run_btn = st.button("🚀 심층 리포트 생성", type="primary", use_container_width=True)
    st.caption("Ver 2.0 - High Visibility Mode")

if run_btn:
    try:
        with st.spinner(f"🕵️ {ticker_input} 분석 중..."):
            val_data = analyze_tech_valuation_full(ticker_input)
            report_text = generate_analyst_report(ticker_input, val_data)
            df_price = yf.download(ticker_input, period="3y", interval="1d", progress=False)
            if isinstance(df_price.columns, pd.MultiIndex): df_price.columns = df_price.columns.get_level_values(0)
            
            dna = get_registered_strategy(ticker_input)
            if not dna:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                opt_res = loop.run_until_complete(optimize_strategy_async(calculate_indicators(df_price.copy()), {'LarryWilliamsVBO': [{'k': 0.6}]}))
                dna = opt_res[0]
                save_to_registry(ticker_input, dna)

            st.markdown(f"<div class='section-title'>2. {ticker_input} 기업 분석 및 액션 플랜</div>", unsafe_allow_html=True)
            
            c_r1, c_r2 = st.columns([1.5, 1])
            with c_r1:
                st.markdown(f"<div class='report-box'>{report_text.replace('\n', '<br>')}</div>", unsafe_allow_html=True)
            
            with c_r2:
                # 액션 플랜 카드
                last_c, last_h, last_l = df_price['Close'].iloc[-1], df_price['High'].iloc[-1], df_price['Low'].iloc[-1]
                entry_p = last_c + (last_h - last_l) * 0.6
                
                st.markdown(f"""
                <div class='action-plan'>
                    🚀 추천 진입가: ${entry_p:,.2f}<br>
                    🛡️ 손절가 기준: 진입가 대비 -10%<br>
                    📈 최적 전략: {dna['strategy']}
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
                st.metric("연평균 수익률", f"{float(dna['cagr'])*100:.1f}%")
                st.metric("최대 낙폭", f"{float(dna['mdd'])*100:.1f}%")

    except Exception as e:
        st.error(f"오류: {e}")