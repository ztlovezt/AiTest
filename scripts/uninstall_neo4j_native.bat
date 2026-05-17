@echo off
chcp 65001 1>nul 2>&1
setlocal EnableDelayedExpansion
title TestHub - Uninstall Neo4j Windows Service

echo.
echo ==================================================
echo   Neo4j Windows Service Uninstaller
echo ==================================================
echo.

if not "%~1"=="" (
    set "NEO4J_HOME=%~1"
)

if "%NEO4J_HOME%"=="" (
    echo [ERROR] 未指定 Neo4j 安装目录
    echo 用法: uninstall_neo4j_native.bat ^<neo4j_home^>
    goto :end_fail
)

if not exist "%NEO4J_HOME%\bin\neo4j.bat" (
    echo [ERROR] %NEO4J_HOME%\bin\neo4j.bat 不存在
    goto :end_fail
)

:: 管理员权限校验
net session >nul 2>&1
if errorlevel 1 (
    echo [ERROR] 此脚本必须以管理员身份运行
    goto :end_fail
)
echo [OK] 管理员权限已确认

:: 1. 停止服务
sc query neo4j >nul 2>&1
if not errorlevel 1 (
    echo [INFO] 停止 neo4j 服务...
    net stop neo4j >nul 2>&1
    echo [OK] 服务已停止
) else (
    echo [INFO] neo4j 服务未注册，跳过停止
)

:: 2. 卸载服务
echo [INFO] 卸载 Windows 服务...
pushd "%NEO4J_HOME%"
call bin\neo4j.bat windows-service uninstall
popd

:: 3. 询问是否清理数据
echo.
set /p CLEAN_DATA=是否同时删除 Neo4j 数据？(y/N)：
if /i "%CLEAN_DATA%"=="y" (
    if exist "%NEO4J_HOME%\data\dbms" rmdir /S /Q "%NEO4J_HOME%\data\dbms"
    if exist "%NEO4J_HOME%\data\databases" rmdir /S /Q "%NEO4J_HOME%\data\databases"
    if exist "%NEO4J_HOME%\data\transactions" rmdir /S /Q "%NEO4J_HOME%\data\transactions"
    echo [OK] 数据已清理
) else (
    echo [INFO] 数据保留在 %NEO4J_HOME%\data
)

echo.
echo [OK] 卸载完成
exit /b 0

:end_fail
exit /b 1
