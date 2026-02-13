@echo off
REM Set console code page to UTF-8
CHCP 65001 > NUL

echo --- Starting FastAPI Backend Server ---

REM Change to script directory
cd /d "%~dp0"

REM Activate venv
if exist "venv\Scripts\activate.bat" (
    call .\venv\Scripts\activate.bat
) else (
    echo Virtual environment not found. Please ensure venv is set up.
    pause
    exit /b
)

REM Run Uvicorn
echo Running Uvicorn server...
uvicorn main:app --reload --host 0.0.0.0 --port 8000

pause
