# OKF Validator - Error Handling Test Suite

This folder contains deliberately broken OKF-format markdown documents,
each violating exactly one validation rule, plus a runner script that
checks whether your validator catches each one correctly.

## Structure

```
okf-test-suite/
├── run_error_handling_tests.py   # test runner
├── test-cases/
│   ├── 00-valid-control.md       # should PASS (sanity check)
│   ├── 01-missing-title.md       # should FAIL - frontmatter
│   ├── 02-invalid-date-format.md # should FAIL - frontmatter
│   ├── 03-missing-sources-array.md
│   ├── 04-source-missing-url.md
│   ├── 05-invalid-source-type.md
│   ├── 06-invalid-confidence-value.md
│   ├── 07-citation-undefined-source.md
│   ├── 08-malformed-citation-format.md
│   ├── 09-empty-file.md
│   └── 10-no-content-body.md
```

## Setup

1. Copy this whole `okf-test-suite/` folder into your repo (e.g. next to
   your existing validation script).
2. Open `run_error_handling_tests.py` and edit the `VALIDATOR_CMD` line
   near the top to match how you actually invoke your validator, e.g.:

   ```python
   VALIDATOR_CMD = ["python", "validate_okf.py"]
   # or
   VALIDATOR_CMD = ["node", "validate_okf.js"]
   ```

3. Confirm your validator exits with code `0` on success and non-zero
   on failure. If instead it always exits 0 and prints "PASS"/"FAIL" to
   stdout, tweak the `ran_ok()` function to check `result.stdout`
   instead of `result.returncode`.

## Run it

```bash
python run_error_handling_tests.py
```

You'll get a table like:

```
File                                   Expected   Got        Result
---------------------------------------------------------------------
00-valid-control.md                    PASS       PASS       ✓ correct
01-missing-title.md                    FAIL       FAIL       ✓ correct
...
```

Exit code is `0` if every case matched expectations, `1` otherwise
(handy for wiring into CI or a pre-commit hook later).

## Why this matters for the assignment

This directly covers the "error handling tests" item: it proves the
validator doesn't just rubber-stamp well-formed documents, but actually
catches each class of malformed input (bad frontmatter, bad source
metadata, bad citations, empty/content-less files) — and doesn't
false-positive on a valid document either.
