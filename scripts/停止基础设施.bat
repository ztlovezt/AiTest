@echo off
setlocal

REM Stop Infrastructure Services for TestHub
REM Requires Administrator privileges (net stop needs elevation)

echo ================================================
echo   Stop TestHub Infrastructure
echo   (Redis + MySQL + Neo4j)
echo ================================================
echo.

REM Check if running as Administrator
net session >NUL 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Administrator privileges required.
    echo [INFO] Right-click this file and select "Run as administrator".
    echo.
    pause
    exit /b 1
)

call :stop_service "Redis" "Redis"
call :stop_service "MySQL84" "MySQL"
call :stop_service "neo4j" "Neo4j"

echo.
echo ================================================
echo   Infrastructure Stop Complete
echo ================================================
echo.
pause
exit /b 0

REM --- Subroutine: Stop a Windows service ---
:stop_service
set svc_name=%~1
set svc_label=%~2

echo.
echo [%svc_label%] Checking service '%svc_name%'...

REM Check if service exists
sc query "%svc_name%" >NUL 2>&1
if %errorlevel% neq 0 (
    echo   [SKIP] Service '%svc_name%' not found.
    goto :eof
)

REM Check if running
sc query "%svc_name%" | findstr "RUNNING" >NUL 2>&1
if %errorlevel% neq 0 (
    echo   [SKIP] Service '%svc_name%' is already stopped.
    goto :eof
)

REM Stop service
echo   [STOP] Stopping '%svc_name%'...
net stop "%svc_name%" >NUL 2>&1

if %errorlevel% equ 0 (
    echo   [OK]   '%svc_name%' stopped successfully.
) else (
    echo   [WARN] Failed to stop '%svc_name%' (exit code %errorlevel%).
    echo          It may require manual intervention.
)

goto :eof
