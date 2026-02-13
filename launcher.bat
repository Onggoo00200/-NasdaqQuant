@echo off
title Nasdaq Quant Agent Center
:menu
cls
echo ==========================================
echo      NASDAQ QUANT AGENT SYSTEM (V2)
echo ==========================================
echo  1. Start MCP Server (For AI Chat)
echo  2. Launch Web Dashboard (Refactored UI)
echo  3. Exit
echo ==========================================
set /p choice="Select an option (1-3): "

if "%choice%"=="1" goto server
if "%choice%"=="2" goto streamlit
if "%choice%"=="3" exit

:server
echo Starting MCP Server...
cd /d "C:\Users\yuikh\.gemini\antigravity\scratch\NasdaqQuant_Async"
"..\finance-project\venv\Scripts\python.exe" "src/interface/mcp_server.py"
pause
goto menu

:streamlit
echo Launching Refactored Web Dashboard...
cd /d "C:\Users\yuikh\.gemini\antigravity\scratch\NasdaqQuant_Async"
"..\finance-project\venv\Scripts\streamlit.exe" run "src/interface/dashboard.py"
pause
goto menu
