@echo off
chcp 65001 > nul 2>&1
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo.
echo ========================================
echo   Gugupet Installer
echo ========================================
echo.

:: ---- Check Python ----
python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found.
    echo Please install Python 3.10+ from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during install.
    echo.
    pause
    exit /b 1
)
for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo [1/4] Python %PYVER% found OK

:: ---- Install dependencies ----
echo [2/4] Installing dependencies...
python -m pip install --upgrade pip --quiet
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install dependencies. Check network connection.
    pause
    exit /b 1
)
echo [2/4] Dependencies installed OK

:: ---- Init dirs ----
echo [3/4] Initializing directories...
if not exist runtime mkdir runtime
if not exist memory mkdir memory
echo [3/4] Directories ready

:: ---- Create shortcuts via Python ----
echo [4/4] Creating desktop shortcuts...
python setup_shortcuts.py
if %errorlevel% neq 0 (
    echo [WARN] Could not create shortcuts. Run start.bat manually.
) else (
    echo [4/4] Desktop shortcuts created OK
)

echo.
echo ========================================
echo   Installation complete!
echo ========================================
echo.
echo Desktop shortcuts created:
echo   - Gugupet           : launch the pet
echo   - Gugupet Panel     : open control panel / chat
echo.
echo First run: open the control panel and set your API Key.
echo Or just double-click start.bat to launch.
echo.
pause
