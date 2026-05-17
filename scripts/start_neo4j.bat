@echo off
chcp 65001 > nul
echo ==========================================
echo  TestHub Neo4j 启动脚本
echo ==========================================

:: 检查 Docker 是否运行
docker info > nul 2>&1
if errorlevel 1 (
    echo [错误] Docker 守护进程未运行。
    echo 请先启动 Docker Desktop,然后重新运行此脚本。
    echo.
    echo 手动启动方式:
    echo   1. 打开 Docker Desktop 应用
    echo   2. 等待左下角状态变为 "Engine running"
    echo   3. 重新运行此脚本
    pause
    exit /b 1
)

echo [1/3] Docker 运行正常,正在启动 Neo4j...
docker compose -f docker-compose.neo4j.yml up -d

if errorlevel 1 (
    echo [错误] Neo4j 启动失败。
    pause
    exit /b 1
)

echo [2/3] 等待 Neo4j 就绪(约 15 秒)...
ping -n 16 127.0.0.1 > nul 2>&1

echo [3/3] 检查 Neo4j 连接状态...
docker exec testhub-neo4j cypher-shell -u neo4j -p testhub "MATCH (n) RETURN count(n) AS nodes;" > nul 2>&1
if errorlevel 1 (
    echo [警告] Neo4j 可能尚未完全启动,请稍后再试。
) else (
    echo [成功] Neo4j 已就绪!
)

echo.
echo ==========================================
echo  Neo4j 访问信息:
echo    Browser: http://localhost:7474
echo    Bolt:    bolt://localhost:7687
echo    用户名:  neo4j
echo    密码:    testhub
echo ==========================================
pause
