@echo off
REM Temporary helper - sets Neo4j initial password
set "JAVA_HOME=C:\Program Files\Eclipse Adoptium\jdk-21.0.11.10-hotspot"
set "NEO4J_HOME=E:\neo4j-community-2026.04.0"
set "PATH=%JAVA_HOME%\bin;%PATH%"
cd /d "%NEO4J_HOME%"
echo ===== JAVA_HOME=%JAVA_HOME% =====
echo ===== NEO4J_HOME=%NEO4J_HOME% =====
java -version 2>&1
echo ===== Setting initial password =====
call bin\neo4j-admin.bat dbms set-initial-password testhub123
echo ===== EXIT_CODE=%ERRORLEVEL% =====
