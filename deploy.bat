@echo off
cd /d "%~dp0"
if exist deploy.exe start "" deploy.exe
if not exist deploy.exe (
    echo deploy.exe not found. Please compile or download it.
    pause
)
