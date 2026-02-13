import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import pandas as pd

def create_tech_valuation_chart(ticker, summary_data, recent_df):
    """
    valuation_engine의 분석 데이터를 받아 Plotly 3단 차트 생성
    (Rule of 40 렌더링 무결성 강화 버전)
    """
    if recent_df is None or recent_df.empty:
        return None

    # 데이터 추출
    dominant_metric = summary_data.get('dominant_metric', 'Valuation')
    mean_val = summary_data.get('mean_val', 0)
    std_val = summary_data.get('std_val', 1)
    
    # 3단 서브플롯 생성
    fig = make_subplots(
        rows=3, cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.08,
        subplot_titles=(
            f"Historical Valuation Band ({dominant_metric}) - 3Y Trend", 
            "Valuation Z-Score Trend (Market Sentiment)",
            "Rule of 40 Trend Analysis (Growth + Margin)"
        )
    )

    # 1. Valuation Band
    fig.add_trace(go.Scatter(x=recent_df.index, y=recent_df['Selected_Value'], 
                             name=f"{dominant_metric}", line=dict(color='#1A202C', width=2.5)), row=1, col=1)
    fig.add_hline(y=mean_val, line_dash="solid", line_color="#38A169", annotation_text="3Y Mean", row=1, col=1)
    fig.add_hline(y=mean_val + std_val, line_dash="dot", line_color="#E53E3E", annotation_text="+1σ", row=1, col=1)
    fig.add_hline(y=mean_val - std_val, line_dash="dot", line_color="#3182CE", annotation_text="-1σ", row=1, col=1)

    # 2. Z-Score Trend
    z_colors = np.where(recent_df['Z_Score'] > 0, '#E53E3E', '#3182CE')
    fig.add_trace(go.Bar(x=recent_df.index, y=recent_df['Z_Score'],
                         name="Z-Score", marker_color=z_colors, opacity=0.7), row=2, col=1)
    fig.add_hline(y=2.0, line_dash="dash", line_color="#cc0000", row=2, col=1)
    fig.add_hline(y=-2.0, line_dash="dash", line_color="#0000cc", row=2, col=1)
    fig.add_hline(y=0, line_color="black", row=2, col=1)

    # 3. Rule of 40 History (강제 재계산 로직 추가)
    # 데이터프레임 내에 이미 계산된 값이 없다면 즉석에서 생성
    if 'Hist_Rule40' not in recent_df.columns:
        # TTM 성장률 + TTM FCF 마진
        growth = recent_df.get('Rev_Growth', 0) * 100
        margin = (recent_df.get('FCF_TTM', 0) / recent_df.get('Revenue_TTM', 1).replace(0, 1)) * 100
        recent_df['Hist_Rule40'] = growth + margin
        
    # 시각화: 선 굵기와 투명 배경 추가로 가시성 극대화
    fig.add_trace(go.Scatter(x=recent_df.index, y=recent_df['Hist_Rule40'], 
                             name="Rule of 40 Score", 
                             line=dict(color='#805AD5', width=3), 
                             fill='tozeroy', fillcolor='rgba(128, 90, 213, 0.1)'), row=3, col=1)
    
    # 가이드라인 (40점 기준선)
    fig.add_hline(y=40, line_dash="dash", line_color="#DD6B20", 
                  annotation_text="Rule of 40 Target", row=3, col=1)

    # 전체 레이아웃 정밀 조정
    fig.update_layout(height=1000, template="plotly_white", showlegend=True,
                      margin=dict(l=20, r=20, t=80, b=20),
                      hovermode="x unified")
    
    # Y축 범위 가이드 (Z-Score 가독성)
    fig.update_yaxes(range=[-4, 4], row=2, col=1) 
    
    return fig