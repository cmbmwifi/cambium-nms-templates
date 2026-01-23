#!/bin/bash
# Run installer menu tests

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=================================================="
echo "Running Installer Menu Tests"
echo "=================================================="
echo ""

python3 "$SCRIPT_DIR/test_installer_menu.py"

echo ""
echo "=================================================="
echo "All installer menu tests completed!"
echo "=================================================="
