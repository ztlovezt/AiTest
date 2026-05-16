@echo off
setlocal EnableDelayedExpansion

REM Start Infrastructure Services for TestHub
REM Requires Administrator privileges (net start needs elevation)

echo ================================================
echo   Start TestHub Infrastructure
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

call :start_service "Redis" "Redis"
call :start_service "MySQL84" "MySQL"
call :start_service "neo4j" "Neo4j"

echo.
echo ================================================
echo   Infrastructure Start Complete
echo ================================================
echo.
pause
exit /b 0

REM --- Subroutine: Start a Windows service ---
:start_service
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

REM Check if already running
sc query "%svc_name%" | findstr "RUNNING" >NUL 2>&1
if %errorlevel% equ 0 (
    echo   [SKIP] Service '%svc_name%' is already running.
    goto :eof
)

REM Start service
echo   [START] Starting '%svc_name%'...
net start "%svc_name%" >NUL 2>&1

if %errorlevel% equ 0 (
    echo   [OK]    '%svc_name%' started successfully.
) else (
    echo   [WARN]  Failed to start '%svc_name%' (exit code %errorlevel%).
    echo           It may require manual intervention.
)

goto :eof
