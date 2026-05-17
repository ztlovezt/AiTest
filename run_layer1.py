"""Run Week 4 Layer 1 tests with pytest."""
import subprocess
import sys

# Run tests for Layer 1
result = subprocess.run(
    [
        sys.executable,
        "-m", "pytest",
        r"E:\testhub_platform\tests\precision_testing\test_week4_layer1_scoring.py",
        "-v",
        "--tb=short",
        "-x",  # Stop on first failure
    ],
    cwd=r"E:\testhub_platform\backend",
    capture_output=True,
    text=True,
    timeout=300,
)
print("STDOUT:", result.stdout[:6000] if result.stdout else "(empty)")
if result.stderr:
    print("STDERR:", result.stderr[:2000])
print("Return code:", result.returncode)