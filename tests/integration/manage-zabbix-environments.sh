#!/bin/bash
#
# Manage Zabbix test environments (all versions in parallel)
#
# Usage:
#   ./manage-zabbix-environments.sh         - Start all Zabbix environments in parallel
#   ./manage-zabbix-environments.sh --down  - Stop all Zabbix environments in parallel
#
# Returns:
#   0 - Success
#   1 - Failed

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ZABBIX_DIR="$SCRIPT_DIR/zabbix"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Parse arguments
MODE="up"
if [ "$1" = "--down" ]; then
    MODE="down"
fi

# Handle teardown
if [ "$MODE" = "down" ]; then
    echo -e "${YELLOW}Stopping all Zabbix environments in parallel...${NC}" >&2

    # Stop all environments in background with unbuffered output
    python3 -u "$ZABBIX_DIR/test_zabbix70.py" --teardown-only 2>&1 | sed -u 's/^/[7.0] /' &
    PID_70=$!

    python3 -u "$ZABBIX_DIR/test_zabbix72.py" --teardown-only 2>&1 | sed -u 's/^/[7.2] /' &
    PID_72=$!

    python3 -u "$ZABBIX_DIR/test_zabbix74.py" --teardown-only 2>&1 | sed -u 's/^/[7.4] /' &
    PID_74=$!

    # Wait for all to complete
    wait $PID_70 || true
    wait $PID_72 || true
    wait $PID_74 || true

    echo -e "${GREEN}✓ All Zabbix environments stopped${NC}" >&2
    exit 0
fi

# Handle startup

# First ensure infrastructure (MySQL, Mock OLTs) is running
echo -e "${YELLOW}Ensuring infrastructure is ready...${NC}" >&2
INFRA_STATUS=$("$SCRIPT_DIR/ensure-infrastructure.sh")
if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Failed to start infrastructure${NC}" >&2
    exit 1
fi

if [ "$INFRA_STATUS" = "STARTED" ]; then
    echo -e "${GREEN}✓ Infrastructure started${NC}" >&2
else
    echo -e "${GREEN}✓ Infrastructure already running${NC}" >&2
fi
echo ""

# Start Zabbix 7.0 first and wait for it
echo -e "${YELLOW}Starting Zabbix 7.0...${NC}" >&2
if python3 -u "$ZABBIX_DIR/test_zabbix70.py" --setup-only 2>&1 | sed -u 's/^/[7.0] /'; then
    echo -e "${GREEN}✓ Zabbix 7.0 ready${NC}" >&2
else
    echo -e "${RED}✗ Zabbix 7.0 failed to start${NC}" >&2
    exit 1
fi

# Now start 7.2 and 7.4 in parallel in the background
echo -e "${YELLOW}Starting Zabbix 7.2 and 7.4 in background...${NC}" >&2

python3 -u "$ZABBIX_DIR/test_zabbix72.py" --setup-only 2>&1 | sed -u 's/^/[7.2] /' &
python3 -u "$ZABBIX_DIR/test_zabbix74.py" --setup-only 2>&1 | sed -u 's/^/[7.4] /' &

# Disown them so they continue after script exits
disown -a 2>/dev/null || true

echo -e "${YELLOW}Note: Zabbix 7.2 and 7.4 are starting in background${NC}" >&2
exit 0
