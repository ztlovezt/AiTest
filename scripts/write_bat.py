#!/usr/bin/env python3
import os

content1 = '''@echo off
chcp 65001 >nul 2>&1
title TestHub - TestHub Start All Services

echo.
echo ==================================================
echo   TestHub - Start All Services
echo   Project: E:\\testhub_platform
echo ==================================================
echo.

if not exist "E:\\testhub_platform\\backend\\venv\\Scripts\\python.exe" (
    echo [ERROR] Python venv not found
    goto :end
)

if not exist "E:\\node22\\node-v22.16.0-win-x64\\node.exe" (
    echo [ERROR] Node.js 22 not found
    goto :end
)

cd /d E:\\testhub_platform
"E:\\testhub_platform\\backend\\venv\\Scripts\\python.exe" -X utf8 -u scripts\\start_all.py

:end
echo.
pause
'''

content2 = '''@echo off
chcp 65001 >nul 2>&1
title TestHub - Service Status Check

echo.
echo ==================================================
echo   TestHub - Service Status Check
echo   Project: E:\\testhub_platform
echo ==================================================
echo.

if not exist "E:\\testhub_platform\\backend\\venv\\Scripts\\python.exe" (
    echo [ERROR] Python venv not found, using simple check.
    goto :simple_check
)

cd /d E:\\testhub_platform
"E:\\testhub_platform\\backend\\venv\\Scripts\\python.exe" -X utf8 -u scripts\\check_status.py

if errorlevel 1 (
    echo.
    echo [WARNING] Some services may have issues.
)
goto :end

:simple_check
echo Running simple port check...
echo.

echo [MySQL  - Port 3306]
netstat -ano | findstr ":3306 " | findstr "LISTENING" >nul 2>&1
if errorlevel 1 (echo   Status: Not Running) else (echo   Status: Running)

echo [Redis  - Port 6379]
netstat -ano | findstr ":6379 " | findstr "LISTENING" >nul 2>&1
if errorlevel 1 (echo   Status: Not Running) else (echo   Status: Running)

echo [Neo4j  - Ports 7474/7687]
netstat -ano | findstr ":7474 " | findstr "LISTENING" >nul 2>&1
if errorlevel 1 (echo   HTTP: Not Running) else (echo   HTTP: Running)
netstat -ano | findstr ":7687 " | findstr "LISTENING" >nul 2>&1
if errorlevel 1 (echo   Bolt: Not Running) else (echo   Bolt: Running)

echo [Docker - Neo4j Container]
docker ps --filter "name=testhub-neo4j" -q >nul 2>&1
if errorlevel 1 (echo   Container: Not Running) else (echo   Container: Running)

echo [Backend - Port 8000]
netstat -ano | findstr ":8000 " | findstr "LISTENING" >nul 2>&1
if errorlevel 1 (echo   Status: Not Running) else (echo   Status: Running)

echo [Frontend - Port 3000]
netstat -ano | findstr ":3000 " | findstr "LISTENING" >nul 2>&1
if errorlevel 1 (echo   Status: Not Running) else (echo   Status: Running)

:end
echo.
pause
'''

content3 = '''@echo off
chcp 65001 >nul 2>&1
title TestHub - Stop All Services

echo.
echo ==================================================
echo   TestHub - Stop All Services
echo   Project: E:\\testhub_platform
echo ==================================================
echo.

echo [1/5] Stopping Backend Uvicorn (port 8000)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000 " ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)

echo [2/5] Stopping Django-Q2 Task Queue...
for /f "tokens=2" %%a in ('tasklist ^| findstr /i "python"') do (
    wmic process where "ProcessId=%%a" get CommandLine 2>nul | findstr /i "qcluster" >nul 2>&1
    if not errorlevel 1 (
        taskkill /F /PID %%a >nul 2>&1
    )
)

echo [3/5] Stopping Frontend Vite (ports 3000-3004)...
for %%p in (3000 3001 3002 3003 3004) do (
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%%p " ^| findstr "LISTENING"') do (
        taskkill /F /PID %%a >nul 2>&1
    )
)

echo [4/5] Stopping Neo4j Docker Container...
docker ps --filter "name=testhub-neo4j" -q >nul 2>&1
if not errorlevel 1 (
    docker stop testhub-neo4j >nul 2>&1
    docker rm testhub-neo4j >nul 2>&1
    echo   Neo4j container stopped and removed
) else (
    echo   Neo4j container not running
)

echo [5/5] Waiting for port release...
ping -n 3 127.0.0.1 >nul 2>&1

echo.
echo ================================================
echo   Stop Complete.
echo   Note: MySQL and Redis run as Windows services
echo   and are not stopped by this script.
echo ================================================
echo.
pause
'''

base = 'E:/testhub_platform/scripts'

with open(os.path.join(base, '启动所有服务.bat'), 'w', encoding='utf-8', newline='\r\n') as f:
    f.write(content1)

with open(os.path.join(base, '检查服务状态.bat'), 'w', encoding='utf-8', newline='\r\n') as f:
    f.write(content2)

with open(os.path.join(base, '停止所有服务.bat'), 'w', encoding='utf-8', newline='\r\n') as f:
    f.write(content3)

print('All batch files written successfully')
