# Installer Integration Tests

Tests the installer's configuration collection, validation, and dependency management.

## What's Tested

### 1. **Dependency Installation** ✓
- Verifies `sshpass` is checked and installed automatically
- Tests that missing dependencies are detected
- Confirms dependencies are functional after installation
- Validates PyYAML and other Python dependencies

### 2. **Configuration Collection** ✓
- Non-interactive mode with all variables
- Non-interactive mode with minimal required variables
- Default value handling for optional parameters

### 3. **Requirements.yaml Parsing** ✓
- Template metadata extraction
- User input definitions
- Conditional input handling

### 4. **Parser Output Format** ✓
- Metadata lines structure
- INPUT line format (8 fields)
- Base64 encoding of help_text
- Field order validation

### 5. **Platform Selection** ✓
- NMS platform configuration
- Product template selection

### 6. **Conditional Inputs** ✓
- Tests inputs that only appear when conditions are met
- Validates condition evaluation

## Running the Tests

```bash
# Run all installer tests
python3 test_installer_menu.py

# Or via the integration test runner
./run_installer_tests.sh
```

## What Gets Caught

These tests will catch:
- Missing dependency checks in install.sh
- Broken requirements.yaml parsing
- Changes to installer output format
- Conditional logic failures
- Platform/product selection issues

## Test Environment

Tests run in a Docker container based on Ubuntu 22.04 to simulate a real Zabbix server environment.
