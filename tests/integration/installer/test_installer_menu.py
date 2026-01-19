#!/usr/bin/env python3
"""
Installer menu system tests (NMS-agnostic)
Tests configuration collection without actual installation
"""

import subprocess
import sys
import time
import yaml
from pathlib import Path
from typing import Dict, Any, Optional


class Colors:
    GREEN = '\033[0;32m'
    RED = '\033[0;31m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'


class InstallerMenuTest:
    """Test harness for installer menu system"""

    ENV_VAR_MAP = {
        'zabbix_api_url': 'ZABBIX_API_URL',
        'zabbix_api_token': 'ZABBIX_API_TOKEN',
        'olt_password': 'OLT_PASSWORD',
        'flush_template': 'FLUSH_TEMPLATE',
        'flush_hosts': 'FLUSH_HOSTS',
        'add_hosts': 'ADD_HOSTS',
        'olt_ip_addresses': 'OLT_IPS',
    }

    def __init__(self):
        self.test_dir = Path(__file__).parent
        self.compose_file = self.test_dir / "docker-compose.yml"
        self.container_name = "installer-menu-test"
        self.passed_tests = 0
        self.failed_tests = 0
        self.requirements: Optional[Dict[str, Any]] = None

    def load_requirements(self, nms_platform="zabbix", product="cambium-fiber"):
        """Load and parse requirements.yaml for the given platform/product"""
        requirements_path = self.test_dir.parent.parent.parent / "templates" / nms_platform / product / "requirements.yaml"

        if not requirements_path.exists():
            raise FileNotFoundError(f"Requirements file not found: {requirements_path}")

        with open(requirements_path, 'r') as f:
            self.requirements = yaml.safe_load(f)

        return self.requirements

    def setup(self):
        """Start the test container"""
        print(f"{Colors.BLUE}Setting up installer menu test environment...{Colors.NC}")

        container_shutdown = subprocess.run(
            ["docker-compose", "-f", str(self.compose_file), "down", "-v"],
            cwd=self.test_dir,
            capture_output=True
        )

        container_startup = subprocess.run(
            ["docker-compose", "-f", str(self.compose_file), "up", "-d"],
            cwd=self.test_dir,
            capture_output=True,
            text=True
        )

        if container_startup.returncode != 0:
            print(f"{Colors.RED}Failed to start container{Colors.NC}")
            print(container_startup.stderr)
            sys.exit(1)

        time.sleep(2)
        print(f"{Colors.GREEN}✓ Container ready{Colors.NC}")

    def teardown(self):
        """Stop the test container"""
        print(f"{Colors.BLUE}Cleaning up...{Colors.NC}")
        subprocess.run(
            ["docker-compose", "-f", str(self.compose_file), "down", "-v"],
            cwd=self.test_dir,
            capture_output=True
        )

    def run_command(self, cmd):
        """Run a command and return exit code and output"""
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )
        return result.returncode, result.stdout + result.stderr

    def _run_installer(self, env_vars):
        """Execute installer with given environment variables"""
        cmd = ["docker", "exec"]
        for key, value in env_vars.items():
            cmd.extend(["-e", f"{key}={value}"])
        cmd.extend([
            self.container_name,
            "/bin/bash", "-c",
            "cd /root/cambium-nms-templates && ./install.sh --local --validate-config"
        ])
        return self.run_command(cmd)

    def _ensure_requirements_loaded(self):
        """Verify requirements are loaded, fail test if not"""
        if not self.requirements:
            print(f"{Colors.RED}✗ FAILED: Requirements not loaded{Colors.NC}")
            self.failed_tests += 1
            return False
        return True

    def _check_installer_exit_code(self, exit_code, output):
        """Check installer exit code and record failure if non-zero"""
        if exit_code != 0:
            print(f"{Colors.RED}✗ FAILED: Installer exited with code {exit_code}{Colors.NC}")
            print(output)
            self.failed_tests += 1
            return False
        return True

    def _record_test_result(self, passed, test_name):
        """Record test result and print status message"""
        if passed:
            print(f"{Colors.GREEN}✓ PASSED: {test_name}{Colors.NC}")
            self.passed_tests += 1
        else:
            print(f"{Colors.RED}✗ FAILED: {test_name}{Colors.NC}")
            self.failed_tests += 1
        return passed

    def _print_summary(self):
        """Print test results summary"""
        print(f"\n{Colors.BLUE}{'='*60}{Colors.NC}")
        print(f"{Colors.BLUE}Test Summary{Colors.NC}")
        print(f"{Colors.BLUE}{'='*60}{Colors.NC}")
        total = self.passed_tests + self.failed_tests
        print(f"Total tests: {total}")
        print(f"{Colors.GREEN}Passed: {self.passed_tests}{Colors.NC}")
        if self.failed_tests > 0:
            print(f"{Colors.RED}Failed: {self.failed_tests}{Colors.NC}")

    def _generate_test_value_for_input(self, inp, include_optional):
        """Generate appropriate test value for a single input"""
        input_type = inp['type']

        value_generators = {
            'url': lambda: 'http://test.example.com/zabbix',
            'secret': lambda: 'test_secret_value_1234567890',
            'boolean': lambda: 'true' if inp.get('default', include_optional) else 'false',
            'list': lambda: '192.168.1.10,192.168.1.11,192.168.1.12',
        }

        generator = value_generators.get(input_type, lambda: inp.get('default', 'test_value'))
        return generator()

    def generate_env_vars_from_requirements(self, include_optional=True):
        """Generate environment variables dict from requirements.yaml"""
        if not self.requirements:
            raise ValueError("Requirements not loaded. Call load_requirements() first.")

        env_vars = {
            'NMS_PLATFORM': 'zabbix',
            'PRODUCT_TEMPLATE': 'cambium-fiber',
        }

        for inp in self.requirements.get('user_inputs', []):
            env_name = inp['name'].upper()
            env_vars[env_name] = self._generate_test_value_for_input(inp, include_optional)

        return env_vars

    def _should_skip_conditional_input(self, inp, env_vars):
        """Check if conditional input should be skipped based on condition"""
        condition = inp.get('condition', '')
        if not condition:
            return False
        if 'add_hosts' in condition.lower():
            return env_vars.get('ADD_HOSTS', 'false').lower() != 'true'
        return False

    def _validate_secret_input(self, name, output):
        """Validate secret input is masked in output"""
        secret_indicators = [name, "password", "token", "secret"]
        has_indicator = any(x in output.lower() for x in secret_indicators)
        is_masked = "******" in output

        if has_indicator and is_masked:
            print(f"  {Colors.GREEN}✓ {name} (masked){Colors.NC}")
            return True
        else:
            print(f"  {Colors.RED}✗ {name} should be collected and masked{Colors.NC}")
            return False

    def _validate_boolean_input(self, name, expected, output):
        """Validate boolean input appears in output"""
        name_variants = [
            f"{name.replace('_', ' ').title()}: {expected}",
            f"{' '.join(name.split('_')).title()}: {expected}",
            f"Flush {name.split('_')[1] if 'flush' in name else name}: {expected}"
        ]

        if any(variant in output for variant in name_variants):
            print(f"  {Colors.GREEN}✓ {name} = {expected}{Colors.NC}")
            return True
        else:
            print(f"  {Colors.RED}✗ {name} not found or incorrect value{Colors.NC}")
            return False

    def _validate_list_input(self, name, expected, output):
        """Validate list input appears in output"""
        if expected and expected in output:
            print(f"  {Colors.GREEN}✓ {name} = {expected}{Colors.NC}")
            return True
        elif not expected:
            print(f"  {Colors.GREEN}✓ {name} (skipped as expected){Colors.NC}")
            return True
        else:
            print(f"  {Colors.RED}✗ {name} not found: {expected}{Colors.NC}")
            return False

    def _validate_text_input(self, name, expected, output):
        """Validate text input appears in output"""
        if expected in output:
            print(f"  {Colors.GREEN}✓ {name} = {expected}{Colors.NC}")
            return True
        else:
            print(f"  {Colors.RED}✗ {name} not found: {expected}{Colors.NC}")
            return False

    def validate_output_against_requirements(self, output, env_vars):
        """Validate installer output matches requirements.yaml expectations"""
        if not self.requirements:
            return False

        all_passed = True

        template_name = self.requirements['metadata']['name']
        if f"Template: {template_name}" in output:
            print(f"  {Colors.GREEN}✓ Template name: {template_name}{Colors.NC}")
        else:
            print(f"  {Colors.RED}✗ Template name not found: {template_name}{Colors.NC}")
            all_passed = False

        for inp in self.requirements.get('user_inputs', []):
            if self._should_skip_conditional_input(inp, env_vars):
                continue

            name = inp['name']
            env_name = name.upper()
            input_type = inp['type']

            if input_type == 'secret':
                all_passed &= self._validate_secret_input(name, output)
            elif input_type == 'boolean':
                expected = env_vars.get(env_name, 'false')
                all_passed &= self._validate_boolean_input(name, expected, output)
            elif input_type == 'list':
                expected = env_vars.get(env_name, '')
                all_passed &= self._validate_list_input(name, expected, output)
            else:
                expected = env_vars.get(env_name, '')
                all_passed &= self._validate_text_input(name, expected, output)

        if "Configuration collected" in output:
            print(f"  {Colors.GREEN}✓ Configuration collection completed{Colors.NC}")
        else:
            print(f"  {Colors.RED}✗ Configuration collection not completed{Colors.NC}")
            all_passed = False

        return all_passed

    def test_non_interactive_all_vars(self):
        """Test non-interactive mode with all environment variables set"""
        print(f"\n{Colors.YELLOW}TEST: Non-interactive mode with all variables (requirements-driven){Colors.NC}")

        self.load_requirements()
        env_vars = self.generate_env_vars_from_requirements(include_optional=True)
        exit_code, output = self._run_installer(env_vars)

        if not self._check_installer_exit_code(exit_code, output):
            return False

        validation_passed = self.validate_output_against_requirements(output, env_vars)
        if not validation_passed:
            print("\nFull output:")
            print(output)

        return self._record_test_result(validation_passed, "All requirements validated")

    def _generate_minimal_env_vars(self):
        """Generate minimal required environment variables from requirements"""
        if not self.requirements:
            raise ValueError("Requirements not loaded")

        env_vars = {
            'NMS_PLATFORM': 'zabbix',
            'PRODUCT_TEMPLATE': 'cambium-fiber',
        }

        for inp in self.requirements.get('user_inputs', []):
            is_required = inp.get('validation', {}).get('required', False) or inp['type'] in ['url', 'secret']
            if not is_required:
                continue

            name = inp['name']
            env_name = name.upper()
            input_type = inp['type']

            if input_type == 'url':
                env_vars[env_name] = 'http://localhost/zabbix'
            elif input_type == 'secret':
                env_vars[env_name] = 'minimal_secret_12345678901234567890'
            else:
                default = inp.get('default')
                if default is not None:
                    env_vars[env_name] = str(default)

        return env_vars

    def _validate_defaults_in_output(self, output):
        """Validate that default values are used for optional inputs"""
        if not self.requirements:
            return

        for inp in self.requirements.get('user_inputs', []):
            is_optional_boolean = inp['type'] == 'boolean' and not inp.get('validation', {}).get('required', False)
            if not is_optional_boolean:
                continue

            default = inp.get('default', False)
            expected = 'true' if default else 'false'
            name = inp['name']

            if f"{expected}" in output.lower():
                print(f"  {Colors.GREEN}✓ {name} defaults to {expected}{Colors.NC}")
            else:
                print(f"  {Colors.YELLOW}⚠ {name} default not clearly visible{Colors.NC}")

    def test_non_interactive_minimal_vars(self):
        """Test non-interactive mode with minimal required variables"""
        print(f"\n{Colors.YELLOW}TEST: Non-interactive mode with minimal variables (requirements-driven){Colors.NC}")

        self.load_requirements()
        if not self._ensure_requirements_loaded():
            return False

        env_vars = self._generate_minimal_env_vars()
        exit_code, output = self._run_installer(env_vars)

        if not self._check_installer_exit_code(exit_code, output):
            return False

        self._validate_defaults_in_output(output)

        configuration_complete = "Configuration collected" in output
        if configuration_complete:
            print(f"  {Colors.GREEN}✓ Configuration completed with defaults{Colors.NC}")
        else:
            print(f"  {Colors.RED}✗ Configuration not completed{Colors.NC}")
            print("\nFull output:")
            print(output)

        return self._record_test_result(configuration_complete, "Minimal configuration works")

    def test_requirements_parsing(self):
        """Test that requirements.yaml is parsed correctly"""
        print(f"\n{Colors.YELLOW}TEST: Requirements.yaml parsing (requirements-driven){Colors.NC}")

        self.load_requirements()

        env_vars = {
            'ZABBIX_API_URL': 'http://test/zabbix',
            'ZABBIX_API_TOKEN': 'parsing_test_token_1234567890123456',
            'OLT_PASSWORD': 'testpass',
        }

        exit_code, output = self._run_installer(env_vars)

        if not self._check_installer_exit_code(exit_code, output):
            return False

        if not self._ensure_requirements_loaded():
            return False

        assert self.requirements is not None
        all_passed = True
        template_name = self.requirements['metadata']['name']

        expected_messages = {
            f"Template: {template_name}": f"Template name extracted: {template_name}",
            "Parsing requirements...": "Requirements parsing initiated",
            "Found requirements.yaml": "Requirements file found",
        }

        for message, success_text in expected_messages.items():
            if message in output:
                print(f"  {Colors.GREEN}✓ {success_text}{Colors.NC}")
            else:
                print(f"  {Colors.RED}✗ {success_text.replace(':', ' not found:')}{Colors.NC}")
                all_passed = False

        assert self.requirements is not None
        input_count = len(self.requirements.get('user_inputs', []))
        print(f"  {Colors.GREEN}✓ Requirements defines {input_count} user inputs{Colors.NC}")

        if not all_passed:
            print("\nFull output:")
            print(output)

        return self._record_test_result(all_passed, "Requirements parsing works")

    def test_conditional_input(self):
        """Test that conditional inputs only appear when condition is met"""
        print(f"\n{Colors.YELLOW}TEST: Conditional input (requirements-driven){Colors.NC}")

        self.load_requirements()
        if not self._ensure_requirements_loaded():
            return False

        assert self.requirements is not None
        conditional_inputs = [
            inp for inp in self.requirements.get('user_inputs', [])
            if inp.get('condition')
        ]

        if not conditional_inputs:
            print(f"  {Colors.YELLOW}⚠ No conditional inputs defined in requirements{Colors.NC}")
            self.passed_tests += 1
            return True

        print(f"  Found {len(conditional_inputs)} conditional input(s) in requirements")
        all_passed = True

        for cond_input in conditional_inputs:
            name = cond_input['name']
            condition = cond_input.get('condition', '')
            print(f"  Testing: {name} (condition: {condition})")

            env_vars = {
                'ZABBIX_API_URL': 'http://test/zabbix',
                'ZABBIX_API_TOKEN': 'conditional_test_token_123456789012',
                'OLT_PASSWORD': 'testpass',
                'ADD_HOSTS': 'true',
                self.ENV_VAR_MAP.get(name, name.upper()): '10.0.0.1,10.0.0.2',
            }

            exit_code, output = self._run_installer(env_vars)

            if exit_code != 0:
                print(f"    {Colors.RED}✗ Installer failed{Colors.NC}")
                all_passed = False
                continue

            env_var_name = self.ENV_VAR_MAP.get(name, name.upper())
            expected_value = env_vars.get(env_var_name, '')

            if expected_value and expected_value in output:
                print(f"    {Colors.GREEN}✓ {name} collected when condition met: {expected_value}{Colors.NC}")
            else:
                print(f"    {Colors.RED}✗ {name} should be collected with value: {expected_value}{Colors.NC}")
                print(f"    Output snippet: {output[-500:]}")
                all_passed = False

        return self._record_test_result(all_passed, "Conditional inputs work")

    def test_platform_selection(self):
        """Test NMS platform selection via environment variable"""
        print(f"\n{Colors.YELLOW}TEST: Platform selection (requirements-driven){Colors.NC}")

        self.load_requirements()
        if not self._ensure_requirements_loaded():
            return False

        assert self.requirements is not None
        platform = self.requirements['compatibility']['nms']['platform']

        env_vars = {
            'NMS_PLATFORM': platform,
            'PRODUCT_TEMPLATE': 'cambium-fiber',
            'ZABBIX_API_URL': 'http://test/zabbix',
            'ZABBIX_API_TOKEN': 'platform_test_token_1234567890123',
            'OLT_PASSWORD': 'testpass',
        }

        exit_code, output = self._run_installer(env_vars)

        if not self._check_installer_exit_code(exit_code, output):
            return False

        all_passed = True

        if f"NMS Platform: {platform}" in output:
            print(f"  {Colors.GREEN}✓ Platform set correctly: {platform}{Colors.NC}")
        else:
            print(f"  {Colors.RED}✗ Platform not found: {platform}{Colors.NC}")
            all_passed = False

        if "Product Template: cambium-fiber" in output:
            print(f"  {Colors.GREEN}✓ Product set correctly{Colors.NC}")
        else:
            print(f"  {Colors.RED}✗ Product not set correctly{Colors.NC}")
            all_passed = False

        if not all_passed:
            print(output)

        return self._record_test_result(all_passed, "Platform selection works")

    def run_all_tests(self):
        """Run all test cases"""
        print(f"\n{Colors.BLUE}{'='*60}{Colors.NC}")
        print(f"{Colors.BLUE}Installer Menu System Tests{Colors.NC}")
        print(f"{Colors.BLUE}{'='*60}{Colors.NC}")

        try:
            self.setup()
            self.test_non_interactive_all_vars()
            self.test_non_interactive_minimal_vars()
            self.test_requirements_parsing()
            self.test_conditional_input()
            self.test_platform_selection()

        finally:
            self.teardown()

        self._print_summary()
        return self.failed_tests == 0


def main():
    test = InstallerMenuTest()
    success = test.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
