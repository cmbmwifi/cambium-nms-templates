#!/bin/bash
#
# Run all integration tests
# Executes test suites for all NMS systems (Zabbix, installer, etc.)
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Start timing
START_TIME=$(date +%s)

echo "========================================"
echo "Running All Integration Tests"
echo "Started: $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================"
echo ""

# Discover all test suites (subdirectories with run_all.sh)
declare -a TEST_SUITES=()
declare -A TEST_RESULTS=()
declare -A TEST_DURATIONS=()

for dir in "$SCRIPT_DIR"/*/; do
    if [ -f "$dir/run_all.sh" ]; then
        suite_name=$(basename "$dir")
        TEST_SUITES+=("$suite_name")
    fi
done

# Sort test suites alphabetically for consistent ordering
IFS=$'\n' TEST_SUITES=($(sort <<<"${TEST_SUITES[*]}"))
unset IFS

if [ ${#TEST_SUITES[@]} -eq 0 ]; then
    echo "No test suites found (no subdirectories with run_all.sh)"
    exit 1
fi

echo "Found ${#TEST_SUITES[@]} test suite(s): ${TEST_SUITES[*]}"
echo ""

# Run each test suite
for suite in "${TEST_SUITES[@]}"; do
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Running ${suite} Tests"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    SUITE_START=$(date +%s)
    if "$SCRIPT_DIR/$suite/run_all.sh"; then
        TEST_RESULTS[$suite]=0
        SUITE_END=$(date +%s)
        TEST_DURATIONS[$suite]=$((SUITE_END - SUITE_START))
        echo "✓ ${suite}: PASSED (${TEST_DURATIONS[$suite]}s)"
    else
        TEST_RESULTS[$suite]=$?
        SUITE_END=$(date +%s)
        TEST_DURATIONS[$suite]=$((SUITE_END - SUITE_START))
        echo "✗ ${suite}: FAILED (${TEST_DURATIONS[$suite]}s)"
    fi
    echo ""
done

END_TIME=$(date +%s)
TOTAL_DURATION=$((END_TIME - START_TIME))

echo "========================================"
echo "Final Results"
echo "========================================"

# Display summary
ALL_PASSED=true
for suite in "${TEST_SUITES[@]}"; do
    if [ ${TEST_RESULTS[$suite]} -eq 0 ]; then
        printf "✓ %-12s PASSED (%ss)\n" "${suite}:" "${TEST_DURATIONS[$suite]}"
    else
        printf "✗ %-12s FAILED (%ss)\n" "${suite}:" "${TEST_DURATIONS[$suite]}"
        ALL_PASSED=false
    fi
done

echo ""
echo "========================================"
echo "Timing Summary"
echo "========================================"
for suite in "${TEST_SUITES[@]}"; do
    printf "%-14s %ss\n" "${suite}:" "${TEST_DURATIONS[$suite]}"
done
echo "────────────────────────────────────────"
echo "Total time:    ${TOTAL_DURATION}s"
echo "Finished: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# Overall result
if [ "$ALL_PASSED" = true ]; then
    echo "All integration tests passed!"
    exit 0
else
    echo "Some tests failed."
    exit 1
fi
