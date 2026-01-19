#!/usr/bin/env python3
"""
Base class for Zabbix integration tests across multiple versions.

DEPRECATED: This module provides backward compatibility with existing tests.
New tests should use base.test_harness.ZabbixTestHarness and validator classes.

Provides common test infrastructure and methods that are shared across
Zabbix 7.0, 7.2, and 7.4 test suites.
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

try:
    import requests
except ImportError:
    print("Error: requests is required. Install with: pip install requests")
    sys.exit(1)

# Import refactored components
try:
    from .base.test_harness import ZabbixTestHarness, LegacyTestMethods
    from .base.docker_helpers import Colors
except ImportError:
    # Fallback for direct execution
    from base.test_harness import ZabbixTestHarness, LegacyTestMethods
    from base.docker_helpers import Colors


class ZabbixTestBase:
    """
    Legacy base test harness for Zabbix integration testing.

    This class wraps the new modular architecture to maintain backward
    compatibility with existing tests. New tests should use ZabbixTestHarness
    and validator classes directly.
    """

    def __init__(self, version: str, compose_version_file: str, project_name: Optional[str] = None):
        """
        Initialize test harness.

        Args:
            version: Zabbix version string (e.g., "7.0", "7.2", "7.4")
            compose_version_file: Docker Compose override filename
            project_name: Docker Compose project name for parallel execution isolation
        """
        # Initialize new harness
        self.harness = ZabbixTestHarness(version, compose_version_file, project_name)
        self.legacy_tests = LegacyTestMethods(self.harness)

        # Expose harness properties for backward compatibility
        self.version = self.harness.version
        self.test_dir = self.harness.test_dir
        self.repo_root = self.harness.repo_root

        self.zabbix_url = self.harness.zabbix_url
        self.zabbix_user = self.harness.zabbix_user
        self.zabbix_password = self.harness.zabbix_password
        self.api_token = self.harness.api_token

        self.mock_olt_1 = self.harness.mock_olt_1
        self.mock_olt_2 = self.harness.mock_olt_2
        self.olt_password = self.harness.olt_password
        self.keep_running = self.harness.keep_running

    @property
    def passed(self) -> int:
        """Number of passed tests."""
        return self.harness.result.passed

    @property
    def failed(self) -> int:
        """Number of failed tests."""
        return self.harness.result.failed

    @property
    def compose_base(self) -> Path:
        """Base docker-compose file path."""
        return self.harness.docker.compose_base

    @property
    def compose_version(self) -> Path:
        """Version-specific docker-compose file path."""
        return self.harness.docker.compose_version

    def setup(self):
        """Start Docker Compose stack"""
        self.harness.setup()
        # Sync api_token back for compatibility
        self.api_token = self.harness.api_token

    def teardown(self):
        """Stop and remove Docker Compose stack"""
        self.harness.teardown()

    def assert_test(self, condition: bool, test_name: str, error_msg: str = ""):
        """Assert test condition and track results"""
        self.harness.assertions.assert_true(condition, test_name, error_msg)

    def run_command(self, cmd: list, capture: bool = True) -> tuple[int, str]:
        """Execute shell command"""
        return self.harness.docker.run_command(cmd, capture)

    def _print_colored(self, message: str, color: str):
        """Print colored message"""
        self.harness.print_colored(message, color)

    def _docker_exec(self, container: str, command: list) -> tuple[int, str]:
        """Execute command in Docker container"""
        return self.harness.docker.exec_command(container, command)

    def _docker_ps_names(self, filter_name: str) -> str:
        """Get Docker container names by filter"""
        return self.harness.docker.get_container_names(filter_name)

    def _docker_compose(self, action: str, extra_args: Optional[list] = None):
        """Run docker-compose command - deprecated, use harness.docker methods"""
        # This is kept for backward compatibility but delegates to new implementation
        import subprocess
        cmd = ["docker-compose", "-f", str(self.compose_base), "-f", str(self.compose_version), action]
        if extra_args:
            cmd.extend(extra_args)

        if action == "down":
            return subprocess.run(
                cmd,
                cwd=self.test_dir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True
            )
        else:
            return subprocess.run(
                cmd,
                cwd=self.test_dir,
                capture_output=True,
                text=True
            )

    def _zabbix_api_request(self, method: str, params: dict, request_id: int = 1) -> dict:
        """Make Zabbix API request"""
        if not self.harness.api_client:
            raise RuntimeError("API client not initialized. Call authenticate() first.")

        # Use new API client
        result = self.harness.api_client.request(method, params)
        return {"result": result}

    def _check_containers_running(self, filter_name: str, expected_containers: list, description: str):
        """Check if expected containers are running"""
        output = self._docker_ps_names(filter_name)
        self.assert_test(
            all(container in output for container in expected_containers),
            f"{description} are running",
            output if any(container not in output for container in expected_containers) else ""
        )

    def _test_ssh_connectivity(self, container: str, olt_name: str):
        """Test SSH connectivity to a container"""
        self.legacy_tests.harness.print_colored(f"  Testing {olt_name}...", Colors.BLUE)
        exit_code, output = self._docker_exec(
            container,
            ["python3", "-c", "import socket; s=socket.socket(); s.connect(('localhost', 22))"]
        )
        self.assert_test(
            exit_code == 0,
            f"{olt_name} SSH server is listening",
            output if exit_code != 0 else ""
        )

    def _docker_cp(self, source: str, dest: str):
        """Copy file to/from Docker container"""
        self.harness.docker.copy_file(source, dest)

    def test_docker_services(self):
        """Test 1: Verify all Docker services are running"""
        self.legacy_tests.test_docker_services()

    def test_olt_data_retrieval(self):
        """Test 3: Retrieve data from mock OLTs using Python script"""
        self.legacy_tests.test_olt_data_retrieval()

    def test_zabbix_web_ui(self):
        """Test 4: Zabbix web UI accessibility"""
        self.legacy_tests.test_zabbix_web_ui()

    def test_zabbix_api_login(self):
        """Test 5: Zabbix API authentication"""
        self.legacy_tests.test_zabbix_api_login()
        # Sync api_token back for compatibility
        self.api_token = self.harness.api_token

    def test_zabbix_version(self):
        """Test 6: Verify Zabbix version matches expected version"""
        self.legacy_tests.test_zabbix_version()

    def test_external_scripts_volume(self):
        """Test 7: Verify external scripts volume is mounted"""
        self.legacy_tests.test_external_scripts_volume()

    def _copy_template_files(self):
        """Verify template files exist in mounted volume"""
        self._print_colored("  Verifying template files in container...", Colors.BLUE)

        if "installer-test" not in self._docker_ps_names("installer-test"):
            raise RuntimeError("installer-test container is not running")

        # Verify template directory exists
        exit_code, output = self._docker_exec(
            "installer-test",
            ["test", "-d", "/root/cambium-nms-templates/templates/zabbix/cambium-fiber"]
        )
        if exit_code != 0:
            raise RuntimeError("Template directory not found in container (volume mount failed?)")

        # Verify key template files exist
        required_files = ["template.yaml", "cambium_olt_ssh_json.py"]
        for file in required_files:
            exit_code, output = self._docker_exec(
                "installer-test",
                ["test", "-f", f"/root/cambium-nms-templates/templates/zabbix/cambium-fiber/{file}"]
            )
            if exit_code != 0:
                raise RuntimeError(f"Required file not found: {file}")

        # Verify install.sh exists
        exit_code, output = self._docker_exec(
            "installer-test",
            ["test", "-f", "/root/cambium-nms-templates/install.sh"]
        )
        if exit_code != 0:
            raise RuntimeError("install.sh not found in container")

        install_sh = self.repo_root / "install.sh"
        if not install_sh.exists():
            raise FileNotFoundError(f"install.sh not found at {install_sh}")

        self._print_colored("    ✓ All template files present in mounted volume", Colors.GREEN)

    def _verify_template_imported(self):
        """Verify template was imported to Zabbix"""
        self._print_colored("  Verifying template import...", Colors.BLUE)

        try:
            result = self._zabbix_api_request(
                "template.get",
                {"filter": {"host": "Cambium Fiber OLT by SSH v1.3.0"}},
                request_id=3
            )
            templates = result.get("result", [])

            self.assert_test(
                len(templates) > 0,
                "Template imported to Zabbix",
                f"Template not found. Response: {result}"
            )
        except Exception as e:
            self.assert_test(False, "Template import verification", str(e))

    def _verify_script_deployed(self):
        """Verify external script was deployed"""
        self._print_colored("  Verifying script deployment...", Colors.BLUE)
        exit_code, output = self._docker_exec(
            "zabbix-server",
            ["test", "-x", "/usr/lib/zabbix/externalscripts/cambium_olt_ssh_json.py"]
        )

        self.assert_test(
            exit_code == 0,
            "External script deployed and executable",
            output if exit_code != 0 else ""
        )

    def test_install_with_installer_sh(self):
        """Test 8: Install template using install.sh (non-interactive mode)"""
        self._print_colored("\nTest 8: Template installation via install.sh", Colors.BLUE)

        if not self.api_token:
            self.assert_test(False, "Template installation", "No API token (authentication failed)")
            return

        try:
            self._copy_template_files()
            self._print_colored("  ✓ Files copied to container", Colors.GREEN)
        except Exception as e:
            self.assert_test(False, "Copy template files", str(e))
            return

        try:
            self._print_colored("  Running install.sh in non-interactive mode...", Colors.BLUE)

            installer_zabbix_url = "http://zabbix-web:8080"

            # Get the actual container name with project prefix
            installer_container = self.harness.docker.get_container_name("installer-test")

            exit_code, output = self.run_command([
                "docker", "exec",
                "-e", f"ZABBIX_API_URL={installer_zabbix_url}",
                "-e", f"ZABBIX_API_TOKEN={self.api_token}",
                "-e", f"OLT_PASSWORD={self.olt_password}",
                "-e", f"ADD_HOSTS=true",
                "-e", f"OLT_IPS={self.mock_olt_1},{self.mock_olt_2}",
                installer_container,
                "/bin/bash", "-c",
                "cd /root/cambium-nms-templates && ./install.sh --local"
            ])

            print(f"{Colors.YELLOW}  Installer output:{Colors.NC}")
            print(output[:1000])

            self.assert_test(
                exit_code == 0,
                "Installer executed without errors",
                f"Exit code: {exit_code}\nOutput: {output[-500:]}" if exit_code != 0 else ""
            )

            if exit_code == 0:
                self._verify_template_imported()
                self._verify_script_deployed()

        except Exception as e:
            self.assert_test(False, "Installer execution", str(e))

    def run_all_tests(self, skip_if_running: bool = False):
        """Run complete test suite

        Args:
            skip_if_running: If True, skip Docker startup if containers already running
        """
        print(f"\n{Colors.YELLOW}{'='*60}{Colors.NC}")
        print(f"{Colors.YELLOW}  Zabbix {self.version} Integration Tests{Colors.NC}")
        print(f"{Colors.YELLOW}{'='*60}{Colors.NC}\n")

        try:
            self.harness.setup(skip_if_running=skip_if_running)

            # Legacy/Core tests
            self.test_docker_services()
            self.test_olt_data_retrieval()
            self.test_zabbix_web_ui()
            self.test_zabbix_api_login()
            self.test_zabbix_version()
            self.test_external_scripts_volume()
            self.test_install_with_installer_sh()

            # Import and run new test suites
            if self.api_token:
                try:
                    from suites.test_core_functionality import CoreFunctionalityTests
                    from suites.test_template_health import TemplateHealthTests
                    from suites.test_graphs import GraphTests
                    from suites.test_host_operations import HostOperationsTests
                    from suites.test_item_data_collection import ItemDataCollectionTests
                    from suites.test_advanced_features import AdvancedFeaturesTests

                    # Priority 1: Core Functionality
                    core_tests = CoreFunctionalityTests(self.harness)
                    core_tests.run_all()

                    # Priority 2: Template Health
                    health_tests = TemplateHealthTests(self.harness)
                    health_tests.run_all()

                    # Priority 3: Graphs
                    graph_tests = GraphTests(self.harness)
                    graph_tests.run_all()

                    # Priority 4: Host Operations
                    host_tests = HostOperationsTests(self.harness)
                    host_tests.run_all()

                    # Priority 5: Item Data Collection
                    item_tests = ItemDataCollectionTests(self.harness)
                    item_tests.run_all()

                    # Priority 6: Advanced Features
                    advanced_tests = AdvancedFeaturesTests(self.harness)
                    advanced_tests.run_all()

                except ImportError as e:
                    print(f"{Colors.YELLOW}Warning: Could not load extended test suites: {e}{Colors.NC}")

        finally:
            self.teardown()

        # Summary
        return self.harness.print_summary()

