"""Run Week 4 comprehensive tests with proper Django settings."""
import subprocess
import sys
import os

env = os.environ.copy()
env['DJANGO_SETTINGS_MODULE'] = 'backend.settings_test'
env['PYTHONPATH'] = r'E:\testhub_platform\backend;' + env.get('PYTHONPATH', '')

files = [
    "test_week4_layer1_scoring.py",
    "test_week4_layer2_selector.py",
    "test_week4_layer3_pipeline.py",
]

all_passed = True
total_passed = 0
total_failed = 0

for f in files:
    result = subprocess.run(
        [
            sys.executable,
            "-m", "pytest",
            f,
            "-v",
            "--tb=short",
        ],
        cwd=r"E:\testhub_platform\tests\precision_testing",
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )
    print(f"\n{'='*60}")
    print(f"FILE: {f}")
    print(f"{'='*60}")
    print(result.stdout[:5000] if result.stdout else "(empty)")
    if result.stderr:
        print("STDERR:", result.stderr[:1000])
    print(f"Return code: {result.returncode}")
    if result.returncode != 0:
        all_passed = False
    # Parse result
    if "passed" in result.stdout:
        total_passed += 1
    if "failed" in result.stdout:
        total_failed += 1

print(f"\n{'='*60}")
print(f"ALL FILES COMPLETED")
print(f"Return codes: {'PASS' if all_passed else 'FAIL'}")
print(f"{'='*60}")