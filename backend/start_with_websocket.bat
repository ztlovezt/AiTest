@echo off
chcp 65001 >nul
title TestHub Backend (Daphne - WebSocket Support)

echo ========================================
echo    TestHub Backend with WebSocket
echo    Using Daphne ASGI Server
echo ========================================
echo.

cd /d "%~dp0"

REM 检查Python环境
echo Checking Python environment...

REM 优先使用项目本地的虚拟环境
if exist ".venv\Scripts\python.exe" (
    echo Found local virtual environment: .venv
    set PYTHON_CMD=.venv\Scripts\python.exe
    goto :found_python
)

if exist "venv\Scripts\python.exe" (
    echo Found local virtual environment: venv
    set PYTHON_CMD=venv\Scripts\python.exe
    goto :found_python
)

REM 检查是否已在虚拟环境中
if defined VIRTUAL_ENV (
    echo Already in virtual environment
    set PYTHON_CMD=python
    goto :found_python
)

REM 使用指定的虚拟环境（备用）
set VENV_PATH=D:\ENV\TestHub
if exist "%VENV_PATH%\Scripts\python.exe" (
    echo Using specified virtual environment: %VENV_PATH%
    set PYTHON_CMD=%VENV_PATH%\Scripts\python.exe
    goto :found_python
)

echo Error: Virtual environment not found!
echo Please create virtual environment first:
echo   python -m venv .venv
echo   .venv\Scripts\activate
echo   pip install -r requirements.txt
pause
exit /b 1

:found_python
echo Python command: %PYTHON_CMD%
echo.

REM 激活虚拟环境（如果使用的是本地虚拟环境）
if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
) else if exist "venv\Scripts\activate.bat" (
    call "venv\Scripts\activate.bat"
) else if defined VIRTUAL_ENV (
    echo Already activated
)

REM 从config.yaml读取端口配置
for /f "tokens=2 delims=: " %%a in ('type ..\config.yaml ^| findstr /i "backend_port"') do set BACKEND_PORT=%%a

REM 如果未找到，则使用默认端口
if "%BACKEND_PORT%"=="" set BACKEND_PORT=8000

echo Starting Daphne server on port %BACKEND_PORT%...
echo WebSocket support: ENABLED
echo.

REM 使用 Daphne 启动（支持 WebSocket）
%PYTHON_CMD% -m daphne -b 0.0.0.0 -p %BACKEND_PORT% backend.asgi:application

echo.
echo Server stopped.
pause
