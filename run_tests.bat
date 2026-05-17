@echo off
cd /d E:\testhub_platform\backend
E:\testhub_platform\venv\Scripts\python.exe -m pytest tests/precision_testing/test_week4_layer1_scoring.py -v --tb=short 2>&1