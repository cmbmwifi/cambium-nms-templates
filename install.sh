#!/bin/bash
# Cambium NMS Templates Installer
# Main installation script that supports multiple modes

set -e

# Color functions
green() { echo -e "\033[0;32m$1\033[0m"; }
yellow() { echo -e "\033[0;33m$1\033[0m"; }
red() { echo -e "\033[0;31m$1\033[0m"; }

# Check for root privileges early
check_root_privileges() {
    # Skip check for validate-config mode
    if [[ " $* " =~ " --validate-config " ]]; then
        return 0
    fi

    if [ "$EUID" -ne 0 ]; then
        red "Error: This installer must be run as root"
        echo ""
        echo "To become root and run this installer:"
        echo ""
        echo "  Option 1: Switch to root user first"
        echo "    sudo su -"
        echo "    # Then run the installer"
        echo ""
        echo "  Option 2: Run with sudo"
        echo "    sudo $0 $*"
        echo ""
        echo "  Note: In Proxmox LXC containers, you're typically already root."
        echo ""
        exit 1
    fi
}

# Check privileges before doing anything else
check_root_privileges "$@"

# Parse command-line arguments
MODE="github"  # default: download from GitHub
HELP=false
VALIDATE_CONFIG_ONLY=false

for arg in "$@"; do
    case $arg in
        --local)
            MODE="local"
            ;;
        --remote)
            MODE="remote"
            ;;
        --validate-config)
            VALIDATE_CONFIG_ONLY=true
            ;;
        --help|-h)
            HELP=true
            ;;
        *)
            echo "Unknown argument: $arg"
            HELP=true
            ;;
    esac
done

# Show help
if [ "$HELP" = true ]; then
    cat << 'EOF'
Cambium NMS Templates Installer

Usage:
  install.sh [OPTIONS]

Options:
  --local           Use local files from ~/cambium-nms-templates/ (development mode)
  --remote          API-only mode without filesystem modifications
  --validate-config Validate configuration only, skip API connection and installation
  --help            Show this help message

Examples:
  # Production install from GitHub
  curl -o- https://raw.githubusercontent.com/cmbmwifi/cambium-nms-templates/refs/heads/main/install.sh | bash

  # Development install with local files
  ./install.sh --local

  # Remote API-only installation
  ./install.sh --remote

  # Validate configuration without connecting to API
  ./install.sh --local --validate-config

EOF
    exit 0
fi

# Check for required Python modules and system packages
# Skip dependency installation in validate-config mode
if [ "$VALIDATE_CONFIG_ONLY" = false ]; then
    yellow 'Checking dependencies...'

    # Check if we can install packages (need root or sudo)
    CAN_INSTALL_PACKAGES=false
    if [ "$EUID" -eq 0 ]; then
        CAN_INSTALL_PACKAGES=true
    elif command -v sudo &> /dev/null && sudo -n true 2>/dev/null; then
        CAN_INSTALL_PACKAGES=true
    fi

    # Check for sshpass
    if ! command -v sshpass &> /dev/null; then
        echo "  sshpass not found"

        if [ "$CAN_INSTALL_PACKAGES" = false ]; then
            red "✗ Error: sshpass is required but not installed"
            echo "  Please run: sudo apt-get install sshpass"
            echo "  Or run this installer as root"
            exit 1
        fi

        echo "  Installing sshpass..."

        if command -v apt-get &> /dev/null; then
            if [ "$EUID" -eq 0 ]; then
                apt-get update -qq && apt-get install -y sshpass
            else
                sudo apt-get update -qq && sudo apt-get install -y sshpass
            fi
        elif command -v yum &> /dev/null; then
            if [ "$EUID" -eq 0 ]; then
                yum install -y sshpass
            else
                sudo yum install -y sshpass
            fi
        else
            red "✗ Error: Cannot automatically install sshpass"
            echo "  Please install manually:"
            echo "    Debian/Ubuntu: sudo apt-get install sshpass"
            echo "    RHEL/CentOS: sudo yum install sshpass"
            exit 1
        fi

        # Verify installation
        if command -v sshpass &> /dev/null; then
            green "  ✓ sshpass installed"
        else
            red "✗ Error: Failed to install sshpass"
            exit 1
        fi
    else
        green "  ✓ sshpass available"
    fi
fi

# Check for PyYAML
if ! python3 -c "import yaml" 2>/dev/null; then
    echo "  PyYAML not found, installing..."

    # Try to install python3-yaml
    if command -v apt-get &> /dev/null; then
        if ! apt-get install -y python3-yaml 2>/dev/null; then
            red "✗ Error: Failed to install python3-yaml"
            echo "  Please run: sudo apt-get install python3-yaml"
            exit 1
        fi
    elif command -v yum &> /dev/null; then
        if ! yum install -y python3-pyyaml 2>/dev/null; then
            red "✗ Error: Failed to install python3-pyyaml"
            echo "  Please run: sudo yum install python3-pyyaml"
            exit 1
        fi
    else
        red "✗ Error: Cannot automatically install PyYAML"
        echo "  Please install manually:"
        echo "    Debian/Ubuntu: sudo apt-get install python3-yaml"
        echo "    RHEL/CentOS: sudo yum install python3-pyyaml"
        echo "    Or via pip: pip3 install pyyaml"
        exit 1
    fi

    green "  ✓ PyYAML installed"
else
    green "  ✓ PyYAML available"
fi

# GitHub repository configuration
GITHUB_BASE_URL="https://raw.githubusercontent.com/cmbmwifi/cambium-nms-templates/refs/heads/main"

# Function to download file from GitHub
download_github_file() {
    local remote_path="$1"
    local local_path="$2"

    # Create directory if needed
    mkdir -p "$(dirname "$local_path")"

    # Download file
    if curl -f -sS -o "$local_path" "${GITHUB_BASE_URL}/${remote_path}"; then
        return 0
    else
        red "Error: Failed to download ${remote_path}"
        return 1
    fi
}

# Cleanup function for temporary files
cleanup_temp_files() {
    if [ "$MODE" = "github" ] && [ -n "$BASE_PATH" ] && [ -d "$BASE_PATH" ]; then
        rm -rf "$BASE_PATH"
    fi
}

# Register cleanup on exit
trap cleanup_temp_files EXIT

# Determine base path based on mode
if [ "$MODE" = "local" ]; then
    BASE_PATH="$HOME/cambium-nms-templates"
    yellow 'Development mode: Using local files'
    echo "Base path: $BASE_PATH"

    # Verify local directory exists
    if [ ! -d "$BASE_PATH" ]; then
        red "Error: Local directory not found: $BASE_PATH"
        echo "Please ensure files are copied to ~/cambium-nms-templates/"
        exit 1
    fi
else
    # GitHub mode - create temporary directory
    BASE_PATH=$(mktemp -d -t cambium-nms-XXXXXX)
    yellow 'GitHub mode: Downloading files from repository'
    echo "Temporary directory: $BASE_PATH"
fi

# Check for whiptail (needed for interactive menus)
if ! command -v whiptail &> /dev/null; then
    # If environment variables are set, we can continue without whiptail
    if [ -z "$ZABBIX_API_URL" ] || [ -z "$ZABBIX_API_TOKEN" ]; then
        red "Error: whiptail is required for interactive mode"
        echo "Install with: sudo apt-get install whiptail"
        echo "Or use non-interactive mode with environment variables"
        exit 1
    fi
fi

# Detect if running in non-interactive mode (all required env vars set)
NON_INTERACTIVE=false
if [ -n "$ZABBIX_API_URL" ] && [ -n "$ZABBIX_API_TOKEN" ]; then
    NON_INTERACTIVE=true
    green 'Non-interactive mode detected'
fi

# NMS Platform Selection Menu (interactive mode only)
if [ -z "$NMS_PLATFORM" ]; then
    if [ "$NON_INTERACTIVE" = false ] && command -v whiptail &> /dev/null; then
        NMS_PLATFORM=$(whiptail --title "Select NMS Platform" \
            --menu "Choose your Network Management System:" 15 70 1 \
            "zabbix" "Zabbix Monitoring Platform" \
            3>&1 1>&2 2>&3)

        if [ -z "$NMS_PLATFORM" ]; then
            red "Installation cancelled"
            exit 1
        fi
    else
        # Fallback: default to zabbix
        NMS_PLATFORM="zabbix"
    fi
else
    green "NMS Platform: $NMS_PLATFORM (from environment)"
fi

# Product Selection Menu (interactive mode only)
if [ -z "$PRODUCT_TEMPLATE" ]; then
    if [ "$NON_INTERACTIVE" = false ] && command -v whiptail &> /dev/null; then
        PRODUCT_TEMPLATE=$(whiptail --title "Select Product Template" \
            --menu "Choose the product template to install:" 15 70 1 \
            "cambium-fiber" "Cambium Fiber OLT by SSH" \
            3>&1 1>&2 2>&3)

        if [ -z "$PRODUCT_TEMPLATE" ]; then
            red "Installation cancelled"
            exit 1
        fi
    else
        # Fallback: default to cambium-fiber
        PRODUCT_TEMPLATE="cambium-fiber"
    fi
else
    green "Product Template: $PRODUCT_TEMPLATE (from environment)"
fi

# Update template path based on selections
TEMPLATE_PATH="$BASE_PATH/templates/$NMS_PLATFORM/$PRODUCT_TEMPLATE"
REQUIREMENTS_FILE="$TEMPLATE_PATH/requirements.yaml"
TEMPLATE_FILE="$TEMPLATE_PATH/template.yaml"
SCRIPT_FILE="$TEMPLATE_PATH/cambium_olt_ssh_json.py"

# Download required files in GitHub mode
if [ "$MODE" = "github" ]; then
    yellow 'Downloading required files...'

    # Download requirements.yaml
    if ! download_github_file "templates/$NMS_PLATFORM/$PRODUCT_TEMPLATE/requirements.yaml" "$REQUIREMENTS_FILE"; then
        exit 1
    fi

    # Download template.yaml
    if ! download_github_file "templates/$NMS_PLATFORM/$PRODUCT_TEMPLATE/template.yaml" "$TEMPLATE_FILE"; then
        exit 1
    fi

    # Download Python script
    if ! download_github_file "templates/$NMS_PLATFORM/$PRODUCT_TEMPLATE/cambium_olt_ssh_json.py" "$SCRIPT_FILE"; then
        exit 1
    fi

    green "✓ Downloaded all required files"
fi

# Verify requirements.yaml exists
if [ ! -f "$REQUIREMENTS_FILE" ]; then
    red "Error: requirements.yaml not found at: $REQUIREMENTS_FILE"
    exit 1
fi

green "✓ Found requirements.yaml"

# Parse requirements.yaml using Python
yellow 'Parsing requirements...'

# Extract metadata and user_inputs using Python with help_text
PARSED_DATA=$(python3 - "$REQUIREMENTS_FILE" <<'PYTHON_EOF'
import yaml
import sys
import base64

try:
    with open(sys.argv[1], 'r') as f:
        data = yaml.safe_load(f)

    # Print metadata
    print("METADATA_NAME=" + str(data['metadata']['name']))
    print("METADATA_DESC=" + str(data['metadata']['description']))

    # Print each user_input as a structured line with base64-encoded help_text
    for inp in data.get('user_inputs', []):
        name = inp['name']
        input_type = inp['type']
        prompt = inp['prompt']
        default_val = str(inp.get('default', ''))
        condition = str(inp.get('condition', ''))
        help_text = inp.get('help_text', '')
        example = inp.get('example', '')

        # Base64 encode help_text to preserve multiline content
        help_b64 = base64.b64encode(help_text.encode('utf-8')).decode('utf-8') if help_text else ''

        # Use string concatenation instead of f-strings for better compatibility
        print("INPUT|" + name + "|" + input_type + "|" + prompt + "|" + default_val + "|" + condition + "|" + help_b64 + "|" + example)

except Exception as e:
    print("ERROR|" + str(e), file=sys.stderr)
    sys.exit(1)
PYTHON_EOF
)

# Check if parsing succeeded
# shellcheck disable=SC2181
if [ $? -ne 0 ]; then
    red "Error parsing requirements.yaml"
    exit 1
fi

# Parse the output
TEMPLATE_NAME=$(echo "$PARSED_DATA" | grep "^METADATA_NAME=" | cut -d'=' -f2-)
TEMPLATE_DESC=$(echo "$PARSED_DATA" | grep "^METADATA_DESC=" | cut -d'=' -f2-)

# Detect if running in non-interactive mode (all required env vars set)
NON_INTERACTIVE=false
if [ -n "$ZABBIX_API_URL" ] && [ -n "$ZABBIX_API_TOKEN" ]; then
    NON_INTERACTIVE=true
    green 'Non-interactive mode detected'
fi

# Show welcome screen (only in interactive mode)
if [ "$NON_INTERACTIVE" = false ]; then
    if command -v whiptail &> /dev/null; then
        whiptail --title "Cambium NMS Templates Installer" \
            --msgbox "Welcome to the Cambium NMS Templates installer!

Template: $TEMPLATE_NAME
Description: $TEMPLATE_DESC

Platform: $NMS_PLATFORM
Product: $PRODUCT_TEMPLATE
Mode: $MODE

This installer will guide you through the installation process.

Press OK to continue..." 18 70
    fi
fi

# Collect user inputs (check env vars first, then prompt)
yellow 'Collecting installation parameters...'

# Process each input from requirements.yaml
declare -A USER_VALUES

# Environment variable name mapping
declare -A ENV_VAR_MAP
ENV_VAR_MAP[zabbix_api_url]="ZABBIX_API_URL"
ENV_VAR_MAP[zabbix_api_token]="ZABBIX_API_TOKEN"
ENV_VAR_MAP[olt_password]="OLT_PASSWORD"
ENV_VAR_MAP[flush_template]="FLUSH_TEMPLATE"
ENV_VAR_MAP[flush_hosts]="FLUSH_HOSTS"
ENV_VAR_MAP[add_hosts]="ADD_HOSTS"
ENV_VAR_MAP[olt_ip_addresses]="OLT_IPS"

# Process each input from parsed requirements
while IFS='|' read -r prefix input_name input_type prompt default_val condition help_b64 _example; do
    # Skip non-INPUT lines and empty names
    [ "$prefix" != "INPUT" ] && continue
    [ -z "$input_name" ] && continue

    # Check if this input has a condition
    if [ -n "$condition" ]; then
        # Simple condition evaluation (e.g., "add_hosts == true")
        cond_var=$(echo "$condition" | awk '{print $1}')
        cond_op=$(echo "$condition" | awk '{print $2}')
        cond_val=$(echo "$condition" | awk '{print $3}')

        # Skip if condition not met
        if [ "$cond_op" = "==" ] && [ "${USER_VALUES[$cond_var]}" != "$cond_val" ]; then
            continue
        fi
    fi

    # Get environment variable name
    ENV_VAR="${ENV_VAR_MAP[$input_name]}"

    # Check environment variable first
    if [ -n "$ENV_VAR" ] && [ -n "${!ENV_VAR}" ]; then
        # Value from environment
        case "$input_type" in
            boolean)
                if [ "${!ENV_VAR}" = "true" ] || [ "${!ENV_VAR}" = "yes" ]; then
                    USER_VALUES[$input_name]="true"
                    echo "  ${prompt}: yes (from environment)"
                else
                    USER_VALUES[$input_name]="false"
                    echo "  ${prompt}: no (from environment)"
                fi
                ;;
            secret)
                USER_VALUES[$input_name]="${!ENV_VAR}"
                echo "  ${prompt}: ****** (from environment)"
                ;;
            *)
                USER_VALUES[$input_name]="${!ENV_VAR}"
                echo "  ${prompt}: ${USER_VALUES[$input_name]} (from environment)"
                ;;
        esac
    else
        # Interactive prompt
        if [ "$NON_INTERACTIVE" = false ]; then
            # Decode and show help text if present
            if [ -n "$help_b64" ]; then
                help_text=$(echo "$help_b64" | base64 -d 2>/dev/null || echo "")
                if [ -n "$help_text" ]; then
                    whiptail --title "Help: $prompt" --msgbox "$help_text" 20 75
                fi
            fi

            # Show input dialog based on type
            case "$input_type" in
                secret)
                    if ! USER_VALUES[$input_name]=$(whiptail --passwordbox "$prompt" 10 70 3>&1 1>&2 2>&3); then
                        red "Installation cancelled"
                        exit 1
                    fi
                    ;;
                boolean)
                    if whiptail --yesno "$prompt" 10 70 3>&1 1>&2 2>&3; then
                        USER_VALUES[$input_name]="true"
                    else
                        USER_VALUES[$input_name]="false"
                    fi
                    ;;
                *)
                    # url, text, list - all use inputbox
                    if ! USER_VALUES[$input_name]=$(whiptail --inputbox "$prompt" 10 70 "$default_val" 3>&1 1>&2 2>&3); then
                        red "Installation cancelled"
                        exit 1
                    fi
                    ;;
            esac
        else
            # Non-interactive - use defaults
            case "$input_type" in
                boolean)
                    if [ "$default_val" = "true" ]; then
                        USER_VALUES[$input_name]="true"
                    else
                        USER_VALUES[$input_name]="false"
                    fi
                    ;;
                *)
                    USER_VALUES[$input_name]="$default_val"
                    ;;
            esac
        fi
    fi
done < <(echo "$PARSED_DATA" | grep "^INPUT|")

echo ""
green "✓ Configuration collected"
echo "  API URL: ${USER_VALUES[zabbix_api_url]}"
echo "  Template: $TEMPLATE_NAME"
echo "  Flush Template: ${USER_VALUES[flush_template]}"
echo "  Flush Hosts: ${USER_VALUES[flush_hosts]}"
echo "  Add Hosts: ${USER_VALUES[add_hosts]}"
if [ "${USER_VALUES[add_hosts]}" = "true" ]; then
    echo "  OLT IPs: ${USER_VALUES[olt_ip_addresses]}"
fi
echo ""

# Exit here if only validating configuration
if [ "$VALIDATE_CONFIG_ONLY" = true ]; then
    green "✓ Configuration validation complete (--validate-config mode)"
    exit 0
fi

#=============================================================================
# Installation Implementation
#=============================================================================

# Helper function: Make Zabbix API request
zabbix_api_call() {
    local method=$1
    local params=$2
    local auth_token="${USER_VALUES[zabbix_api_token]}"

    # Prepare auth field based on version (will be detected later)
    local auth_field=""
    if [ "$ZABBIX_VERSION_MAJOR" = "7.0" ]; then
        # Zabbix 7.0 uses auth field in payload
        auth_field="\"auth\": \"$auth_token\","
    else
        # Zabbix 7.2+ uses Bearer token in header (no auth field in payload)
        auth_field=""
    fi

    local payload="{
        \"jsonrpc\": \"2.0\",
        \"method\": \"$method\",
        \"params\": $params,
        $auth_field
        \"id\": 1
    }"

    # Make request with appropriate auth method
    if [ "$ZABBIX_VERSION_MAJOR" = "7.0" ]; then
        # Use auth field for 7.0
        curl -s -X POST "${USER_VALUES[zabbix_api_url]}/api_jsonrpc.php" \
            -H "Content-Type: application/json" \
            -d "$payload"
    else
        # Use Bearer token for 7.2+
        curl -s -X POST "${USER_VALUES[zabbix_api_url]}/api_jsonrpc.php" \
            -H "Content-Type: application/json" \
            -H "Authorization: Bearer $auth_token" \
            -d "$payload"
    fi
}

# Step 1: Validate API connection and detect version
yellow '▶ Step 1: Validating Zabbix API connection...'
API_VERSION_RESPONSE=$(curl -s -X POST "${USER_VALUES[zabbix_api_url]}/api_jsonrpc.php" \
    -H "Content-Type: application/json" \
    -d '{
        "jsonrpc": "2.0",
        "method": "apiinfo.version",
        "params": {},
        "id": 1
    }')

# Check if API is reachable
if [ -z "$API_VERSION_RESPONSE" ]; then
    red "✗ Error: Cannot reach Zabbix API at ${USER_VALUES[zabbix_api_url]}"
    exit 1
fi

# Extract version
ZABBIX_VERSION=$(echo "$API_VERSION_RESPONSE" | grep -o '"result":"[^"]*"' | cut -d'"' -f4)
if [ -z "$ZABBIX_VERSION" ]; then
    red "✗ Error: Failed to get Zabbix version"
    echo "  Response: $API_VERSION_RESPONSE"
    exit 1
fi

ZABBIX_VERSION_MAJOR=$(echo "$ZABBIX_VERSION" | cut -d'.' -f1,2)
green "  ✓ Zabbix version: $ZABBIX_VERSION (API $ZABBIX_VERSION_MAJOR)"

# Test authentication
echo "  Testing API authentication..."
if [ "$ZABBIX_VERSION_MAJOR" = "7.0" ]; then
    # Test auth field for 7.0
    AUTH_TEST=$(curl -s -X POST "${USER_VALUES[zabbix_api_url]}/api_jsonrpc.php" \
        -H "Content-Type: application/json" \
        -d "{
            \"jsonrpc\": \"2.0\",
            \"method\": \"user.get\",
            \"params\": {\"output\": [\"userid\"]},
            \"auth\": \"${USER_VALUES[zabbix_api_token]}\",
            \"id\": 1
        }")
else
    # Test Bearer auth for 7.2+
    AUTH_TEST=$(curl -s -X POST "${USER_VALUES[zabbix_api_url]}/api_jsonrpc.php" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer ${USER_VALUES[zabbix_api_token]}" \
        -d '{
            "jsonrpc": "2.0",
            "method": "user.get",
            "params": {"output": ["userid"]},
            "id": 1
        }')
fi

# Check for auth error
if echo "$AUTH_TEST" | grep -q '"error"'; then
    red "✗ Error: API authentication failed"
    echo "  Response: $AUTH_TEST"
    exit 1
fi

green "  ✓ API authentication successful"

# Step 2: Flush existing template if requested
if [ "${USER_VALUES[flush_template]}" = "true" ]; then
    yellow '▶ Step 2: Removing existing template...'

    # Get template ID
    TEMPLATE_RESPONSE=$(zabbix_api_call "template.get" '{
        "filter": {"host": "Cambium Fiber OLT by SSH v1.3.0"}
    }')

    TEMPLATE_ID=$(echo "$TEMPLATE_RESPONSE" | grep -o '"templateid":"[^"]*"' | head -1 | cut -d'"' -f4)

    if [ -n "$TEMPLATE_ID" ]; then
        echo "  Found existing template (ID: $TEMPLATE_ID), deleting..."
        DELETE_RESPONSE=$(zabbix_api_call "template.delete" "[\"$TEMPLATE_ID\"]")

        if echo "$DELETE_RESPONSE" | grep -q '"error"'; then
            red "✗ Error: Failed to delete template"
            echo "  Response: $DELETE_RESPONSE"
            exit 1
        fi
        green "  ✓ Template removed"
    else
        echo "  No existing template found (skipping)"
    fi
fi

# Step 3: Flush existing hosts if requested
if [ "${USER_VALUES[flush_hosts]}" = "true" ]; then
    yellow '▶ Step 3: Removing existing hosts...'

    # Get template ID first
    TEMPLATE_RESPONSE=$(zabbix_api_call "template.get" '{
        "filter": {"host": "Cambium Fiber OLT by SSH v1.3.0"}
    }')

    TEMPLATE_ID=$(echo "$TEMPLATE_RESPONSE" | grep -o '"templateid":"[^"]*"' | head -1 | cut -d'"' -f4)

    if [ -n "$TEMPLATE_ID" ]; then
        # Get all hosts using this template
        HOSTS_RESPONSE=$(zabbix_api_call "host.get" "{
            \"templateids\": [\"$TEMPLATE_ID\"],
            \"output\": [\"hostid\", \"host\"]
        }")

        # Extract host IDs
        HOST_IDS=$(echo "$HOSTS_RESPONSE" | grep -o '"hostid":"[^"]*"' | cut -d'"' -f4)

        if [ -n "$HOST_IDS" ]; then
            HOST_COUNT=$(echo "$HOST_IDS" | wc -l)
            echo "  Found $HOST_COUNT host(s) to remove..."

            # Build array of host IDs for deletion
            HOST_ID_ARRAY="["
            FIRST=true
            for host_id in $HOST_IDS; do
                if [ "$FIRST" = false ]; then
                    HOST_ID_ARRAY+=","
                fi
                HOST_ID_ARRAY+="\"$host_id\""
                FIRST=false
            done
            HOST_ID_ARRAY+="]"

            DELETE_RESPONSE=$(zabbix_api_call "host.delete" "$HOST_ID_ARRAY")

            if echo "$DELETE_RESPONSE" | grep -q '"error"'; then
                red "✗ Error: Failed to delete hosts"
                echo "  Response: $DELETE_RESPONSE"
                exit 1
            fi
            green "  ✓ Removed $HOST_COUNT host(s)"
        else
            echo "  No existing hosts found (skipping)"
        fi
    else
        echo "  Template not found (skipping host deletion)"
    fi
fi

# Step 4: Import template via API
yellow '▶ Step 4: Importing template...'

# Ensure template group exists
echo "  Checking for template group..."
TEMPLATE_GROUP_NAME="Templates/Network devices/Cambium Fiber"
TEMPLATEGROUP_RESPONSE=$(zabbix_api_call "templategroup.get" "{
    \"filter\": {\"name\": \"$TEMPLATE_GROUP_NAME\"}
}")

TEMPLATEGROUP_ID=$(echo "$TEMPLATEGROUP_RESPONSE" | grep -o '"groupid":"[^"]*"' | head -1 | cut -d'"' -f4)

if [ -z "$TEMPLATEGROUP_ID" ]; then
    echo "  Creating template group '$TEMPLATE_GROUP_NAME'..."
    TEMPLATEGROUP_CREATE=$(zabbix_api_call "templategroup.create" "{
        \"name\": \"$TEMPLATE_GROUP_NAME\"
    }")

    if echo "$TEMPLATEGROUP_CREATE" | grep -q '"error"'; then
        red "✗ Error: Failed to create template group"
        echo "  Response: $TEMPLATEGROUP_CREATE"
        exit 1
    fi
    green "  ✓ Template group created"
else
    echo "  ✓ Template group exists"
fi

# Read template file (path set earlier)
if [ ! -f "$TEMPLATE_FILE" ]; then
    red "✗ Error: Template file not found: $TEMPLATE_FILE"
    exit 1
fi

# Prepare template content (escape for JSON)
TEMPLATE_CONTENT=$(python3 -c "import sys, json; print(json.dumps(sys.stdin.read()))" < "$TEMPLATE_FILE")

# Import template with appropriate rules
IMPORT_RESPONSE=$(zabbix_api_call "configuration.import" "{
    \"format\": \"yaml\",
    \"rules\": {
        \"templates\": {
            \"createMissing\": true,
            \"updateExisting\": true
        },
        \"items\": {
            \"createMissing\": true,
            \"updateExisting\": true
        },
        \"discoveryRules\": {
            \"createMissing\": true,
            \"updateExisting\": true
        },
        \"triggers\": {
            \"createMissing\": true,
            \"updateExisting\": true
        },
        \"graphs\": {
            \"createMissing\": true,
            \"updateExisting\": true
        },
        \"valueMaps\": {
            \"createMissing\": true,
            \"updateExisting\": true
        }
    },
    \"source\": $TEMPLATE_CONTENT
}")

if echo "$IMPORT_RESPONSE" | grep -q '"error"'; then
    red "✗ Error: Failed to import template"
    echo "  Response: $IMPORT_RESPONSE"
    exit 1
fi

green "  ✓ Template imported successfully"

# Step 5: Deploy external script
yellow '▶ Step 5: Deploying external script...'

# Script file path set earlier during download/setup
if [ ! -f "$SCRIPT_FILE" ]; then
    red "✗ Error: Script file not found: $SCRIPT_FILE"
    exit 1
fi

# Detect ExternalScripts directory
EXTERNALSCRIPTS_DIR="/usr/lib/zabbix/externalscripts"

if [ ! -d "$EXTERNALSCRIPTS_DIR" ]; then
    red "✗ Error: ExternalScripts directory not found: $EXTERNALSCRIPTS_DIR"
    echo "  Please ensure Zabbix server is installed or create the directory"
    exit 1
fi

if [ ! -w "$EXTERNALSCRIPTS_DIR" ]; then
    red "✗ Error: No write access to $EXTERNALSCRIPTS_DIR"
    echo "  Please run this installer as root or with sudo"
    exit 1
fi

# Copy script to ExternalScripts directory
if ! cp "$SCRIPT_FILE" "$EXTERNALSCRIPTS_DIR/cambium_olt_ssh_json.py"; then
    red "✗ Error: Failed to copy script to $EXTERNALSCRIPTS_DIR"
    exit 1
fi

# Make script executable
if ! chmod +x "$EXTERNALSCRIPTS_DIR/cambium_olt_ssh_json.py"; then
    red "✗ Error: Failed to make script executable"
    exit 1
fi

green "  ✓ Script deployed: cambium_olt_ssh_json.py"

# Step 6: Configure {$OLT.PASS} macro on template
yellow '▶ Step 6: Configuring macros...'

# Get template ID
TEMPLATE_RESPONSE=$(zabbix_api_call "template.get" '{
    "filter": {"host": "Cambium Fiber OLT by SSH v1.3.0"},
    "output": ["templateid"]
}')

TEMPLATE_ID=$(echo "$TEMPLATE_RESPONSE" | grep -o '"templateid":"[^"]*"' | head -1 | cut -d'"' -f4)

if [ -z "$TEMPLATE_ID" ]; then
    red "✗ Error: Cannot find imported template"
    exit 1
fi

# Update macro
MACRO_RESPONSE=$(zabbix_api_call "template.update" "{
    \"templateid\": \"$TEMPLATE_ID\",
    \"macros\": [
        {
            \"macro\": \"{\$OLT.PASS}\",
            \"value\": \"${USER_VALUES[olt_password]}\",
            \"type\": 1
        }
    ]
}")

if echo "$MACRO_RESPONSE" | grep -q '"error"'; then
    red "✗ Error: Failed to configure macro"
    echo "  Response: $MACRO_RESPONSE"
    exit 1
fi

green "  ✓ Macro {\$OLT.PASS} configured"

# Step 7: Create hosts if requested
if [ "${USER_VALUES[add_hosts]}" = "true" ]; then
    yellow '▶ Step 7: Creating OLT hosts...'

    # Ensure host group exists
    HOSTGROUP_RESPONSE=$(zabbix_api_call "hostgroup.get" '{
        "filter": {"name": "Cambium Fiber OLT"}
    }')

    HOSTGROUP_ID=$(echo "$HOSTGROUP_RESPONSE" | grep -o '"groupid":"[^"]*"' | head -1 | cut -d'"' -f4)

    if [ -z "$HOSTGROUP_ID" ]; then
        echo "  Creating host group 'Cambium Fiber OLT'..."
        HOSTGROUP_CREATE=$(zabbix_api_call "hostgroup.create" '{
            "name": "Cambium Fiber OLT"
        }')
        HOSTGROUP_ID=$(echo "$HOSTGROUP_CREATE" | grep -o '"groupids":\["[^"]*"' | cut -d'"' -f4)
    fi

    # Parse IP addresses
    IFS=',' read -ra IP_ARRAY <<< "${USER_VALUES[olt_ip_addresses]}"

    for ip in "${IP_ARRAY[@]}"; do
        # Trim whitespace
        ip=$(echo "$ip" | xargs)

        echo "  Creating host for OLT: $ip"

        # Generate host name (use IP-based naming as fallback)
        HOST_NAME="OLT-$(echo "$ip" | tr '.' '-')"

        # Create host
        HOST_RESPONSE=$(zabbix_api_call "host.create" "{
            \"host\": \"$HOST_NAME\",
            \"name\": \"$HOST_NAME\",
            \"groups\": [{\"groupid\": \"$HOSTGROUP_ID\"}],
            \"templates\": [{\"templateid\": \"$TEMPLATE_ID\"}],
            \"interfaces\": [
                {
                    \"type\": 1,
                    \"main\": 1,
                    \"useip\": 1,
                    \"ip\": \"$ip\",
                    \"dns\": \"\",
                    \"port\": \"10050\"
                }
            ]
        }")

        if echo "$HOST_RESPONSE" | grep -q '"error"'; then
            red "  ✗ Warning: Failed to create host for $ip"
            echo "    Response: $HOST_RESPONSE"
            continue
        fi

        green "  ✓ Host created: $HOST_NAME ($ip)"
    done
fi

echo ""
green "✓ Installation completed successfully!"
echo ""
echo "Summary:"
echo "  Template: $TEMPLATE_NAME"
echo "  Zabbix Version: $ZABBIX_VERSION"
echo "  API URL: ${USER_VALUES[zabbix_api_url]}"
if [ "${USER_VALUES[add_hosts]}" = "true" ]; then
    echo "  Hosts created: ${#IP_ARRAY[@]}"
fi
echo ""
echo "Next steps:"
echo "  1. Log in to Zabbix web interface"
echo "  2. Navigate to Configuration → Hosts"
if [ "${USER_VALUES[add_hosts]}" = "true" ]; then
    echo "  3. Verify OLT hosts are created and linked to template"
    echo "  4. Wait 1-2 minutes for initial data collection"
else
    echo "  3. Manually create hosts and link to template"
    echo "  4. Add {\$OLT.PASS} macro to each host (or use template default)"
fi
echo ""
