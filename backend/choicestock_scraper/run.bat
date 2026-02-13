@echo off
chcp 65001
echo ========================================================
echo [Choicestock Scraper] 프로그램 준비 중...
echo ========================================================

:: 1. 파이썬 설치 여부 확인
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [오류] Python이 설치되어 있지 않습니다.
    echo https://www.python.org/downloads/ 에서 Python을 먼저 설치해주세요.
    pause
    exit
)

:: 2. 필수 라이브러리 설치 (처음에만 시간이 걸림)
echo 필수 라이브러리를 확인하고 설치합니다...
pip install -r requirements.txt

:: 3. Streamlit 앱 실행
echo.
echo 프로그램을 실행합니다. 잠시만 기다려주세요...
echo 브라우저가 자동으로 열립니다.
echo.
streamlit run app.py

pause
