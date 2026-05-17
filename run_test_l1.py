"""Run Week 4 comprehensive tests and output results."""
import sys
import subprocess

result = subprocess.run(
    [
        r"C:\Program Files\Python311\python.exe",
        "-m", "pytest",
        r"E:\testhub_platform\tests\precision_testing\test_week4_layer1_scoring.py",
        "-v",
        "--tb=short",
        "--no-header",
        "-q",
    ],
    capture_output=True,
    text=True,
    timeout=300,
)
print("STDOUT:", result.stdout[:8000] if result.stdout else "(empty)")
print("STDERR:", result.stderr[:2000] if result.stderr else "(empty)")
print("Return code:", result.returncode)
sys.exit(result.returncode)