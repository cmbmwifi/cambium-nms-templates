#!/bin/bash
#
# Manage test infrastructure (MySQL, Mock OLTs)
# Called by all test scripts to start or stop shared infrastructure
#
# Usage:
#   ./ensure-infrastructure.sh         - Start infrastructure if not running
#   ./ensure-infrastructure.sh --down  - Stop infrastructure
#
# Outputs to stdout (when starting):
#   "ALREADY_RUNNING" - Infrastructure was already running
#   "STARTED" - Infrastructure was started by this script
#
# Returns:
#   0 - Success
#   1 - Failed
#
# Example:
#   INFRA_STATUS=$(./ensure-infrastructure.sh)
#   if [ "$INFRA_STATUS" = "STARTED" ]; then
#       # Clean up when done
#       ./ensure-infrastructure.sh --down
#   fi

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output (to stderr to not interfere with status output)
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Parse arguments
MODE="up"
if [ "$1" = "--down" ]; then
    MODE="down"
fi

# Handle teardown
if [ "$MODE" = "down" ]; then
    echo -e "${YELLOW}Stopping test infrastructure...${NC}" >&2

    # Stop Mock OLTs
    cd "$SCRIPT_DIR/mock-olt"
    docker-compose -p infrastructure down -v 2>/dev/null || true

    # Stop MySQL
    cd "$SCRIPT_DIR/mysql"
    docker-compose -p infrastructure down -v 2>/dev/null || true

    echo -e "${GREEN}✓ Test infrastructure stopped${NC}" >&2
    exit 0
fi

# Handle startup

# Ensure shared network exists
docker network create --subnet=172.20.0.0/16 zabbix-shared-network 2>/dev/null || true

# Check if MySQL is running
if docker ps --filter "name=mysql-1" --filter "status=running" --format "{{.Names}}" 2>/dev/null | grep -q "mysql-1"; then
    MYSQL_RUNNING=1
else
    MYSQL_RUNNING=0
fi

# Check if both Mock OLTs are running
MOCK_OLTS_RUNNING=$(docker ps --filter "name=mock-olt" --filter "status=running" --format "{{.Names}}" 2>/dev/null | wc -l)

if [ "$MYSQL_RUNNING" -eq 1 ] && [ "$MOCK_OLTS_RUNNING" -eq 2 ]; then
    echo -e "${GREEN}✓ Test infrastructure already running${NC}" >&2
    echo "ALREADY_RUNNING"
    exit 0
fi

echo -e "${YELLOW}Starting test infrastructure...${NC}" >&2

# Start MySQL if not running
if [ "$MYSQL_RUNNING" -eq 0 ]; then
    echo "  Starting MySQL..." >&2
    cd "$SCRIPT_DIR/mysql"
    docker-compose -p infrastructure up -d >&2
fi

# Start Mock OLTs if not both running
if [ "$MOCK_OLTS_RUNNING" -lt 2 ]; then
    echo "  Starting Mock OLTs..." >&2
    cd "$SCRIPT_DIR/mock-olt"
    docker-compose -p infrastructure up -d >&2
fi

# Wait for MySQL to be ready (Mock OLTs will be ready by the time tests need them)
echo "  Waiting for MySQL to be ready..." >&2
MAX_WAIT=60
WAITED=0

while [ $WAITED -lt $MAX_WAIT ]; do
    # Check MySQL health (healthcheck now tests actual query execution)
    MYSQL_HEALTH=$(docker inspect --format='{{.State.Health.Status}}' mysql-1 2>/dev/null || echo "unknown")

    if [ "$MYSQL_HEALTH" = "healthy" ]; then
        echo -e "${GREEN}✓ MySQL ready for database operations${NC}" >&2
        echo "STARTED"
        exit 0
    fi

    sleep 0.5
    WAITED=$((WAITED + 1))
done

echo "Error: MySQL did not become ready in time" >&2
exit 1

