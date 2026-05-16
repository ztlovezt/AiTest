"""tests/ 根目录 conftest.py

将 backend/ 注入 sys.path，使所有测试子目录可以 ``import apps.*``。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# 必须在 pytest-django 插件加载前设置，避免 DRF 等顶层导入失败
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings_test")

import django
django.setup()

import pytest

# repo root = tests/ 的上级目录
REPO_ROOT = Path(__file__).resolve().parent
BACKEND_DIR = REPO_ROOT / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# 让 Django settings 能够找到 apps 模块
sys.path.insert(0, str(REPO_ROOT))
