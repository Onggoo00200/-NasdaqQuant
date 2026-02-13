"""
ChoiceStock NVDA 데이터 스크래핑 스크립트
- 대상 사이트: https://www.choicestock.co.kr/search/summary/NVDA
- 추출 데이터: 투자지표, 재무제표 테이블
- 출력 파일: NVDA_ChoiceStock_Report.xlsx
"""
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd

def create_driver():
    """Headless Chrome WebDriver 생성"""
    chrome_options = Options()
    
    # Headless 모드 설정
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # User-Agent 설정 (일반 윈도우 PC처럼 보이도록)
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
    
    # 봇 탐지 회피를 위한 추가 설정
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # navigator.webdriver 속성 숨기기
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            })
        """
    })
    
    return driver

def extract_tables(driver, url):
    """페이지에서 모든 테이블 추출"""
    print(f"[정보] 페이지 접속 중: {url}")
    driver.get(url)
    
    # 5초 대기 (JavaScript 로딩 대기)
    print("[정보] 페이지 로딩 대기 중 (5초)...")
    time.sleep(5)
    
    # 모든 <table> 태그 찾기
    tables = driver.find_elements(By.TAG_NAME, "table")
    print(f"[정보] 발견된 테이블 수: {len(tables)}")
    
    if not tables:
        # 테이블이 없으면 페이지 소스 일부 출력
        page_source = driver.page_source
        print("\n[경고] 테이블을 찾을 수 없습니다!")
        print("=" * 60)
        print("[디버그] 페이지 소스 일부:")
        print(page_source[:3000])
        print("=" * 60)
        return None
    
    return tables

def parse_tables_to_dataframes(driver):
    """테이블을 Pandas DataFrame으로 변환"""
    # Pandas read_html을 사용하여 모든 테이블 읽기
    try:
        dfs = pd.read_html(driver.page_source, encoding='utf-8')
        print(f"[정보] Pandas로 파싱된 테이블 수: {len(dfs)}")
        return dfs
    except ValueError as e:
        print(f"[오류] 테이블 파싱 실패: {e}")
        return []

def find_target_tables(dfs):
    """투자지표와 재무제표 관련 테이블 찾기"""
    result = {}
    
    keywords_investment = ['PER', 'PBR', 'ROE', 'EPS', '배당', '시가총액', '투자지표']
    keywords_financial = ['매출', '영업이익', '순이익', '자산', '부채', '자본', '재무']
    
    for i, df in enumerate(dfs):
        # DataFrame을 문자열로 변환하여 키워드 검색
        df_str = df.to_string()
        
        # 투자지표 테이블 확인
        if any(keyword in df_str for keyword in keywords_investment):
            sheet_name = f'투자지표_{len([k for k in result.keys() if "투자" in k]) + 1}'
            result[sheet_name] = df
            print(f"[정보] '{sheet_name}' 테이블 발견 (인덱스: {i})")
        
        # 재무제표 테이블 확인
        elif any(keyword in df_str for keyword in keywords_financial):
            sheet_name = f'재무제표_{len([k for k in result.keys() if "재무" in k]) + 1}'
            result[sheet_name] = df
            print(f"[정보] '{sheet_name}' 테이블 발견 (인덱스: {i})")
    
    # 관련 테이블을 못 찾은 경우, 모든 테이블 저장
    if not result:
        print("[경고] 투자지표/재무제표 관련 테이블을 찾지 못했습니다.")
        print("[정보] 발견된 모든 테이블을 저장합니다.")
        for i, df in enumerate(dfs):
            result[f'테이블_{i + 1}'] = df
    
    return result

def save_to_excel(tables_dict, output_file):
    """여러 테이블을 Excel 파일로 저장 (시트별로)"""
    if not tables_dict:
        print("[오류] 저장할 테이블이 없습니다.")
        return False
    
    try:
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            for sheet_name, df in tables_dict.items():
                # Excel 시트 이름 제한 (31자)
                safe_name = sheet_name[:31]
                df.to_excel(writer, sheet_name=safe_name, index=False)
                print(f"[정보] 시트 '{safe_name}' 저장 완료")
        
        print(f"\n[성공] Excel 파일 저장 완료: {output_file}")
        return True
    except Exception as e:
        print(f"[오류] Excel 저장 실패: {e}")
        return False

def main():
    """메인 실행 함수"""
    url = "https://www.choicestock.co.kr/search/summary/NVDA"
    output_file = "NVDA_ChoiceStock_Report.xlsx"
    
    driver = None
    try:
        # WebDriver 생성
        driver = create_driver()
        
        # 테이블 추출
        tables = extract_tables(driver, url)
        
        if tables is None:
            print("[실패] 프로그램을 종료합니다.")
            return
        
        # DataFrame으로 변환
        dfs = parse_tables_to_dataframes(driver)
        
        if not dfs:
            print("[실패] 테이블을 DataFrame으로 변환하지 못했습니다.")
            # 페이지 소스 일부 출력
            print("\n[디버그] 페이지 소스 일부:")
            print(driver.page_source[:3000])
            return
        
        # 투자지표/재무제표 테이블 찾기
        target_tables = find_target_tables(dfs)
        
        # Excel로 저장
        save_to_excel(target_tables, output_file)
        
    except Exception as e:
        print(f"[오류] 예상치 못한 에러 발생: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if driver:
            driver.quit()
            print("[정보] WebDriver 종료")

if __name__ == "__main__":
    main()
