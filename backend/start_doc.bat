@echo off
setlocal enabledelayedexpansion
title TestHub Document Parser (Tika Server)

echo ========================================
echo    TestHub Document Parser Startup
echo ========================================
echo.

cd /d "%~dp0"

if not exist "..\config.yaml" (
    echo Error: Configuration file ..\config.yaml not found
    pause
    exit /b 1
)

set DOC_PARSER_URL=
set TIKA_TIMEOUT=
set TIKA_MEMORY=

for /f "delims=" %%i in ('python -c "import yaml; c=yaml.safe_load(open('../config.yaml','r',encoding='utf-8')); s=c.get('server',{}); print(s.get('doc_parser_url','http://localhost:9987'))" 2^>nul') do (
    set "DOC_PARSER_URL=%%i"
)

for /f "delims=" %%i in ('python -c "import yaml; c=yaml.safe_load(open('../config.yaml','r',encoding='utf-8')); s=c.get('server',{}); print(s.get('tika_timeout',180))" 2^>nul') do (
    set "TIKA_TIMEOUT=%%i"
)

for /f "delims=" %%i in ('python -c "import yaml; c=yaml.safe_load(open('../config.yaml','r',encoding='utf-8')); s=c.get('server',{}); print(s.get('tika_memory','2g'))" 2^>nul') do (
    set "TIKA_MEMORY=%%i"
)

if "%DOC_PARSER_URL%"=="" set DOC_PARSER_URL=http://localhost:9987
if "%TIKA_TIMEOUT%"=="" set TIKA_TIMEOUT=180
if "%TIKA_MEMORY%"=="" set TIKA_MEMORY=2g

set TIKA_HOST=localhost
set TIKA_PORT=9987

for /f "tokens=2 delims=:/" %%a in ("%DOC_PARSER_URL%") do (
    if not "%%a"=="" set TIKA_HOST=%%a
)

for /f "tokens=3 delims=:/" %%a in ("%DOC_PARSER_URL%") do (
    if not "%%a"=="" set TIKA_PORT=%%a
)

echo Configuration:
echo   - URL: %DOC_PARSER_URL%
echo   - Host: %TIKA_HOST%
echo   - Port: %TIKA_PORT%
echo   - Timeout: %TIKA_TIMEOUT%s
echo   - Memory: %TIKA_MEMORY%
echo.

echo Checking Java environment...
java -version >nul 2>&1
if errorlevel 1 (
    echo Error: Java not found! Please install Java runtime environment.
    pause
    exit /b 1
)
echo Java environment OK
echo.

set TIKA_JAR=..\expand\doc_analysis\tika-server.jar
if not exist "%TIKA_JAR%" (
    echo Error: tika-server.jar not found!
    echo Expected path: %TIKA_JAR%
    pause
    exit /b 1
)

echo Starting Tika Server...
echo Press Ctrl+C to stop the server
echo.

java -Djava.awt.headless=true -Xmx%TIKA_MEMORY% -jar "%TIKA_JAR%" --host=%TIKA_HOST% --port=%TIKA_PORT%
