@echo off
cd /d "%~dp0"

:: ============================================================
:: baibot - Windows Control Panel
:: ============================================================

:: -- Find Python --
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

echo [FAIL] No Python found
echo   Install Python 3.10+ from https://www.python.org/downloads/
pause
exit /b 1

:found_python
set "VENV_DIR=%~dp0.venv"
set "MARKER_FILE=%VENV_DIR%\.installed"
set "PID_FILE=%~dp0baibot.pid"
set "LOG_FILE=%~dp0baibot.log"

:: -- CLI args --
if /i "%~1"=="cli"       goto :cli
if /i "%~1"=="start"     goto :webui
if /i "%~1"=="stop"      goto :do_stop
if /i "%~1"=="restart"   goto :cmd_restart
if /i "%~1"=="status"    goto :status
if /i "%~1"=="log"       goto :log
if /i "%~1"=="update"    goto :update_deps
if /i "%~1"=="uninstall" goto :uninstall

:: ============================================================
:: MAIN MENU
:: ============================================================
:menu
set "IS_RUN=0"
if exist "%PID_FILE%" (
    set /p _p=<"%PID_FILE%"
    tasklist /FI "PID eq %_p%" 2>nul | findstr "%_p%" >nul
    if not errorlevel 1 set "IS_RUN=1"
)

cls
echo.
echo   ========================================
echo       baibot WebUI - Windows Control Panel
echo   ========================================
echo.
if "%IS_RUN%"=="1" (
    set /p _p=<"%PID_FILE%"
    echo   [ONLINE]  PID: %_p%  http://localhost:7200
) else (
    echo   [OFFLINE]
)
echo.
echo   [1] Start WebUI (background)
echo   [2] Stop WebUI
echo   [3] Restart WebUI
echo   [4] Status
echo   [5] View log
echo.
echo   [6] CLI chat
echo.
echo   [7] Update deps
echo   [8] Uninstall (remove venv/config)
echo.
echo   [0] Exit
echo.
set "choice="
set /p "choice=Enter number: "

if "%choice%"=="0" exit /b
if "%choice%"=="1" goto :webui
if "%choice%"=="2" goto :do_stop
if "%choice%"=="3" goto :cmd_restart
if "%choice%"=="4" goto :status
if "%choice%"=="5" goto :log
if "%choice%"=="6" goto :cli
if "%choice%"=="7" goto :update_deps
if "%choice%"=="8" goto :uninstall

echo  Invalid
timeout /t 1 /nobreak >nul
goto :menu

:: ============================================================
:ensure_venv
if not exist "%VENV_DIR%" (
    echo   [1/2] Creating venv...
    "%PYTHON_EXE%" -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo   [FAIL] venv creation failed
        pause
        exit /b 1
    )
    echo        done
)
if not exist "%MARKER_FILE%" (
    echo   [2/2] Installing deps...
    call "%VENV_DIR%\Scripts\activate.bat" >nul
    pip install --quiet --upgrade pip
    pip install --quiet -r "%~dp0requirements.txt"
    if errorlevel 1 (
        echo   [FAIL] pip install failed, check network
        pause
        exit /b 1
    )
    type nul > "%MARKER_FILE%"
    echo        done
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

    echo   Starting WebUI...
    powershell -Command "$p=Start-Process -FilePath '%VENV_DIR%\Scripts\python.exe' -ArgumentList '%~dp0server.py' -WindowStyle Hidden -PassThru; $p.Id | Out-File -Encoding ASCII '%PID_FILE%'"
    timeout /t 3 /nobreak >nul

    if not exist "%PID_FILE%" (
        echo   [FAIL] no PID file
        pause
        goto :menu
    )
    set /p _p=<"%PID_FILE%"
    tasklist /FI "PID eq %_p%" 2>nul | findstr "%_p%" >nul
    if errorlevel 1 (
        echo   [FAIL] startup failed, check log: type "%LOG_FILE%"
        del "%PID_FILE%" >nul 2>&1
        pause
        goto :menu
    )
    echo.
    echo   +----------------------------------------+
    echo   ^|  baibot WebUI is running               ^|
    echo   ^|                                        ^|
    echo   ^|  http://localhost:7200                  ^|
    echo   ^|                                        ^|
    echo   ^|  stop: deploy.bat stop                 ^|
    echo   ^|  status: deploy.bat status             ^|
    echo   ^+----------------------------------------+
    echo.
    pause
    goto :menu

:do_stop
    call :stop_running
    echo   Stopped
    pause
    goto :menu

:cmd_restart
    call :stop_running
    goto :webui

:status
    if exist "%PID_FILE%" (
        set /p _p=<"%PID_FILE%"
        tasklist /FI "PID eq %_p%" 2>nul | findstr "%_p%" >nul
        if errorlevel 1 (
            echo   Offline
        ) else (
            echo.
            echo   Online  PID: %_p%  Port: 7200
            echo   http://localhost:7200
            echo.
        )
    ) else (
        echo   Offline
    )
    pause
    goto :menu

:log
    if exist "%LOG_FILE%" (
        type "%LOG_FILE%"
    ) else (
        echo   No log yet
    )
    pause
    goto :menu

:cli
    call :ensure_venv
    if errorlevel 1 goto :menu_fail
    echo.
    echo   CLI chat mode
    echo   /help for help  /exit to quit
    echo.
    "%VENV_DIR%\Scripts\python.exe" "%~dp0main.py"
    goto :menu

:update_deps
    call :ensure_venv
    if errorlevel 1 goto :menu_fail
    echo   Updating...
    call "%VENV_DIR%\Scripts\activate.bat" >nul
    pip install --quiet --upgrade pip
    pip install --quiet --upgrade -r "%~dp0requirements.txt"
    echo   Done
    pause
    goto :menu

:uninstall
    echo.
    echo   [WARNING] Will remove venv, logs and config
    echo   Source code will NOT be deleted
    echo.
    set "confirm="
    set /p "confirm=Type yes to confirm: "
    if /i not "%confirm%"=="yes" (
        echo   Cancelled
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
    echo   Uninstall complete
    pause
    goto :menu

:menu_fail
    pause
    goto :menu
