@echo off
cd /d E:\testhub_platform

REM ============================================
REM   TestHub Service Starter
REM ============================================
echo.

if not exist "backend\venv\Scripts\python.exe" (
    echo [ERROR] Python venv not found
    goto :end
)

set "NODE22_NVM=C:\Users\Administrator\AppData\Local\nvm\v22.22.2\node.exe"
set "NODE22_FALLBACK=E:\node22\node-v22.16.0-win-x64\node.exe"

if not exist "%NODE22_NVM%" (
    if not exist "%NODE22_FALLBACK%" (
        echo [ERROR] Node.js 22 not found
        echo   Tried: %NODE22_NVM%
        echo   Tried: %NODE22_FALLBACK%
        goto :end
    )
)

echo Starting via Python script...
backend\venv\Scripts\python.exe -X utf8 -u scripts\start_all.py
if errorlevel 1 (
    echo [WARN] Python script returned error. Check logs above.
)

:end
echo.
echo Done. Press any key to exit.
pause >nul
