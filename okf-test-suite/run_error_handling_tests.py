#!/usr/bin/env python3
"""
OKF Validator - Error Handling Test Suite
-------------------------------------------
Feeds a set of deliberately broken (and one valid) markdown documents
through the OKF validation script and checks whether the validator's
pass/fail result matches what's expected for each case.

USAGE:
    python run_error_handling_tests.py

This calls scripts/validate-okf.js exactly the way Claude Code's PreToolUse
hook calls it in production: a JSON tool-invocation payload on stdin
(`{"tool_name": "Write", "tool_input": {"file_path": ..., "content": ...}}`),
no CLI arguments. Exit code 0 = allowed (valid OKF), exit code 2 = blocked
(invalid OKF) — see scripts/validate-okf.js and .claude/settings.json.
"""

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
VALIDATOR_CMD = ["node", str(REPO_ROOT / "scripts" / "validate-okf.js")]

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
    "11-missing-type.md": False,
}


def ran_ok(filepath: Path) -> tuple[bool, str]:
    """
    Runs the validator against a single file, simulating a Write tool call
    with that file's content — the real PreToolUse invocation shape.
    Returns (passed, details) where passed=True means the validator
    considered the file VALID (exit code 0; exit code 2 blocks).
    """
    content = filepath.read_text(encoding='utf-8')
    tool_invocation = json.dumps({
        "tool_name": "Write",
        "tool_input": {"file_path": str(filepath), "content": content}
    })

    try:
        result = subprocess.run(
            VALIDATOR_CMD,
            input=tool_invocation,
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
        result_str = "PASS" if match else "FAIL"

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
        print("All error-handling cases behaved as expected. PASS")
        sys.exit(0)


if __name__ == "__main__":
    main()
