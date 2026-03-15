@echo off
chcp 65001 >nul
title TestHub Startup Script

echo ========================================
echo    TestHub Service Startup Script
echo ========================================
echo.

cd /d "%~dp0"

REM Check Python environment
echo Checking Python environment...

REM Use virtual environment if available
if exist "venv\Scripts\python.exe" (
    echo Found virtual environment: venv
    set PYTHON_CMD=venv\Scripts\python.exe
    goto :found_python
)

if exist ".venv\Scripts\python.exe" (
    echo Found virtual environment: .venv
    set PYTHON_CMD=.venv\Scripts\python.exe
    goto :found_python
)

REM Check if already in virtual environment
if defined VIRTUAL_ENV (
    echo Already in virtual environment
    set PYTHON_CMD=python
    goto :found_python
)

REM Use specified virtual environment
set VENV_PATH=D:\ENV\TestHub
if exist "%VENV_PATH%\Scripts\python.exe" (
    echo Using specified virtual environment: %VENV_PATH%
    set PYTHON_CMD=%VENV_PATH%\Scripts\python.exe
    goto :found_python
)

echo Error: Virtual environment not found!
echo Please create virtual environment or activate virtual environment
echo Expected path: %VENV_PATH%
pause
exit /b 1

:found_python
echo Python command: %PYTHON_CMD%
echo.

REM Activate virtual environment (optional, for setting environment variables)
call "%VENV_PATH%\Scripts\activate.bat"

echo [1/2] Starting Django development server...

REM Read port configuration from config.yaml
REM Note: Script is in backend directory, need to read config.yaml from parent directory
for /f "tokens=2 delims=: " %%a in ('type ..\config.yaml ^| findstr /i "backend_port"') do set BACKEND_PORT=%%a

REM Use default port if not found
if "%BACKEND_PORT%"=="" set BACKEND_PORT=8000

echo Starting backend server, port: %BACKEND_PORT%
start "Django Server" cmd /k "%PYTHON_CMD% manage.py runserver 0.0.0.0:%BACKEND_PORT%"

timeout /t 2 /nobreak >nul

echo [2/2] Starting Django-Q task queue service...
start "Django-Q Cluster" cmd /k "%PYTHON_CMD% manage.py qcluster"

echo.
echo ========================================
echo    All services started!
echo ========================================
echo.
echo Tips:
echo   - Press Ctrl+C to stop all services
echo   - Check logs in logs/ directory
echo.
rem pause
