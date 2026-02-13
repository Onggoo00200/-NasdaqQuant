from bs4 import BeautifulSoup
import pandas as pd
import io
import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

class ChoiceStockScraper:
    def __init__(self):
        self.base_url = "https://www.choicestock.co.kr/search"
        self.driver = None

    def _init_driver(self):
        """Selenium WebDriver 초기화"""
        try:
            options = webdriver.ChromeOptions()
            options.add_argument("--headless=new") # 백그라운드 실행
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            return True
        except Exception as e:
            print(f"[Scraper] Driver Init Error: {e}")
            return False

    def _get_page_source(self, url):
        try:
            if not self.driver: self._init_driver()
            self.driver.get(url)
            WebDriverWait(self.driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            return self.driver.page_source
        except Exception as e:
            print(f"[Scraper] Page Load Error ({url}): {e}")
            return None

    def _clean_df(self, df):
        if df.empty: return df
        # 멀티 인덱스 평탄화
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = ['_'.join(col).strip() if isinstance(col, tuple) else str(col) for col in df.columns.values]
        
        # 불필요한 컬럼 제거
        df = df.loc[:, ~df.columns.duplicated()]
        df = df.dropna(how='all').reset_index(drop=True)
        return df

    def get_financial_data(self, ticker):
        """
        특정 티커의 재무 데이터를 스크래핑하여 딕셔너리로 반환.
        Keys: income_statement, balance_sheet, cash_flow, indicators
        """
        ticker = ticker.upper()
        print(f"[ChoiceStock] {ticker} 데이터 수집 시작 (Selenium)...")
        
        data = {}
        if not self._init_driver(): return None

        try:
            # 1. 투자지표 (Invest)
            url_invest = f"{self.base_url}/invest/{ticker}"
            src_invest = self._get_page_source(url_invest)
            if src_invest:
                soup = BeautifulSoup(src_invest, 'html.parser')
                table = soup.select_one("table.tableRanking")
                if table:
                    df = pd.read_html(io.StringIO(str(table)))[0]
                    data['indicators'] = self._clean_df(df)

            # 2. 재무제표 (Financials)
            url_fin = f"{self.base_url}/financials/{ticker}"
            src_fin = self._get_page_source(url_fin)
            if src_fin:
                soup = BeautifulSoup(src_fin, 'html.parser')
                wraps = soup.select(".scroll_table_wrap")
                
                sheet_map = {
                    "손익계산서": "income_statement", 
                    "재무상태표": "balance_sheet", 
                    "현금흐름표": "cash_flow"
                }
                
                for wrap in wraps:
                    title = wrap.select_one("h4.table_title")
                    if not title: continue
                    title_text = title.get_text(strip=True)
                    
                    for k_kor, k_eng in sheet_map.items():
                        if k_kor in title_text:
                            table = wrap.select_one("table.tableRanking")
                            if table:
                                df = pd.read_html(io.StringIO(str(table)))[0]
                                data[k_eng] = self._clean_df(df)
                            break
                            
        except Exception as e:
            print(f"[Scraper] Execution Error: {e}")
        finally:
            if self.driver:
                self.driver.quit()
                self.driver = None
        
        return data if data else None

# 전역 인스턴스 (필요시 사용)
scraper = ChoiceStockScraper()
