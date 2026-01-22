#!/usr/bin/env bash
#
# Smoke Test Helper - Start containerized Zabbix environments for manual testing
#
# This script provides an easy way to spin up a complete Zabbix environment
# (MySQL + mock OLTs + Zabbix server) for manual testing and exploration.
#
# Unlike automated tests, this keeps the environment running so you can:
# - Access the Zabbix GUI
# - Run install.sh from inside the Zabbix web container with --local
# - Debug template behavior
# - Explore the system interactively
#
# The install.sh script is mounted at /opt/cambium-nms-templates inside the
# Zabbix web container, where it can access the local Zabbix environment.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# NMS system to use (currently only zabbix, future: librenms, etc.)
NMS_SYSTEM="zabbix"
COMPOSE_DIR="$PROJECT_ROOT/tests/integration/$NMS_SYSTEM"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

show_help() {
    cat << EOF
Smoke Test Helper - Start containerized Zabbix environments for manual testing

USAGE:
    $0 <version>           Start Zabbix environment for manual testing
    $0 --clean <version>   Start fresh environment (reset database)
    $0 --pre-install <version>  Start environment and run installer
    $0 --halt              Stop all running smoke test environments
    $0 --shutdown          Alias for --halt
    $0 --help              Show this help message

VERSIONS:
    zabbix70            Zabbix 7.0 (port 8080)
    zabbix72            Zabbix 7.2 (port 8081)
    zabbix74            Zabbix 7.4 (port 8082)
    zabbix80            Zabbix 8.0 (port 8083)

EXAMPLES:
    # Start Zabbix 7.4 environment
    $0 zabbix74

    # Start fresh Zabbix 7.0 (clean database)
    $0 --clean zabbix70

    # Start Zabbix 7.2 and run installer with both mock OLTs
    $0 --pre-install zabbix72

    # Stop all environments
    $0 --halt

NOTES:
    - MySQL and mock OLT containers are shared across versions
    - Use --clean to ensure a fresh baseline state
    - Use --pre-install to automatically run the installer after startup
    - GUI credentials: Admin / zabbix
EOF
}

get_port_for_version() {
    local version=$1
    case "$version" in
        zabbix70) echo "8080" ;;
        zabbix72) echo "8081" ;;
        zabbix74) echo "8082" ;;
        zabbix80) echo "8083" ;;
        *) echo "" ;;
    esac
}

wait_for_zabbix() {
    local port=$1
    local max_wait=120
    local elapsed=0

    echo -e "${YELLOW}Waiting for Zabbix to be ready...${NC}"

    while [ $elapsed -lt $max_wait ]; do
        if curl -s "http://localhost:$port" >/dev/null 2>&1; then
            echo -e "${GREEN}✓ Zabbix is ready!${NC}"
            return 0
        fi
        sleep 2
        elapsed=$((elapsed + 2))
        if [ $((elapsed % 10)) -eq 0 ]; then
            echo "  Still waiting... ($elapsed seconds)"
        fi
    done

    echo -e "${RED}✗ Zabbix failed to start within ${max_wait} seconds${NC}"
    return 1
}

run_installer() {
    local version=$1
    local port
    port=$(get_port_for_version "$version")

    echo -e "${YELLOW}Running installer with both mock OLTs...${NC}"

    # Authenticate and get API token (like the tests do)
    echo -e "${BLUE}Authenticating with Zabbix API...${NC}"
    api_token=$(curl -s -X POST "http://localhost:$port/api_jsonrpc.php" \
        -H "Content-Type: application/json" \
        -d '{
            "jsonrpc": "2.0",
            "method": "user.login",
            "params": {
                "username": "Admin",
                "password": "zabbix"
            },
            "id": 1
        }' | jq -r '.result // empty')

    if [ -z "$api_token" ]; then
        echo -e "${RED}Failed to authenticate with Zabbix API${NC}"
        return 1
    fi

    echo -e "${GREEN}✓ Authenticated${NC}"

    # Run installer using Python test infrastructure (like the tests do)
    # This gets the correct container name and has all dependencies
    echo -e "${YELLOW}Installing template and adding OLT hosts...${NC}"
    cd "$COMPOSE_DIR"
    python3 -c "
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
from test_${version} import $(echo "$version" | sed 's/zabbix/Zabbix/' | sed 's/\([0-9]\)\([0-9]\)/\1\2/')Test
from suites.test_installer_operations import InstallerOperationsTests

# Create test instance
test = $(echo "$version" | sed 's/zabbix/Zabbix/' | sed 's/\([0-9]\)\([0-9]\)/\1\2/')Test()
test.harness.api_token = '${api_token}'

# Run installer
installer = InstallerOperationsTests(test.harness)
env = {
    'ADD_HOSTS': 'true',
    'OLT_IPS': '172.20.0.10,172.20.0.11'
}
exit_code, output = installer.run_installer_with_env(env)
print(output)
sys.exit(exit_code)
"

    exit_status=$?
    if [ $exit_status -eq 0 ]; then
        echo -e "${GREEN}✓ Installer completed successfully${NC}"
        return 0
    else
        echo -e "${RED}✗ Installer failed${NC}"
        return 1
    fi
}

start_environment() {
    local version=$1
    local clean_mode=${2:-false}
    local run_installer_after=${3:-false}

    # Validate version
    local port
    port=$(get_port_for_version "$version")
    if [ -z "$port" ]; then
        echo -e "${RED}Error: Invalid version '$version'${NC}"
        echo "Valid versions: zabbix70, zabbix72, zabbix74, zabbix80"
        exit 1
    fi

    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}Starting Smoke Test Environment: ${version}${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    cd "$COMPOSE_DIR"

    # Handle clean mode
    if [ "$clean_mode" = "true" ]; then
        echo -e "${YELLOW}Clean mode: Resetting environment to baseline state${NC}"

        # Stop and remove the specific Zabbix version
        docker-compose -f docker-compose.base.yml -f "docker-compose.${version}.yml" \
            -p "zabbix-smoketest-${version}" down -v 2>/dev/null || true

        # Also stop base infrastructure to ensure complete reset
        cd "$PROJECT_ROOT/tests/integration"
        docker-compose -f mysql/docker-compose.yml -p infrastructure down -v 2>/dev/null || true
        docker-compose -f mock-olt/docker-compose.yml -p infrastructure down -v 2>/dev/null || true

        echo -e "${GREEN}✓ Environment reset${NC}"
        echo ""
    fi

    # Start base infrastructure (MySQL + mock OLTs) using ensure-infrastructure.sh
    echo -e "${YELLOW}Starting shared infrastructure (MySQL + mock OLTs)...${NC}"
    cd "$PROJECT_ROOT/tests/integration"
    if ./ensure-infrastructure.sh >/dev/null 2>&1; then
        echo -e "${GREEN}✓ Infrastructure ready${NC}"
    else
        echo -e "${RED}✗ Failed to start infrastructure${NC}"
        exit 1
    fi
    echo ""

    cd "$COMPOSE_DIR"

    # Start the specific Zabbix version using the Python test script (same path as automated tests)
    echo -e "${YELLOW}Starting Zabbix ${version}...${NC}"
    if ! python3 -u "test_${version}.py" --setup-only; then
        echo -e "${RED}Failed to start Zabbix. Check logs with:${NC}"
        # Map version to actual container name (test scripts use underscores)
        local container_prefix
        container_prefix=$(echo "$version" | sed 's/zabbix/zabbix_/' | sed 's/\([0-9]\)\([0-9]\)/\1_\2/')
        echo "  docker logs ${container_prefix}-server-1"
        exit 1
    fi

    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}✓ Smoke Test Environment Ready!${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # Run installer if requested
    if [ "$run_installer_after" = "true" ]; then
        echo ""
        run_installer "$version" || true
        echo ""
    fi

    echo -e "${BLUE}Zabbix GUI:${NC}"
    echo "  URL:      http://localhost:$port"
    echo "  Username: Admin"
    echo "  Password: zabbix"
    echo "  (Get API token: User settings → API tokens → Create API token)"
    echo ""
    echo -e "${BLUE}Mock OLT devices:${NC}"
    echo "  OLT 1: 172.20.0.10:22 (SSH password: password)"
    echo "  OLT 2: 172.20.0.11:22 (SSH password: password)"
    echo ""
    echo -e "${BLUE}Run installer manually (inside web container):${NC}"
    echo "  docker exec -it --user root ${version}-web-1 bash"
    echo "  cd /opt/cambium-nms-templates"
    echo "  export ZABBIX_API_URL=http://localhost:8080"
    echo "  export ZABBIX_API_TOKEN=<get-from-gui>"
    echo "  export OLT_PASSWORD=password"
    echo "  export ADD_HOSTS=true"
    echo "  export OLT_IPS=172.20.0.10,172.20.0.11"
    echo "  ./install.sh --local"
    echo ""
    echo -e "${YELLOW}To stop this environment:${NC}"
    echo "  $0 --halt"
    echo ""
}

halt_all() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}Stopping All Smoke Test Environments${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    cd "$COMPOSE_DIR"

    # Stop each Zabbix version using Python teardown
    for version in zabbix70 zabbix72 zabbix74 zabbix80; do
        echo -e "${YELLOW}Stopping ${version}...${NC}"
        python3 -u "test_${version}.py" --teardown-only 2>/dev/null || true
    done

    # Stop shared infrastructure using ensure-infrastructure.sh
    echo -e "${YELLOW}Stopping shared infrastructure (MySQL + mock OLTs)...${NC}"
    cd "$PROJECT_ROOT/tests/integration"
    ./ensure-infrastructure.sh --down >/dev/null 2>&1 || true

    echo ""
    echo -e "${GREEN}✓ All smoke test environments stopped and cleaned${NC}"
}

# Main logic
case "${1:-}" in
    --help|-h|help)
        show_help
        exit 0
        ;;
    --halt|--shutdown)
        halt_all
        exit 0
        ;;
    --clean)
        if [ -z "${2:-}" ]; then
            echo -e "${RED}Error: --clean requires a version${NC}"
            echo "Example: $0 --clean zabbix74"
            exit 1
        fi
        start_environment "$2" true false
        ;;
    --pre-install)
        if [ -z "${2:-}" ]; then
            echo -e "${RED}Error: --pre-install requires a version${NC}"
            echo "Example: $0 --pre-install zabbix74"
            exit 1
        fi
        start_environment "$2" false true
        ;;
    zabbix70|zabbix72|zabbix74|zabbix80)
        # Check if second argument is --pre-install or --clean
        if [ "${2:-}" = "--pre-install" ]; then
            start_environment "$1" false true
        elif [ "${2:-}" = "--clean" ]; then
            start_environment "$1" true false
        else
            start_environment "$1" false false
        fi
        ;;
    "")
        echo -e "${RED}Error: No version specified${NC}"
        echo ""
        show_help
        exit 1
        ;;
    *)
        echo -e "${RED}Error: Unknown option or version '$1'${NC}"
        echo ""
        show_help
        exit 1
        ;;
esac
