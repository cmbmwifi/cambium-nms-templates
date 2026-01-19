#!/usr/bin/env python3
"""
Standalone test for mock OLT SSH server.

Tests that the mock OLT container works independently of the full Zabbix stack.

Run with:
    python3 test_mock_olt.py
"""

import json
import subprocess
import sys
import time
from pathlib import Path


class Colors:
    GREEN = '\033[0;32m'
    RED = '\033[0;31m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'


class MockOLTTest:
    def __init__(self):
        self.test_dir = Path(__file__).parent
        self.passed = 0
        self.failed = 0
        self.container_name = "test-mock-olt"
        self.olt_ip = "172.30.0.10"
        self.olt_password = "password"

    def print_colored(self, message: str, color: str):
        """Print colored message"""
        print(f"{color}{message}{Colors.NC}")

    def assert_test(self, condition: bool, test_name: str, error_msg: str = ""):
        """Assert test condition and track results"""
        if condition:
            print(f"{Colors.GREEN}✓ {test_name}{Colors.NC}")
            self.passed += 1
        else:
            print(f"{Colors.RED}✗ {test_name}{Colors.NC}")
            if error_msg:
                print(f"  Error: {error_msg}")
            self.failed += 1

    def run_command(self, cmd: list) -> tuple[int, str]:
        """Execute shell command"""
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode, result.stdout + result.stderr

    def setup(self):
        """Start mock OLT container"""
        self.print_colored("\n============================================================", Colors.BLUE)
        self.print_colored("  Mock OLT Standalone Test", Colors.BLUE)
        self.print_colored("============================================================\n", Colors.BLUE)

        self.print_colored("Building and starting mock OLT container...", Colors.YELLOW)

        # Clean up any existing container
        subprocess.run(["docker", "rm", "-f", self.container_name],
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Build the image
        exit_code, output = self.run_command([
            "docker", "build", "-t", "mock-olt-test",
            "-f", str(self.test_dir / "Dockerfile"),
            str(self.test_dir)
        ])

        if exit_code != 0:
            self.print_colored(f"Failed to build image:\n{output}", Colors.RED)
            return False

        # Create network if it doesn't exist
        subprocess.run([
            "docker", "network", "create",
            "--subnet=172.30.0.0/16", "mock-olt-test-net"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Start container
        exit_code, output = self.run_command([
            "docker", "run", "-d",
            "--name", self.container_name,
            "--network", "mock-olt-test-net",
            "--ip", self.olt_ip,
            "-p", "2224:22",
            "-v", f"{self.test_dir.parent.parent / 'fixtures'}:/app/fixtures:ro",
            "-e", "OLT_NAME=Test-OLT",
            "mock-olt-test"
        ])

        if exit_code != 0:
            self.print_colored(f"Failed to start container:\n{output}", Colors.RED)
            return False

        # Wait for container to be healthy
        self.print_colored("Waiting for SSH server to start...", Colors.BLUE)
        for i in range(30):
            exit_code, _ = self.run_command([
                "docker", "exec", self.container_name,
                "python3", "-c",
                "import socket; s=socket.socket(); s.connect(('localhost', 22))"
            ])
            if exit_code == 0:
                self.print_colored("✓ Mock OLT is ready\n", Colors.GREEN)
                return True
            time.sleep(1)

        self.print_colored("Timeout waiting for SSH server", Colors.RED)
        return False

    def teardown(self):
        """Clean up containers and networks"""
        self.print_colored("\nCleaning up...", Colors.YELLOW)
        subprocess.run(["docker", "rm", "-f", self.container_name],
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["docker", "network", "rm", "mock-olt-test-net"],
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def test_container_running(self):
        """Test 1: Container is running"""
        self.print_colored("Test 1: Container health", Colors.BLUE)
        exit_code, output = self.run_command([
            "docker", "ps", "--filter", f"name={self.container_name}",
            "--format", "{{.Names}}"
        ])
        self.assert_test(
            self.container_name in output,
            "Mock OLT container is running",
            output if self.container_name not in output else ""
        )

    def test_ssh_port_listening(self):
        """Test 2: SSH port is accessible"""
        self.print_colored("\nTest 2: SSH connectivity", Colors.BLUE)
        exit_code, output = self.run_command([
            "docker", "exec", self.container_name,
            "python3", "-c",
            "import socket; s=socket.socket(); s.connect(('localhost', 22))"
        ])
        self.assert_test(
            exit_code == 0,
            "SSH port 22 is listening",
            output if exit_code != 0 else ""
        )

    def test_ssh_auth_from_host(self):
        """Test 3: SSH authentication and basic command"""
        self.print_colored("\nTest 3: SSH authentication and OLT commands", Colors.BLUE)

        # Try SSH connection from host via mapped port with OLT-specific commands
        process = subprocess.Popen(
            [
                "sshpass", "-p", self.olt_password,
                "ssh", "-o", "StrictHostKeyChecking=no",
                "-o", "UserKnownHostsFile=/dev/null",
                "-o", "ConnectTimeout=5",
                "-T",  # Disable PTY allocation
                "-p", "2224",
                "admin@localhost"
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        try:
            # Send OLT commands
            stdout, stderr = process.communicate(input="info\nshow all\nexit\n", timeout=10)
            exit_code = process.returncode

            # Check if we got JSON data
            has_json = "{" in stdout and "}" in stdout

            self.assert_test(
                exit_code == 0 and has_json,
                "SSH authentication and OLT commands successful",
                f"Exit code: {exit_code}, Has JSON: {has_json}, Output: {stdout[:200]}"
            )

            return exit_code == 0 and has_json
        except subprocess.TimeoutExpired:
            process.kill()
            self.assert_test(False, "SSH authentication and OLT commands", "Command timed out")
            return False
    def test_olt_commands(self):
        """Test 4: OLT returns expected data structure"""
        self.print_colored("\nTest 4: Validate OLT JSON data structure", Colors.BLUE)

        # Send commands via stdin
        process = subprocess.Popen(
            [
                "sshpass", "-p", self.olt_password,
                "ssh", "-o", "StrictHostKeyChecking=no",
                "-o", "UserKnownHostsFile=/dev/null",
                "-o", "ConnectTimeout=5",
                "-T",
                "-p", "2224",
                "admin@localhost"
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        try:
            stdout, stderr = process.communicate(input="info\nshow all\nexit\n", timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            self.assert_test(False, "Get OLT data", "Command timed out")
            return

        # Check if output looks like JSON
        has_json = "{" in stdout and "}" in stdout

        self.assert_test(
            process.returncode == 0 and has_json,
            "OLT returns JSON data",
        )

        if has_json:
            # Try to find and parse JSON
            try:
                # Find JSON in output (may have other text before/after)
                json_start = stdout.find('{')
                json_end = stdout.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = stdout[json_start:json_end]
                    data = json.loads(json_str)

                    self.assert_test(
                        len(data) > 0,
                        "JSON data is not empty",
                        f"Got: {list(data.keys()) if isinstance(data, dict) else type(data)}"
                    )

                    # Check for expected keys
                    if isinstance(data, dict):
                        expected_keys = ["Ethernet", "Candidate", "System"]
                        found_keys = [k for k in expected_keys if k in data]
                        self.assert_test(
                            len(found_keys) > 0,
                            f"JSON has expected structure (found: {found_keys})",
                            f"Missing expected keys. Got: {list(data.keys())[:5]}"
                        )
                else:
                    self.assert_test(False, "Extract JSON from output", "Could not find JSON boundaries")
            except json.JSONDecodeError as e:
                self.assert_test(False, "Parse JSON output", f"JSON error: {e}")

    def run_all_tests(self):
        """Run all tests"""
        try:
            if not self.setup():
                return 1

            self.test_container_running()
            self.test_ssh_port_listening()
            self.test_ssh_auth_from_host()
            self.test_olt_commands()

        finally:
            self.teardown()

        # Print summary
        self.print_colored("\n============================================================", Colors.BLUE)
        if self.failed > 0:
            self.print_colored(f"✗ {self.failed}/{self.passed + self.failed} tests failed", Colors.RED)
        self.print_colored(f"✓ {self.passed}/{self.passed + self.failed} tests passed", Colors.GREEN)
        self.print_colored("============================================================\n", Colors.BLUE)

        return 1 if self.failed > 0 else 0


def main():
    """Main entry point"""
    test = MockOLTTest()
    exit_code = test.run_all_tests()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
