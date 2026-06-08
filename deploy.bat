@echo off
cd /d "%~dp0"

echo.
echo ============================================
echo  RISE ETF - Generate + Deploy to GitHub
echo ============================================
echo.

:: Check git
git --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Git not installed. Download from https://git-scm.com
    pause & exit /b 1
)

:: Check python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found.
    pause & exit /b 1
)

:: Install packages
echo [1/5] Checking packages...
pip install requests beautifulsoup4 pandas openpyxl jinja2 lxml yfinance --quiet

:: Generate all factsheets
echo [2/5] Generating factsheets...
cd pipeline
python main.py
cd ..

:: Copy output files to docs/output/
echo [3/5] Copying to docs/...
if not exist docs\output mkdir docs\output
xcopy /Y /Q output\*.html docs\output\ >nul 2>&1

:: Build index.html
echo [4/5] Building index page...
python build_index.py

:: Git push
echo [5/5] Pushing to GitHub...
git add docs/
git add output/
git commit -m "Update factsheets %DATE% %TIME:~0,5%"
git push

echo.
echo ============================================
echo  Done! GitHub Pages will update in ~1 min.
echo ============================================
echo.
pause
