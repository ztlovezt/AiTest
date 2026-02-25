@echo off
REM TestHub 后端启动脚本
REM 自动使用 config.yaml 中配置的端口

cd /d D:\platform\testhub_platform\backend

REM 激活虚拟环境
call D:\ENV\testhub\Scripts\activate.bat

REM 从 config.yaml 读取端口配置
for /f "tokens=2 delims=: " %%a in ('type config.yaml ^| findstr /C:"backend_port"') do set BACKEND_PORT=%%a

REM 如果没有找到端口配置，使用默认端口
if "%BACKEND_PORT%"=="" set BACKEND_PORT=8000

echo 正在启动后端服务器，端口: %BACKEND_PORT%
python manage.py runserver 0.0.0.0:%BACKEND_PORT%

pause