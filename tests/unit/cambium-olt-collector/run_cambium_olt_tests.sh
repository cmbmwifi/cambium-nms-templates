#!/bin/bash
# Unit test runner for Cambium OLT data collector
# Tests error handling and data parsing for cambium_olt_ssh_json.py

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

echo -e "${YELLOW}Running Cambium OLT Collector Unit Tests${NC}"
echo ""

# Run error handling tests
python3 "$SCRIPT_DIR/test_error_handling.py"

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ All Cambium OLT collector unit tests passed${NC}"
    exit 0
else
    echo ""
    echo -e "${RED}✗ Cambium OLT collector unit tests failed${NC}"
    exit 1
fi
