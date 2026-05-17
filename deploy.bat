@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0"

:: ============================================================
:: baibot Windows 一键部署 & 控制面板
:: 双击运行或用: deploy.bat [cli|start|stop|restart|status|log|update|uninstall]
:: ============================================================

set "PROJECT_DIR=%~dp0"
set "VENV_DIR=%PROJECT_DIR%.venv"
set "LOG_FILE=%PROJECT_DIR%baibot.log"
set "PID_FILE=%PROJECT_DIR%baibot.pid"
set "PORT=7200"

:: ============================================================
:: 检测 Python
:: ============================================================
:detect_python
set "PYTHON_EXE="

if exist "%USERPROFILE%\python-sdk\python3.13.2\python.exe" set "PYTHON_EXE=%USERPROFILE%\python-sdk\python3.13.2\python.exe"
if not defined PYTHON_EXE if exist "%LOCALAPPDATA%\Programs\Python\Python314\python.exe" set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python314\python.exe"
if not defined PYTHON_EXE if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
if not defined PYTHON_EXE if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not defined PYTHON_EXE if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
if not defined PYTHON_EXE if exist "C:\Python313\python.exe" set "PYTHON_EXE=C:\Python313\python.exe"
if not defined PYTHON_EXE if exist "C:\Python312\python.exe" set "PYTHON_EXE=C:\Python312\python.exe"

if not defined PYTHON_EXE (
    for /f "tokens=*" %%a in ('where python 2^>nul') do (
        "%%a" --version >nul 2>&1
        if not errorlevel 1 (
            set "PYTHON_EXE=%%a"
            goto :python_found
        )
    )
    goto :no_python
)
:python_found

if not defined PYTHON_EXE goto :no_python
goto :python_ok

:no_python
echo  [X] 未找到 Python！请安装 Python 3.10+
echo      下载: https://www.python.org/downloads/
pause
exit /b 1

:python_ok
for /f "tokens=2" %%v in ('"%PYTHON_EXE%" --version 2^>^&1') do set "PY_VER=%%v"

:: ============================================================
:: 工具函数
:: ============================================================
:ensure_venv
if exist "%VENV_DIR%\Scripts\python.exe" exit /b
echo  [>] 创建虚拟环境...
"%PYTHON_EXE%" -m venv "%VENV_DIR%"
if errorlevel 1 (
    echo  [X] 虚拟环境创建失败
    pause
    exit /b 1
)
echo  [√] 虚拟环境创建完成
exit /b

:ensure_deps
if exist "%VENV_DIR%\.installed" exit /b
echo  [>] 安装 Python 依赖...
call "%VENV_DIR%\Scripts\activate.bat" >nul
pip install --quiet --upgrade pip
pip install --quiet -r "%PROJECT_DIR%requirements.txt"
if errorlevel 1 (
    echo  [X] 依赖安装失败，请检查网络
    pause
    exit /b 1
)
type nul > "%VENV_DIR%\.installed"
echo  [√] 依赖安装完成
exit /b

:is_running
if not exist "%PID_FILE%" exit /b 1
set /p _pid=<"%PID_FILE%"
powershell -Command "Get-Process -Id !_pid! -ErrorAction SilentlyContinue | Select-Object -First 1" >nul 2>&1
exit /b %errorlevel%

:get_ip
for /f "tokens=*" %%i in ('powershell -Command "(Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.InterfaceAlias -notmatch 'Loopback' -and $_.PrefixOrigin -ne 'Manual'} | Select-Object -First 1).IPAddress" 2^>nul') do set "LAN_IP=%%i"
if not defined LAN_IP set "LAN_IP=127.0.0.1"
exit /b

:: ============================================================
:: 功能模块
:: ============================================================

:start_cli
call :ensure_venv
call :ensure_deps
echo.
echo  [>] 启动命令行聊天模式...
echo.
"%VENV_DIR%\Scripts\python.exe" "%PROJECT_DIR%main.py"
exit /b %errorlevel%

:start_webui
call :ensure_venv
call :ensure_deps

call :is_running
if not errorlevel 1 (
    set /p _oldpid=<"%PID_FILE%"
    taskkill /PID !_oldpid! /F >nul 2>&1
    del "%PID_FILE%" >nul 2>&1
    timeout /t 1 /nobreak >nul
)

echo  [>] 启动 WebUI 服务...
call :get_ip
powershell -Command "$p=Start-Process -FilePath '%VENV_DIR%\Scripts\python.exe' -ArgumentList '%PROJECT_DIR%server.py' -WindowStyle Hidden -PassThru; $p.Id | Out-File -Encoding ASCII '%PID_FILE%'"

timeout /t 2 /nobreak >nul

call :is_running
if errorlevel 1 (
    echo  [X] 启动失败，查看日志: type "%LOG_FILE%"
    del "%PID_FILE%" >nul 2>&1
    pause
    exit /b 1
)

set /p _pid=<"%PID_FILE%"
echo.
echo   ╔══════════════════════════════════════╗
echo   ║    baibot WebUI 已启动               ║
echo   ╠══════════════════════════════════════╣
echo   ║                                      ║
echo   ║    本地访问:                          ║
echo   ║    http://localhost:%PORT%                  ║
if not "%LAN_IP%"=="127.0.0.1" (
echo   ║                                      ║
echo   ║    局域网访问:                        ║
echo   ║    http://%LAN_IP%:%PORT%        ║
)
echo   ║                                      ║
echo   ╠══════════════════════════════════════╣
echo   ║    返回菜单: deploy.bat               ║
echo   ║    日志:     type baibot.log          ║
echo   ╚══════════════════════════════════════╝
echo.
exit /b 0

:stop_server
call :is_running
if errorlevel 1 (
    echo  [!] 服务未运行
    exit /b 0
)
set /p _pid=<"%PID_FILE%"
taskkill /PID !_pid! /F >nul 2>&1
del "%PID_FILE%" >nul 2>&1
echo  [√] 服务已停止
exit /b 0

:restart_webui
call :stop_server
call :start_webui
exit /b %errorlevel%

:show_status
call :is_running
if errorlevel 1 (
    echo.
    echo   服务未运行
    echo.
    exit /b 0
)
call :get_ip
set /p _pid=<"%PID_FILE%"
echo.
echo   运行中   PID: !_pid!   端口: %PORT%
echo   本地:   http://localhost:%PORT%
if not "%LAN_IP%"=="127.0.0.1" echo   局域网: http://%LAN_IP%:%PORT%
echo.
exit /b 0

:show_log
if not exist "%LOG_FILE%" (
    echo  [!] 日志文件不存在
    exit /b 0
)
echo.
type "%LOG_FILE%"
echo.
exit /b 0

:update_deps
call :ensure_venv
call "%VENV_DIR%\Scripts\activate.bat" >nul
echo  [>] 更新依赖...
pip install --quiet --upgrade pip
pip install --quiet --upgrade -r "%PROJECT_DIR%requirements.txt"
echo  [√] 依赖更新完成
exit /b 0

:uninstall_all
echo.
echo  [警告] 此操作将删除虚拟环境、PID 文件、日志和持久化配置
echo         项目源代码不会被删除
echo.
set /p "confirm=确认卸载？输入 yes 继续: "
if /i not "%confirm%"=="yes" (
    echo 已取消
    exit /b 0
)

call :stop_server

if exist "%VENV_DIR%" (
    rmdir /s /q "%VENV_DIR%" >nul 2>&1
)
del "%PID_FILE%" >nul 2>&1
del "%LOG_FILE%" >nul 2>&1
del "%PROJECT_DIR%config.json" >nul 2>&1
del "%PROJECT_DIR%plugin_config.json" >nul 2>&1
del "%PROJECT_DIR%app_config.json" >nul 2>&1

if exist "%PROJECT_DIR%__pycache__" rmdir /s /q "%PROJECT_DIR%__pycache__" >nul 2>&1
if exist "%PROJECT_DIR%tools\__pycache__" rmdir /s /q "%PROJECT_DIR%tools\__pycache__" >nul 2>&1

echo  [√] 卸载完成！项目源码保留在 %PROJECT_DIR%
exit /b 0

:: ============================================================
:: 主菜单
:: ============================================================
:main_menu
cls
echo.
echo   ╔══════════════════════════════════╗
echo   ║     baibot ^· 小白  控制面板     ║
echo   ╚══════════════════════════════════╝
echo.

echo   [检查] Python %PY_VER%

call :is_running
if errorlevel 1 (
    echo   ○ WebUI 未运行
) else (
    set /p _pid=<"%PID_FILE%"
    echo   ● WebUI 运行中  (PID: !_pid!)  http://localhost:%PORT%
)

echo.
echo   ── 启动 ──
echo   [1] 命令行聊天
echo   [2] 启动 WebUI
echo.
echo   ── 管理 ──
echo   [3] 重启 WebUI
echo   [4] 停止 WebUI
echo   [5] 查看状态
echo   [6] 查看日志
echo.
echo   ── 系统 ──
echo   [7] 更新依赖
echo   [8] 卸载 (删除 venv / 配置)
echo.
echo   [0] 退出
echo.
set /p "choice=请输入数字: "

if "%choice%"=="1" (
    call :start_cli
    goto :main_menu
)
if "%choice%"=="2" (
    call :start_webui
    pause
    goto :main_menu
)
if "%choice%"=="3" (
    call :restart_webui
    pause
    goto :main_menu
)
if "%choice%"=="4" (
    call :stop_server
    pause
    goto :main_menu
)
if "%choice%"=="5" (
    call :show_status
    pause
    goto :main_menu
)
if "%choice%"=="6" (
    call :show_log
    pause
    goto :main_menu
)
if "%choice%"=="7" (
    call :update_deps
    pause
    goto :main_menu
)
if "%choice%"=="8" (
    call :uninstall_all
    pause
    goto :main_menu
)
if "%choice%"=="0" exit /b 0

echo  无效输入
timeout /t 1 /nobreak >nul
goto :main_menu

:: ============================================================
:: 命令行参数入口
:: ============================================================
set "ACTION=%~1"
if "%ACTION%"=="" goto :main_menu
if /i "%ACTION%"=="menu" goto :main_menu
if /i "%ACTION%"=="cli" call :start_cli & exit /b
if /i "%ACTION%"=="start" call :start_webui & exit /b
if /i "%ACTION%"=="stop" call :stop_server & exit /b
if /i "%ACTION%"=="restart" call :restart_webui & exit /b
if /i "%ACTION%"=="status" call :show_status & exit /b
if /i "%ACTION%"=="log" call :show_log & exit /b
if /i "%ACTION%"=="update" call :update_deps & exit /b
if /i "%ACTION%"=="uninstall" call :uninstall_all & exit /b

echo 用法: deploy.bat [menu^|cli^|start^|stop^|restart^|status^|log^|update^|uninstall]
echo.
echo   无参数      交互式控制面板菜单
echo   cli         直接进入命令行聊天
echo   start       后台启动 WebUI
echo   stop        停止 WebUI
echo   restart     重启 WebUI
echo   status      查看运行状态
echo   log         查看日志
echo   update      更新 Python 依赖
echo   uninstall   卸载 venv / 配置 / 缓存
exit /b 0
