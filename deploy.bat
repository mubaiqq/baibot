@echo off
cd /d "%~dp0"

:: ============================================================
:: baibot - Windows 控制面板
:: ============================================================

:: -- 检测 Python --
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

set "PYTHON_EXE="
for /f "tokens=*" %%a in ('where python 2^>nul') do (
    "%%a" --version >nul 2>&1
    if not errorlevel 1 (
        set "PYTHON_EXE=%%a"
        goto :found_python
    )
)

echo [失败] 未找到 Python！
echo   请安装 Python 3.10+
echo   下载: https://www.python.org/downloads/
pause
exit /b 1

:found_python
set "VENV_DIR=%~dp0.venv"
set "MARKER_FILE=%VENV_DIR%\.installed"
set "PID_FILE=%~dp0baibot.pid"
set "LOG_FILE=%~dp0baibot.log"
set "PORT=7200"

:: -- 命令行参数路由 --
if /i "%~1"=="cli"       goto :cli
if /i "%~1"=="start"     goto :webui
if /i "%~1"=="stop"      goto :stop
if /i "%~1"=="restart"   goto :restart_cmd
if /i "%~1"=="status"    goto :status
if /i "%~1"=="log"       goto :log
if /i "%~1"=="update"    goto :update_deps
if /i "%~1"=="uninstall" goto :uninstall

:: ============================================================
:: 主菜单
:: ============================================================
:menu

:: 检查是否已运行
set "IS_RUN=0"
if exist "%PID_FILE%" (
    set /p _p=<"%PID_FILE%"
    tasklist /FI "PID eq %_p%" 2>nul | findstr "%_p%" >nul
    if not errorlevel 1 set "IS_RUN=1"
)

cls
echo.
echo   ========================================
echo       baibot WebUI - Windows 控制面板
echo   ========================================
echo.
if "%IS_RUN%"=="1" (
    set /p _p=<"%PID_FILE%"
    echo   [运行中]  PID: %_p%  http://localhost:%PORT%
) else (
    echo   [未运行]
)
echo.
echo   [1] 启动 WebUI（后台运行）
echo   [2] 停止 WebUI
echo   [3] 重启 WebUI
echo   [4] 查看状态
echo   [5] 查看日志
echo.
echo   [6] 命令行聊天终端
echo.
echo   [7] 更新依赖
echo   [8] 卸载（删除 venv / 配置）
echo.
echo   [0] 退出
echo.
set "choice="
set /p "choice=请输入数字: "

if "%choice%"=="0" exit /b
if "%choice%"=="1" goto :webui
if "%choice%"=="2" goto :stop
if "%choice%"=="3" goto :restart
if "%choice%"=="4" goto :status
if "%choice%"=="5" goto :log
if "%choice%"=="6" goto :cli
if "%choice%"=="7" goto :update_deps
if "%choice%"=="8" goto :uninstall

echo  无效输入，重试...
timeout /t 1 /nobreak >nul
goto :menu

:: ============================================================
:ensure_venv
if not exist "%VENV_DIR%" (
    echo   [1/2] 正在创建虚拟环境...
    "%PYTHON_EXE%" -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo   [失败] 虚拟环境创建失败
        pause
        exit /b 1
    )
    echo        完成
)
if not exist "%MARKER_FILE%" (
    echo   [2/2] 正在安装依赖...
    call "%VENV_DIR%\Scripts\activate.bat" >nul
    pip install --quiet --upgrade pip
    pip install --quiet -r "%~dp0requirements.txt"
    if errorlevel 1 (
        echo   [失败] 依赖安装失败，请检查网络
        pause
        exit /b 1
    )
    type nul > "%MARKER_FILE%"
    echo        完成
)
exit /b

:stop_running
    if exist "%PID_FILE%" (
        set /p _p=<"%PID_FILE%"
        taskkill /PID %_p% /F >nul 2>&1
        del "%PID_FILE%" >nul 2>&1
    )
    exit /b

:: ============================================================
:webui
    call :ensure_venv
    if errorlevel 1 goto :menu_fail

    call :stop_running

    echo   启动 WebUI 服务...
    powershell -Command "$p=Start-Process -FilePath '%VENV_DIR%\Scripts\python.exe' -ArgumentList '%~dp0server.py' -WindowStyle Hidden -PassThru; $p.Id | Out-File -Encoding ASCII '%PID_FILE%'"
    timeout /t 3 /nobreak >nul

    if not exist "%PID_FILE%" (
        echo   [失败] 未生成 PID 文件
        pause
        goto :menu
    )
    set /p _p=<"%PID_FILE%"
    tasklist /FI "PID eq %_p%" 2>nul | findstr "%_p%" >nul
    if errorlevel 1 (
        echo   [失败] 启动失败，查看日志: type "%LOG_FILE%"
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

:stop
    call :stop_running
    echo   已停止
    pause
    goto :menu

:restart
    call :stop_running
    goto :webui

:restart_cmd
    call :stop_running
    goto :webui

:status
    if exist "%PID_FILE%" (
        set /p _p=<"%PID_FILE%"
        tasklist /FI "PID eq %_p%" 2>nul | findstr "%_p%" >nul
        if errorlevel 1 (
            echo   服务未运行
        ) else (
            echo.
            echo   运行中  PID: %_p%  端口: %PORT%
            echo   http://localhost:%PORT%
            echo.
        )
    ) else (
        echo   服务未运行
    )
    pause
    goto :menu

:log
    if exist "%LOG_FILE%" (
        type "%LOG_FILE%"
    ) else (
        echo   暂无日志
    )
    pause
    goto :menu

:cli
    call :ensure_venv
    if errorlevel 1 goto :menu_fail
    echo.
    echo   命令行聊天模式
    echo   输入 /help 查看帮助  /exit 退出
    echo.
    "%VENV_DIR%\Scripts\python.exe" "%~dp0main.py"
    goto :menu

:update_deps
    call :ensure_venv
    if errorlevel 1 goto :menu_fail
    echo   更新依赖...
    call "%VENV_DIR%\Scripts\activate.bat" >nul
    pip install --quiet --upgrade pip
    pip install --quiet --upgrade -r "%~dp0requirements.txt"
    echo   完成
    pause
    goto :menu

:uninstall
    echo.
    echo   [警告] 将删除虚拟环境、日志和持久化配置
    echo   项目源代码不会被删除
    echo.
    set "confirm="
    set /p "confirm=确认卸载？输入 yes 继续: "
    if /i not "%confirm%"=="yes" (
        echo   已取消
        pause
        goto :menu
    )
    call :stop_running
    if exist "%VENV_DIR%" rmdir /s /q "%VENV_DIR%" >nul 2>&1
    del "%PID_FILE%" >nul 2>&1
    del "%LOG_FILE%" >nul 2>&1
    del "%~dp0config.json" >nul 2>&1
    del "%~dp0plugin_config.json" >nul 2>&1
    del "%~dp0app_config.json" >nul 2>&1
    echo   卸载完成
    pause
    goto :menu

:menu_fail
    pause
    goto :menu
