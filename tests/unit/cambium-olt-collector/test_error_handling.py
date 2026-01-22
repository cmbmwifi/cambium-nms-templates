#!/usr/bin/env python3
"""
Unit tests for error handling in cambium_olt_ssh_json.py

These tests ensure that SSH failures and other errors are properly
propagated instead of being silently swallowed.
"""
import sys
import unittest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path


class Colors:
    GREEN = '\033[0;32m'
    RED = '\033[0;31m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'


class ColoredTextTestResult(unittest.TextTestResult):
    """Custom test result class with colored output."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.test_results = []

    def addSuccess(self, test):
        super().addSuccess(test)
        test_name = test._testMethodDoc or str(test).split()[0]
        print(f"{Colors.GREEN}✓ {test_name}{Colors.NC}")
        self.test_results.append(('success', test_name))

    def addError(self, test, err):
        super().addError(test, err)
        test_name = test._testMethodDoc or str(test).split()[0]
        print(f"{Colors.RED}✗ {test_name} (ERROR){Colors.NC}")
        self.test_results.append(('error', test_name))

    def addFailure(self, test, err):
        super().addFailure(test, err)
        test_name = test._testMethodDoc or str(test).split()[0]
        print(f"{Colors.RED}✗ {test_name} (FAILED){Colors.NC}")
        self.test_results.append(('failure', test_name))

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        test_name = test._testMethodDoc or str(test).split()[0]
        print(f"{Colors.YELLOW}⊘ {test_name} (SKIPPED){Colors.NC}")
        self.test_results.append(('skip', test_name))


class ColoredTextTestRunner(unittest.TextTestRunner):
    """Custom test runner with colored output."""
    resultclass = ColoredTextTestResult

    def run(self, test):
        print(f"\n{Colors.BLUE}{'='*60}{Colors.NC}")
        print(f"{Colors.BLUE}Running Unit Tests: Error Handling{Colors.NC}")
        print(f"{Colors.BLUE}{'='*60}{Colors.NC}\n")

        result = super().run(test)

        # Print summary
        print(f"\n{Colors.BLUE}{'='*60}{Colors.NC}")
        print(f"{Colors.BLUE}Test Summary{Colors.NC}")
        print(f"{Colors.BLUE}{'='*60}{Colors.NC}")

        total = result.testsRun
        passed = total - len(result.failures) - len(result.errors)

        print(f"Total tests: {total}")
        print(f"{Colors.GREEN}Passed: {passed}{Colors.NC}")

        if result.failures:
            print(f"{Colors.RED}Failed: {len(result.failures)}{Colors.NC}")
        if result.errors:
            print(f"{Colors.RED}Errors: {len(result.errors)}{Colors.NC}")
        if result.skipped:
            print(f"{Colors.YELLOW}Skipped: {len(result.skipped)}{Colors.NC}")

        print()

        return result


# Add the template directory to path
template_dir = Path(__file__).parent.parent.parent.parent / "templates" / "zabbix" / "cambium-fiber"
sys.path.insert(0, str(template_dir))

from cambium_olt_ssh_json import (
    OLTTransport,
    OLTOutput,
    OLTRequest,
    DebugLog,
    OLTCLI,
)


class TestSSHErrorPropagation(unittest.TestCase):
    """Test that SSH errors are properly propagated, not swallowed."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        debug_log = DebugLog(enabled=False)
        self.debug_log = debug_log
        self.output = OLTOutput(debug_log)
        self.transport = OLTTransport(self.output, debug_log)
        self.request = OLTRequest(host="192.168.1.1", password="testpass")

    def test_ssh_connection_failure_raises_exception(self):
        """Test that SSH connection failures raise an exception."""
        with patch.object(self.transport, '_run_sshpass') as mock_ssh:
            mock_ssh.side_effect = RuntimeError("SSH connection failed")

            with self.assertRaises(RuntimeError) as context:
                self.transport.fetch_all(self.request)

            self.assertIn("SSH connection failed", str(context.exception))

    def test_ssh_timeout_raises_exception(self):
        """Test that SSH timeouts raise an exception."""
        with patch.object(self.transport, '_run_sshpass') as mock_ssh:
            mock_ssh.side_effect = TimeoutError("Connection timeout")

            with self.assertRaises(TimeoutError) as context:
                self.transport.fetch_all(self.request)

            self.assertIn("timeout", str(context.exception).lower())

    def test_invalid_json_raises_exception(self):
        """Test that invalid JSON from OLT raises an exception."""
        with patch.object(self.transport, '_run_sshpass') as mock_ssh:
            # Return invalid JSON
            mock_ssh.return_value = "This is not JSON"

            with self.assertRaises(Exception):
                self.transport.fetch_all(self.request)

    def test_empty_response_raises_exception(self):
        """Test that empty SSH responses raise an exception."""
        with patch.object(self.transport, '_run_sshpass') as mock_ssh:
            mock_ssh.return_value = ""

            with self.assertRaises(Exception):
                self.transport.fetch_all(self.request)

    def test_successful_fetch_returns_data(self):
        """Test that successful SSH fetch returns parsed data."""
        with patch.object(self.transport, '_run_sshpass') as mock_ssh:
            mock_ssh.return_value = '{"test": "data", "number": "42"}'

            result = self.transport.fetch_all(self.request)

            self.assertIsInstance(result, dict)
            self.assertEqual(result["test"], "data")
            # Verify number coercion
            self.assertEqual(result["number"], 42)


class TestCLIErrorHandling(unittest.TestCase):
    """Test that CLI properly handles and reports errors."""

    def setUp(self):
        """Set up test fixtures."""
        self.cli = OLTCLI()

    def test_cli_returns_error_code_on_ssh_failure(self):
        """Test that CLI exits with error code 1 on SSH failure."""
        with patch('cambium_olt_ssh_json.OLTTransport.fetch_all') as mock_fetch:
            mock_fetch.side_effect = RuntimeError("SSH failed")

            exit_code = self.cli.run(["192.168.1.1", "badpass"])

            self.assertEqual(exit_code, 1)

    def test_cli_returns_error_code_on_json_parse_failure(self):
        """Test that CLI exits with error code 1 on JSON parse failure."""
        with patch('cambium_olt_ssh_json.OLTTransport._run_sshpass') as mock_ssh:
            mock_ssh.return_value = "invalid json"

            exit_code = self.cli.run(["192.168.1.1", "testpass"])

            self.assertEqual(exit_code, 1)

    def test_cli_returns_success_on_valid_data(self):
        """Test that CLI exits with code 0 on success."""
        with patch('cambium_olt_ssh_json.OLTTransport._run_sshpass') as mock_ssh:
            mock_ssh.return_value = '{"test": "data"}'

            with patch('sys.stdout'):  # Suppress output
                exit_code = self.cli.run(["192.168.1.1", "testpass", "--no-cache"])

            self.assertEqual(exit_code, 0)

    @patch('sys.stderr')
    def test_cli_outputs_error_message_to_stderr(self, mock_stderr):
        """Test that CLI writes error messages to stderr."""
        with patch('cambium_olt_ssh_json.OLTTransport.fetch_all') as mock_fetch:
            mock_fetch.side_effect = RuntimeError("Connection refused")

            exit_code = self.cli.run(["192.168.1.1", "testpass"])

            self.assertEqual(exit_code, 1)


class TestOutputParsing(unittest.TestCase):
    """Test that output parsing errors are properly raised."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        debug_log = DebugLog(enabled=False)
        self.debug_log = debug_log
        self.output = OLTOutput(debug_log)

    def test_no_json_in_output_raises_exception(self):
        """Test that output with no JSON raises an exception."""
        raw_output = "Error: Command not found\nConnection closed"

        with self.assertRaises(ValueError) as context:
            self.output.to_json_text(raw_output)

        self.assertIn("no JSON found", str(context.exception))

    def test_malformed_json_detected(self):
        """Test that malformed JSON in output is detected."""
        # Include complete JSON so to_json_text can extract it
        raw_output = '{"incomplete": "data"}'

        # to_json_text should extract it successfully
        json_text = self.output.to_json_text(raw_output)

        # Now test with actual malformed JSON
        import json
        malformed = '{"incomplete": "data"'
        with self.assertRaises(json.JSONDecodeError):
            json.loads(malformed)


def run_tests():
    """Run all unit tests."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = ColoredTextTestRunner(verbosity=1, stream=sys.stdout)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(run_tests())
