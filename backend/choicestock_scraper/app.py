import streamlit as st
import pandas as pd
import os
import traceback
import FinanceDataReader as fdr
from choicestock import generate_excel_report
from deep_translator import GoogleTranslator
from streamlit_searchbox import st_searchbox # Import Searchbox
import re

st.set_page_config(page_title="ChoiceStock Scraper", layout="wide")

st.title("📈 종목 분석 데이터 스크레이퍼")
st.caption("데이터 소스: choicestock.co.kr | 제공: FinanceDataReader | 번역: Deep Translator")

# --- Helper Function: Load Stock Data ---
@st.cache_data
def get_stock_list():
    """
    Loads stock lists for KRX (Korea) and ALL US Stocks (NASDAQ, NYSE, AMEX).
    """
    all_dfs = []

    # 1. KRX (Korean Stocks)
    try:
        df_krx = fdr.StockListing('KRX')
        df_krx = df_krx[['Code', 'Name']]
        df_krx['Display'] = df_krx['Name'] + " (" + df_krx['Code'] + ") - KRX"
        df_krx['Market'] = 'KRX'
        all_dfs.append(df_krx)
    except Exception as e:
        st.error(f"한국 주식 목록 로드 실패: {e}")

    # 2. Manual Korean Mapping (Optional but good for speed)
    us_mapping = {
        "엔비디아": "NVDA", "테슬라": "TSLA", "애플": "AAPL", "마이크로소프트": "MSFT",
        "구글": "GOOGL", "아마존": "AMZN", "메타": "META", 
        "넷플릭스": "NFLX", "AMD": "AMD", "인텔": "INTC", "TSMC": "TSM",
        "크레도": "CRDO", "크레도테크놀로지": "CRDO",
        "슈퍼마이크로": "SMCI", "슈퍼마이크로컴퓨터": "SMCI",
        "암": "ARM"
    }
    
    us_manual_data = []
    for kor_name, ticker in us_mapping.items():
        us_manual_data.append({
            'Code': ticker,
            'Name': kor_name,
            'Display': f"★ {kor_name} ({ticker}) - 주요미국주식",
            'Market': 'US_POPULAR'
        })
    all_dfs.append(pd.DataFrame(us_manual_data))

    # 3. All US Stocks (NASDAQ, NYSE, AMEX)
    us_markets = ['NASDAQ', 'NYSE', 'AMEX']
    for market in us_markets:
        try:
            df = fdr.StockListing(market)
            df = df[['Symbol', 'Name']]
            df.columns = ['Code', 'Name']
            df['Display'] = df['Name'] + " (" + df['Code'] + ") - " + market
            df['Market'] = market
            all_dfs.append(df)
        except Exception as e:
            print(f"Failed to load {market}: {e}")

    if all_dfs:
        combined_df = pd.concat(all_dfs, ignore_index=True)
        combined_df.drop_duplicates(subset=['Code'], keep='first', inplace=True)
        return combined_df
    else:
        return pd.DataFrame()

# --- Load Data ---
with st.spinner("전체 종목 리스트(KRX + 미국 전체)를 불러오는 중입니다..."):
    stock_df = get_stock_list()

# --- Search Logic for st_searchbox ---
def search_stock_function(searchterm: str):
    """
    Callback function for the searchbox.
    Returns a list of tuples: (Label, Value)
    """
    if not searchterm:
        return []
    
    searchterm = searchterm.strip()
    
    # 1. Direct Search (Korean Name, English Name, Ticker)
    mask = (
        stock_df['Name'].str.contains(searchterm, case=False, na=False) | 
        stock_df['Code'].str.contains(searchterm, case=False, na=False)
    )
    
    results = stock_df[mask]

    # 2. Translation Search (if Korean input and few results found directly)
    if bool(re.search("[가-힣]", searchterm)):
        try:
            translated = GoogleTranslator(source='ko', target='en').translate(searchterm)
            if translated and translated.lower() != searchterm.lower():
                mask_trans = stock_df['Name'].str.contains(translated, case=False, na=False)
                results = pd.concat([results, stock_df[mask_trans]])
        except:
            pass 

    results = results.drop_duplicates(subset=['Code']).head(20)
    
    return list(zip(results['Display'], results['Code']))

# --- Search Interface ---
st.write("### 🔍 스마트 종목 검색")
st.markdown("한글(자동 번역됨), 영어, 티커로 검색하여 리스트에서 바로 선택하세요.")

selected_ticker = st_searchbox(
    search_stock_function,
    key="stock_searchbox",
    placeholder="종목명 또는 티커 입력 (예: 삼성, 크레도, Credo, NVDA)",
    label=None, 
    clear_on_submit=False,
)

# --- Scrape Logic ---
if selected_ticker:
    st.info(f"선택된 종목: **{selected_ticker}**")
    
    if st.button(f"'{selected_ticker}' 데이터 가져오기"):
        target_ticker = selected_ticker
        
        with st.spinner(f"'{target_ticker}'의 재무 데이터를 choicestock.co.kr에서 가져오는 중..."):
            try:
                # Generate the report
                excel_filename = generate_excel_report(target_ticker)

                if excel_filename and os.path.exists(excel_filename):
                    st.success(f"✅ '{target_ticker}' 데이터 스크레이핑 완료!")

                    # Read the generated Excel file
                    try:
                        with open(excel_filename, "rb") as f:
                            excel_data = f.read()

                        # --- Display Data & Download Button ---
                        col1, col2 = st.columns([1, 4])
                        with col1:
                            st.download_button(
                                label=f"💾 엑셀 다운로드",
                                data=excel_data,
                                file_name=excel_filename,
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            )
                        
                        # Use context manager
                        with pd.ExcelFile(excel_filename) as xls:
                            sheet_names = xls.sheet_names
                            st.info(f"발견된 시트: {', '.join(sheet_names)}")
                            tabs = st.tabs([f"📄 {name}" for name in sheet_names])
                            for i, sheet in enumerate(sheet_names):
                                with tabs[i]:
                                    df = pd.read_excel(xls, sheet_name=sheet)
                                    st.dataframe(df, use_container_width=True)
                        
                    except Exception as read_error:
                         st.error(f"파일을 읽는 중 오류가 발생했습니다: {read_error}")
                    finally:
                        if os.path.exists(excel_filename):
                            os.remove(excel_filename)

                else:
                    st.error("데이터를 가져오는 데 실패했습니다.")

            except Exception as e:
                st.error("오류가 발생했습니다.")
                st.code(traceback.format_exc())
