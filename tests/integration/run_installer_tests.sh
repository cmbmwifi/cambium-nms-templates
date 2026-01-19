#!/bin/bash
# Run installer menu tests

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/installer"

echo "=================================================="
echo "Running Installer Menu Tests"
echo "=================================================="
echo ""

python3 test_installer_menu.py

echo ""
echo "=================================================="
echo "All installer menu tests completed!"
echo "=================================================="
