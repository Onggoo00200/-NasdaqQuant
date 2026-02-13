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

def get_driver():
    """Initializes and returns a NEW Selenium WebDriver instance."""
    print("Initializing new Selenium WebDriver...")
    try:
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        print("WebDriver initialized successfully.")
        return driver
    except Exception as e:
        print(f"FATAL: Error initializing WebDriver: {e}")
        return None

def get_page_source_with_driver(driver, url: str) -> str | None:
    """Fetches a URL using the PROVIDED driver."""
    try:
        driver.get(url)
        # Increased timeout to 20 seconds
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        return driver.page_source
    except Exception as e:
        print(f"An unexpected error occurred in Selenium: {e}")
        return None

def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Cleans and formats a DataFrame."""
    if df.empty: return df
    
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = ['_'.join(col).strip() if isinstance(col, tuple) else str(col) for col in df.columns.values]
    
    if df.columns.empty: return df
    
    first_col_name = df.columns[0]
    if first_col_name.startswith('Unnamed:') or first_col_name == '항목':
        df = df.rename(columns={first_col_name: '구분'})
    
    df = df.loc[:, ~df.columns.duplicated()]
    
    if '구분' in df.columns:
        df['구분'] = df['구분'].ffill()
        df = df.dropna(subset=['구분'])
        if not df.empty and df.iloc[0].astype(str).tolist() == df.columns.astype(str).tolist():
            df = df.iloc[1:]

    df = df.dropna(how='all').reset_index(drop=True)
    return df

def generate_excel_report(ticker: str) -> str | None:
    """
    Generates a financial report for the given ticker.
    Creates a fresh WebDriver for each call to ensure stability.
    """
    print(f"Starting Excel report generation for {ticker}...")
    base_url = "https://www.choicestock.co.kr/search"
    output_file = f"{ticker}_ChoiceStock_Report.xlsx"
    all_data_frames = {}

    # Initialize Driver HERE
    driver = get_driver()
    if not driver:
        return None

    try:
        # 1. Investment Indicators
        invest_url = f"{base_url}/invest/{ticker}"
        invest_source = get_page_source_with_driver(driver, invest_url)
        
        if invest_source:
            soup = BeautifulSoup(invest_source, 'html.parser')
            # Try multiple selectors just in case
            table_html = soup.select_one(".scroll_table_wrap > .scroll_table > table.tableRanking.table_search_invest")
            if not table_html:
                 table_html = soup.select_one("table.tableRanking") # Fallback
            
            if table_html:
                try:
                    df = pd.read_html(io.StringIO(str(table_html)))[0]
                    all_data_frames["투자지표"] = clean_dataframe(df)
                    print(f"Successfully scraped Investment Indicators for {ticker}.")
                except Exception as e:
                    print(f"ERROR: Could not parse investment indicators table: {e}")
            else:
                 print("WARNING: Investment table not found in HTML.")

        # 2. Financial Statements
        fin_url = f"{base_url}/financials/{ticker}"
        fin_source = get_page_source_with_driver(driver, fin_url)
        
        if fin_source:
            soup = BeautifulSoup(fin_source, 'html.parser')
            all_tables_wrap = soup.select(".scroll_table_wrap")
            sheet_map = {"손익계산서": "손익계산서", "재무상태표": "재무상태표", "현금흐름표": "현금흐름표"}

            for wrap in all_tables_wrap:
                title_tag = wrap.select_one("h4.table_title")
                if not title_tag: continue
                
                title_text = title_tag.get_text(strip=True)
                
                for key_korean, title_to_find in sheet_map.items():
                    if title_to_find in title_text:
                        table_html = wrap.select_one("table.tableRanking")
                        if table_html:
                            try:
                                df = pd.read_html(io.StringIO(str(table_html)))[0]
                                all_data_frames[key_korean] = clean_dataframe(df)
                                print(f"Successfully scraped {title_to_find} for {ticker}.")
                            except Exception as e:
                                print(f"ERROR: Could not parse table for {title_to_find}: {e}")
                        break
        
    except Exception as e:
        print(f"ERROR during scraping execution: {e}")
    finally:
        # ALWAYS quit the driver
        print("Quitting Selenium WebDriver...")
        driver.quit()

    if not all_data_frames:
        print(f"WARNING: No data was scraped for {ticker}. Excel report not created.")
        return None

    print(f"Saving data to {output_file}...")
    try:
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            for sheet_name, df_to_save in all_data_frames.items():
                if not df_to_save.empty:
                    df_to_save.to_excel(writer, sheet_name=sheet_name, index=False)
                else:
                    print(f"WARNING: No data for sheet '{sheet_name}'. Skipping.")
        print(f"Successfully saved report to {output_file}.")
        return output_file
    except Exception as e:
        print(f"ERROR saving Excel file: {e}")
        return None

def scrape_data(ticker: str) -> dict | None:
    """
    Scrapes financial data for the given ticker and returns a dictionary of DataFrames.
    Keys: "investment_indicators", "income_statement", "balance_sheet", "cash_flow"
    """
    print(f"Starting scraping for {ticker}...")
    base_url = "https://www.choicestock.co.kr/search"
    data_frames = {}

    driver = get_driver()
    if not driver:
        return None

    try:
        # 1. Investment Indicators
        invest_url = f"{base_url}/invest/{ticker}"
        invest_source = get_page_source_with_driver(driver, invest_url)
        
        if invest_source:
            soup = BeautifulSoup(invest_source, 'html.parser')
            table_html = soup.select_one(".scroll_table_wrap > .scroll_table > table.tableRanking.table_search_invest")
            if not table_html:
                 table_html = soup.select_one("table.tableRanking")
            
            if table_html:
                try:
                    df = pd.read_html(io.StringIO(str(table_html)))[0]
                    data_frames["investment_indicators"] = clean_dataframe(df)
                    print(f"Successfully scraped Investment Indicators for {ticker}.")
                except Exception as e:
                    print(f"ERROR: Could not parse investment indicators table: {e}")

        # 2. Financial Statements
        fin_url = f"{base_url}/financials/{ticker}"
        fin_source = get_page_source_with_driver(driver, fin_url)
        
        if fin_source:
            soup = BeautifulSoup(fin_source, 'html.parser')
            all_tables_wrap = soup.select(".scroll_table_wrap")
            
            # Map Korean titles to English keys expected by frontend
            sheet_map = {
                "손익계산서": "income_statement", 
                "재무상태표": "balance_sheet", 
                "현금흐름표": "cash_flow"
            }

            for wrap in all_tables_wrap:
                title_tag = wrap.select_one("h4.table_title")
                if not title_tag: continue
                
                title_text = title_tag.get_text(strip=True)
                
                for key_korean, key_eng in sheet_map.items():
                    if key_korean in title_text:
                        table_html = wrap.select_one("table.tableRanking")
                        if table_html:
                            try:
                                df = pd.read_html(io.StringIO(str(table_html)))[0]
                                data_frames[key_eng] = clean_dataframe(df)
                                print(f"Successfully scraped {key_korean} as {key_eng} for {ticker}.")
                            except Exception as e:
                                print(f"ERROR: Could not parse table for {key_korean}: {e}")
                        break
        
    except Exception as e:
        print(f"ERROR during scraping execution: {e}")
    finally:
        print("Quitting Selenium WebDriver...")
        driver.quit()

    if not data_frames:
        return None
        
    return data_frames

def scrape_stock_data_json(ticker: str) -> dict | None:
    """
    Scrapes data and converts it to a JSON-friendly format (list of dicts).
    """
    data = scrape_data(ticker)
    if not data:
        return None
    
    json_data = {"ticker": ticker}
    for key, df in data.items():
        # Replace NaN with null (None) for JSON validity
        json_data[key] = df.where(pd.notnull(df), None).to_dict(orient='records')
        
    return json_data

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        ticker = sys.argv[1].upper()
    else:
        ticker = input("조회할 종목 코드를 입력하세요 (예: AAPL, NVDA): ").strip().upper()
    
    if ticker:
        generate_excel_report(ticker)
