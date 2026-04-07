@echo off
chcp 65001 >nul
title TestHub Document Parser (Tika Server)

echo Starting Tika Server on port 9987...
echo Press Ctrl+C to stop the server
echo.

java -Djava.awt.headless=true -Xmx512m -jar ../expand/tika-server.jar --host=localhost --port=9987
