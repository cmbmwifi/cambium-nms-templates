#!/usr/bin/env python3
"""
Test assertion helpers for Zabbix integration tests.

Provides colored output and test result tracking.
"""

from typing import Any, List, Tuple


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[0;32m'
    RED = '\033[0;31m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'


class TestResult:
    """Container for test results."""

    def __init__(self):
        """Initialize test result tracker."""
        self.passed = 0
        self.failed = 0
        self.errors: List[Tuple[str, str]] = []

    def add_pass(self, test_name: str) -> None:
        """
        Record a passed test.

        Args:
            test_name: Name of the test
        """
        print(f"{Colors.GREEN}✓{Colors.NC} {test_name}")
        self.passed += 1

    def add_fail(self, test_name: str, error_msg: str = "") -> None:
        """
        Record a failed test.

        Args:
            test_name: Name of the test
            error_msg: Error message or details
        """
        print(f"{Colors.RED}✗{Colors.NC} {test_name}")
        if error_msg:
            print(f"  Error: {error_msg}")
        self.failed += 1
        self.errors.append((test_name, error_msg))

    @property
    def total(self) -> int:
        """Total number of tests run."""
        return self.passed + self.failed

    @property
    def success_rate(self) -> float:
        """Success rate as percentage."""
        return (self.passed / self.total * 100) if self.total > 0 else 0.0

    def print_summary(self, version: str = "") -> int:
        """
        Print test summary.

        Args:
            version: Optional version string to include in summary

        Returns:
            Exit code (0 for success, 1 for failure)
        """
        print(f"\n{Colors.YELLOW}{'='*60}{Colors.NC}")

        if self.failed == 0:
            print(f"{Colors.GREEN}✓ All {self.total} tests passed!{Colors.NC}")
            if version:
                print(f"\n{Colors.GREEN}Zabbix {version} is fully operational{Colors.NC}")
            return 0
        else:
            print(f"{Colors.RED}✗ {self.failed}/{self.total} tests failed{Colors.NC}")
            print(f"{Colors.GREEN}✓ {self.passed}/{self.total} tests passed{Colors.NC}")
            print(f"\n{Colors.YELLOW}Failed tests:{Colors.NC}")
            for test_name, error in self.errors:
                print(f"  • {test_name}")
                if error:
                    error_preview = error[:200] + "..." if len(error) > 200 else error
                    print(f"    {error_preview}")
            return 1


class TestAssertions:
    """Custom assertions for Zabbix testing."""

    def __init__(self, result: TestResult):
        """
        Initialize assertions helper.

        Args:
            result: TestResult instance for tracking
        """
        self.result = result
        self.current_test = None

    def start_test(self, test_name: str) -> None:
        """
        Start a new test (prints test name).

        Args:
            test_name: Name of the test
        """
        self.current_test = test_name
        print(f"\n{Colors.BLUE}▶ {test_name}{Colors.NC}")

    def print_info(self, message: str) -> None:
        """
        Print informational message.

        Args:
            message: Message to print
        """
        print(f"{Colors.BLUE}{message}{Colors.NC}")

    def assert_true(self, condition: bool, test_name: str, error_msg: str = "") -> bool:
        """
        Assert condition is true.

        Args:
            condition: Condition to test
            test_name: Name of the test
            error_msg: Error message if assertion fails

        Returns:
            True if assertion passed
        """
        if condition:
            self.result.add_pass(test_name)
            return True
        else:
            self.result.add_fail(test_name, error_msg)
            return False

    def assert_equal(self, actual: Any, expected: Any, test_name: str) -> bool:
        """
        Assert actual equals expected.

        Args:
            actual: Actual value
            expected: Expected value
            test_name: Name of the test

        Returns:
            True if assertion passed
        """
        if actual == expected:
            self.result.add_pass(test_name)
            return True
        else:
            error_msg = f"Expected {expected}, got {actual}"
            self.result.add_fail(test_name, error_msg)
            return False

    def assert_not_empty(self, items: list, test_name: str, error_msg: str = "") -> bool:
        """
        Assert list/collection is not empty.

        Args:
            items: Collection to check
            test_name: Name of the test
            error_msg: Optional error message

        Returns:
            True if assertion passed
        """
        if items:
            self.result.add_pass(test_name)
            return True
        else:
            error_msg = error_msg or "Expected non-empty collection"
            self.result.add_fail(test_name, error_msg)
            return False

    def assert_empty(self, items: list, test_name: str, error_msg: str = "") -> bool:
        """
        Assert list/collection is empty.

        Args:
            items: Collection to check
            test_name: Name of the test
            error_msg: Optional error message

        Returns:
            True if assertion passed
        """
        if not items:
            self.result.add_pass(test_name)
            return True
        else:
            error_msg = error_msg or f"Expected empty collection, got {len(items)} items"
            self.result.add_fail(test_name, error_msg)
            return False

    def assert_contains(self, text: str, substring: str, test_name: str) -> bool:
        """
        Assert text contains substring.

        Args:
            text: Text to search in
            substring: Substring to find
            test_name: Name of the test

        Returns:
            True if assertion passed
        """
        if substring in text:
            self.result.add_pass(test_name)
            return True
        else:
            error_msg = f"Expected to find '{substring}' in text"
            self.result.add_fail(test_name, error_msg)
            return False

    def assert_all_supported(self, items: list, test_name: str) -> bool:
        """
        Assert all items are in supported state (state=0).

        Args:
            items: List of item dicts with 'state' field
            test_name: Name of the test

        Returns:
            True if all items supported
        """
        unsupported = [item for item in items if item.get("state") == "1"]
        if not unsupported:
            self.result.add_pass(test_name)
            return True
        else:
            error_msg = f"{len(unsupported)} item(s) unsupported: {[i.get('name') for i in unsupported[:3]]}"
            self.result.add_fail(test_name, error_msg)
            return False
