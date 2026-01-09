#!/usr/bin/env python3
"""Run all test scenarios and generate a report."""

import sys
import subprocess
import json
from datetime import datetime
from pathlib import Path

def run_test(test_file):
    """Run a single test and capture output."""
    print(f"\nRunning {test_file}...")
    try:
        result = subprocess.run(
            [sys.executable, str(Path(__file__).parent / test_file)],
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

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
        success, stdout, stderr = run_test(test)
        results[test] = {
            "success": success,
            "stdout": stdout,
            "stderr": stderr
        }
    
    # Summary
    print("\n" + "="*60)
    print("  Test Summary")
    print("="*60)
    
    passed = sum(1 for r in results.values() if r["success"])
    total = len(results)
    
    for test, result in results.items():
        status = "PASS" if result["success"] else "FAIL"
        print(f"\n{status}: {test}")
        if result["stderr"]:
            print(f"  Error: {result['stderr'][:200]}")
    
    print(f"\n{'='*60}")
    print(f"Overall: {passed}/{total} tests passed")
    print(f"Success Rate: {passed/total*100:.1f}%")
    print(f"{'='*60}\n")
    
    # Save report
    report_file = Path(__file__).parent / f"TEST_REPORT_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total_tests": total,
            "passed_tests": passed,
            "success_rate": passed/total,
            "results": {k: {"success": v["success"]} for k, v in results.items()}
        }, f, indent=2)
    
    print(f"Report saved to: {report_file}")
    
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())
