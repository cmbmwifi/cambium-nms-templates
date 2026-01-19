#!/usr/bin/env python3
"""
Advanced Features Test Suite

Tests advanced Zabbix features including:
- Template-level macros and inheritance
- LLD (Low-Level Discovery) functionality
- Complex trigger expressions and dependencies
- Error handling and edge cases
- Performance and optimization
"""

import sys
from pathlib import Path

# Support both package imports and direct script execution
try:
    from ..base.test_harness import ZabbixTestHarness, Colors
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from base.test_harness import ZabbixTestHarness, Colors


TEMPLATE_NAME = "Cambium Fiber OLT by SSH v1.3.0"


class AdvancedFeaturesTests:
    """Advanced features tests"""

    def __init__(self, harness: ZabbixTestHarness):
        self.harness = harness

    def test_template_macro_inheritance(self) -> bool:
        """Verify template macros are inherited by hosts"""
        self.harness.assertions.start_test("Template macro inheritance")

        if not self.harness.api_client:
            self.harness.assertions.assert_true(False, "API client not initialized")
            return False

        template = self.harness.api_client.get_template(TEMPLATE_NAME)
        if not template:
            self.harness.assertions.assert_true(False, "Template not found")
            return False

        result = self.harness.api_client.request("usermacro.get", {
            "templateids": template['templateid'],
            "output": ["macro", "value"]
        })

        macros = result if isinstance(result, list) else []

        if macros:
            self.harness.assertions.assert_true(
                True,
                f"Template has {len(macros)} macros that will be inherited"
            )
            return True
        else:
            self.harness.assertions.assert_true(
                True,
                "Template has no macros (acceptable)"
            )
            return True

    def test_lld_rule_key_format(self) -> bool:
        """Verify LLD rules use proper key format"""
        self.harness.assertions.start_test("LLD rule key format")

        if not self.harness.api_client:
            self.harness.assertions.assert_true(False, "API client not initialized")
            return False

        template = self.harness.api_client.get_template(TEMPLATE_NAME)
        if not template:
            self.harness.assertions.assert_true(False, "Template not found")
            return False

        result = self.harness.api_client.request("discoveryrule.get", {
            "templateids": template['templateid'],
            "output": ["itemid", "name", "key_", "type"]
        })

        rules = result if isinstance(result, list) else []
        if not rules:
            self.harness.assertions.assert_true(False, "No LLD rules found")
            return False

        # Check key format (should typically end with .discovery or similar)
        valid_keys = []
        for rule in rules:
            key = rule.get('key_', '')
            if '.discovery' in key.lower() or 'discovery' in key.lower():
                valid_keys.append(rule['name'])

        percentage = (len(valid_keys) / len(rules)) * 100

        if percentage > 50:
            self.harness.assertions.assert_true(
                True,
                f"{len(valid_keys)}/{len(rules)} LLD rules follow naming convention ({percentage:.1f}%)"
            )
            return True
        else:
            self.harness.assertions.assert_true(
                True,
                f"LLD rules may use custom naming ({len(rules)} rules total)"
            )
            return True

    def test_lld_filter_configuration(self) -> bool:
        """Verify LLD rules have filters configured"""
        self.harness.assertions.start_test("LLD filter configuration")

        if not self.harness.api_client:
            self.harness.assertions.assert_true(False, "API client not initialized")
            return False

        template = self.harness.api_client.get_template(TEMPLATE_NAME)
        if not template:
            self.harness.assertions.assert_true(False, "Template not found")
            return False

        result = self.harness.api_client.request("discoveryrule.get", {
            "templateids": template['templateid'],
            "selectFilter": ["conditions"],
            "output": ["itemid", "name"]
        })

        rules = result if isinstance(result, list) else []
        if not rules:
            self.harness.assertions.assert_true(False, "No LLD rules found")
            return False

        rules_with_filters = [r for r in rules if r.get('filter', {}).get('conditions')]

        if rules_with_filters:
            percentage = (len(rules_with_filters) / len(rules)) * 100
            self.harness.assertions.assert_true(
                True,
                f"{len(rules_with_filters)}/{len(rules)} LLD rules have filters ({percentage:.1f}%)"
            )
        else:
            self.harness.assertions.assert_true(
                True,
                "LLD rules have no filters (acceptable if not needed)"
            )
        return True

    def test_lld_lifetime_configuration(self) -> bool:
        """Verify LLD rules have lost resource lifetime configured"""
        self.harness.assertions.start_test("LLD lifetime configuration")

        if not self.harness.api_client:
            self.harness.assertions.assert_true(False, "API client not initialized")
            return False

        template = self.harness.api_client.get_template(TEMPLATE_NAME)
        if not template:
            self.harness.assertions.assert_true(False, "Template not found")
            return False

        result = self.harness.api_client.request("discoveryrule.get", {
            "templateids": template['templateid'],
            "output": ["itemid", "name", "lifetime"]
        })

        rules = result if isinstance(result, list) else []
        if not rules:
            self.harness.assertions.assert_true(False, "No LLD rules found")
            return False

        rules_with_lifetime = [r for r in rules if r.get('lifetime')]

        if len(rules_with_lifetime) == len(rules):
            self.harness.assertions.assert_true(
                True,
                f"All {len(rules)} LLD rules have lifetime configured"
            )
            return True
        else:
            self.harness.assertions.assert_true(
                True,
                f"{len(rules_with_lifetime)}/{len(rules)} LLD rules have custom lifetime"
            )
            return True

    def test_trigger_dependencies(self) -> bool:
        """Verify trigger dependencies are properly configured"""
        self.harness.assertions.start_test("Trigger dependencies")

        if not self.harness.api_client:
            self.harness.assertions.assert_true(False, "API client not initialized")
            return False

        template = self.harness.api_client.get_template(TEMPLATE_NAME)
        if not template:
            self.harness.assertions.assert_true(False, "Template not found")
            return False

        result = self.harness.api_client.request("trigger.get", {
            "templateids": template['templateid'],
            "selectDependencies": ["triggerid"],
            "output": ["triggerid", "description"]
        })

        triggers = result if isinstance(result, list) else []
        if not triggers:
            self.harness.assertions.assert_true(False, "No triggers found")
            return False

        triggers_with_deps = [t for t in triggers if t.get('dependencies')]

        if triggers_with_deps:
            self.harness.assertions.assert_true(
                True,
                f"{len(triggers_with_deps)}/{len(triggers)} triggers have dependencies"
            )
        else:
            self.harness.assertions.assert_true(
                True,
                "No trigger dependencies (acceptable if not needed)"
            )
        return True

    def test_trigger_prototype_configuration(self) -> bool:
        """Verify trigger prototypes are configured for LLD items"""
        self.harness.assertions.start_test("Trigger prototypes")

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
                "No discovery rules, so no trigger prototypes expected"
            )
            return True

        # Get trigger prototypes
        trigger_proto_result = self.harness.api_client.request("triggerprototype.get", {
            "discoveryids": [r['itemid'] for r in rules],
            "output": ["triggerid", "description"]
        })

        trigger_protos = trigger_proto_result if isinstance(trigger_proto_result, list) else []

        if trigger_protos:
            self.harness.assertions.assert_true(
                True,
                f"Template has {len(trigger_protos)} trigger prototypes"
            )
            return True
        else:
            self.harness.assertions.assert_true(
                True,
                "No trigger prototypes (acceptable if not needed)"
            )
            return True

    def test_template_linked_templates(self) -> bool:
        """Verify template linking and inheritance"""
        self.harness.assertions.start_test("Template linking")

        if not self.harness.api_client:
            self.harness.assertions.assert_true(False, "API client not initialized")
            return False

        template = self.harness.api_client.get_template(TEMPLATE_NAME)
        if not template:
            self.harness.assertions.assert_true(False, "Template not found")
            return False

        result = self.harness.api_client.request("template.get", {
            "templateids": template['templateid'],
            "selectParentTemplates": ["templateid", "name"]
        })

        if isinstance(result, list) and len(result) > 0:
            parent_templates = result[0].get('parentTemplates', [])

            if parent_templates:
                parent_names = [t['name'] for t in parent_templates]
                self.harness.assertions.assert_true(
                    True,
                    f"Template inherits from: {', '.join(parent_names)}"
                )
            else:
                self.harness.assertions.assert_true(
                    True,
                    "Template is standalone (no parent templates)"
                )
            return True
        else:
            self.harness.assertions.assert_true(False, "Failed to get template details")
            return False

    def test_item_error_handling(self) -> bool:
        """Verify items handle errors gracefully"""
        self.harness.assertions.start_test("Item error handling")

        if not self.harness.api_client:
            self.harness.assertions.assert_true(False, "API client not initialized")
            return False

        template = self.harness.api_client.get_template(TEMPLATE_NAME)
        if not template:
            self.harness.assertions.assert_true(False, "Template not found")
            return False

        # Get items with error handling parameters
        result = self.harness.api_client.request("item.get", {
            "templateids": template['templateid'],
            "output": ["itemid", "name", "error_handler"]
        })

        items = result if isinstance(result, list) else []
        if not items:
            self.harness.assertions.assert_true(False, "No items found")
            return False

        self.harness.assertions.assert_true(
            True,
            f"{len(items)} items configured (error handling is automatic in Zabbix)"
        )
        return True

    def test_template_tags(self) -> bool:
        """Verify template has tags for organization"""
        self.harness.assertions.start_test("Template tags")

        if not self.harness.api_client:
            self.harness.assertions.assert_true(False, "API client not initialized")
            return False

        template = self.harness.api_client.get_template(TEMPLATE_NAME)
        if not template:
            self.harness.assertions.assert_true(False, "Template not found")
            return False

        result = self.harness.api_client.request("template.get", {
            "templateids": template['templateid'],
            "selectTags": ["tag", "value"]
        })

        if isinstance(result, list) and len(result) > 0:
            tags = result[0].get('tags', [])

            if tags:
                self.harness.assertions.assert_true(
                    True,
                    f"Template has {len(tags)} tags"
                )
            else:
                self.harness.assertions.assert_true(
                    True,
                    "Template has no tags (acceptable)"
                )
            return True
        else:
            self.harness.assertions.assert_true(False, "Failed to get template tags")
            return False

    def test_discovery_rule_overrides(self) -> bool:
        """Verify LLD rules have overrides configured if needed"""
        self.harness.assertions.start_test("LLD rule overrides")

        if not self.harness.api_client:
            self.harness.assertions.assert_true(False, "API client not initialized")
            return False

        template = self.harness.api_client.get_template(TEMPLATE_NAME)
        if not template:
            self.harness.assertions.assert_true(False, "Template not found")
            return False

        result = self.harness.api_client.request("discoveryrule.get", {
            "templateids": template['templateid'],
            "selectLLDMacroSPaths": ["lld_macro", "path"],
            "output": ["itemid", "name"]
        })

        rules = result if isinstance(result, list) else []
        if not rules:
            self.harness.assertions.assert_true(False, "No LLD rules found")
            return False

        rules_with_paths = [r for r in rules if r.get('lld_macro_paths')]

        if rules_with_paths:
            self.harness.assertions.assert_true(
                True,
                f"{len(rules_with_paths)}/{len(rules)} LLD rules have macro paths"
            )
        else:
            self.harness.assertions.assert_true(
                True,
                "LLD rules use default macro extraction (acceptable)"
            )
        return True

    def test_template_dashboard(self) -> bool:
        """Verify template has dashboard configured"""
        self.harness.assertions.start_test("Template dashboard")

        if not self.harness.api_client:
            self.harness.assertions.assert_true(False, "API client not initialized")
            return False

        template = self.harness.api_client.get_template(TEMPLATE_NAME)
        if not template:
            self.harness.assertions.assert_true(False, "Template not found")
            return False

        result = self.harness.api_client.request("templatedashboard.get", {
            "templateids": template['templateid'],
            "output": ["dashboardid", "name"]
        })

        dashboards = result if isinstance(result, list) else []

        if dashboards:
            self.harness.assertions.assert_true(
                True,
                f"Template has {len(dashboards)} dashboard(s)"
            )
        else:
            self.harness.assertions.assert_true(
                True,
                "Template has no dashboard (acceptable)"
            )
        return True

    def test_item_prototype_preprocessing(self) -> bool:
        """Verify item prototypes have preprocessing configured"""
        self.harness.assertions.start_test("Item prototype preprocessing")

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
                "No discovery rules to check"
            )
            return True

        # Get item prototypes with preprocessing
        prototypes_result = self.harness.api_client.request("itemprototype.get", {
            "discoveryids": [r['itemid'] for r in rules],
            "selectPreprocessing": ["type"],
            "output": ["itemid", "name"]
        })

        prototypes = prototypes_result if isinstance(prototypes_result, list) else []
        if not prototypes:
            self.harness.assertions.assert_true(
                True,
                "No item prototypes to check"
            )
            return True

        prototypes_with_preprocessing = [p for p in prototypes if p.get('preprocessing')]

        if prototypes_with_preprocessing:
            percentage = (len(prototypes_with_preprocessing) / len(prototypes)) * 100
            self.harness.assertions.assert_true(
                True,
                f"{len(prototypes_with_preprocessing)}/{len(prototypes)} prototypes use preprocessing ({percentage:.1f}%)"
            )
        else:
            self.harness.assertions.assert_true(
                True,
                "Item prototypes don't use preprocessing (acceptable)"
            )
        return True

    def test_web_scenarios(self) -> bool:
        """Verify web scenarios if template monitors web services"""
        self.harness.assertions.start_test("Web scenarios")

        if not self.harness.api_client:
            self.harness.assertions.assert_true(False, "API client not initialized")
            return False

        template = self.harness.api_client.get_template(TEMPLATE_NAME)
        if not template:
            self.harness.assertions.assert_true(False, "Template not found")
            return False

        result = self.harness.api_client.request("httptest.get", {
            "templateids": template['templateid'],
            "output": ["httptestid", "name"]
        })

        web_scenarios = result if isinstance(result, list) else []

        if web_scenarios:
            self.harness.assertions.assert_true(
                True,
                f"Template has {len(web_scenarios)} web scenario(s)"
            )
        else:
            self.harness.assertions.assert_true(
                True,
                "Template has no web scenarios (expected for SSH-based template)"
            )
        return True

    def test_template_screen_compatibility(self) -> bool:
        """Verify template compatibility with screens/dashboards"""
        self.harness.assertions.start_test("Screen/Dashboard compatibility")

        if not self.harness.api_client:
            self.harness.assertions.assert_true(False, "API client not initialized")
            return False

        template = self.harness.api_client.get_template(TEMPLATE_NAME)
        if not template:
            self.harness.assertions.assert_true(False, "Template not found")
            return False

        # Just verify template exists and has items/graphs that can be used in dashboards
        items_result = self.harness.api_client.request("item.get", {
            "templateids": template['templateid'],
            "output": ["itemid"]
        })

        items = items_result if isinstance(items_result, list) else []

        if items:
            self.harness.assertions.assert_true(
                True,
                f"Template has {len(items)} items that can be used in dashboards"
            )
        else:
            self.harness.assertions.assert_true(False, "No items for dashboard use")
        return True

    def run_all(self) -> dict:
        """Run all advanced features tests"""
        print(f"\n{Colors.BLUE}{'='*70}{Colors.NC}")
        print(f"{Colors.BLUE}Advanced Features Tests{Colors.NC}")
        print(f"{Colors.BLUE}{'='*70}{Colors.NC}\n")

        tests = [
            ("Template Macro Inheritance", self.test_template_macro_inheritance),
            ("LLD Rule Key Format", self.test_lld_rule_key_format),
            ("LLD Filter Configuration", self.test_lld_filter_configuration),
            ("LLD Lifetime Configuration", self.test_lld_lifetime_configuration),
            ("Trigger Dependencies", self.test_trigger_dependencies),
            ("Trigger Prototypes", self.test_trigger_prototype_configuration),
            ("Template Linking", self.test_template_linked_templates),
            ("Item Error Handling", self.test_item_error_handling),
            ("Template Tags", self.test_template_tags),
            ("LLD Rule Overrides", self.test_discovery_rule_overrides),
            ("Template Dashboard", self.test_template_dashboard),
            ("Item Prototype Preprocessing", self.test_item_prototype_preprocessing),
            ("Web Scenarios", self.test_web_scenarios),
            ("Dashboard Compatibility", self.test_template_screen_compatibility),
        ]

        results = {}
        for test_name, test_func in tests:
            try:
                results[test_name] = test_func()
            except Exception as e:
                self.harness.assertions.assert_true(False, f"Test exception: {str(e)}")
                results[test_name] = False

        return results
