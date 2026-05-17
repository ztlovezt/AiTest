#!/bin/bash
set -e

echo "=========================================="
echo " TestHub Neo4j 启动脚本"
echo "=========================================="

# 检查 Docker
if ! docker info > /dev/null 2>&1; then
    echo "[错误] Docker 守护进程未运行。"
    echo "请先启动 Docker,然后重新运行此脚本。"
    exit 1
fi

echo "[1/3] 正在启动 Neo4j..."
if docker compose version &> /dev/null; then
    docker compose -f docker-compose.neo4j.yml up -d
else
    docker-compose -f docker-compose.neo4j.yml up -d
fi

echo "[2/3] 等待 Neo4j 就绪(约 15 秒)..."
sleep 15

echo "[3/3] 检查 Neo4j 连接状态..."
if docker exec testhub-neo4j cypher-shell -u neo4j -p testhub "MATCH (n) RETURN count(n) AS nodes;" > /dev/null 2>&1; then
    echo "[成功] Neo4j 已就绪!"
else
    echo "[警告] Neo4j 可能尚未完全启动,请稍后再试。"
fi

echo ""
echo "=========================================="
echo " Neo4j 访问信息:"
echo "   Browser: http://localhost:7474"
echo "   Bolt:    bolt://localhost:7687"
echo "   用户名:  neo4j"
echo "   密码:    testhub"
echo "=========================================="
