@echo off
chcp 65001 >nul 2>&1
title TestHub - Check Status (JSON)

echo.
echo ==================================================
echo   TestHub - Service Status Check (JSON)
echo ==================================================
echo.

cd /d E:\AiTsstPlant\testhub_platform

if not exist "E:\AiTsstPlant\testhub_platform\backend\venv\Scripts\python.exe" (
    echo [ERROR] Python venv not found at:
    echo   E:\AiTsstPlant\testhub_platform\backend\venv\Scripts\python.exe
    goto :end
)

E:\AiTsstPlant\testhub_platform\backend\venv\Scripts\python.exe -X utf8 -u scripts\check_status.py --json

if errorlevel 1 (
    echo.
    echo [ERROR] Script exited with error code %errorlevel%
)

:end
echo.
pause
