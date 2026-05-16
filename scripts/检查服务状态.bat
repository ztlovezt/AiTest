@echo off
chcp 65001 1>nul 2>&1
title TestHub - Service Status Check

echo.
echo ==================================================
echo   TestHub - Service Status Check
echo   Project: E:\testhub_platform
echo ==================================================
echo.

if not exist "E:\testhub_platform\backend\venv\Scripts\python.exe" (
    echo [ERROR] Python venv not found, using simple check.
    goto :simple_check
)

cd /d E:\testhub_platform
"E:\testhub_platform\backend\venv\Scripts\python.exe" -X utf8 -u scripts\check_status.py

if errorlevel 1 (
    echo.
    echo [WARNING] Some services may have issues.
)
goto :end

:simple_check
echo Running simple port check...
echo.

echo [MySQL  - Port 3306]
netstat -ano | findstr ":3306 " | findstr "LISTENING" 1>nul 2>&1
if errorlevel 1 (echo   Status: Not Running) else (echo   Status: Running)

echo [Redis  - Port 6379]
netstat -ano | findstr ":6379 " | findstr "LISTENING" 1>nul 2>&1
if errorlevel 1 (echo   Status: Not Running) else (echo   Status: Running)

echo [Neo4j  - Ports 7474/7687]
netstat -ano | findstr ":7474 " | findstr "LISTENING" 1>nul 2>&1
if errorlevel 1 (echo   HTTP: Not Running) else (echo   HTTP: Running)
netstat -ano | findstr ":7687 " | findstr "LISTENING" 1>nul 2>&1
if errorlevel 1 (echo   Bolt: Not Running) else (echo   Bolt: Running)

echo [Neo4j - Windows Service]
sc query neo4j 1>nul 2>&1
if errorlevel 1 (
    echo   Service: Not Registered
    echo   Checking Docker fallback...
    docker ps --filter "name=testhub-neo4j" -q 1>nul 2>&1
    if errorlevel 1 (echo   Container: Not Running) else (echo   Container: Running)
) else (
    echo   Service: Registered
    netstat -ano | findstr ":7687 " | findstr "LISTENING" 1>nul 2>&1
    if errorlevel 1 (echo   Bolt Port: Not Listening) else (echo   Bolt Port: Listening)
)

echo [Backend - Port 8000]
netstat -ano | findstr ":8000 " | findstr "LISTENING" 1>nul 2>&1
if errorlevel 1 (echo   Status: Not Running) else (echo   Status: Running)

echo [Frontend - Port 3000]
netstat -ano | findstr ":3000 " | findstr "LISTENING" 1>nul 2>&1
if errorlevel 1 (echo   Status: Not Running) else (echo   Status: Running)

:end
echo.
pause
