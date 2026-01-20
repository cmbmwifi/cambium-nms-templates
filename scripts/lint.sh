#!/bin/bash
# Linting script - runs the same checks as GitHub CI
# This is used by pre-commit hook to ensure consistency

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

CHECKS_FAILED=0

# Function to run a check
run_check() {
    local check_name="$1"
    local check_command="$2"

    echo "► ${check_name}"
    # Run command and capture both output and exit code
    local output
    output=$(eval "$check_command" 2>&1) || local exit_code=$?

    # Display output with indentation
    if [ -n "$output" ]; then
        # shellcheck disable=SC2001
        echo "$output" | sed 's/^/  /'
    fi

    if [ "${exit_code:-0}" -eq 0 ]; then
        echo -e "${GREEN}✓ ${check_name} passed${NC}"
        echo ""
        return 0
    else
        echo -e "${RED}✗ ${check_name} failed${NC}"
        echo ""
        CHECKS_FAILED=1
        return 1
    fi
}

echo "Running linting checks (same as GitHub CI)..."
echo ""

# 1. Validate Python syntax
run_check "Python syntax" "find . -name '*.py' -type f -exec python3 -m py_compile {} +"

# 2. Validate Bash syntax
run_check "Bash syntax" "bash -n install.sh && find scripts tests -name '*.sh' -type f -exec bash -n {} +"

# 3. Run shellcheck (if installed)
if command -v shellcheck &> /dev/null; then
    run_check "Shellcheck" "shellcheck install.sh && find scripts -name '*.sh' -type f -exec shellcheck {} +"
else
    echo -e "${YELLOW}⚠ Shellcheck not installed - skipping (install with: sudo apt install shellcheck)${NC}"
    echo ""
fi

# 4. Validate YAML files
run_check "YAML validation" "python3 -c \"import yaml; yaml.safe_load(open('templates/zabbix/cambium-fiber/template.yaml')); yaml.safe_load(open('templates/zabbix/cambium-fiber/requirements.yaml'))\""

# 5. Type checking with mypy (if installed)
if command -v mypy &> /dev/null; then
    run_check "Type checking" "mypy --ignore-missing-imports --check-untyped-defs tests/integration/installer/test_installer_menu.py"
elif python3 -m mypy --version &> /dev/null; then
    run_check "Type checking" "python3 -m mypy --ignore-missing-imports --check-untyped-defs tests/integration/installer/test_installer_menu.py"
else
    echo -e "${YELLOW}⚠ mypy not installed - skipping type checking (install with: pip install mypy)${NC}"
    echo ""
fi

# Exit with failure if any check failed
if [ $CHECKS_FAILED -eq 1 ]; then
    exit 1
fi

exit 0
