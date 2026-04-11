@echo off
chcp 65001 > nul 2>&1
cd /d "%~dp0"

:: Quick dependency check — auto-install if missing
python -c "import PIL; import yaml" >nul 2>&1
if %errorlevel% neq 0 (
    echo 正在安装依赖...
    python -m pip install -r requirements.txt >nul 2>&1
)

:: Ensure runtime dirs exist
if not exist runtime mkdir runtime
if not exist memory mkdir memory

:: Launch (brain + body together)
echo 启动咕咕桌宠...
pythonw app/launcher.py
if %errorlevel% neq 0 (
    echo.
    echo 启动失败，尝试使用 python 模式...
    python app/launcher.py
    if %errorlevel% neq 0 (
        echo.
        echo ERROR: 启动失败，请运行 install.bat 检查环境
        pause
    )
)
