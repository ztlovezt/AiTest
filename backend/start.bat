@echo off
chcp 65001 >nul
title TestHub 启动脚本

echo ========================================
echo    TestHub 服务启动脚本
echo ========================================
echo.

cd /d "%~dp0"

REM 检测Python环境
echo 检测Python环境...

REM 优先使用虚拟环境中的Python
if exist "venv\Scripts\python.exe" (
    echo 找到虚拟环境: venv
    set PYTHON_CMD=venv\Scripts\python.exe
    goto :found_python
)

if exist ".venv\Scripts\python.exe" (
    echo 找到虚拟环境: .venv
    set PYTHON_CMD=.venv\Scripts\python.exe
    goto :found_python
)

REM 检查是否在虚拟环境中
if defined VIRTUAL_ENV (
    echo 已在虚拟环境中
    set PYTHON_CMD=python
    goto :found_python
)

REM 尝试使用系统Python
where python >nul 2>&1
if %errorlevel% equ 0 (
    echo 使用系统Python
    set PYTHON_CMD=python
    goto :found_python
)

REM 尝试使用Python Launcher
where py >nul 2>&1
if %errorlevel% equ 0 (
    echo 使用Python Launcher
    set PYTHON_CMD=py
    goto :found_python
)

echo 错误：未找到Python环境！
echo 请确保已安装Python或激活虚拟环境
pause
exit /b 1

:found_python
echo Python命令: %PYTHON_CMD%
echo.

echo [1/2] 启动 Django 开发服务器...
start "Django Server" cmd /k "%PYTHON_CMD% manage.py runserver"

timeout /t 2 /nobreak >nul

echo [2/2] 启动 Django-Q 任务队列服务...
start "Django-Q Cluster" cmd /k "%PYTHON_CMD% manage.py qcluster"

echo.
echo ========================================
echo    所有服务已启动！
echo ========================================
echo.
echo 服务信息：
echo   - Django Server: http://localhost:8000
echo   - API 文档: http://localhost:8000/api/docs/
echo   - Admin 后台: http://localhost:8000/admin/
echo.
echo 提示：
echo   - 按 Ctrl+C 停止所有服务
echo   - 查看日志请查看 logs/ 目录下的日志文件
echo.
pause
