@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ================================
echo   baibot — AI 助手控制面板
echo ================================
echo.

set "PYTHON_EXE=%USERPROFILE%\python-sdk\python3.13.2\python.exe"
if exist "%PYTHON_EXE%" goto :found_python

set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python314\python.exe"
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
set "PID_FILE=%~dp0baibot.pid"
set "LOG_FILE=%~dp0baibot.log"

if not exist "%VENV_DIR%" (
    echo.
    echo [1/2] 正在创建虚拟环境...
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
    echo [2/2] 正在安装依赖...
    pip install --quiet -r "%~dp0requirements.txt"
    if errorlevel 1 (
        echo [失败] 依赖安装失败，请检查网络
        pause
        exit /b 1
    )
    type nul > "%MARKER_FILE%"
    echo       完成
) else (
    echo [2/2] 依赖已安装，跳过
)

echo.
echo  初始化完成！请选择运行模式:
echo.
echo   ── 命令行参数 ──
echo   deploy.bat cli        命令行聊天
echo   deploy.bat start      启动 WebUI
echo   deploy.bat stop       停止 WebUI
echo   deploy.bat restart    重启 WebUI
echo   deploy.bat status     查看状态
echo   deploy.bat log        查看日志
echo   deploy.bat update     更新依赖
echo   deploy.bat uninstall  卸载
echo.

:: ── 命令行参数路由 ──
if /i "%~1"=="cli"       goto :cli
if /i "%~1"=="start"     goto :webui
if /i "%~1"=="stop"      goto :stop
if /i "%~1"=="restart"   goto :restart
if /i "%~1"=="status"    goto :status
if /i "%~1"=="log"       goto :log
if /i "%~1"=="update"    goto :update_deps
if /i "%~1"=="uninstall" goto :uninstall

:: ── 无参数 → 显示交互菜单 ──
:menu
echo [1] 命令行聊天
echo [2] 启动 WebUI（后台运行）
echo [3] 停止 WebUI
echo [4] 重启 WebUI
echo [5] 查看状态
echo [6] 查看日志
echo [7] 更新依赖
echo [8] 卸载
echo [0] 退出
echo.
set "choice="
set /p "choice=请输入数字: "

if "%choice%"=="0" exit /b
if "%choice%"=="1" goto :cli
if "%choice%"=="2" goto :webui
if "%choice%"=="3" goto :stop
if "%choice%"=="4" goto :restart
if "%choice%"=="5" goto :status
if "%choice%"=="6" goto :log
if "%choice%"=="7" goto :update_deps
if "%choice%"=="8" goto :uninstall

echo 无效输入
timeout /t 1 /nobreak >nul
goto :menu

:: ============================================================
:cli
echo.
echo 启动命令行聊天模式...
echo 输入 /help 查看命令帮助  /exit 退出
echo.
"%~dp0.venv\Scripts\python.exe" "%~dp0main.py"
pause
goto :menu

:: ============================================================
:webui
:: 如果已运行则先停
if exist "%PID_FILE%" (
    set /p _p=<"%PID_FILE%"
    taskkill /PID %_p% /F >nul 2>&1
    del "%PID_FILE%" >nul 2>&1
    timeout /t 1 /nobreak >nul
)

echo.
echo 启动 WebUI 服务...
powershell -Command "$p=Start-Process -FilePath '%VENV_DIR%\Scripts\python.exe' -ArgumentList '%~dp0server.py' -WindowStyle Hidden -PassThru; $p.Id | Out-File -Encoding ASCII '%PID_FILE%'"
timeout /t 3 /nobreak >nul

if not exist "%PID_FILE%" (
    echo [失败] 未生成 PID 文件
    pause
    goto :menu
)
set /p _p=<"%PID_FILE%"
tasklist /FI "PID eq %_p%" 2>nul | findstr "%_p%" >nul
if errorlevel 1 (
    echo [失败] 启动失败，查看日志: type "%LOG_FILE%"
    del "%PID_FILE%" >nul 2>&1
    pause
    goto :menu
)

echo.
echo   +----------------------------------------+
echo   ^|  baibot WebUI 已启动                   ^|
echo   ^|                                        ^|
echo   ^|  http://localhost:7200                  ^|
echo   ^|                                        ^|
echo   ^|  停止: deploy.bat stop                 ^|
echo   ^|  状态: deploy.bat status               ^|
echo   ^+----------------------------------------+
echo.
pause
goto :menu

:: ============================================================
:stop
if not exist "%PID_FILE%" (
    echo 服务未运行
    pause
    goto :menu
)
set /p _p=<"%PID_FILE%"
taskkill /PID %_p% /F >nul 2>&1
del "%PID_FILE%" >nul 2>&1
echo 已停止
pause
goto :menu

:: ============================================================
:restart
if exist "%PID_FILE%" (
    set /p _p=<"%PID_FILE%"
    taskkill /PID %_p% /F >nul 2>&1
    del "%PID_FILE%" >nul 2>&1
    timeout /t 1 /nobreak >nul
)
echo 重启 WebUI...
goto :webui

:: ============================================================
:status
if exist "%PID_FILE%" (
    set /p _p=<"%PID_FILE%"
    tasklist /FI "PID eq %_p%" 2>nul | findstr "%_p%" >nul
    if errorlevel 1 (
        echo 服务未运行（PID 文件残留）
    ) else (
        echo.
        echo 运行中  PID: %_p%  端口: 7200
        echo http://localhost:7200
        echo.
    )
) else (
    echo 服务未运行
)
pause
goto :menu

:: ============================================================
:log
if exist "%LOG_FILE%" (
    type "%LOG_FILE%"
) else (
    echo 暂无日志
)
pause
goto :menu

:: ============================================================
:update_deps
echo 更新依赖...
call "%VENV_DIR%\Scripts\activate.bat" >nul
pip install --quiet --upgrade pip
pip install --quiet --upgrade -r "%~dp0requirements.txt"
echo 完成
pause
goto :menu

:: ============================================================
:uninstall
echo.
echo [警告] 将删除虚拟环境、日志和持久化配置
echo 项目源代码不会被删除
echo.
set "confirm="
set /p "confirm=确认卸载？输入 yes 继续: "
if /i not "%confirm%"=="yes" (
    echo 已取消
    pause
    goto :menu
)

if exist "%PID_FILE%" (
    set /p _p=<"%PID_FILE%"
    taskkill /PID %_p% /F >nul 2>&1
    del "%PID_FILE%" >nul 2>&1
)

if exist "%VENV_DIR%" rmdir /s /q "%VENV_DIR%" >nul 2>&1
del "%PID_FILE%" >nul 2>&1
del "%LOG_FILE%" >nul 2>&1
del "%~dp0config.json" >nul 2>&1
del "%~dp0plugin_config.json" >nul 2>&1
del "%~dp0app_config.json" >nul 2>&1
echo 卸载完成
pause
goto :menu
