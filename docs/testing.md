# Testing Guide

## Test Structure

The project uses a hierarchical test organization:

**Top Level** - Run all tests across all test suites:
```bash
./tests/run_all.sh
```

**Suite Level** - Run all tests for a specific component:
```bash
./tests/integration/run_all_zabbix_tests.sh  # All Zabbix tests
./tests/integration/run_installer_tests.sh   # All installer tests
```

**Individual Level** - Run specific test scripts:
```bash
./tests/integration/zabbix/test_zabbix70.py
./tests/integration/zabbix/test_zabbix72.py
./tests/integration/installer/test_installer_menu.py
```

This design supports both focused development (test what you're changing) and comprehensive validation (test everything before release).

## Test Philosophy

### Docker Isolation

All tests run in isolated Docker environments to ensure reproducibility across different development machines and CI/CD systems.

### Hierarchical Organization

Tests are grouped by component (zabbix, installer, mock-olt) with each level able to run independently or as part of the full suite.

### Shared Infrastructure

Common services (MySQL, Mock devices) are reused across tests to reduce overhead:
- **Smart Lifecycle**: Infrastructure starts only when needed
- **Conditional Cleanup**: Only stop what the test run started
- **Clean Slate Pattern**: Each test recreates its database for isolation
- **Non-Persistent Storage**: No data accumulation between test sessions

This allows:
- Individual test runs that manage their own dependencies
- Orchestrated suites that share infrastructure across multiple tests
- Fast iteration during development
- Reliable results in CI/CD

## Running Tests

### Development Workflow

Run what you're working on:
```bash
# Working on Zabbix 7.0 template
./tests/integration/zabbix/test_zabbix70.py

# Working on installer menu
./tests/integration/installer/test_installer_menu.py
```

### Pre-Commit Validation

Before pushing changes, run the full suite:
```bash
./tests/run_all.sh
```

### Debugging

Keep test environment running for manual inspection:
```bash
./tests/integration/zabbix/test_zabbix70.py --keep-running
```

Access services:
- Zabbix 7.0: http://localhost:8080 (Admin/zabbix)
- Zabbix 7.2: http://localhost:8081 (Admin/zabbix)
- Zabbix 7.4: http://localhost:8082 (Admin/zabbix)

Manual cleanup when done:
```bash
docker-compose -f base.yml -f zabbix70.yml -p zabbix-test-70 down
```

## Writing Tests

### Design Principles

- **Test behavior, not implementation**: Validate outcomes, not internal mechanics
- **One concept per test**: Makes failures easy to diagnose
- **Independent execution**: Tests shouldn't depend on each other
- **Version compatibility**: Tests should work across all supported versions

### Adding Tests

1. Identify appropriate suite or create new test file
2. Follow existing patterns for consistency
3. Use provided test infrastructure (API clients, assertions, helpers)
4. Validate across all relevant versions

See existing test suites in `tests/integration/` for examples.

## Troubleshooting

**Port conflicts**: Existing containers using test ports
- Solution: `docker-compose down` or use different ports

**Timeout failures**: Services taking longer to start
- Cause: System load, slow Docker on macOS
- Solution: Tests retry with backoff, usually self-resolving

**Database errors**: Stale state or connection issues
- Solution: Tests use clean slate pattern, restarting MySQL fixes edge cases

**Type errors**: Python type hints flag issues
- Tool: Use IDE type checker or `mypy` for validation

## CI/CD Integration

Tests are designed for automated pipelines:
- Single command execution (`./tests/run_all.sh`)
- Exit code indicates pass/fail
- No manual intervention required
- Docker handles all dependencies
