#!/bin/bash
#
# Run all Zabbix version tests
# Shared infrastructure (MySQL, Mock OLTs) started once and reused
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ZABBIX_DIR="$SCRIPT_DIR/zabbix"

# Start timing
START_TIME=$(date +%s)

echo "========================================"
echo "Running Zabbix Tests (All Versions)"
echo "Started: $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================"
echo ""

# Ensure test infrastructure is running
echo "Ensuring test infrastructure (MySQL, Mock OLTs)..."
cd "$ZABBIX_DIR"
docker network create --subnet=172.20.0.0/16 zabbix-shared-network 2>/dev/null || true

# Check if MySQL and Mock OLTs are already running
if docker ps --filter "name=test-mysql" --filter "status=running" --format "{{.Names}}" 2>/dev/null | grep -q "test-mysql"; then
    MYSQL_RUNNING=1
else
    MYSQL_RUNNING=0
fi

MOCK_OLTS_RUNNING=$(docker ps --filter "name=zabbix-mock-olt" --filter "status=running" --format "{{.Names}}" 2>/dev/null | wc -l)

if [ "$MYSQL_RUNNING" -gt "0" ] && [ "$MOCK_OLTS_RUNNING" -ge "2" ]; then
    echo "✓ Test infrastructure already running"
    INFRASTRUCTURE_STARTED=0
else
    echo "Starting test infrastructure..."
    INFRASTRUCTURE_STARTED=1

    # Start MySQL if not running
    if [ "$MYSQL_RUNNING" -eq "0" ]; then
        echo "  Starting MySQL..."
        cd "$SCRIPT_DIR/mysql"
        docker-compose up -d
        sleep 5
    fi

    # Start Mock OLTs if not running (need both containers)
    if [ "$MOCK_OLTS_RUNNING" -lt "2" ]; then
        echo "  Starting Mock OLTs..."
        cd "$ZABBIX_DIR"
        docker-compose -f docker-compose.mock-olts.yml up -d
    fi

    echo "Waiting for test services to be ready..."
    sleep 10
    echo "✓ Test infrastructure ready"
fi
echo ""

# Test results
RESULT_70=0
RESULT_72=0
RESULT_74=0
# RESULT_80=0  # Commented out - Zabbix 8.0 not yet stable

# Run Zabbix 7.0 tests
TEST_70_START=$(date +%s)
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Running Zabbix 7.0 tests..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if "$ZABBIX_DIR/test_zabbix70.py"; then
    TEST_70_END=$(date +%s)
    TEST_70_DURATION=$((TEST_70_END - TEST_70_START))
    echo "✓ Zabbix 7.0: PASSED (${TEST_70_DURATION}s)"
else
    RESULT_70=$?
    TEST_70_END=$(date +%s)
    TEST_70_DURATION=$((TEST_70_END - TEST_70_START))
    echo "✗ Zabbix 7.0: FAILED (${TEST_70_DURATION}s)"
fi
echo ""

# Run Zabbix 7.2 tests
TEST_72_START=$(date +%s)
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Running Zabbix 7.2 tests..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if "$ZABBIX_DIR/test_zabbix72.py"; then
    TEST_72_END=$(date +%s)
    TEST_72_DURATION=$((TEST_72_END - TEST_72_START))
    echo "✓ Zabbix 7.2: PASSED (${TEST_72_DURATION}s)"
else
    RESULT_72=$?
    TEST_72_END=$(date +%s)
    TEST_72_DURATION=$((TEST_72_END - TEST_72_START))
    echo "✗ Zabbix 7.2: FAILED (${TEST_72_DURATION}s)"
fi
echo ""

# Run Zabbix 7.4 tests
TEST_74_START=$(date +%s)
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Running Zabbix 7.4 tests..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if "$ZABBIX_DIR/test_zabbix74.py"; then
    TEST_74_END=$(date +%s)
    TEST_74_DURATION=$((TEST_74_END - TEST_74_START))
    echo "✓ Zabbix 7.4: PASSED (${TEST_74_DURATION}s)"
else
    RESULT_74=$?
    TEST_74_END=$(date +%s)
    TEST_74_DURATION=$((TEST_74_END - TEST_74_START))
    echo "✗ Zabbix 7.4: FAILED (${TEST_74_DURATION}s)"
fi
echo ""

# Zabbix 8.0 tests commented out - not yet stable
# Zabbix 8.0 has not been officially released yet. We're using the 'trunk' (development)
# Docker images which are unstable and have compatibility issues. Once Zabbix 8.0 is
# officially released with stable 'alpine-8.0-latest' images, uncomment these tests.
#
# TEST_80_START=$(date +%s)
# echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
# echo "Running Zabbix 8.0 tests..."
# echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
# if "$ZABBIX_DIR/test_zabbix80.py"; then
#     TEST_80_END=$(date +%s)
#     TEST_80_DURATION=$((TEST_80_END - TEST_80_START))
#     echo "✓ Zabbix 8.0: PASSED (${TEST_80_DURATION}s)"
# else
#     RESULT_80=$?
#     TEST_80_END=$(date +%s)
#     TEST_80_DURATION=$((TEST_80_END - TEST_80_START))
#     echo "✗ Zabbix 8.0: FAILED (${TEST_80_DURATION}s)"
# fi
# echo ""

# Note: Test infrastructure (MySQL, Mock OLTs) left running for next test
# To clean up manually:
#   cd tests/integration/mysql && docker-compose down
#   cd tests/integration/zabbix && docker-compose -f docker-compose.mock-olts.yml down

END_TIME=$(date +%s)
TOTAL_DURATION=$((END_TIME - START_TIME))

echo "========================================"
echo "Final Results"
echo "========================================"

# Display summary
if [ $RESULT_70 -eq 0 ]; then
    echo "✓ Zabbix 7.0: PASSED (${TEST_70_DURATION}s)"
else
    echo "✗ Zabbix 7.0: FAILED (${TEST_70_DURATION}s)"
fi

if [ $RESULT_72 -eq 0 ]; then
    echo "✓ Zabbix 7.2: PASSED (${TEST_72_DURATION}s)"
else
    echo "✗ Zabbix 7.2: FAILED (${TEST_72_DURATION}s)"
fi

if [ $RESULT_74 -eq 0 ]; then
    echo "✓ Zabbix 7.4: PASSED (${TEST_74_DURATION}s)"
else
    echo "✗ Zabbix 7.4: FAILED (${TEST_74_DURATION}s)"
fi

# Zabbix 8.0 - commented out (see above)
# if [ $RESULT_80 -eq 0 ]; then
#     echo "✓ Zabbix 8.0: PASSED (${TEST_80_DURATION}s)"
# else
#     echo "✗ Zabbix 8.0: FAILED (${TEST_80_DURATION}s)"
# fi

echo ""
echo "========================================"
echo "Timing Summary"
echo "========================================"
echo "Zabbix 7.0:    ${TEST_70_DURATION}s"
echo "Zabbix 7.2:    ${TEST_72_DURATION}s"
echo "Zabbix 7.4:    ${TEST_74_DURATION}s"
# echo "Zabbix 8.0:    ${TEST_80_DURATION}s"  # Commented out - not yet stable
echo "────────────────────────────────────────"
echo "Total time:    ${TOTAL_DURATION}s"
echo "Finished: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# Clean up test infrastructure if we started it
if [ "$INFRASTRUCTURE_STARTED" -eq "1" ]; then
    echo "Cleaning up test infrastructure (we started it)..."
    cd "$ZABBIX_DIR"
    docker-compose -f docker-compose.mock-olts.yml down
    cd "$SCRIPT_DIR/mysql"
    docker-compose down
    echo "✓ Test infrastructure stopped"
    echo ""
fi

# Overall result
if [ $RESULT_70 -eq 0 ] && [ $RESULT_72 -eq 0 ] && [ $RESULT_74 -eq 0 ]; then
    echo "All Zabbix tests passed!"
    exit 0
else
    echo "Some tests failed."
    exit 1
fi
