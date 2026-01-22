#!/usr/bin/env python3
"""
Item validator for Zabbix integration tests.

Validates item states, errors, and configuration.
"""

import sys
from pathlib import Path
from typing import List, NamedTuple

# Support both package imports and direct script execution
try:
    from ..base.api_helpers import ZabbixAPIClient  # type: ignore[no-redef]
    from .template_validator import ValidationResult  # type: ignore[no-redef]
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from base.api_helpers import ZabbixAPIClient  # type: ignore[no-redef]
    from validators.template_validator import ValidationResult  # type: ignore[no-redef]


class ItemError(NamedTuple):
    """Container for item error information."""
    itemid: str
    name: str
    key: str
    error: str


class ItemValidator:
    """Validates Zabbix item configuration and state."""

    def __init__(self, api_client: ZabbixAPIClient):
        """
        Initialize item validator.

        Args:
            api_client: ZabbixAPIClient instance
        """
        self.api = api_client

    def check_item_states(self, host_id: str) -> List[ItemError]:
        """
        Check for items in unsupported/error state.

        Args:
            host_id: Host ID to check

        Returns:
            List of ItemError instances
        """
        error_items = self.api.get_items_with_errors(host_id)

        return [
            ItemError(
                itemid=item.get("itemid", ""),
                name=item.get("name", ""),
                key=item.get("key_", ""),
                error=item.get("error", "")
            )
            for item in error_items
        ]

    def validate_all_items_supported(self, host_id: str) -> ValidationResult:
        """
        Validate all items are in supported state.

        Args:
            host_id: Host ID to check

        Returns:
            ValidationResult
        """
        errors = self.check_item_states(host_id)

        if not errors:
            return ValidationResult(True, "All items are in supported state")
        else:
            error_summary = ", ".join([e.name for e in errors[:3]])
            if len(errors) > 3:
                error_summary += f" (and {len(errors) - 3} more)"

            return ValidationResult(
                False,
                f"{len(errors)} item(s) with errors: {error_summary}",
                {"errors": [e._asdict() for e in errors]}
            )

    def validate_calculated_items(self, host_id: str, expected_keys: List[str]) -> ValidationResult:
        """
        Validate calculated items exist.

        Args:
            host_id: Host ID to check
            expected_keys: List of expected item keys

        Returns:
            ValidationResult
        """
        all_items = self.api.get_items(host_id)
        item_keys = {item.get("key_") for item in all_items}

        missing_keys = [key for key in expected_keys if key not in item_keys]

        if not missing_keys:
            return ValidationResult(
                True,
                f"All {len(expected_keys)} calculated items exist"
            )
        else:
            return ValidationResult(
                False,
                f"Missing {len(missing_keys)} calculated item(s): {', '.join(missing_keys)}",
                {"missing": missing_keys}
            )
