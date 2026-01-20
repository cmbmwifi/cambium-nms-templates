#!/bin/bash
# Master test runner for cambium-nms-templates
# Runs all test suites in the project

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Running All Tests${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

TESTS_FAILED=0
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Function to run a test and track failures
run_test() {
    local test_name="$1"
    local test_command="$2"

    echo -e "${YELLOW}► Running: ${test_name}${NC}"
    echo "  Command: $test_command"
    echo ""

    if eval "$test_command"; then
        echo -e "${GREEN}✓ ${test_name} passed${NC}"
        echo ""
        return 0
    else
        echo -e "${RED}✗ ${test_name} failed${NC}"
        echo ""
        TESTS_FAILED=1
        return 1
    fi
}

# 1. Unit Tests (run first)
run_test "Unit Tests" "'$SCRIPT_DIR/unit/run_unit_tests.sh'"

# 2. Mock OLT Tests
run_test "Mock OLT Tests" "python3 '$SCRIPT_DIR/integration/mock-olt/test_mock_olt.py'"

# 3. Installer Tests
run_test "Installer Tests" "'$SCRIPT_DIR/integration/run_installer_tests.sh'"

# 4. Zabbix Integration Tests
run_test "Zabbix Integration Tests" "'$SCRIPT_DIR/integration/run_all_zabbix_tests.sh'"

# Summary
echo -e "${BLUE}========================================${NC}"
if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed successfully!${NC}"
    echo -e "${BLUE}========================================${NC}"
    exit 0
else
    echo -e "${RED}❌ Some tests failed${NC}"
    echo -e "${BLUE}========================================${NC}"
    exit 1
fi
