# Testing Guide

## Testing Approaches

### Automated Testing (Recommended for Development)

Use the containerized test suite for development and validation:
```bash
# Run all tests
./tests/run_all.sh

# Run just integration tests
./tests/integration/run_all_zabbix_tests.sh
```

**Why containerized tests:**
- ✅ Works on any development machine
- ✅ No Zabbix installation required
- ✅ Tests against multiple Zabbix versions (7.0, 7.2, 7.4, 8.0)
- ✅ Isolated Docker environments ensure reproducibility
- ✅ Same tests that run in CI/CD

### Manual Smoke Testing (Requires Live Zabbix Server)

If you have access to a live Zabbix server, you can manually test the installer:
```bash
./install.sh --local
```

**Requirements:**
- Running Zabbix server (not required on development machine)
- SSH access to the Zabbix server
- Root/sudo privileges on the Zabbix server

**Note:** Most developers should use the automated containerized tests instead. Use `--local` only when you need to verify installer behavior on a real Zabbix instance.

## Test Structure

The project uses a hierarchical test organization with two main categories:

### Unit Tests

Fast, isolated tests that run without external dependencies:

```bash
# Run all unit tests
./tests/unit/run_unit_tests.sh

# Run specific test suite
./tests/unit/cambium-olt-collector/run_cambium_olt_tests.sh
```

**What's tested:**
- Error handling and propagation
- Data parsing logic
- CLI argument processing
- Function-level behavior

**Benefits:**
- ⚡ Fast (milliseconds)
- 🔒 No privileges required
- 📦 No external dependencies
- 💻 Run anywhere

### Integration Tests

Full system tests that verify everything works together:

```bash
# Run all integration tests
./tests/integration/run_all_zabbix_tests.sh
./tests/integration/run_installer_tests.sh

# Run specific version test
./tests/integration/zabbix/test_zabbix74.py
```

**What's tested:**
- Installer functionality
- Template import and validation
- API interactions
- Multi-version compatibility
- Dependency installation

**Requirements:**
- 🐳 Docker
- 🔑 Root/sudo (for some tests)
- ⏱️ More time (minutes)

### Top Level - Run Everything

```bash
./tests/run_all.sh
```

This runs:
1. **Unit tests first** (fast feedback)
2. **Mock OLT tests** (device simulation)
3. **Installer tests** (configuration/dependencies)
4. **Integration tests** (full Zabbix tests)

## Test Philosophy

### Unit Tests: Fast Feedback

Unit tests provide immediate feedback during development:
- Test individual functions in isolation
- Mock external dependencies
- Verify error handling
- Validate data transformations

### Integration Tests: Docker Isolation

All integration tests run in isolated Docker environments to ensure reproducibility across different development machines and CI/CD systems.

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

Use containerized tests during development (no Zabbix installation needed):
```bash
# Working on Zabbix templates - test against specific version
./tests/integration/zabbix/test_zabbix70.py

# Working on installer menu
./tests/integration/installer/test_installer_menu.py

# Test all Zabbix versions
./tests/integration/run_all_zabbix_tests.sh
```

### Pre-Commit Validation

Before pushing changes, run the full suite:
```bash
./tests/run_all.sh
```

### Debugging and Manual Testing

For quick manual testing without running full test suites, use the smoke test helper:

```bash
# Start a Zabbix environment for manual exploration
./scripts/smoketest.sh zabbix74

# Start fresh (clean database)
./scripts/smoketest.sh --clean zabbix70

# Stop all smoke test environments
./scripts/smoketest.sh --halt
```

This keeps the environment running so you can access the GUI, run the installer manually, and explore templates interactively. See `./scripts/smoketest.sh --help` for details.

**Alternative - Keep test environment running:**
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
