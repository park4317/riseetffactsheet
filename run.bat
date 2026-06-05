@echo off
cd /d "%~dp0"

echo.
echo ============================================
echo  RISE ETF Factsheet System - Starting...
echo ============================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.10+
    pause & exit /b 1
)

echo [Setup] Installing required packages...
pip install flask requests beautifulsoup4 pandas openpyxl jinja2 lxml --quiet
echo [Setup] Done.
echo.

echo [Server] Starting on port 5100...
echo [Access] http://localhost:5100
echo [Stop]   Close this window or press Ctrl+C
echo.

start /min cmd /c "timeout /t 4 /nobreak >nul && start http://localhost:5100"
python app.py

pause
