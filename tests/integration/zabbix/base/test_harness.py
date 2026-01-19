#!/usr/bin/env python3
"""
Core test harness for Zabbix integration tests.

Provides minimal setup/teardown infrastructure and coordinates
test execution using extracted helper components.
"""

import json
import sys
from pathlib import Path
from typing import Optional

try:
    import requests
except ImportError:
    print("Error: requests is required. Install with: pip install requests")
    sys.exit(1)

from .docker_helpers import DockerManager, Colors
from .api_helpers import ZabbixAPIClient
from .assertions import TestResult, TestAssertions


class ZabbixTestHarness:
    """
    Lightweight test harness that coordinates Docker, API, and test execution.

    This class focuses on setup/teardown and provides access to helper
    components, delegating actual test logic to validator classes.
    """

    def __init__(self, version: str, compose_version_file: str, project_name: Optional[str] = None):
        """
        Initialize test harness.

        Args:
            version: Zabbix version string (e.g., "7.0", "7.2", "7.4")
            compose_version_file: Docker Compose override filename
            project_name: Docker Compose project name for parallel execution isolation
        """
        self.version = version
        self.test_dir = Path(__file__).parent.parent
        self.repo_root = self.test_dir.parent.parent.parent

        compose_base = self.test_dir / "docker-compose.base.yml"
        compose_version = self.test_dir / compose_version_file

        # Determine database name from version
        database_name = f"zabbix{version.replace('.', '')}"

        # Initialize helper components
        self.docker = DockerManager(self.test_dir, compose_base, compose_version, project_name, database_name)
        self.result = TestResult()
        self.assertions = TestAssertions(self.result)

        # Zabbix connection details (port varies by version)
        port_map = {"7.0": 8080, "7.2": 8081, "7.4": 8082, "8.0": 8083}
        port = port_map.get(version, 8080)
        self.zabbix_url = f"http://localhost:{port}"
        self.zabbix_user = "Admin"
        self.zabbix_password = "zabbix"
        self.api_token: Optional[str] = None
        self.api_client: Optional[ZabbixAPIClient] = None

        # OLT connection details
        self.mock_olt_1 = "172.20.0.10"
        self.mock_olt_2 = "172.20.0.11"
        self.olt_password = "password"

        self.keep_running = False

    def setup(self, skip_if_running: bool = False) -> None:
        """Start Docker Compose stack and initialize API client.

        Args:
            skip_if_running: If True, skip startup if containers are already running
        """
        try:
            self.docker.compose_up(skip_if_running=skip_if_running)
        except RuntimeError as e:
            print(f"{Colors.RED}Setup failed: {e}{Colors.NC}")
            self.docker.compose_down()
            sys.exit(1)

    def teardown(self) -> None:
        """Stop and remove Docker Compose stack."""
        if not self.keep_running:
            self.docker.compose_down()
        else:
            self._print_keep_running_info()

    def authenticate(self) -> bool:
        """
        Authenticate with Zabbix API and initialize API client.

        Returns:
            True if authentication successful
        """
        try:
            response = requests.post(
                f"{self.zabbix_url}/api_jsonrpc.php",
                json={
                    "jsonrpc": "2.0",
                    "method": "user.login",
                    "params": {
                        "username": self.zabbix_user,
                        "password": self.zabbix_password
                    },
                    "id": 1
                },
                headers={"Content-Type": "application/json"},
                timeout=10
            )

            result = response.json()

            if "result" in result:
                self.api_token = result["result"]
                if self.api_token:  # Only create client if token exists
                    self.api_client = ZabbixAPIClient(self.zabbix_url, self.api_token, self.version)
                return True
            else:
                error = result.get("error", {}).get("data", "Unknown error")
                print(f"{Colors.RED}Authentication failed: {error}{Colors.NC}")
                return False

        except Exception as e:
            print(f"{Colors.RED}Authentication error: {e}{Colors.NC}")
            return False

    def print_colored(self, message: str, color: str) -> None:
        """
        Print colored message.

        Args:
            message: Message to print
            color: Color code from Colors class
        """
        print(f"{color}{message}{Colors.NC}")

    def print_summary(self) -> int:
        """
        Print test summary and return exit code.

        Returns:
            Exit code (0 for success, 1 for failure)
        """
        return self.result.print_summary(self.version)

    def _print_keep_running_info(self) -> None:
        """Print information about keeping stack running for manual testing."""
        print(f"\n{Colors.BLUE}{'='*60}{Colors.NC}")
        print(f"{Colors.BLUE}  Zabbix Stack Left Running for Manual Testing{Colors.NC}")
        print(f"{Colors.BLUE}{'='*60}{Colors.NC}")
        print(f"\n{Colors.GREEN}Access Information:{Colors.NC}")
        print(f"  Web UI:      {self.zabbix_url}")
        print(f"  Username:    {self.zabbix_user}")
        print(f"  Password:    {self.zabbix_password}")
        if self.api_token:
            print(f"  API Token:   {self.api_token}")
        print(f"\n{Colors.YELLOW}Mock OLTs:{Colors.NC}")
        print(f"  OLT 1:       {self.mock_olt_1}:22 (admin/{self.olt_password})")
        print(f"  OLT 2:       {self.mock_olt_2}:22 (admin/{self.olt_password})")
        print(f"\n{Colors.YELLOW}To stop:{Colors.NC}")
        print(f"  cd {self.test_dir}")
        print(f"  docker-compose -f docker-compose.base.yml -f {self.docker.compose_version.name} down -v")
        print(f"{Colors.BLUE}{'='*60}{Colors.NC}\n")


class LegacyTestMethods:
    """
    Legacy test methods from original ZabbixTestBase.

    These methods are kept for backward compatibility with existing tests.
    New tests should use validator classes instead.
    """

    def __init__(self, harness: ZabbixTestHarness):
        """
        Initialize legacy test methods.

        Args:
            harness: ZabbixTestHarness instance
        """
        self.harness = harness

    def test_docker_services(self) -> None:
        """Test: Verify Zabbix Docker services are running."""
        self.harness.print_colored("\nTest: Docker services health", Colors.BLUE)

        # Check Zabbix containers
        zabbix_server = self.harness.docker.get_container_name("zabbix-server")
        zabbix_web = self.harness.docker.get_container_name("zabbix-web")
        output = self.harness.docker.get_container_names("zabbix")
        self.harness.assertions.assert_true(
            zabbix_server in output and zabbix_web in output,
            "Zabbix containers are running",
            output if zabbix_server not in output or zabbix_web not in output else ""
        )

    def test_olt_data_retrieval(self) -> None:
        """Test: Retrieve data from mock OLTs using Python script."""
        self.harness.print_colored("\nTest: OLT data retrieval", Colors.BLUE)

        script_path = "/root/cambium-nms-templates/templates/zabbix/cambium-fiber/cambium_olt_ssh_json.py"
        exit_code, output = self.harness.docker.exec_command(
            "installer-test",
            ["python3", script_path, self.harness.mock_olt_1, self.harness.olt_password]
        )

        # Filter out SSH warnings
        lines = output.split('\n')
        json_output = '\n'.join([line for line in lines if not line.startswith('Warning:')])

        try:
            data = json.loads(json_output)
            has_data = len(data) > 0

            self.harness.assertions.assert_true(
                exit_code == 0 and has_data,
                "Retrieved JSON data from Mock OLT 1",
                f"Got empty JSON. Exit code: {exit_code}" if not has_data else ""
            )

            if has_data:
                self.harness.assertions.assert_true(
                    "Ethernet" in data or "Candidate" in data,
                    "JSON data has expected structure",
                    f"Missing expected keys. Got: {list(data.keys())}"
                )
        except json.JSONDecodeError as e:
            self.harness.assertions.assert_true(
                False,
                "Retrieved valid JSON from Mock OLT 1",
                f"Invalid JSON: {e}"
            )

    def test_zabbix_web_ui(self) -> None:
        """Test: Zabbix web UI accessibility."""
        self.harness.print_colored("\nTest: Zabbix web UI", Colors.BLUE)

        try:
            response = requests.get(f"{self.harness.zabbix_url}/", timeout=10)
            self.harness.assertions.assert_true(
                response.status_code == 200,
                "Zabbix web UI is accessible",
                f"HTTP {response.status_code}"
            )

            self.harness.assertions.assert_contains(
                response.text,
                "Zabbix",
                "Zabbix web UI content is valid"
            )
        except Exception as e:
            self.harness.assertions.assert_true(False, "Zabbix web UI is accessible", str(e))

    def test_zabbix_api_login(self) -> None:
        """Test: Zabbix API authentication."""
        self.harness.print_colored("\nTest: Zabbix API authentication", Colors.BLUE)

        if self.harness.authenticate():
            self.harness.assertions.assert_true(True, "Zabbix API authentication successful")
        else:
            self.harness.assertions.assert_true(False, "Zabbix API authentication", "Login failed")

    def test_zabbix_version(self) -> None:
        """Test: Verify Zabbix version matches expected version."""
        self.harness.print_colored("\nTest: Zabbix version check", Colors.BLUE)

        if not self.harness.api_client:
            self.harness.assertions.assert_true(False, "Zabbix version check", "No API client")
            return

        try:
            response = requests.post(
                f"{self.harness.zabbix_url}/api_jsonrpc.php",
                json={"jsonrpc": "2.0", "method": "apiinfo.version", "params": {}, "id": 2},
                headers={"Content-Type": "application/json"},
                timeout=10
            )

            result = response.json()
            if "result" in result:
                version = result["result"]
                self.harness.assertions.assert_true(
                    version.startswith(self.harness.version),
                    f"Zabbix version is {self.harness.version}.x (got {version})",
                    f"Expected {self.harness.version}.x, got {version}"
                )
            else:
                error = result.get("error", {}).get("data", "Unknown error")
                self.harness.assertions.assert_true(False, "Zabbix version check", f"API error: {error}")
        except Exception as e:
            self.harness.assertions.assert_true(False, "Zabbix version check", str(e))

    def test_external_scripts_volume(self) -> None:
        """Test: Verify external scripts volume is mounted."""
        self.harness.print_colored("\nTest: External scripts volume", Colors.BLUE)

        exit_code, output = self.harness.docker.exec_command(
            "zabbix-server",
            ["ls", "-la", "/usr/lib/zabbix/externalscripts"]
        )

        self.harness.assertions.assert_true(
            exit_code == 0,
            "External scripts directory exists",
            output if exit_code != 0 else ""
        )
