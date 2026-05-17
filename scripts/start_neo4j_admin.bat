@echo off
chcp 65001 >nul
cd /d E:\testhub_platform
echo Starting Neo4j...
docker compose -f docker-compose.neo4j.yml up -d
echo Done.
