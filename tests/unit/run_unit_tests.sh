#!/bin/bash
# Unit test runner for cambium-nms-templates
# Runs all unit tests in all subdirectories

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Running All Unit Tests${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

TESTS_FAILED=0

# Function to run a unit test suite
run_test_suite() {
    local suite_name="$1"
    local test_script="$2"

    echo -e "${YELLOW}► Running: ${suite_name}${NC}"
    echo ""

    if "$test_script"; then
        echo -e "${GREEN}✓ ${suite_name} passed${NC}"
        echo ""
        return 0
    else
        echo -e "${RED}✗ ${suite_name} failed${NC}"
        echo ""
        TESTS_FAILED=1
        return 1
    fi
}

# Run unit test suites
run_test_suite "Cambium OLT Collector Tests" "$SCRIPT_DIR/cambium-olt-collector/run_cambium_olt_tests.sh"

# Add more test suites here as they are created
# run_test_suite "Another Test Suite" "$SCRIPT_DIR/another-suite/run_tests.sh"

# Summary
echo -e "${BLUE}========================================${NC}"
if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All unit tests passed!${NC}"
    echo -e "${BLUE}========================================${NC}"
    exit 0
else
    echo -e "${RED}❌ Some unit tests failed${NC}"
    echo -e "${BLUE}========================================${NC}"
    exit 1
fi
