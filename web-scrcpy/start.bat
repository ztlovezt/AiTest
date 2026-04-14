@echo off
chcp 65001 >nul

echo ========================================
echo Web-Scrcpy Server
echo ========================================

REM Kill existing python processes on port 6899
echo Stopping existing service...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :6899 ^| findstr LISTENING') do (
    echo Stopping process %%a on port 6899...
    taskkill /F /PID %%a >nul 2>&1
)

REM Kill any running python app.py processes
taskkill /F /IM python.exe /FI "WINDOWTITLE eq *app.py*" >nul 2>&1

REM Wait a moment for port to be released
timeout /t 2 /nobreak >nul

echo.
echo Starting service...
echo Port: 6899
echo Access: http://localhost:6899/
echo.
echo Press Ctrl+C to stop server
echo.

python app.py --video_bit_rate 8192000
pause
