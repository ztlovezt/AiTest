@echo off
chcp 65001 1>nul 2>&1
setlocal EnableDelayedExpansion
title TestHub - Install Neo4j as Windows Service

echo.
echo ==================================================
echo   Neo4j Windows Service Installer for TestHub
echo ==================================================
echo.

:: ---------------------------------------------------
:: 0. 解析 Neo4j 安装目录（参数 1 优先，否则环境变量）
:: ---------------------------------------------------
if not "%~1"=="" (
    set "NEO4J_HOME=%~1"
) else if "%NEO4J_HOME%"=="" (
    echo [ERROR] 未指定 Neo4j 安装目录
    echo.
    echo 用法:
    echo   install_neo4j_native.bat ^<neo4j_home^>
    echo   install_neo4j_native.bat E:\neo4j-community-5.28.0
    echo.
    echo 或先设置环境变量:
    echo   set NEO4J_HOME=E:\neo4j-community-5.28.0
    echo   install_neo4j_native.bat
    goto :end_fail
)

if not exist "%NEO4J_HOME%\bin\neo4j.bat" (
    echo [ERROR] %NEO4J_HOME%\bin\neo4j.bat 不存在，路径无效
    goto :end_fail
)
echo [OK] NEO4J_HOME = %NEO4J_HOME%

:: ---------------------------------------------------
:: 1. 管理员权限校验
:: ---------------------------------------------------
net session >nul 2>&1
if errorlevel 1 (
    echo [ERROR] 此脚本必须以管理员身份运行
    echo 操作: 在开始菜单搜索 cmd，右键 "以管理员身份运行"
    goto :end_fail
)
echo [OK] 管理员权限已确认

:: ---------------------------------------------------
:: 2. JDK 21 检查
:: ---------------------------------------------------
if "%JAVA_HOME%"=="" (
    echo [ERROR] JAVA_HOME 未设置
    echo 请先安装 JDK 21 并设置 JAVA_HOME 环境变量
    echo 推荐: https://adoptium.net/temurin/releases/?version=21
    goto :end_fail
)

if not exist "%JAVA_HOME%\bin\java.exe" (
    echo [ERROR] JAVA_HOME 路径无效: %JAVA_HOME%
    goto :end_fail
)

"%JAVA_HOME%\bin\java.exe" -version 2>&1 | findstr /R "version \"21\." >nul
if errorlevel 1 (
    echo [WARN] JAVA_HOME 似乎不是 JDK 21
    "%JAVA_HOME%\bin\java.exe" -version
    echo Neo4j 5.28 强制要求 JDK 17 或 21，按 Ctrl+C 中止，或任意键继续
    pause >nul
)
echo [OK] JDK 已就绪

:: ---------------------------------------------------
:: 3. APOC 插件检查
:: ---------------------------------------------------
if not exist "%NEO4J_HOME%\plugins\apoc-*.jar" (
    echo [WARN] %NEO4J_HOME%\plugins\ 中未发现 apoc-*.jar
    echo 请先下载 apoc-5.28.0-core.jar 到 plugins\ 目录:
    echo   https://github.com/neo4j/apoc/releases/tag/5.28.0
    echo 按 Ctrl+C 中止，或任意键忽略并继续（Week 3 图谱构建需要 APOC）
    pause >nul
) else (
    echo [OK] APOC 插件已就绪
)

:: ---------------------------------------------------
:: 4. 备份并补丁 conf\neo4j.conf
:: ---------------------------------------------------
set "CONF=%NEO4J_HOME%\conf\neo4j.conf"
if not exist "%CONF%" (
    echo [ERROR] %CONF% 不存在
    goto :end_fail
)

if not exist "%CONF%.bak" (
    copy /Y "%CONF%" "%CONF%.bak" >nul
    echo [OK] 已备份原配置到 neo4j.conf.bak
)

:: 追加 TestHub 配置块（若已存在则跳过）
findstr /C:"# TestHub-managed config" "%CONF%" >nul 2>&1
if errorlevel 1 (
    echo. >> "%CONF%"
    echo # TestHub-managed config (do not delete this line) >> "%CONF%"
    echo server.default_listen_address=0.0.0.0 >> "%CONF%"
    echo server.bolt.listen_address=:7687 >> "%CONF%"
    echo server.http.listen_address=:7474 >> "%CONF%"
    echo server.memory.heap.initial_size=512m >> "%CONF%"
    echo server.memory.heap.max_size=2G >> "%CONF%"
    echo dbms.security.procedures.unrestricted=apoc.* >> "%CONF%"
    echo dbms.security.procedures.allowlist=apoc.* >> "%CONF%"
    echo [OK] 已写入 TestHub 配置块到 neo4j.conf
) else (
    echo [OK] neo4j.conf 已包含 TestHub 配置块（跳过）
)

:: ---------------------------------------------------
:: 5. 设置初始密码（仅在 data 目录为空时）
:: ---------------------------------------------------
if not exist "%NEO4J_HOME%\data\dbms\auth" (
    echo [INFO] 设置初始密码 testhub...
    pushd "%NEO4J_HOME%"
    call bin\neo4j-admin dbms set-initial-password testhub
    popd
    if errorlevel 1 (
        echo [WARN] 初始密码设置失败（可能已设置过），继续
    ) else (
        echo [OK] 初始密码已设置: neo4j / testhub
    )
) else (
    echo [INFO] 检测到既有 auth 文件，跳过密码初始化
    echo        如需重置: 删除 %NEO4J_HOME%\data\dbms\auth 后重跑此脚本
)

:: ---------------------------------------------------
:: 6. 安装 Windows 服务
:: ---------------------------------------------------
sc query neo4j >nul 2>&1
if errorlevel 1 (
    echo [INFO] 安装 Windows 服务 neo4j...
    pushd "%NEO4J_HOME%"
    call bin\neo4j.bat windows-service install
    popd
    if errorlevel 1 (
        echo [ERROR] Windows 服务安装失败
        goto :end_fail
    )
    echo [OK] Windows 服务 neo4j 已安装
) else (
    echo [OK] Windows 服务 neo4j 已存在（跳过安装）
)

:: ---------------------------------------------------
:: 7. 配置开机自启 + 启动服务
:: ---------------------------------------------------
sc config neo4j start= auto >nul 2>&1
echo [OK] 已设置 neo4j 开机自启

net start neo4j >nul 2>&1
:: 不强校验返回码：服务可能已运行

echo [INFO] 等待 Bolt 端口 7687 就绪 (最多 60s)...
set /a _wait_count=0
:wait_port
netstat -ano | findstr :7687 | findstr LISTENING >nul 2>&1
if not errorlevel 1 goto :port_ready
set /a _wait_count+=1
if !_wait_count! geq 60 goto :port_timeout
timeout /t 1 /nobreak >nul
goto :wait_port

:port_timeout
echo [WARN] 60s 内端口 7687 未就绪，请检查日志:
echo   %NEO4J_HOME%\logs\neo4j.log
echo   %NEO4J_HOME%\logs\debug.log
goto :end_fail

:port_ready
echo.
echo ==================================================
echo   Neo4j 安装完成
echo ==================================================
echo   Bolt:    bolt://localhost:7687
echo   Browser: http://localhost:7474/
echo   账号:    neo4j / testhub
echo.
echo   后续操作:
echo     start ^| net start neo4j
echo     stop  ^| net stop neo4j
echo     check ^| sc query neo4j
echo.
goto :end_ok

:end_fail
echo.
echo [FAIL] 安装未完成，请检查上方错误
exit /b 1

:end_ok
exit /b 0
