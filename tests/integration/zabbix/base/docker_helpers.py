#!/usr/bin/env python3
"""
Docker container management helpers for Zabbix integration tests.

Provides utilities for Docker Compose operations, container execution,
and health checking.
"""

import subprocess
import time
from pathlib import Path
from typing import List, Optional, Tuple


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[0;32m'
    RED = '\033[0;31m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'


class DockerManager:
    """Manages Docker Compose stacks and container operations."""

    def __init__(self, test_dir: Path, compose_base: Path, compose_version: Path, project_name: Optional[str] = None, database_name: Optional[str] = None):
        """
        Initialize Docker manager.

        Args:
            test_dir: Test directory for command execution
            compose_base: Path to base docker-compose.yml
            compose_version: Path to version-specific docker-compose override
            project_name: Docker Compose project name for isolation (default: derived from compose files)
            database_name: MySQL database name for this Zabbix version (e.g., 'zabbix70')
        """
        self.test_dir = test_dir
        self.compose_base = compose_base
        self.compose_version = compose_version
        self.project_name = project_name
        self.database_name = database_name

        # Track what infrastructure this instance started for smart cleanup
        self.started_mysql = False
        self.started_mock_olts = False

    def get_container_name(self, service_name: str) -> str:
        """
        Get the actual Docker container name for a service.

        With project names, containers are named: {project}-{service}-{replica}
        Without project names, they use the directory name as project.

        Args:
            service_name: The service name from docker-compose.yml

        Returns:
            The actual container name
        """
        if self.project_name:
            return f"{self.project_name}-{service_name}-1"
        # Without explicit project name, docker-compose uses directory name
        return f"zabbix-{service_name}-1"

    def _ensure_shared_network(self) -> None:
        """Create shared network if it doesn't exist."""
        result = subprocess.run(
            ["docker", "network", "inspect", "zabbix-shared-network"],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            # Network doesn't exist, create it
            result = subprocess.run(
                ["docker", "network", "create", "--subnet=172.20.0.0/16", "zabbix-shared-network"],
                capture_output=True,
                text=True
            )
            # Ignore error if network was created by another parallel test (race condition)
            if result.returncode != 0 and "already exists" not in result.stderr:
                raise RuntimeError(f"Failed to create shared network: {result.stderr}")

    def _check_infrastructure_running(self) -> tuple[bool, bool]:
        """
        Check if test infrastructure is running.

        Returns:
            Tuple of (mysql_running, mock_olts_running)
        """
        mysql_check = subprocess.run(
            ["docker", "ps", "--filter", "name=test-mysql", "--filter", "status=running", "--format", "{{.Names}}"],
            capture_output=True,
            text=True
        )
        mysql_running = "test-mysql" in mysql_check.stdout

        olt_check = subprocess.run(
            ["docker", "ps", "--filter", "name=zabbix-mock-olt", "--filter", "status=running", "--format", "{{.Names}}"],
            capture_output=True,
            text=True
        )
        mock_olts_running = "zabbix-mock-olt" in olt_check.stdout

        return mysql_running, mock_olts_running

    def _recreate_database(self) -> None:
        """
        Drop and recreate the database for this Zabbix version.
        Ensures each test run starts with a clean slate.
        """
        if not self.database_name:
            return

        print(f"{Colors.YELLOW}Recreating database '{self.database_name}' for clean slate...{Colors.NC}")

        # Wait for MySQL to be fully ready
        max_retries = 5
        for attempt in range(max_retries):
            result = subprocess.run(
                [
                    "docker", "exec", "test-mysql",
                    "mysql", "-uroot", "-proot_pass", "-e",
                    f"DROP DATABASE IF EXISTS {self.database_name}; "
                    f"CREATE DATABASE {self.database_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;"
                ],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print(f"{Colors.GREEN}✓ Database '{self.database_name}' recreated{Colors.NC}")
                return

            if attempt < max_retries - 1:
                time.sleep(2)

        raise RuntimeError(f"Failed to recreate database after {max_retries} attempts: {result.stderr}")

    def _drop_all_test_databases(self) -> None:
        """
        Drop all Zabbix test databases (zabbix70, zabbix72, zabbix74).
        Useful for cleanup after failed tests when MySQL stays running.
        """
        # Check if MySQL is running
        mysql_check = subprocess.run(
            ["docker", "ps", "--filter", "name=test-mysql", "--filter", "status=running", "--format", "{{.Names}}"],
            capture_output=True,
            text=True
        )
        if "test-mysql" not in mysql_check.stdout:
            return  # MySQL not running, nothing to clean

        print(f"{Colors.YELLOW}Dropping test databases...{Colors.NC}")
        for db in ["zabbix70", "zabbix72", "zabbix74", "zabbix80"]:
            subprocess.run(
                [
                    "docker", "exec", "test-mysql",
                    "mysql", "-uroot", "-proot_pass", "-e",
                    f"DROP DATABASE IF EXISTS {db};"
                ],
                capture_output=True,
                text=True
            )
        print(f"{Colors.GREEN}✓ Test databases dropped{Colors.NC}")

    def _ensure_test_infrastructure(self) -> tuple[bool, bool]:
        """
        Start test infrastructure (MySQL, Mock OLTs) if not already running.

        Returns:
            Tuple of (started_mysql, started_mock_olts) indicating what was started
        """
        mysql_running, mock_olts_running = self._check_infrastructure_running()
        started_mysql = False
        started_mock_olts = False

        # Start MySQL if not running
        if not mysql_running:
            print(f"{Colors.YELLOW}Starting MySQL test infrastructure...{Colors.NC}")
            mysql_compose = self.test_dir.parent / "mysql" / "docker-compose.yml"
            result = subprocess.run(
                ["docker-compose", "-f", str(mysql_compose), "up", "-d"],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                raise RuntimeError(f"Failed to start MySQL: {result.stderr}")
            started_mysql = True
            time.sleep(5)
            print(f"{Colors.GREEN}✓ MySQL ready{Colors.NC}")
        else:
            print(f"{Colors.GREEN}✓ MySQL already running{Colors.NC}")

        # Start Mock OLTs if not running
        if not mock_olts_running:
            print(f"{Colors.YELLOW}Starting Mock OLT test infrastructure...{Colors.NC}")
            olt_compose = self.test_dir / "docker-compose.mock-olts.yml"
            result = subprocess.run(
                ["docker-compose", "-f", str(olt_compose), "up", "-d"],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                raise RuntimeError(f"Failed to start Mock OLTs: {result.stderr}")
            started_mock_olts = True
            time.sleep(5)
            print(f"{Colors.GREEN}✓ Mock OLTs ready{Colors.NC}")
        else:
            print(f"{Colors.GREEN}✓ Mock OLTs already running{Colors.NC}")

        return started_mysql, started_mock_olts

    def compose_up(self, timeout_seconds: int = 120, skip_if_running: bool = False) -> None:
        """
        Start Docker Compose stack and wait for services to be healthy.

        Args:
            timeout_seconds: Maximum time to wait for health checks
            skip_if_running: If True, skip startup if containers are already running

        Raises:
            RuntimeError: If services fail to become healthy
        """
        # Check if already running (useful when starting multiple environments in parallel)
        if skip_if_running and self.is_stack_running():
            print(f"{Colors.GREEN}✓ Stack already running and healthy{Colors.NC}")
            return

        print(f"{Colors.YELLOW}Starting Docker Compose stack...{Colors.NC}")

        # Ensure shared network exists
        self._ensure_shared_network()

        # Ensure test infrastructure (MySQL, Mock OLTs) is running
        # Store what we started so we can clean up appropriately
        self.started_mysql, self.started_mock_olts = self._ensure_test_infrastructure()

        # Recreate database for clean slate (test isolation)
        self._recreate_database()

        # Clean up any existing containers for this version
        self._docker_compose("down", ["-v"])

        # Start services
        startup_result = self._docker_compose("up", ["-d"])
        if startup_result.returncode != 0:
            raise RuntimeError(f"Failed to start Docker Compose: {startup_result.stderr}")

        print(f"{Colors.BLUE}Waiting for services to be healthy (timeout: {timeout_seconds}s)...{Colors.NC}")

        start_time = time.time()
        while time.time() - start_time < timeout_seconds:
            if self._check_all_healthy():
                print(f"{Colors.GREEN}✓ All services are healthy{Colors.NC}")
                time.sleep(5)  # Stabilization delay
                return

            time.sleep(5)

        raise RuntimeError("Timeout waiting for services to be healthy")

    def compose_down(self) -> None:
        """Stop and remove Docker Compose stack, and clean up test infrastructure if we started it."""
        print(f"{Colors.YELLOW}Stopping Docker Compose stack...{Colors.NC}")
        self._docker_compose("down", ["-v"])

        # Smart cleanup: only stop infrastructure if we started it
        # This allows reusing infrastructure when running multiple tests
        if self.started_mock_olts:
            print(f"{Colors.YELLOW}Stopping Mock OLTs (we started them)...{Colors.NC}")
            subprocess.run(
                ["docker", "compose", "-f", self.test_dir / "docker-compose.mock-olts.yml", "down"],
                cwd=self.test_dir,
                check=True
            )

        if self.started_mysql:
            # Drop all test databases before stopping MySQL
            # (useful for failed test cleanup, though databases are non-persistent)
            self._drop_all_test_databases()
            print(f"{Colors.YELLOW}Stopping MySQL (we started it)...{Colors.NC}")
            subprocess.run(
                ["docker", "compose", "-f", self.test_dir.parent / "mysql" / "docker-compose.yml", "down"],
                cwd=self.test_dir.parent / "mysql",
                check=True
            )

    def exec_command(self, container: str, command: List[str]) -> Tuple[int, str]:
        """
        Execute command in Docker container.

        Args:
            container: Container service name (will be converted to actual container name)
            command: Command and arguments as list

        Returns:
            Tuple of (exit_code, output)
        """
        container_name = self.get_container_name(container)
        cmd = ["docker", "exec", container_name] + command
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=self.test_dir
        )
        return result.returncode, result.stdout + result.stderr

    def copy_file(self, source: str, dest: str) -> None:
        """
        Copy file to/from Docker container.

        Args:
            source: Source path (container:path or local path)
            dest: Destination path (container:path or local path)

        Raises:
            RuntimeError: If copy operation fails
        """
        result = subprocess.run(
            ["docker", "cp", source, dest],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            raise RuntimeError(f"Failed to copy {source} to {dest}: {result.stderr}")

    def get_container_names(self, filter_name: str) -> str:
        """
        Get Docker container names by filter.

        Args:
            filter_name: Partial service name to filter by

        Returns:
            Container names (one per line)
        """
        # For project-based naming, we need to search for the project prefix + filter
        if self.project_name:
            search_pattern = f"{self.project_name}-{filter_name}"
        else:
            search_pattern = filter_name

        result = subprocess.run(
            ["docker", "ps", "--filter", f"name={search_pattern}", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            cwd=self.test_dir
        )
        return result.stdout

    def container_exists(self, container_name: str) -> bool:
        """
        Check if container exists and is running.

        Args:
            container_name: Container name to check

        Returns:
            True if container is running
        """
        return container_name in self.get_container_names(container_name)

    def run_command(self, cmd: List[str], capture: bool = True) -> Tuple[int, str]:
        """
        Execute shell command.

        Args:
            cmd: Command and arguments as list
            capture: Whether to capture output

        Returns:
            Tuple of (exit_code, output)
        """
        result = subprocess.run(
            cmd,
            capture_output=capture,
            text=True,
            cwd=self.test_dir
        )
        return result.returncode, result.stdout + result.stderr

    def _docker_compose(self, action: str, extra_args: Optional[List[str]] = None) -> subprocess.CompletedProcess:
        """
        Run docker-compose command.

        Args:
            action: Docker Compose action (up, down, etc.)
            extra_args: Additional arguments

        Returns:
            CompletedProcess instance
        """
        cmd = ["docker-compose"]
        if self.project_name:
            cmd.extend(["-p", self.project_name])
        cmd.extend(["-f", str(self.compose_base), "-f", str(self.compose_version), action])
        if extra_args:
            cmd.extend(extra_args)

        if action == "down":
            # Suppress output for down command
            return subprocess.run(
                cmd,
                cwd=self.test_dir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True
            )
        else:
            # Capture output for other commands
            return subprocess.run(
                cmd,
                cwd=self.test_dir,
                capture_output=True,
                text=True
            )

    def _check_all_healthy(self) -> bool:
        """
        Check if all required services are healthy.

        Returns:
            True if all services are healthy
        """
        result = subprocess.run(
            ["docker", "ps", "--filter", "health=healthy", "--format", "{{.Names}}"],
            capture_output=True,
            text=True
        )

        healthy = result.stdout
        # Mock OLTs are managed separately and shared by all test versions
        # Only check for project-specific containers
        required_services = ["zabbix-server", "zabbix-web"]
        # Convert service names to actual container names
        required_containers = [self.get_container_name(svc) for svc in required_services]
        return all(container in healthy for container in required_containers)

    def is_stack_running(self) -> bool:
        """
        Check if Docker Compose stack is already running and healthy.

        Returns:
            True if all required containers are running and healthy
        """
        return self._check_all_healthy()
