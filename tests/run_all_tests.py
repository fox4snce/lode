"""
Run all tests in the project.
"""
import subprocess
import sys
import os
from pathlib import Path

# Get the tests directory (where this script is located)
tests_dir = Path(__file__).parent

# List of all test files (relative to tests directory)
test_files = [
    'test_continue_feature.py',
    'test_redaction.py',
    'test_deduplication.py',
    'test_import_report.py',
    'test_integrity_checks.py',
]

def run_test(test_file):
    """Run a single test file."""
    test_path = tests_dir / test_file
    print(f"\n{'='*60}")
    print(f"Running {test_file}")
    print('='*60)
    
    result = subprocess.run(
        [sys.executable, str(test_path)],
        capture_output=True,
        text=True,
        cwd=str(tests_dir.parent)  # Run from project root
    )
    
    if result.returncode == 0:
        print(f"[PASS] {test_file}")
        if result.stdout:
            print(result.stdout)
        return True
    else:
        print(f"[FAIL] {test_file}")
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)
        return False

if __name__ == '__main__':
    print("Running all tests...")
    
    passed = 0
    failed = 0
    
    for test_file in test_files:
        test_path = tests_dir / test_file
        if test_path.exists():
            if run_test(test_file):
                passed += 1
            else:
                failed += 1
        else:
            print(f"[SKIP] {test_file} (not found)")
    
    print(f"\n{'='*60}")
    print(f"Test Summary: {passed} passed, {failed} failed")
    print('='*60)
    
    sys.exit(0 if failed == 0 else 1)

