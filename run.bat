@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ================================
echo   baibot — AI 助手启动中...
echo ================================
echo.

set "PYTHON_EXE=%USERPROFILE%\python-sdk\python3.13.2\python.exe"
if exist "%PYTHON_EXE%" goto :found_python

set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
if exist "%PYTHON_EXE%" goto :found_python

set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if exist "%PYTHON_EXE%" goto :found_python

set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
if exist "%PYTHON_EXE%" goto :found_python

set "PYTHON_EXE=C:\Python313\python.exe"
if exist "%PYTHON_EXE%" goto :found_python

set "PYTHON_EXE=C:\Python312\python.exe"
if exist "%PYTHON_EXE%" goto :found_python

set "PYTHON_EXE=C:\Python311\python.exe"
if exist "%PYTHON_EXE%" goto :found_python

set "PYTHON_EXE="
for /f "tokens=*" %%a in ('where python 2^>nul') do (
    "%%a" --version >nul 2>&1
    if not errorlevel 1 (
        set "PYTHON_EXE=%%a"
        goto :found_python
    )
)

echo [失败] 未找到可用的 Python！
echo.
echo   预期路径: %USERPROFILE%\python-sdk\python3.13.2\python.exe
echo.
echo   如该路径不存在，请安装 Python 3.10+
echo   下载: https://www.python.org/downloads/
echo.
pause
exit /b 1

:found_python
echo [OK] Python: %PYTHON_EXE%

set "VENV_DIR=%~dp0.venv"
set "MARKER_FILE=%~dp0.venv\.installed"

if not exist "%VENV_DIR%" (
    echo.
    echo [1/3] 正在创建虚拟环境...
    "%PYTHON_EXE%" -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo [失败] 虚拟环境创建失败
        pause
        exit /b 1
    )
    echo       完成
)

call "%VENV_DIR%\Scripts\activate.bat" >nul

if not exist "%MARKER_FILE%" (
    echo [2/3] 正在安装依赖...
    pip install --quiet -r "%~dp0requirements.txt"
    if errorlevel 1 (
        echo [失败] 依赖安装失败，请检查网络
        pause
        exit /b 1
    )
    type nul > "%MARKER_FILE%"
    echo       完成
) else (
    echo [2/3] 依赖已安装，跳过
)

echo.
echo [3/3] 启动 baibot...
echo.
echo   输入 /help 查看命令帮助
echo   输入 /exit 退出程序
echo.

"%~dp0.venv\Scripts\python.exe" "%~dp0main.py"

pause
