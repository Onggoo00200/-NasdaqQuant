@echo off
REM Set console code page to UTF-8 for better character display
CHCP 65001 > NUL

echo --- Starting ChoicestockUS Scraper ---

REM Change to the directory where this script is located (backend directory)
cd /d "%~dp0"

REM Activate the virtual environment and run the Python script
REM Use 'call' to ensure the activate script fully executes and returns control
call .\venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo Error: Failed to activate virtual environment.
    goto :eof
)

REM Run the Python scraper script
python choicestock_scraper\choicestock.py

REM Keep the console window open after execution
echo.
echo Operation complete. Press any key to exit...
pause > NUL