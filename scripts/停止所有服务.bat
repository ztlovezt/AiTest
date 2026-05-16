@echo off
cd /d E:\testhub_platform

REM ============================================
REM   TestHub Service Stopper
REM ============================================
echo.

if exist "backend\venv\Scripts\python.exe" (
    echo Stopping via Python script...
    backend\venv\Scripts\python.exe -X utf8 -u scripts\start_all.py --stop
    if errorlevel 1 (
        echo [WARN] Python stop returned error, using fallback...
        call :fallback_kill
    )
) else (
    echo [ERROR] Python venv not found, using fallback...
    call :fallback_kill
)

echo.
echo Done. Press any key to exit.
pause >nul
goto :eof

:fallback_kill
REM Fallback: brute-force kill by process name
taskkill /F /IM python.exe /T 2>nul
taskkill /F /IM node.exe /T 2>nul
echo Fallback cleanup executed.
goto :eof
