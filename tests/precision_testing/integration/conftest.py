"""tests/precision_testing/integration conftest.py

初始化 Django（供集成测试连接真实 Neo4j）。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_DIR = REPO_ROOT / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def pytest_configure(config):
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
    import django
    django.setup()
