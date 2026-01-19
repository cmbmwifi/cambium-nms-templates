#!/usr/bin/env python3
"""
Template validator for Zabbix integration tests.

Validates template import, structure, and configuration.
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional

# Support both package imports and direct script execution
try:
    from ..base.api_helpers import ZabbixAPIClient
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from base.api_helpers import ZabbixAPIClient



class ValidationResult:
    """Container for validation results."""

    def __init__(self, passed: bool, message: str = "", details: Optional[Dict] = None):
        """
        Initialize validation result.

        Args:
            passed: Whether validation passed
            message: Result message
            details: Optional details dict
        """
        self.passed = passed
        self.message = message
        self.details = details or {}


class TemplateValidator:
    """Validates Zabbix template configuration and structure."""

    def __init__(self, api_client: ZabbixAPIClient):
        """
        Initialize template validator.

        Args:
            api_client: ZabbixAPIClient instance
        """
        self.api = api_client

    def validate_import(self, template_name: str) -> ValidationResult:
        """
        Validate template was successfully imported.

        Args:
            template_name: Template name to check

        Returns:
            ValidationResult
        """
        template = self.api.get_template(template_name)

        if template:
            return ValidationResult(
                True,
                f"Template '{template_name}' found",
                {"template_id": template.get("templateid")}
            )
        else:
            return ValidationResult(False, f"Template '{template_name}' not found")

    def validate_discovery_rules(self, template_name: str) -> ValidationResult:
        """
        Validate discovery rules exist for template.

        Args:
            template_name: Template name

        Returns:
            ValidationResult
        """
        template = self.api.get_template(template_name)
        if not template:
            return ValidationResult(False, "Template not found")

        rules = self.api.get_discovery_rules(template["templateid"])

        if rules:
            rule_names = [r["name"] for r in rules]
            return ValidationResult(
                True,
                f"Found {len(rules)} discovery rule(s)",
                {"rules": rule_names}
            )
        else:
            return ValidationResult(False, "No discovery rules found")

    def validate_item_count(self, template_name: str, min_expected: int) -> ValidationResult:
        """
        Validate minimum number of items exist.

        Args:
            template_name: Template name
            min_expected: Minimum expected item count

        Returns:
            ValidationResult
        """
        template = self.api.get_template(template_name)
        if not template:
            return ValidationResult(False, "Template not found")

        items = self.api.get_items(template["templateid"])
        item_count = len(items)

        if item_count >= min_expected:
            return ValidationResult(
                True,
                f"Found {item_count} items (>= {min_expected})",
                {"count": item_count}
            )
        else:
            return ValidationResult(
                False,
                f"Found {item_count} items (expected >= {min_expected})",
                {"count": item_count, "expected": min_expected}
            )

    def get_template_id(self, template_name: str) -> Optional[str]:
        """
        Get template ID by name.

        Args:
            template_name: Template name

        Returns:
            Template ID or None
        """
        template = self.api.get_template(template_name)
        return template.get("templateid") if template else None
