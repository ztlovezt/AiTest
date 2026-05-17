"""Run pytest and capture output."""
import subprocess
import sys

result = subprocess.run(
    [
        r"C:\Program Files\Python311\python.exe",
        "-m", "pytest",
        "test_risk_predictor.py",
        "-v",
        "--tb=short",
    ],
    cwd=r"E:\testhub_platform\tests\precision_testing",
    capture_output=True,
    text=True,
    timeout=300,
)
print("STDOUT:")
print(result.stdout[:8000] if result.stdout else "(empty)")
if result.stderr:
    print("\nSTDERR:")
    print(result.stderr[:2000])
print("\nReturn code:", result.returncode)
sys.exit(result.returncode)