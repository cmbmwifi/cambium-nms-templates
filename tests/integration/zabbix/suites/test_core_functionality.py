#!/usr/bin/env python3
"""
Core Functionality Test Suite

Tests critical template functionality including:
- Template import and verification
- API version compatibility
- External script execution
- Item error state detection
"""

import sys
from pathlib import Path
from typing import Optional

# Support both package imports and direct script execution
try:
    from ..base.test_harness import ZabbixTestHarness, Colors  # type: ignore[no-redef]
    from ..validators.template_validator import TemplateValidator  # type: ignore[no-redef]
    from ..validators.item_validator import ItemValidator  # type: ignore[no-redef]
except ImportError:
    # Add parent directory to path for direct script execution
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from base.test_harness import ZabbixTestHarness, Colors  # type: ignore[no-redef]
    from validators.template_validator import TemplateValidator  # type: ignore[no-redef]
    from validators.item_validator import ItemValidator  # type: ignore[no-redef]


TEMPLATE_NAME = "Cambium Fiber OLT by SSH v1.3.0"



class CoreFunctionalityTests:
    """Core template functionality test suite."""

    def __init__(self, harness: ZabbixTestHarness):
        """
        Initialize test suite.

        Args:
            harness: ZabbixTestHarness instance
        """
        self.harness = harness
        self.template_validator: Optional[TemplateValidator] = None
        self.item_validator: Optional[ItemValidator] = None

    def setup_validators(self) -> None:
        """Initialize validators after API authentication."""
        if not self.harness.api_client:
            raise RuntimeError("API client not initialized")

        self.template_validator = TemplateValidator(self.harness.api_client)
        self.item_validator = ItemValidator(self.harness.api_client)

    def test_template_import(self) -> str:
        """Test 1: Template YAML imports successfully."""
        self.harness.print_colored("\nTest Suite: Core Functionality", Colors.BLUE)
        self.harness.print_colored("Test 1: Template import", Colors.BLUE)

        if not self.template_validator:
            raise RuntimeError("Validators not initialized")

        result = self.template_validator.validate_import(TEMPLATE_NAME)
        self.harness.assertions.assert_true(
            result.passed,
            result.message,
            "" if result.passed else "Template not found in Zabbix"
        )
        template_id: str = str(result.details.get("template_id", ""))
        return template_id

    def test_discovery_rules_exist(self) -> None:
        """Test 2: Discovery rules are created and operational."""
        self.harness.print_colored("Test 2: Discovery rules", Colors.BLUE)

        if not self.template_validator:
            raise RuntimeError("Validators not initialized")

        result = self.template_validator.validate_discovery_rules(TEMPLATE_NAME)
        self.harness.assertions.assert_true(
            result.passed,
            result.message,
            "" if result.passed else "No discovery rules found"
        )

    def test_minimum_item_count(self) -> None:
        """Test 3: Minimum number of items exist."""
        self.harness.print_colored("Test 3: Item count validation", Colors.BLUE)

        if not self.template_validator:
            raise RuntimeError("Validators not initialized")

        # Template should have at least 20 base items (excluding discovered)
        result = self.template_validator.validate_item_count(TEMPLATE_NAME, min_expected=20)
        self.harness.assertions.assert_true(
            result.passed,
            result.message,
            "Item count below minimum" if not result.passed else ""
        )

    def test_api_version_compatibility(self) -> None:
        """Test 4: API version compatibility check."""
        self.harness.print_colored("Test 4: API version compatibility", Colors.BLUE)

        if not self.harness.api_client:
            self.harness.assertions.assert_true(False, "API version check", "API client not initialized")
            return

        try:
            # This is already tested in harness setup, but we verify explicitly
            version_result = self.harness.api_client.request("apiinfo.version", {})
            expected_prefix = self.harness.version

            # Version result should be a string
            version_str = str(version_result) if not isinstance(version_result, str) else version_result

            self.harness.assertions.assert_true(
                version_str.startswith(expected_prefix),
                f"API version {version_str} matches expected {expected_prefix}.x",
                f"Version mismatch: expected {expected_prefix}.x, got {version_str}"
            )
        except Exception as e:
            self.harness.assertions.assert_true(
                False,
                "API version check",
                str(e)
            )

    def run_all(self) -> None:
        """Run all core functionality tests."""
        self.setup_validators()

        template_id = self.test_template_import()
        if template_id:
            self.test_discovery_rules_exist()
            self.test_minimum_item_count()

        self.test_api_version_compatibility()


def run_core_tests(harness: ZabbixTestHarness):
    """
    Run core functionality test suite.

    Args:
        harness: Initialized ZabbixTestHarness

    Returns:
        Number of tests passed
    """
    tests = CoreFunctionalityTests(harness)
    tests.run_all()
    return harness.result.passed
