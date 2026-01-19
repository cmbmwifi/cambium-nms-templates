# Zabbix Integration Tests

Python-based integration tests for Zabbix 7.0, 7.2, and 7.4 compatibility using Docker containers.

## Architecture (Refactored)

The test suite has been refactored into a modular architecture:

```
tests/integration/zabbix/
├── base/                          # Core infrastructure
│   ├── test_harness.py           # Main test coordinator
│   ├── docker_helpers.py         # Docker operations
│   ├── api_helpers.py            # Zabbix API client
│   └── assertions.py             # Test assertions
├── validators/                    # Validation logic
│   ├── template_validator.py    # Template validation
│   └── item_validator.py        # Item validation
├── suites/                        # Test suites by priority
│   └── test_core_functionality.py
├── zabbix_test_base.py           # Legacy compatibility wrapper
└── test_zabbix*.py               # Version-specific test runners
```

**Key Benefits:**
- Separation of concerns (Docker, API, validation, tests)
- DRY principle - no code duplication
- Easy to extend with new tests
- Validators can be unit tested independently

## Requirements

- Python 3.x
- requests: `pip3 install requests`
- Docker and docker-compose
- sshpass (for mock OLT SSH testing)

## Running Tests

```bash
# Run all Zabbix versions (7.0, 7.2, 7.4)
./tests/integration/run_all_zabbix_tests.sh

# Or run individual version tests
python3 tests/integration/zabbix/test_zabbix70.py
python3 tests/integration/zabbix/test_zabbix72.py
python3 tests/integration/zabbix/test_zabbix74.py

# Keep stack running for manual testing
python3 tests/integration/zabbix/test_zabbix70.py --keep
```

## What's Tested

Each Zabbix version test runs the following:

1. **Docker Services Health** - Verifies all containers are running
2. **Mock OLT SSH Connectivity** - Tests SSH connections to mock OLT devices
3. **OLT Data Retrieval** - Validates Python script can retrieve JSON data from OLTs
4. **Zabbix Web UI** - Confirms web interface is accessible
5. **Zabbix API Authentication** - Tests API login (version-specific methods)
6. **Zabbix Version Check** - Verifies correct Zabbix version is running
7. **External Scripts Volume** - Confirms external scripts directory exists
8. **Template Installation** - Tests install.sh in non-interactive mode

## Test Architecture

### Structure
```
tests/integration/
├── run_all_zabbix_tests.sh        # Runs all version tests
├── mock-olt/                      # Standalone mock OLT for testing
│   ├── mock_olt_ssh_server.py
│   ├── test_mock_olt.py
│   └── Dockerfile
└── zabbix/
    ├── zabbix_test_base.py        # Shared test base class (DRY)
    ├── test_zabbix70.py           # Zabbix 7.0 LTS tests
    ├── test_zabbix72.py           # Zabbix 7.2 tests
    ├── test_zabbix74.py           # Zabbix 7.4 tests
    ├── docker-compose.base.yml    # Common services (mock OLTs, DB)
    ├── docker-compose.zabbix70.yml
    ├── docker-compose.zabbix72.yml
    └── docker-compose.zabbix74.yml
```

### Components
- **Docker containers** - Isolated testing environment with Zabbix + Mock OLTs
- **Mock OLT SSH servers** - Simulated Cambium devices returning fixture data
- **ZabbixTestBase** - Shared test infrastructure (all common logic)
- **Version-specific tests** - Minimal subclasses (version + compose file only)

## Why Python?

Python offers several advantages over bash for testing:

1. **Better testing frameworks** - Structured test classes and assertions
2. **pexpect** - Robust interactive automation (better than expect scripts)
3. **Error handling** - Try/except blocks and proper exception handling
4. **Package ecosystem** - Easy integration with other tools
5. **Maintainability** - Cleaner, more readable test code
6. **Debugging** - Better tooling and error messages

## Test Output

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Integration Test Suite - Multiple Zabbix Versions
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

============================================================
  Zabbix 7.0 Integration Tests
============================================================

Starting Docker Compose stack...
Waiting for services to be healthy (this may take 60-90 seconds)...
✓ All services are healthy

Test 1: Docker services health
✓ Mock OLT containers are running
✓ Zabbix containers are running

Test 2: Mock OLT SSH connectivity
✓ Mock OLT 1 SSH server is listening
✓ Mock OLT 2 SSH server is listening

...

============================================================
✓ All 12 tests passed!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Aggregate Test Summary
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Zabbix 7.0: ✓ PASSED
  Zabbix 7.2: ✓ PASSED
  Zabbix 7.4: ✓ PASSED

Total: 3 passed, 0 failed
```

## Adding New Tests

### For all Zabbix versions (common test)
Add a new test method to `zabbix_test_base.py`:
```python
def test_my_feature(self):
    """Test X: Description"""
    self._print_colored("\nTest X: My Feature", Colors.BLUE)
    # Test logic here
    self.assert_test(
        condition,
        "Test description",
        "Error message if failed"
    )
```

Then add it to `run_all_tests()` in the base class.

### For version-specific tests
Override a method in the specific test file (e.g., `test_zabbix74.py`):
```python
class Zabbix74Test(ZabbixTestBase):
    def test_version_specific_feature(self):
        # 7.4-specific logic
        pass
```

### Adding a new Zabbix version
1. Create `docker-compose.zabbix{version}.yml`
2. Create `test_zabbix{version}.py` with version and compose file
3. Add to `run_all_zabbix_tests.sh`

