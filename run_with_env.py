"""Run pytest with proper Django settings."""
import subprocess
import sys
import os

env = os.environ.copy()
env['DJANGO_SETTINGS_MODULE'] = 'backend.settings_test'
env['PYTHONPATH'] = r'E:\testhub_platform\backend;' + env.get('PYTHONPATH', '')

result = subprocess.run(
    [
        sys.executable,
        "-m", "pytest",
        "test_risk_predictor.py",
        "-v",
        "--tb=short",
        "-x",
    ],
    cwd=r"E:\testhub_platform\tests\precision_testing",
    env=env,
    capture_output=True,
    text=True,
    timeout=300,
)
print("STDOUT:")
print(result.stdout[:8000] if result.stdout else "(empty)")
if result.stderr:
    print("\nSTDERR (first 2000):")
    print(result.stderr[:2000])
print("\nReturn code:", result.returncode)