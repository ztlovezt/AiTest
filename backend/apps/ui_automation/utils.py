"""
UI自动化工具函数
"""
import os
import json
import subprocess
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def _check_java_environment():
    """检查 Java 环境是否可用"""
    try:
        result = subprocess.run(['java', '-version'], capture_output=True, text=True, timeout=10)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
