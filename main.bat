@echo off
chcp 65001 >nul
cd /d "%~dp0"

:: 直接用虚拟环境中的 Python 运行 main.py
if exist "%~dp0.venv\Scripts\python.exe" (
    "%~dp0.venv\Scripts\python.exe" "%~dp0main.py"
) else (
    echo 请先运行 run.bat 完成初始化
    pause
)
pause
