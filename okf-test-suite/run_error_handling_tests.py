#!/usr/bin/env python3
"""
OKF Validator - Error Handling Test Suite
-------------------------------------------
Feeds a set of deliberately broken (and one valid) markdown documents
through the OKF validation script and checks whether the validator's
pass/fail result matches what's expected for each case.

USAGE:
    python run_error_handling_tests.py

CONFIGURE:
    Edit VALIDATOR_CMD below to match how your validator is actually
    invoked (path to script + any flags). It's currently assumed to:
      - take a single file path as its argument
      - exit with code 0 on success, non-zero on validation failure
    If your validator instead prints "PASS"/"FAIL" to stdout regardless
    of exit code, tweak `ran_ok()` accordingly (see comment inline).
"""

import subprocess
import sys
from pathlib import Path

# ---- CONFIGURE THIS ----
# Example if it's a python script: ["python", "validate_okf.py"]
# Example if it's a node script:   ["node", "validate_okf.js"]
# Example if it's a Claude Code agent/CLI wrapper, replace accordingly.
VALIDATOR_CMD = ["node", "../scripts/validate-okf.js"]
# -------------------------

TEST_DIR = Path(__file__).parent / "test-cases"

# expected result: True = should PASS validation, False = should FAIL
EXPECTATIONS = {
    "00-valid-control.md": True,
    "01-missing-title.md": False,
    "02-invalid-date-format.md": False,
    "03-missing-sources-array.md": False,
    "04-source-missing-url.md": False,
    "05-invalid-source-type.md": False,
    "06-invalid-confidence-value.md": False,
    "07-citation-undefined-source.md": False,
    "08-malformed-citation-format.md": False,
    "09-empty-file.md": False,
    "10-no-content-body.md": False,
}


def ran_ok(filepath: Path) -> tuple[bool, str]:
    """
    Runs the validator against a single file.
    Returns (passed, details) where passed=True means the validator
    considered the file VALID (exit code 0).
    """
    try:
        result = subprocess.run(
            VALIDATOR_CMD + [str(filepath)],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except FileNotFoundError:
        print(f"ERROR: could not run {VALIDATOR_CMD}. "
              f"Check the command/path in VALIDATOR_CMD.")
        sys.exit(1)
    except subprocess.TimeoutExpired:
        return False, "validator timed out"

    passed = result.returncode == 0
    details = (result.stdout + result.stderr).strip()
    return passed, details


def main():
    if not TEST_DIR.exists():
        print(f"ERROR: test-cases directory not found at {TEST_DIR}")
        sys.exit(1)

    total = 0
    correct = 0
    failures = []

    print("Running OKF validator error-handling test suite...\n")
    print(f"{'File':<38} {'Expected':<10} {'Got':<10} {'Result'}")
    print("-" * 75)

    for filename, expect_pass in sorted(EXPECTATIONS.items()):
        filepath = TEST_DIR / filename
        if not filepath.exists():
            print(f"{filename:<38} {'MISSING FILE':<10}")
            continue

        total += 1
        actual_pass, details = ran_ok(filepath)

        expected_str = "PASS" if expect_pass else "FAIL"
        actual_str = "PASS" if actual_pass else "FAIL"
        match = actual_pass == expect_pass
        result_str = "✓ correct" if match else "✗ WRONG"

        if match:
            correct += 1
        else:
            failures.append((filename, expected_str, actual_str, details))

        print(f"{filename:<38} {expected_str:<10} {actual_str:<10} {result_str}")

    print("-" * 75)
    print(f"\n{correct}/{total} test cases handled correctly.\n")

    if failures:
        print("Details on mismatches:\n")
        for filename, expected, actual, details in failures:
            print(f"- {filename}: expected {expected}, validator said {actual}")
            if details:
                snippet = details[:300]
                print(f"    validator output: {snippet}")
        print()
        sys.exit(1)
    else:
        print("All error-handling cases behaved as expected. ✅")
        sys.exit(0)


if __name__ == "__main__":
    main()
