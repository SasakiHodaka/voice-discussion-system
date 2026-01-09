#!/usr/bin/env python3
"""Run all test scenarios."""

import sys
import subprocess
import json
from datetime import datetime
from pathlib import Path

def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("  EchoMind System Test Suite")
    print("="*60)
    print(f"\nTest Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tests = [
        "test_stagnation.py",
        "test_imbalance.py",
        "test_productive.py"
    ]
    
    results = {}
    
    for test in tests:
        print(f"\n[*] Running {test}...")
        try:
            result = subprocess.run(
                [sys.executable, str(Path(__file__).parent / test)],
                capture_output=True,
                text=True,
                timeout=30
            )
            success = result.returncode == 0
            results[test] = {"success": success}
            if success:
                print(f"    SUCCESS")
            else:
                print(f"    FAILED")
                if result.stderr:
                    print(f"    Error: {result.stderr[:100]}")
        except Exception as e:
            results[test] = {"success": False}
            print(f"    ERROR: {str(e)}")
    
    # Summary
    print("\n" + "="*60)
    print("  Test Summary")
    print("="*60)
    
    passed = sum(1 for r in results.values() if r["success"])
    total = len(results)
    
    for test, result in results.items():
        status = "PASS" if result["success"] else "FAIL"
        print(f"{status}: {test}")
    
    print(f"\n{'='*60}")
    print(f"Results: {passed}/{total} tests passed")
    print(f"{'='*60}\n")
    
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())
