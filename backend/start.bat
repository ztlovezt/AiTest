@echo off
chcp 65001 >nul
title TestHub 启动脚本

echo ========================================
echo    TestHub 服务启动脚本
echo ========================================
echo.

cd /d "%~dp0"

REM 检测 Python 环境
echo 检测 Python 环境...

REM 优先使用虚拟环境中的 Python
if exist "venv\Scripts\python.exe" (
    echo 找到虚拟环境：venv
    set PYTHON_CMD=venv\Scripts\python.exe
    goto :found_python
)

if exist ".venv\Scripts\python.exe" (
    echo 找到虚拟环境：.venv
    set PYTHON_CMD=.venv\Scripts\python.exe
    goto :found_python
)

REM 检查是否在虚拟环境中
if defined VIRTUAL_ENV (
    echo 已在虚拟环境中
    set PYTHON_CMD=python
    goto :found_python
)

REM 使用指定的虚拟环境
set VENV_PATH=D:\ENV\TestHub
if exist "%VENV_PATH%\Scripts\python.exe" (
    echo 使用指定虚拟环境：%VENV_PATH%
    set PYTHON_CMD=%VENV_PATH%\Scripts\python.exe
    goto :found_python
)

echo 错误：未找到虚拟环境！
echo 请确保已创建虚拟环境或激活虚拟环境
echo 期望路径：%VENV_PATH%
pause
exit /b 1

:found_python
echo Python 命令：%PYTHON_CMD%
echo.

REM 激活虚拟环境（可选，用于设置环境变量）
call "%VENV_PATH%\Scripts\activate.bat"

echo [1/2] 启动 Django 开发服务器...

REM 从 config.yaml 读取端口配置
for /f "tokens=2 delims=: " %%a in ('type config.yaml ^| findstr /C:"backend_port"') do set BACKEND_PORT=%%a

REM 如果没有找到端口配置，使用默认端口
if "%BACKEND_PORT%"=="" set BACKEND_PORT=8000

echo 正在启动后端服务器，端口：%BACKEND_PORT%
start "Django Server" cmd /k "%PYTHON_CMD% manage.py runserver 0.0.0.0:%BACKEND_PORT%"

timeout /t 2 /nobreak >nul

echo [2/2] 启动 Django-Q 任务队列服务...
start "Django-Q Cluster" cmd /k "%PYTHON_CMD% manage.py qcluster"

echo.
echo ========================================
echo    所有服务已启动！
echo ========================================
echo.
echo 提示：
echo   - 按 Ctrl+C 停止所有服务
echo   - 查看日志请查看 logs/ 目录下的日志文件
echo.
rem pause
