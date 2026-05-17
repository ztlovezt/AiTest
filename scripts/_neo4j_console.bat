@echo off
chcp 65001 > nul
set JAVA_HOME=C:\Program Files\Eclipse Adoptium\jdk-21.0.11.10-hotspot
cd /d E:\neo4j-community-2026.04.0\bin
neo4j.bat console
