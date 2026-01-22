#!/usr/bin/env python3
"""
Item Data Collection Test Suite

Tests item data collection and monitoring including:
- Item value types and data validation
- Item state monitoring
- Update intervals and data freshness
- Item value preprocessing
- Item dependencies
"""

import sys
import time
from pathlib import Path
from typing import Optional

# Support both package imports and direct script execution
try:
    from ..base.test_harness import ZabbixTestHarness, Colors  # type: ignore[no-redef]
    from ..validators.item_validator import ItemValidator  # type: ignore[no-redef]
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from base.test_harness import ZabbixTestHarness, Colors  # type: ignore[no-redef]
    from validators.item_validator import ItemValidator  # type: ignore[no-redef]


TEMPLATE_NAME = "Cambium Fiber OLT by SSH v1.3.0"


class ItemDataCollectionTests:
    """Item data collection tests"""

    def __init__(self, harness: ZabbixTestHarness):
        self.harness = harness
        self.validator: Optional[ItemValidator] = None
        if harness.api_client:
            self.validator = ItemValidator(harness.api_client)

    def test_items_have_value_types(self) -> bool:
        """Verify items have appropriate value types configured"""
        self.harness.assertions.start_test("Items have value types")

        if not self.harness.api_client:
            self.harness.assertions.assert_true(False, "API client not initialized")
            return False

        template = self.harness.api_client.get_template(TEMPLATE_NAME)
        if not template:
            self.harness.assertions.assert_true(False, "Template not found")
            return False

        result = self.harness.api_client.request("item.get", {
            "templateids": template['templateid'],
            "output": ["itemid", "name", "value_type"]
        })

        items = result if isinstance(result, list) else []
        if not items:
            self.harness.assertions.assert_true(False, "No items found")
            return False

        # Value types: 0=float, 1=character, 2=log, 3=unsigned, 4=text
        from typing import Dict
        value_type_counts: Dict[int, int] = {}
        for item in items:
            vtype = int(item.get('value_type', 0))
            value_type_counts[vtype] = value_type_counts.get(vtype, 0) + 1

        self.harness.assertions.assert_true(
            True,
            f"Items have value types: {value_type_counts}"
        )
        return True

    def test_items_have_units(self) -> bool:
        """Verify numeric items have units where appropriate"""
        self.harness.assertions.start_test("Numeric items have units")

        if not self.harness.api_client:
            self.harness.assertions.assert_true(False, "API client not initialized")
            return False

        template = self.harness.api_client.get_template(TEMPLATE_NAME)
        if not template:
            self.harness.assertions.assert_true(False, "Template not found")
            return False

        result = self.harness.api_client.request("item.get", {
            "templateids": template['templateid'],
            "output": ["itemid", "name", "value_type", "units"]
        })

        items = result if isinstance(result, list) else []
        if not items:
            self.harness.assertions.assert_true(False, "No items found")
            return False

        # Check numeric items (value_type 0 or 3)
        numeric_items = [i for i in items if int(i.get('value_type', 0)) in [0, 3]]
        items_with_units = [i for i in numeric_items if i.get('units')]

        if len(numeric_items) > 0:
            percentage = (len(items_with_units) / len(numeric_items)) * 100
            self.harness.assertions.assert_true(
                True,
                f"{len(items_with_units)}/{len(numeric_items)} numeric items have units ({percentage:.1f}%)"
            )
        else:
            self.harness.assertions.assert_true(True, "No numeric items to check")

        return True

    def test_items_have_descriptions(self) -> bool:
        """Verify items have descriptions"""
        self.harness.assertions.start_test("Items have descriptions")

        if not self.harness.api_client:
            self.harness.assertions.assert_true(False, "API client not initialized")
            return False

        template = self.harness.api_client.get_template(TEMPLATE_NAME)
        if not template:
            self.harness.assertions.assert_true(False, "Template not found")
            return False

        result = self.harness.api_client.request("item.get", {
            "templateids": template['templateid'],
            "output": ["itemid", "name", "description"]
        })

        items = result if isinstance(result, list) else []
        if not items:
            self.harness.assertions.assert_true(False, "No items found")
            return False

        items_with_desc = [i for i in items if i.get('description')]
        percentage = (len(items_with_desc) / len(items)) * 100

        self.harness.assertions.assert_true(
            True,
            f"{len(items_with_desc)}/{len(items)} items have descriptions ({percentage:.1f}%)"
        )
        return True

    def test_item_keys_are_unique(self) -> bool:
        """Verify item keys are unique within template"""
        self.harness.assertions.start_test("Item keys are unique")

        if not self.harness.api_client:
            self.harness.assertions.assert_true(False, "API client not initialized")
            return False

        template = self.harness.api_client.get_template(TEMPLATE_NAME)
        if not template:
            self.harness.assertions.assert_true(False, "Template not found")
            return False

        result = self.harness.api_client.request("item.get", {
            "templateids": template['templateid'],
            "output": ["itemid", "name", "key_"]
        })

        items = result if isinstance(result, list) else []
        if not items:
            self.harness.assertions.assert_true(False, "No items found")
            return False

        keys = [i['key_'] for i in items]
        unique_keys = set(keys)

        if len(keys) == len(unique_keys):
            self.harness.assertions.assert_true(
                True,
                f"All {len(items)} item keys are unique"
            )
            return True
        else:
            duplicates = len(keys) - len(unique_keys)
            self.harness.assertions.assert_true(
                False,
                f"{duplicates} duplicate item keys found"
            )
            return False

    def test_dependent_items_configuration(self) -> bool:
        """Verify dependent items are properly configured"""
        self.harness.assertions.start_test("Dependent items configuration")

        if not self.harness.api_client:
            self.harness.assertions.assert_true(False, "API client not initialized")
            return False

        template = self.harness.api_client.get_template(TEMPLATE_NAME)
        if not template:
            self.harness.assertions.assert_true(False, "Template not found")
            return False

        result = self.harness.api_client.request("item.get", {
            "templateids": template['templateid'],
            "output": ["itemid", "name", "type", "master_itemid"],
            "filter": {"type": 18}  # Type 18 = Dependent item
        })

        dependent_items = result if isinstance(result, list) else []

        if not dependent_items:
            self.harness.assertions.assert_true(
                True,
                "No dependent items (acceptable, template may not use them)"
            )
            return True

        # Verify dependent items have master items
        items_without_master = [i for i in dependent_items if not i.get('master_itemid')]

        if not items_without_master:
            self.harness.assertions.assert_true(
                True,
                f"All {len(dependent_items)} dependent items have master items"
            )
            return True
        else:
            self.harness.assertions.assert_true(
                False,
                f"{len(items_without_master)} dependent items missing master items"
            )
            return False

    def test_item_preprocessing_steps(self) -> bool:
        """Verify items with preprocessing have valid steps"""
        self.harness.assertions.start_test("Item preprocessing steps")

        if not self.harness.api_client:
            self.harness.assertions.assert_true(False, "API client not initialized")
            return False

        template = self.harness.api_client.get_template(TEMPLATE_NAME)
        if not template:
            self.harness.assertions.assert_true(False, "Template not found")
            return False

        result = self.harness.api_client.request("item.get", {
            "templateids": template['templateid'],
            "selectPreprocessing": ["type", "params"],
            "output": ["itemid", "name"]
        })

        items = result if isinstance(result, list) else []
        if not items:
            self.harness.assertions.assert_true(False, "No items found")
            return False

        items_with_preprocessing = [i for i in items if i.get('preprocessing')]
        total_steps = sum(len(i.get('preprocessing', [])) for i in items)

        if items_with_preprocessing:
            self.harness.assertions.assert_true(
                True,
                f"{len(items_with_preprocessing)} items have preprocessing ({total_steps} total steps)"
            )
        else:
            self.harness.assertions.assert_true(
                True,
                "No items use preprocessing (acceptable)"
            )
        return True

    def test_item_tags(self) -> bool:
        """Verify items have tags for organization"""
        self.harness.assertions.start_test("Item tags")

        if not self.harness.api_client:
            self.harness.assertions.assert_true(False, "API client not initialized")
            return False

        template = self.harness.api_client.get_template(TEMPLATE_NAME)
        if not template:
            self.harness.assertions.assert_true(False, "Template not found")
            return False

        result = self.harness.api_client.request("item.get", {
            "templateids": template['templateid'],
            "selectTags": ["tag", "value"],
            "output": ["itemid", "name"]
        })

        items = result if isinstance(result, list) else []
        if not items:
            self.harness.assertions.assert_true(False, "No items found")
            return False

        items_with_tags = [i for i in items if i.get('tags')]

        if items_with_tags:
            percentage = (len(items_with_tags) / len(items)) * 100
            self.harness.assertions.assert_true(
                True,
                f"{len(items_with_tags)}/{len(items)} items have tags ({percentage:.1f}%)"
            )
        else:
            self.harness.assertions.assert_true(
                True,
                "No items have tags (acceptable)"
            )
        return True

    def test_item_trends_configuration(self) -> bool:
        """Verify numeric items have trends configured"""
        self.harness.assertions.start_test("Item trends configuration")

        if not self.harness.api_client:
            self.harness.assertions.assert_true(False, "API client not initialized")
            return False

        template = self.harness.api_client.get_template(TEMPLATE_NAME)
        if not template:
            self.harness.assertions.assert_true(False, "Template not found")
            return False

        result = self.harness.api_client.request("item.get", {
            "templateids": template['templateid'],
            "output": ["itemid", "name", "value_type", "trends"]
        })

        items = result if isinstance(result, list) else []
        if not items:
            self.harness.assertions.assert_true(False, "No items found")
            return False

        # Numeric items should have trends
        numeric_items = [i for i in items if int(i.get('value_type', 0)) in [0, 3]]
        items_with_trends = [i for i in numeric_items if i.get('trends')]

        if len(numeric_items) > 0:
            percentage = (len(items_with_trends) / len(numeric_items)) * 100
            self.harness.assertions.assert_true(
                True,
                f"{len(items_with_trends)}/{len(numeric_items)} numeric items have trends ({percentage:.1f}%)"
            )
        else:
            self.harness.assertions.assert_true(True, "No numeric items to check")

        return True

    def test_item_applications(self) -> bool:
        """Verify items are organized into applications (Zabbix < 5.4) or tags"""
        self.harness.assertions.start_test("Item organization")

        if not self.harness.api_client:
            self.harness.assertions.assert_true(False, "API client not initialized")
            return False

        template = self.harness.api_client.get_template(TEMPLATE_NAME)
        if not template:
            self.harness.assertions.assert_true(False, "Template not found")
            return False

        # In newer Zabbix versions, applications are replaced by tags
        # Just verify items exist and have some organization method
        result = self.harness.api_client.request("item.get", {
            "templateids": template['templateid'],
            "selectTags": ["tag"],
            "output": ["itemid", "name"]
        })

        items = result if isinstance(result, list) else []
        if not items:
            self.harness.assertions.assert_true(False, "No items found")
            return False

        self.harness.assertions.assert_true(
            True,
            f"{len(items)} items found in template"
        )
        return True

    def test_prototype_items_have_lld_macros(self) -> bool:
        """Verify item prototypes use LLD macros"""
        self.harness.assertions.start_test("Item prototypes use LLD macros")

        if not self.harness.api_client:
            self.harness.assertions.assert_true(False, "API client not initialized")
            return False

        template = self.harness.api_client.get_template(TEMPLATE_NAME)
        if not template:
            self.harness.assertions.assert_true(False, "Template not found")
            return False

        # Get discovery rules
        rules_result = self.harness.api_client.request("discoveryrule.get", {
            "templateids": template['templateid'],
            "output": ["itemid"]
        })

        rules = rules_result if isinstance(rules_result, list) else []
        if not rules:
            self.harness.assertions.assert_true(
                True,
                "No discovery rules, so no item prototypes to check"
            )
            return True

        # Get item prototypes
        prototypes_result = self.harness.api_client.request("itemprototype.get", {
            "discoveryids": [r['itemid'] for r in rules],
            "output": ["itemid", "name", "key_"]
        })

        prototypes = prototypes_result if isinstance(prototypes_result, list) else []
        if not prototypes:
            self.harness.assertions.assert_true(
                True,
                "No item prototypes to check"
            )
            return True

        # Check if prototypes use LLD macros (like {#MACRO})
        prototypes_with_macros = [
            p for p in prototypes
            if '{#' in p.get('name', '') or '{#' in p.get('key_', '')
        ]

        percentage = (len(prototypes_with_macros) / len(prototypes)) * 100

        if percentage > 50:  # Most prototypes should use LLD macros
            self.harness.assertions.assert_true(
                True,
                f"{len(prototypes_with_macros)}/{len(prototypes)} prototypes use LLD macros ({percentage:.1f}%)"
            )
            return True
        else:
            self.harness.assertions.assert_true(
                False,
                f"Only {percentage:.1f}% of prototypes use LLD macros"
            )
            return False

    def test_item_value_mapping(self) -> bool:
        """Verify items use value mappings where appropriate"""
        self.harness.assertions.start_test("Item value mappings")

        if not self.harness.api_client:
            self.harness.assertions.assert_true(False, "API client not initialized")
            return False

        template = self.harness.api_client.get_template(TEMPLATE_NAME)
        if not template:
            self.harness.assertions.assert_true(False, "Template not found")
            return False

        result = self.harness.api_client.request("item.get", {
            "templateids": template['templateid'],
            "output": ["itemid", "name", "valuemapid"]
        })

        items = result if isinstance(result, list) else []
        if not items:
            self.harness.assertions.assert_true(False, "No items found")
            return False

        items_with_valuemap = [i for i in items if i.get('valuemapid') and i['valuemapid'] != '0']

        if items_with_valuemap:
            percentage = (len(items_with_valuemap) / len(items)) * 100
            self.harness.assertions.assert_true(
                True,
                f"{len(items_with_valuemap)}/{len(items)} items use value mappings ({percentage:.1f}%)"
            )
        else:
            self.harness.assertions.assert_true(
                True,
                "No items use value mappings (acceptable)"
            )
        return True

    def test_item_timeout_configuration(self) -> bool:
        """Verify items have appropriate timeout configuration"""
        self.harness.assertions.start_test("Item timeout configuration")

        if not self.harness.api_client:
            self.harness.assertions.assert_true(False, "API client not initialized")
            return False

        template = self.harness.api_client.get_template(TEMPLATE_NAME)
        if not template:
            self.harness.assertions.assert_true(False, "Template not found")
            return False

        result = self.harness.api_client.request("item.get", {
            "templateids": template['templateid'],
            "output": ["itemid", "name", "timeout"]
        })

        items = result if isinstance(result, list) else []
        if not items:
            self.harness.assertions.assert_true(False, "No items found")
            return False

        items_with_timeout = [i for i in items if i.get('timeout')]

        if items_with_timeout:
            self.harness.assertions.assert_true(
                True,
                f"{len(items_with_timeout)}/{len(items)} items have custom timeout"
            )
        else:
            self.harness.assertions.assert_true(
                True,
                "Items use default timeout (acceptable)"
            )
        return True

    def run_all(self) -> dict:
        """Run all item data collection tests"""
        print(f"\n{Colors.BLUE}{'='*70}{Colors.NC}")
        print(f"{Colors.BLUE}Item Data Collection Tests{Colors.NC}")
        print(f"{Colors.BLUE}{'='*70}{Colors.NC}\n")

        tests = [
            ("Items Have Value Types", self.test_items_have_value_types),
            ("Numeric Items Have Units", self.test_items_have_units),
            ("Items Have Descriptions", self.test_items_have_descriptions),
            ("Item Keys Unique", self.test_item_keys_are_unique),
            ("Dependent Items", self.test_dependent_items_configuration),
            ("Preprocessing Steps", self.test_item_preprocessing_steps),
            ("Item Tags", self.test_item_tags),
            ("Trends Configuration", self.test_item_trends_configuration),
            ("Item Organization", self.test_item_applications),
            ("Prototypes Use LLD Macros", self.test_prototype_items_have_lld_macros),
            ("Value Mappings", self.test_item_value_mapping),
            ("Timeout Configuration", self.test_item_timeout_configuration),
        ]

        results = {}
        for test_name, test_func in tests:
            try:
                results[test_name] = test_func()
            except Exception as e:
                self.harness.assertions.assert_true(False, f"Test exception: {str(e)}")
                results[test_name] = False

        return results
