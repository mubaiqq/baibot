@echo off
chcp 65001 >nul
cd /d "%~dp0"

:: ═══════════════════════════════════════════════════════
:: baibot · 小白  Windows 控制面板
:: 双击运行，或: deploy.bat [cli|start|stop|restart|status|log|update|uninstall]
:: ═══════════════════════════════════════════════════════

set "PROJECT_DIR=%~dp0"
set "VENV_DIR=%PROJECT_DIR%.venv"
set "LOG_FILE=%PROJECT_DIR%baibot.log"
set "PID_FILE=%PROJECT_DIR%baibot.pid"
set "PORT=7200"

:: ── 检测 Python ──
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

echo  [X] 未找到 Python！请安装 Python 3.10+
echo     下载: https://www.python.org/downloads/
pause
exit /b

:found_python
for /f "tokens=2" %%v in ('"%PYTHON_EXE%" --version 2^>^&1') do set "PY_VER=%%v"
echo  [√] Python %PY_VER%

:: ── 命令行参数路由 ──
set "ACTION=%~1"
if /i "%ACTION%"=="cli"     goto :cmd_cli
if /i "%ACTION%"=="start"   goto :cmd_start
if /i "%ACTION%"=="stop"    goto :cmd_stop
if /i "%ACTION%"=="restart" goto :cmd_restart
if /i "%ACTION%"=="status"  goto :cmd_status
if /i "%ACTION%"=="log"     goto :cmd_log
if /i "%ACTION%"=="update"  goto :cmd_update
if /i "%ACTION%"=="uninstall" goto :cmd_uninstall
if not "%ACTION%"=="" (
    if /i not "%ACTION%"=="menu" (
        echo 用法: deploy.bat [menu^|cli^|start^|stop^|restart^|status^|log^|update^|uninstall]
        pause
        exit /b
    )
)

:: ── 进入交互菜单 ──
goto :main_menu

:: ═══════════════════════════════════════════════════════
:: 命令行直通入口
:: ═══════════════════════════════════════════════════════
:cmd_cli
    call :ensure_env
    "%VENV_DIR%\Scripts\python.exe" "%PROJECT_DIR%main.py"
    exit /b
:cmd_start
    call :ensure_env
    call :do_start
    exit /b
:cmd_stop
    call :do_stop
    exit /b
:cmd_restart
    call :do_stop
    call :do_start
    exit /b
:cmd_status
    call :show_status
    exit /b
:cmd_log
    call :show_log
    exit /b
:cmd_update
    call :ensure_env
    call :do_update
    exit /b
:cmd_uninstall
    call :do_uninstall
    exit /b

:: ═══════════════════════════════════════════════════════
:: 交互主菜单
:: ═══════════════════════════════════════════════════════
:main_menu
cls
echo.
echo   ╔══════════════════════════════════╗
echo   ║     baibot · 小白  控制面板     ║
echo   ╚══════════════════════════════════╝
echo.
echo   [检查] Python %PY_VER%

call :is_running
if errorlevel 1 (
    echo   ○ WebUI 未运行
) else (
    echo   ● WebUI 运行中  (端口: %PORT%)  http://localhost:%PORT%
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
set "choice="
set /p "choice=请输入数字: "

if "%choice%"=="0" exit /b
if "%choice%"=="1" goto :menu_cli
if "%choice%"=="2" goto :menu_webui
if "%choice%"=="3" goto :menu_restart
if "%choice%"=="4" goto :menu_stop
if "%choice%"=="5" goto :menu_status
if "%choice%"=="6" goto :menu_log
if "%choice%"=="7" goto :menu_update
if "%choice%"=="8" goto :menu_uninstall

echo  无效输入
timeout /t 1 /nobreak >nul
goto :main_menu

:menu_cli
    call :ensure_env
    echo.
    echo  [>] 启动命令行聊天模式...
    echo.
    "%VENV_DIR%\Scripts\python.exe" "%PROJECT_DIR%main.py"
    goto :main_menu

:menu_webui
    call :ensure_env
    call :do_start
    pause
    goto :main_menu

:menu_restart
    call :do_stop
    call :do_start
    pause
    goto :main_menu

:menu_stop
    call :do_stop
    pause
    goto :main_menu

:menu_status
    call :show_status
    pause
    goto :main_menu

:menu_log
    call :show_log
    pause
    goto :main_menu

:menu_update
    call :ensure_env
    call :do_update
    pause
    goto :main_menu

:menu_uninstall
    call :do_uninstall
    pause
    goto :main_menu

:: ═══════════════════════════════════════════════════════
:: 工具函数
:: ═══════════════════════════════════════════════════════

:ensure_env
    if not exist "%VENV_DIR%\Scripts\python.exe" (
        echo  [>] 创建虚拟环境...
        "%PYTHON_EXE%" -m venv "%VENV_DIR%"
        if errorlevel 1 (
            echo  [X] 虚拟环境创建失败
            pause
            exit /b 1
        )
        echo  [√] 虚拟环境创建完成
    )
    if not exist "%VENV_DIR%\.installed" (
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
    )
    exit /b

:is_running
    if not exist "%PID_FILE%" exit /b 1
    set /p _pid=<"%PID_FILE%"
    tasklist /FI "PID eq %_pid%" 2>nul | findstr "%_pid%" >nul
    if errorlevel 1 exit /b 1
    exit /b 0

:get_ip
    set "LAN_IP=127.0.0.1"
    for /f "tokens=*" %%i in ('powershell -Command "(Get-NetIPAddress -AddressFamily IPv4 ^| Where-Object {$_.InterfaceAlias -notmatch 'Loopback' -and $_.PrefixOrigin -ne 'Manual'} ^| Select-Object -First 1).IPAddress" 2^>nul') do if not "%%i"=="" set "LAN_IP=%%i"
    exit /b

:do_start
    call :is_running
    if not errorlevel 1 (
        set /p _oldpid=<"%PID_FILE%"
        taskkill /PID %_oldpid% /F >nul 2>&1
        del "%PID_FILE%" >nul 2>&1
        timeout /t 1 /nobreak >nul
    )
    echo  [>] 启动 WebUI 服务...
    call :get_ip
    powershell -Command "$p=Start-Process -FilePath '%VENV_DIR%\Scripts\python.exe' -ArgumentList '%PROJECT_DIR%server.py' -WindowStyle Hidden -PassThru; $p.Id | Out-File -Encoding ASCII '%PID_FILE%'"
    timeout /t 3 /nobreak >nul
    call :is_running
    if errorlevel 1 (
        echo  [X] 启动失败，查看日志: type "%LOG_FILE%"
        del "%PID_FILE%" >nul 2>&1
        exit /b 1
    )
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

:do_stop
    call :is_running
    if errorlevel 1 (
        echo  [!] 服务未运行
        exit /b 0
    )
    set /p _pid=<"%PID_FILE%"
    taskkill /PID %_pid% /F >nul 2>&1
    del "%PID_FILE%" >nul 2>&1
    echo  [√] 服务已停止
    exit /b 0

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
    echo   运行中   PID: %_pid%   端口: %PORT%
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

:do_update
    echo  [>] 更新依赖...
    call "%VENV_DIR%\Scripts\activate.bat" >nul
    pip install --quiet --upgrade pip
    pip install --quiet --upgrade -r "%PROJECT_DIR%requirements.txt"
    echo  [√] 依赖更新完成
    exit /b 0

:do_uninstall
    echo.
    echo  [警告] 此操作将删除虚拟环境、PID 文件、日志和持久化配置
    echo         项目源代码不会被删除
    echo.
    set "confirm="
    set /p "confirm=确认卸载？输入 yes 继续: "
    if /i not "%confirm%"=="yes" (
        echo 已取消
        exit /b 0
    )
    call :do_stop
    if exist "%VENV_DIR%" rmdir /s /q "%VENV_DIR%" >nul 2>&1
    del "%PID_FILE%" >nul 2>&1
    del "%LOG_FILE%" >nul 2>&1
    del "%PROJECT_DIR%config.json" >nul 2>&1
    del "%PROJECT_DIR%plugin_config.json" >nul 2>&1
    del "%PROJECT_DIR%app_config.json" >nul 2>&1
    if exist "%PROJECT_DIR%__pycache__" rmdir /s /q "%PROJECT_DIR%__pycache__" >nul 2>&1
    if exist "%PROJECT_DIR%tools\__pycache__" rmdir /s /q "%PROJECT_DIR%tools\__pycache__" >nul 2>&1
    echo  [√] 卸载完成！项目源码保留在 %PROJECT_DIR%
    exit /b 0
