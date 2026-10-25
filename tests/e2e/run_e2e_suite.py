#!/usr/bin/env python3
"""Unified E2E Test Suite Runner for My-PKM.

Executes tests across Tiers 1-4 with comprehensive reporting.
Usage:
    python tests/e2e/run_e2e_suite.py [OPTIONS]

Options:
    --tier <1|2|3|4>    Run only a specific tier (default: run all tiers)
    --verbose, -v       Show verbose test-by-test results
    --fail-fast, -x     Stop on first failure
    --json              Output summary report in JSON format
"""

import argparse
import json
import os
import sys
import time
import unittest
from pathlib import Path

# Add tests/e2e to sys.path
E2E_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = E2E_DIR.parent.parent
if str(E2E_DIR) not in sys.path:
    sys.path.insert(0, str(E2E_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Tier mapping to test modules
TIER_MODULES = {
    1: ("Tier 1: Feature Coverage", "test_tier1_features"),
    2: ("Tier 2: Boundary & Corner Cases", "test_tier2_boundaries"),
    3: ("Tier 3: Cross-Feature Combinations", "test_tier3_combinations"),
    4: ("Tier 4: Real-World Scenarios", "test_tier4_scenarios"),
}


class TierTestResult(unittest.TestResult):
    """Custom TestResult collecting detailed execution metrics per Tier."""

    def __init__(self, verbosity=1):
        super().__init__()
        self.verbosity = verbosity
        self.records = []
        self._test_start_time = None

    def startTest(self, test):
        super().startTest(test)
        self._test_start_time = time.perf_counter()
        if self.verbosity > 1:
            test_id = test.id().split(".")[-1]
            cls_name = test.__class__.__name__
            sys.stdout.write(f"  {cls_name}.{test_id} ... ")
            sys.stdout.flush()

    def addSuccess(self, test):
        super().addSuccess(test)
        elapsed = time.perf_counter() - self._test_start_time
        self.records.append({
            "test": test.id(),
            "status": "PASS",
            "duration": elapsed,
            "error": None,
        })
        if self.verbosity > 1:
            print(f"\033[92mPASS\033[0m ({elapsed:.3f}s)")

    def addFailure(self, test, err):
        super().addFailure(test, err)
        elapsed = time.perf_counter() - self._test_start_time
        err_msg = self._exc_info_to_string(err, test)
        self.records.append({
            "test": test.id(),
            "status": "FAIL",
            "duration": elapsed,
            "error": err_msg,
        })
        if self.verbosity > 1:
            print(f"\033[91mFAIL\033[0m ({elapsed:.3f}s)")

    def addError(self, test, err):
        super().addError(test, err)
        elapsed = time.perf_counter() - self._test_start_time
        err_msg = self._exc_info_to_string(err, test)
        self.records.append({
            "test": test.id(),
            "status": "ERROR",
            "duration": elapsed,
            "error": err_msg,
        })
        if self.verbosity > 1:
            print(f"\033[93mERROR\033[0m ({elapsed:.3f}s)")


def run_tier(tier_num: int, fail_fast: bool = False, verbosity: int = 1):
    tier_name, module_name = TIER_MODULES[tier_num]
    try:
        mod = __import__(module_name)
    except Exception as exc:
        return {
            "tier": tier_num,
            "name": tier_name,
            "error": f"Failed to import {module_name}: {exc}",
            "tests_run": 0,
            "passed": 0,
            "failed": 0,
            "errors": 1,
            "duration": 0.0,
            "records": [],
        }

    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(mod)

    result = TierTestResult(verbosity=verbosity)
    result.failfast = fail_fast

    start_time = time.perf_counter()
    suite.run(result)
    elapsed = time.perf_counter() - start_time

    return {
        "tier": tier_num,
        "name": tier_name,
        "tests_run": result.testsRun,
        "passed": result.testsRun - len(result.failures) - len(result.errors),
        "failed": len(result.failures),
        "errors": len(result.errors),
        "duration": elapsed,
        "records": result.records,
    }


def main():
    parser = argparse.ArgumentParser(description="My-PKM Unified E2E Test Suite Runner")
    parser.add_argument("--tier", type=int, choices=[1, 2, 3, 4], help="Run only specific tier")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose test execution")
    parser.add_argument("-x", "--fail-fast", action="store_true", help="Stop on first failure")
    parser.add_argument("--json", action="store_true", help="Output JSON results")
    args = parser.parse_args()

    verbosity = 2 if args.verbose else 1
    tiers_to_run = [args.tier] if args.tier else [1, 2, 3, 4]

    if not args.json:
        print("=" * 72)
        print(" " * 20 + "My-PKM E2E Test Suite Runner")
        print("=" * 72)
        print(f"Project Root : {PROJECT_ROOT}")
        print(f"Python Exec  : {sys.executable} (Python {sys.version.split()[0]})")
        print(f"Tiers In Scope: {tiers_to_run}")
        print("=" * 72)

    tier_results = []
    total_start = time.perf_counter()

    for t in tiers_to_run:
        tier_title = TIER_MODULES[t][0]
        if not args.json:
            print(f"\n--- Running {tier_title} ---")
        res = run_tier(t, fail_fast=args.fail_fast, verbosity=verbosity)
        tier_results.append(res)
        if not args.json:
            print(f"  Result: {res['passed']} passed, {res['failed']} failed, {res['errors']} errors ({res['duration']:.2f}s)")
        if args.fail_fast and (res["failed"] > 0 or res["errors"] > 0):
            break

    total_elapsed = time.perf_counter() - total_start

    total_run = sum(r["tests_run"] for r in tier_results)
    total_passed = sum(r["passed"] for r in tier_results)
    total_failed = sum(r["failed"] for r in tier_results)
    total_errors = sum(r["errors"] for r in tier_results)

    if args.json:
        output_payload = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "total_run": total_run,
            "passed": total_passed,
            "failed": total_failed,
            "errors": total_errors,
            "total_duration": total_elapsed,
            "tiers": tier_results,
        }
        print(json.dumps(output_payload, indent=2, ensure_ascii=False))
    else:
        print("\n" + "=" * 72)
        print(" " * 24 + "E2E TEST SUMMARY REPORT")
        print("=" * 72)
        print(f"{'Tier / Component':<36} {'Run':<6} {'Pass':<6} {'Fail':<6} {'Err':<6} {'Time':<8}")
        print("-" * 72)
        for r in tier_results:
            print(f"{r['name']:<36} {r['tests_run']:<6} {r['passed']:<6} {r['failed']:<6} {r['errors']:<6} {r['duration']:.2f}s")
        print("-" * 72)
        print(f"{'TOTAL':<36} {total_run:<6} {total_passed:<6} {total_failed:<6} {total_errors:<6} {total_elapsed:.2f}s")
        print("=" * 72)

        # Print failure diagnostics
        all_failures = []
        for r in tier_results:
            for rec in r["records"]:
                if rec["status"] in ("FAIL", "ERROR"):
                    all_failures.append(rec)

        if all_failures:
            print(f"\nDiscovered {len(all_failures)} failure(s) / pending feature(s):")
            for idx, f in enumerate(all_failures, 1):
                test_name = f["test"].split(".")[-1]
                cls_name = f["test"].split(".")[-2]
                print(f"\n[{idx}] {cls_name}.{test_name} ({f['status']}):")
                lines = (f["error"] or "").strip().splitlines()
                # Print the last few informative lines of error
                for line in lines[-4:]:
                    print(f"    {line}")

        if total_failed == 0 and total_errors == 0:
            print("\n\033[92mALL TESTS PASSED SUCCESSFULLY! (100%)\033[0m\n")
        else:
            print(f"\n\033[93mTest Suite completed with {total_failed} failure(s) and {total_errors} error(s).\033[0m\n")

    return 0 if (total_failed == 0 and total_errors == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
