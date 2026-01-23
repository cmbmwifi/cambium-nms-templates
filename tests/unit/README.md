# Unit Tests

Unit tests for individual components of cambium-nms-templates. These tests are fast, isolated, and don't require external dependencies like Docker or live systems.

## Structure

```
tests/unit/
├── run_all.sh                     # Main unit test runner
├── cambium-olt-collector/         # Tests for Cambium OLT data collector
│   ├── run_all.sh                 # Runner for this test suite
│   └── test_error_handling.py     # Error propagation tests
└── README.md                       # This file
```

## Test Suites

### Cambium OLT Collector Tests

Tests for the `cambium_olt_ssh_json.py` data collector script.

**What's tested:**
- SSH error propagation (connection failures, timeouts)
- JSON parsing error handling
- CLI exit codes (0 for success, 1 for errors)
- Output format validation
- Error messages to stderr

**Run these tests:**
```bash
./tests/unit/cambium-olt-collector/run_all.sh
```

## Running Unit Tests

### Run all unit tests
```bash
./tests/unit/run_all.sh
```

### Run specific test suite
```bash
./tests/unit/cambium-olt-collector/run_all.sh
```

### Run from project root
```bash
./tests/run_all.sh  # Runs unit tests first, then integration tests
```

## Adding New Unit Tests

1. **Create a new directory** under `tests/unit/` for your test suite:
   ```bash
   mkdir tests/unit/my-new-component/
   ```

2. **Add your test files** (Python, bash, etc.):
   ```bash
   tests/unit/my-new-component/test_something.py
   ```

3. **Create a test suite runner**:
   ```bash
   tests/unit/my-new-component/run_my_tests.sh
   ```

4. The `tests/unit/run_all.sh` script will **automatically discover** your test suite:
   - It looks for any `run_*.sh` script in subdirectories
   - No manual registration required
   - Just ensure your runner script follows the naming pattern: `run_*.sh`

## Why Unit Tests?

Unit tests complement integration tests by:
- ✅ Running **much faster** (no Docker, no external services)
- ✅ Testing **specific behaviors** in isolation
- ✅ Providing **immediate feedback** during development
- ✅ Catching **logic errors** before integration
- ✅ Running **without privileges** or system dependencies

Integration tests verify everything works together; unit tests verify each piece works correctly.

## Test Output

Unit tests use colored output with clear pass/fail indicators:
- ✓ Green checkmarks for passing tests
- ✗ Red X's for failing tests
- Summary with total/passed/failed counts

Example output:
```
============================================================
Running Unit Tests: Error Handling
============================================================

✓ Test that SSH connection failures raise an exception.
✓ Test that CLI exits with error code 1 on SSH failure.
✓ Test that successful SSH fetch returns parsed data.

============================================================
Test Summary
============================================================
Total tests: 11
Passed: 11
```

## Requirements

- Python 3.8+
- Standard library only (unittest, mock)
- No external dependencies for unit tests

## See Also

- [Integration Tests](../integration/README.md) - Full system tests with Docker
- [Contributing Guide](../../docs/contributing.md) - Development workflow
- [Testing Guide](../../docs/testing.md) - Comprehensive testing documentation
