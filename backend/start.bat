@echo off
chcp 65001 >nul
title TestHub Startup Script

echo ========================================
echo    TestHub Service Startup Script
echo ========================================
echo.

cd /d "%~dp0"

REM 检查Python环境
echo Checking Python environment...

REM 使用虚拟环境（如果可用）
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

REM 检查是否已在虚拟环境中
if defined VIRTUAL_ENV (
    echo Already in virtual environment
    set PYTHON_CMD=python
    goto :found_python
)

REM 使用指定的虚拟环境
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

REM 激活虚拟环境（可选，用于设置环境变量）
call "%VENV_PATH%\Scripts\activate.bat"

echo [1/2] Starting Daphne ASGI server (with WebSocket support)...

REM 禁用 OneDNN 和其他优化以避免 PaddlePaddle 3.x 兼容性问题
set FLAGS_use_mkldnn=0
set FLAGS_enable_mkldnn=0
set FLAGS_enable_onednn=0
set FLAGS_cinn_new_group_scheduler=0
set FLAGS_enable_pir_api=0
set FLAGS_check_cuda_version=0
set FLAGS_skip_allocator_mem_check=1
set PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True

REM 从config.yaml读取端口配置
REM 注意：脚本在后端目录中，需要从父目录读取config.yaml
for /f "tokens=2 delims=: " %%a in ('type ..\config.yaml ^| findstr /i "backend_port"') do set BACKEND_PORT=%%a

REM 如果未找到，则使用默认端口
if "%BACKEND_PORT%"=="" set BACKEND_PORT=8000

echo Starting backend server, port: %BACKEND_PORT%
echo WebSocket support: ENABLED
start "Daphne Server" cmd /k "%PYTHON_CMD% -m daphne -b 0.0.0.0 -p %BACKEND_PORT% backend.asgi:application"

timeout /t 2 /nobreak >nul

echo [2/2] Starting Django-Q task queue service...
start "Django-Q Cluster" cmd /k "%PYTHON_CMD% manage.py qcluster"

echo.
echo ========================================
echo    All services started!
echo ========================================
echo.
echo Services:
echo   - Daphne ASGI Server (WebSocket enabled): http://127.0.0.1:%BACKEND_PORT%
echo   - Django-Q Task Queue: Running
echo.
echo Tips:
echo   - Close window to stop service
echo   - Check logs in logs/ directory
echo   - API Docs: http://127.0.0.1:%BACKEND_PORT%/api/docs/
echo.
rem pause
