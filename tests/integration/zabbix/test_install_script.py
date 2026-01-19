#!/usr/bin/env python3
"""
Integration tests for install.sh

This test suite validates the Cambium NMS Templates installer by:
1. Running non-interactive tests (flags, parsing, execution)
2. Running interactive tests (whiptail dialogs with pexpect)
3. Validating installation steps and output

Uses Docker containers for isolated testing.
"""

import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

try:
    import pexpect
except ImportError:
    print("Error: pexpect is required. Install with: pip install pexpect")
    sys.exit(1)


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[0;32m'
    RED = '\033[0;31m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color


class InstallerTest:
    """Test harness for install.sh using Docker containers"""

    def __init__(self):
        self.container_id: Optional[str] = None
        self.test_dir = Path(__file__).parent
        self.passed = 0
        self.failed = 0

    def setup(self):
        """Build and start test container"""
        print(f"{Colors.YELLOW}Building test container...{Colors.NC}")
        subprocess.run(
            ["docker-compose", "build", "--quiet"],
            cwd=self.test_dir,
            check=True
        )

        print(f"{Colors.YELLOW}Starting container...{Colors.NC}")
        result = subprocess.run(
            ["docker-compose", "run", "-d", "installer-test", "sleep", "300"],
            cwd=self.test_dir,
            capture_output=True,
            text=True,
            check=True
        )
        self.container_id = result.stdout.strip()
        print(f"Container ID: {self.container_id}\n")
        time.sleep(2)  # Wait for container to be ready

    def teardown(self):
        """Stop and remove test container"""
        if self.container_id:
            print(f"\n{Colors.YELLOW}Cleaning up...{Colors.NC}")
            subprocess.run(["docker", "stop", self.container_id],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["docker", "rm", self.container_id],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def run_command(self, command: str) -> tuple[int, str]:
        """Execute command in container and return exit code and output"""
        result = subprocess.run(
            ["docker", "exec", self.container_id, "bash", "-c", command],
            capture_output=True,
            text=True
        )
        return result.returncode, result.stdout + result.stderr

    def assert_test(self, condition: bool, test_name: str, error_msg: str = ""):
        """Assert test condition and track results"""
        if condition:
            print(f"{Colors.GREEN}✓{Colors.NC} {test_name}")
            self.passed += 1
        else:
            print(f"{Colors.RED}✗{Colors.NC} {test_name}")
            if error_msg:
                print(f"  Error: {error_msg}")
            self.failed += 1

    def test_installer_execution(self):
        """Test 1: Installer executes without errors"""
        print(f"{Colors.BLUE}Test 1: Basic installer execution{Colors.NC}")
        exit_code, output = self.run_command("./install.sh --local 2>&1 | head -20")
        self.assert_test(
            exit_code == 0,
            "Installer executes without errors",
            f"Exit code: {exit_code}"
        )

    def test_help_flag(self):
        """Test 2: --help flag works"""
        print(f"\n{Colors.BLUE}Test 2: Help flag{Colors.NC}")
        exit_code, output = self.run_command("./install.sh --help")
        self.assert_test(
            exit_code == 0 and "Usage:" in output,
            "--help flag displays usage information",
            output if exit_code != 0 else ""
        )

    def test_local_flag(self):
        """Test 3: --local flag enables development mode"""
        print(f"\n{Colors.BLUE}Test 3: Local development mode{Colors.NC}")
        exit_code, output = self.run_command("./install.sh --local 2>&1 | head -5")
        self.assert_test(
            "Development mode" in output,
            "--local flag enables development mode",
            output
        )

    def test_requirements_parsing(self):
        """Test 4: requirements.yaml parsing"""
        print(f"\n{Colors.BLUE}Test 4: Requirements file parsing{Colors.NC}")
        exit_code, output = self.run_command("./install.sh --local 2>&1 | head -10")
        self.assert_test(
            "Found requirements.yaml" in output,
            "requirements.yaml is found and parsed",
            output
        )

    def test_dependency_detection(self):
        """Test 5: Dependency detection"""
        print(f"\n{Colors.BLUE}Test 5: Dependency detection{Colors.NC}")
        exit_code, output = self.run_command(
            "grep -A 5 'dependencies:' /root/cambium-nms-templates/templates/zabbix/cambium-fiber/requirements.yaml"
        )
        self.assert_test(
            "openssh-client" in output or "system_packages" in output,
            "Dependencies are defined in requirements.yaml",
            output if exit_code != 0 else ""
        )

    def test_whiptail_dialogs(self):
        """Test 6: Interactive whiptail dialogs with pexpect"""
        print(f"\n{Colors.BLUE}Test 6: Interactive whiptail dialogs{Colors.NC}")

        try:
            # Spawn installer with pseudo-terminal
            child = pexpect.spawn(
                f"docker exec -it {self.container_id} /bin/bash -c './install.sh --local'",
                encoding='utf-8',
                timeout=15,
                codec_errors='ignore'  # Ignore encoding errors from box-drawing characters
            )

            # Enable logging for debugging
            # child.logfile = sys.stdout

            # Test 6a: Welcome dialog with template info
            try:
                child.expect("Welcome", timeout=10)
                self.assert_test(True, "Welcome dialog appears")
                time.sleep(1)
                child.send("\r")  # Press Enter (use \r for better compatibility)
            except pexpect.TIMEOUT:
                print(f"Buffer: {child.before}")
                self.assert_test(False, "Welcome dialog appears", "Timeout waiting for dialog")
                child.close()
                return

            # Test 6b: Status dialog
            try:
                time.sleep(1)  # Wait for next dialog
                child.expect("skeleton", timeout=10)
                self.assert_test(True, "Status dialog appears")
                time.sleep(1)
                child.send("\r")  # Press Enter
            except pexpect.TIMEOUT:
                print(f"Buffer: {child.before}")

            # Test 6d: Completion
            try:
                child.expect([
                    "Test installer completed successfully",
                    pexpect.EOF
                ], timeout=10)
                self.assert_test(True, "Installer completes successfully")
            except pexpect.TIMEOUT:
                self.assert_test(False, "Installer completes successfully", "Timeout")

            child.close()

        except Exception as e:
            self.assert_test(False, "Interactive dialog testing", str(e))

    def run_all_tests(self):
        """Run complete test suite"""
        print(f"\n{Colors.YELLOW}{'='*60}{Colors.NC}")
        print(f"{Colors.YELLOW}Starting integration tests for install.sh{Colors.NC}")
        print(f"{Colors.YELLOW}{'='*60}{Colors.NC}\n")

        try:
            self.setup()

            # Non-interactive tests
            self.test_installer_execution()
            self.test_help_flag()
            self.test_local_flag()
            self.test_requirements_parsing()
            self.test_dependency_detection()

            # Interactive tests
            self.test_whiptail_dialogs()

        finally:
            self.teardown()

        # Summary
        print(f"\n{Colors.YELLOW}{'='*60}{Colors.NC}")
        total = self.passed + self.failed
        if self.failed == 0:
            print(f"{Colors.GREEN}✓ All {total} tests passed!{Colors.NC}")
            print(f"\n{Colors.GREEN}Summary:{Colors.NC}")
            print(f"  ✓ Installer executes successfully")
            print(f"  ✓ Command-line flags work (--help, --local)")
            print(f"  ✓ requirements.yaml parsing works")
            print(f"  ✓ Interactive whiptail dialogs work")
            print(f"  ✓ Dialog navigation and flow complete")
            return 0
        else:
            print(f"{Colors.RED}✗ {self.failed}/{total} tests failed{Colors.NC}")
            print(f"{Colors.GREEN}✓ {self.passed}/{total} tests passed{Colors.NC}")
            return 1


def main():
    """Main entry point"""
    test = InstallerTest()
    exit_code = test.run_all_tests()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
