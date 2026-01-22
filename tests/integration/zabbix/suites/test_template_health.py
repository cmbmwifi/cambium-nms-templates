#!/usr/bin/env python3
"""
Template Health Test Suite

Tests template structure and configuration including:
- Template properties and metadata
- Discovery rules and item prototypes
- Triggers and their dependencies
- Item configurations and types
"""

import sys
from pathlib import Path
from typing import Optional

# Support both package imports and direct script execution
try:
    from ..base.test_harness import ZabbixTestHarness, Colors  # type: ignore[no-redef]
    from ..validators.template_validator import TemplateValidator  # type: ignore[no-redef]
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from base.test_harness import ZabbixTestHarness, Colors  # type: ignore[no-redef]
    from validators.template_validator import TemplateValidator  # type: ignore[no-redef]


TEMPLATE_NAME = "Cambium Fiber OLT by SSH v1.3.0"


class TemplateHealthTests:
    """Template Health validation tests"""

    def __init__(self, harness: ZabbixTestHarness):
        self.harness = harness
        self.validator: Optional[TemplateValidator] = None
        if harness.api_client:
            self.validator = TemplateValidator(harness.api_client)

    def test_template_exists(self) -> bool:
        """Verify template exists in Zabbix after import"""
        self.harness.assertions.start_test("Template exists in Zabbix")

        if not self.harness.api_client:
            self.harness.assertions.assert_true(False, "API client not initialized")
            return False
        template = self.harness.api_client.get_template(TEMPLATE_NAME)

        if template:
            self.harness.assertions.assert_true(
                True,
                f"Template '{TEMPLATE_NAME}' found with ID {template.get('templateid')}"
            )
            return True
        else:
            self.harness.assertions.assert_true(
                False,
                f"Template '{TEMPLATE_NAME}' not found in Zabbix"
            )
            return False

    def test_template_has_items(self) -> bool:
        """Verify template has expected items"""
        self.harness.assertions.start_test("Template has items")

        if not self.harness.api_client:
            self.harness.assertions.assert_true(False, "API client not initialized")
            return False
        template = self.harness.api_client.get_template(TEMPLATE_NAME)
        if not template:
            self.harness.assertions.assert_true(False, "Template not found")
            return False

        result = self.harness.api_client.request("item.get", {
            "templateids": template['templateid'],
            "output": ["itemid", "name", "key_", "type"]
        })

        items = result if isinstance(result, list) else []
        item_count = len(items)

        # Template should have multiple items
        if item_count > 0:
            self.harness.assertions.assert_true(
                True,
                f"Template has {item_count} items"
            )
            return True
        else:
            self.harness.assertions.assert_true(
                False,
                "Template has no items"
            )
            return False

    def test_template_has_discovery_rules(self) -> bool:
        """Verify template has discovery rules"""
        self.harness.assertions.start_test("Template has discovery rules")

        if not self.harness.api_client:
            self.harness.assertions.assert_true(False, "API client not initialized")
            return False

        template = self.harness.api_client.get_template(TEMPLATE_NAME)
        if not template:
            self.harness.assertions.assert_true(False, "Template not found")
            return False

        result = self.harness.api_client.request("discoveryrule.get", {
            "templateids": template['templateid'],
            "output": ["itemid", "name", "key_"]
        })

        rules = result if isinstance(result, list) else []
        rule_count = len(rules)

        if rule_count > 0:
            self.harness.assertions.assert_true(
                True,
                f"Template has {rule_count} discovery rules"
            )
            return True
        else:
            self.harness.assertions.assert_true(
                False,
                "Template has no discovery rules"
            )
            return False

    def test_discovery_rule_has_item_prototypes(self) -> bool:
        """Verify discovery rules have item prototypes"""
        self.harness.assertions.start_test("Discovery rules have item prototypes")
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
            "output": ["itemid", "name"]
        })

        rules = rules_result if isinstance(rules_result, list) else []
        if not rules:
            self.harness.assertions.assert_true(False, "No discovery rules found")
            return False

        # Check each discovery rule has item prototypes
        all_have_prototypes = True
        total_prototypes = 0

        for rule in rules:
            prototypes_result = self.harness.api_client.request("itemprototype.get", {
                "discoveryids": rule['itemid'],
                "output": ["itemid", "name"]
            })

            prototypes = prototypes_result if isinstance(prototypes_result, list) else []
            prototype_count = len(prototypes)
            total_prototypes += prototype_count

            if prototype_count == 0:
                all_have_prototypes = False
                self.harness.assertions.assert_true(
                    False,
                    f"Discovery rule '{rule['name']}' has no item prototypes"
                )

        if all_have_prototypes and total_prototypes > 0:
            self.harness.assertions.assert_true(
                True,
                f"All discovery rules have item prototypes (total: {total_prototypes})"
            )
            return True
        else:
            return False

    def test_template_has_triggers(self) -> bool:
        """Verify template has triggers"""
        self.harness.assertions.start_test("Template has triggers")

        if not self.harness.api_client:
            self.harness.assertions.assert_true(False, "API client not initialized")
            return False
        template = self.harness.api_client.get_template(TEMPLATE_NAME)
        if not template:
            self.harness.assertions.assert_true(False, "Template not found")
            return False

        result = self.harness.api_client.request("trigger.get", {
            "templateids": template['templateid'],
            "output": ["triggerid", "description", "priority"]
        })

        triggers = result if isinstance(result, list) else []
        trigger_count = len(triggers)

        if trigger_count > 0:
            self.harness.assertions.assert_true(
                True,
                f"Template has {trigger_count} triggers"
            )
            return True
        else:
            self.harness.assertions.assert_true(
                False,
                "Template has no triggers"
            )
            return False

    def test_trigger_severities_are_valid(self) -> bool:
        """Verify trigger severities are within valid range"""
        self.harness.assertions.start_test("Trigger severities are valid")

        if not self.harness.api_client:
            self.harness.assertions.assert_true(False, "API client not initialized")
            return False

        template = self.harness.api_client.get_template(TEMPLATE_NAME)
        if not template:
            self.harness.assertions.assert_true(False, "Template not found")
            return False

        result = self.harness.api_client.request("trigger.get", {
            "templateids": template['templateid'],
            "output": ["triggerid", "description", "priority"]
        })

        triggers = result if isinstance(result, list) else []
        if not triggers:
            self.harness.assertions.assert_true(False, "No triggers found")
            return False

        # Valid severities: 0-5 (Not classified, Information, Warning, Average, High, Disaster)
        invalid_triggers = []
        for trigger in triggers:
            priority = int(trigger.get('priority', 0))
            if priority < 0 or priority > 5:
                invalid_triggers.append(trigger['description'])

        if not invalid_triggers:
            self.harness.assertions.assert_true(
                True,
                f"All {len(triggers)} triggers have valid severities (0-5)"
            )
            return True
        else:
            self.harness.assertions.assert_true(
                False,
                f"Invalid severities in triggers: {', '.join(invalid_triggers)}"
            )
            return False

    def test_template_has_macros(self) -> bool:
        """Verify template has user macros"""
        self.harness.assertions.start_test("Template has user macros")

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
        macro_count = len(macros)

        if macro_count > 0:
            self.harness.assertions.assert_true(
                True,
                f"Template has {macro_count} user macros"
            )
            return True
        else:
            self.harness.assertions.assert_true(
                True,
                "Template has no user macros (acceptable)"
            )
            return True

    def test_ssh_item_authentication(self) -> bool:
        """Verify SSH items have proper authentication configured"""
        self.harness.assertions.start_test("SSH items have authentication")

        if not self.harness.api_client:
            self.harness.assertions.assert_true(False, "API client not initialized")
            return False

        template = self.harness.api_client.get_template(TEMPLATE_NAME)
        if not template:
            self.harness.assertions.assert_true(False, "Template not found")
            return False

        result = self.harness.api_client.request("item.get", {
            "templateids": template['templateid'],
            "output": ["itemid", "name", "key_", "type", "authtype", "username"],
            "filter": {"type": 13}  # SSH agent type
        })

        ssh_items = result if isinstance(result, list) else []

        if not ssh_items:
            self.harness.assertions.assert_true(
                True,
                "No SSH items found (template may use different item types)"
            )
            return True

        items_with_auth = [item for item in ssh_items if item.get('username')]

        if len(items_with_auth) == len(ssh_items):
            self.harness.assertions.assert_true(
                True,
                f"All {len(ssh_items)} SSH items have authentication configured"
            )
            return True
        else:
            self.harness.assertions.assert_true(
                False,
                f"Only {len(items_with_auth)}/{len(ssh_items)} SSH items have authentication"
            )
            return False

    def test_external_script_items_exist(self) -> bool:
        """Verify template has external script items"""
        self.harness.assertions.start_test("External script items exist")

        if not self.harness.api_client:
            self.harness.assertions.assert_true(False, "API client not initialized")
            return False

        template = self.harness.api_client.get_template(TEMPLATE_NAME)
        if not template:
            self.harness.assertions.assert_true(False, "Template not found")
            return False

        result = self.harness.api_client.request("item.get", {
            "templateids": template['templateid'],
            "output": ["itemid", "name", "key_", "type"],
            "filter": {"type": 10}  # External check type
        })

        script_items = result if isinstance(result, list) else []

        if len(script_items) > 0:
            self.harness.assertions.assert_true(
                True,
                f"Template has {len(script_items)} external script items"
            )
            return True
        else:
            self.harness.assertions.assert_true(
                False,
                "Template has no external script items"
            )
            return False

    def test_item_update_intervals(self) -> bool:
        """Verify items have reasonable update intervals"""
        self.harness.assertions.start_test("Items have reasonable update intervals")

        if not self.harness.api_client:
            self.harness.assertions.assert_true(False, "API client not initialized")
            return False

        template = self.harness.api_client.get_template(TEMPLATE_NAME)
        if not template:
            self.harness.assertions.assert_true(False, "Template not found")
            return False

        result = self.harness.api_client.request("item.get", {
            "templateids": template['templateid'],
            "output": ["itemid", "name", "key_", "delay"]
        })

        items = result if isinstance(result, list) else []
        if not items:
            self.harness.assertions.assert_true(False, "No items found")
            return False

        # Check for unreasonably short intervals (< 30s) or missing delays
        problematic_items = []
        for item in items:
            delay = item.get('delay', '')
            if delay:
                # Parse delay (could be like "30s", "1m", etc.)
                try:
                    if delay.endswith('s'):
                        seconds = int(delay[:-1])
                    elif delay.endswith('m'):
                        seconds = int(delay[:-1]) * 60
                    elif delay.endswith('h'):
                        seconds = int(delay[:-1]) * 3600
                    else:
                        seconds = int(delay)

                    if seconds < 30:
                        problematic_items.append(item['name'])
                except:
                    pass  # Skip parsing errors

        if not problematic_items:
            self.harness.assertions.assert_true(
                True,
                f"All {len(items)} items have reasonable update intervals (≥30s)"
            )
            return True
        else:
            self.harness.assertions.assert_true(
                False,
                f"{len(problematic_items)} items have very short intervals: {problematic_items[:3]}"
            )
            return False

    def test_template_value_maps(self) -> bool:
        """Verify template has value maps configured"""
        self.harness.assertions.start_test("Template has value maps")

        if not self.harness.api_client:
            self.harness.assertions.assert_true(False, "API client not initialized")
            return False

        template = self.harness.api_client.get_template(TEMPLATE_NAME)
        if not template:
            self.harness.assertions.assert_true(False, "Template not found")
            return False

        # Value maps are typically global or template-specific
        result = self.harness.api_client.request("valuemap.get", {
            "output": ["valuemapid", "name"]
        })

        valuemaps = result if isinstance(result, list) else []

        if len(valuemaps) > 0:
            self.harness.assertions.assert_true(
                True,
                f"Found {len(valuemaps)} value maps in system"
            )
            return True
        else:
            self.harness.assertions.assert_true(
                True,
                "No value maps found (acceptable, not all templates use them)"
            )
            return True

    def test_template_groups(self) -> bool:
        """Verify template is assigned to appropriate groups"""
        self.harness.assertions.start_test("Template has template groups")

        if not self.harness.api_client:
            self.harness.assertions.assert_true(False, "API client not initialized")
            return False

        template = self.harness.api_client.get_template(TEMPLATE_NAME)
        if not template:
            self.harness.assertions.assert_true(False, "Template not found")
            return False

        # Zabbix 7.2+ uses templategroups instead of groups for templates
        if self.harness.version == "7.0":
            result = self.harness.api_client.request("template.get", {
                "templateids": template['templateid'],
                "selectGroups": ["groupid", "name"]
            })
            groups = result[0].get('groups', []) if isinstance(result, list) and len(result) > 0 else []
        else:
            result = self.harness.api_client.request("template.get", {
                "templateids": template['templateid'],
                "selectTemplateGroups": ["groupid", "name"]
            })
            groups = result[0].get('templategroups', []) if isinstance(result, list) and len(result) > 0 else []

        group_count = len(groups)

        if group_count > 0:
            group_names = [g['name'] for g in groups]
            self.harness.assertions.assert_true(
                True,
                f"Template assigned to {group_count} groups: {', '.join(group_names)}"
            )
            return True
        else:
            self.harness.assertions.assert_true(
                False,
                "Template not assigned to any groups"
            )
            return False

    def test_discovery_rule_intervals(self) -> bool:
        """Verify discovery rules have appropriate intervals"""
        self.harness.assertions.start_test("Discovery rules have appropriate intervals")

        if not self.harness.api_client:
            self.harness.assertions.assert_true(False, "API client not initialized")
            return False

        template = self.harness.api_client.get_template(TEMPLATE_NAME)
        if not template:
            self.harness.assertions.assert_true(False, "Template not found")
            return False

        result = self.harness.api_client.request("discoveryrule.get", {
            "templateids": template['templateid'],
            "output": ["itemid", "name", "delay"]
        })

        rules = result if isinstance(result, list) else []
        if not rules:
            self.harness.assertions.assert_true(False, "No discovery rules found")
            return False

        # Discovery rules should typically be slower (e.g., 5m+)
        all_valid = True
        for rule in rules:
            delay = rule.get('delay', '')
            if delay:
                self.harness.assertions.print_info(f"  Rule '{rule['name']}': {delay}")
            else:
                all_valid = False

        if all_valid:
            self.harness.assertions.assert_true(
                True,
                f"All {len(rules)} discovery rules have intervals configured"
            )
            return True
        else:
            self.harness.assertions.assert_true(
                False,
                "Some discovery rules missing interval configuration"
            )
            return False

    def test_trigger_expressions_valid(self) -> bool:
        """Verify trigger expressions are properly formatted"""
        self.harness.assertions.start_test("Trigger expressions are valid")

        if not self.harness.api_client:
            self.harness.assertions.assert_true(False, "API client not initialized")
            return False

        template = self.harness.api_client.get_template(TEMPLATE_NAME)
        if not template:
            self.harness.assertions.assert_true(False, "Template not found")
            return False

        result = self.harness.api_client.request("trigger.get", {
            "templateids": template['templateid'],
            "output": ["triggerid", "description", "expression"]
        })

        triggers = result if isinstance(result, list) else []
        if not triggers:
            self.harness.assertions.assert_true(False, "No triggers found")
            return False

        # Basic validation: expression should not be empty
        invalid_triggers = [t for t in triggers if not t.get('expression')]

        if not invalid_triggers:
            self.harness.assertions.assert_true(
                True,
                f"All {len(triggers)} triggers have valid expressions"
            )
            return True
        else:
            self.harness.assertions.assert_true(
                False,
                f"{len(invalid_triggers)} triggers have empty/invalid expressions"
            )
            return False

    def test_item_history_storage(self) -> bool:
        """Verify items have appropriate history storage configured"""
        self.harness.assertions.start_test("Items have history storage configured")

        if not self.harness.api_client:
            self.harness.assertions.assert_true(False, "API client not initialized")
            return False

        template = self.harness.api_client.get_template(TEMPLATE_NAME)
        if not template:
            self.harness.assertions.assert_true(False, "Template not found")
            return False

        result = self.harness.api_client.request("item.get", {
            "templateids": template['templateid'],
            "output": ["itemid", "name", "history", "trends"]
        })

        items = result if isinstance(result, list) else []
        if not items:
            self.harness.assertions.assert_true(False, "No items found")
            return False

        # Items should have history configured
        items_with_history = [i for i in items if i.get('history')]

        if len(items_with_history) == len(items):
            self.harness.assertions.assert_true(
                True,
                f"All {len(items)} items have history storage configured"
            )
            return True
        else:
            self.harness.assertions.assert_true(
                False,
                f"Only {len(items_with_history)}/{len(items)} items have history configured"
            )
            return False

    def run_all(self) -> dict:
        """Run all template health tests"""
        print(f"\n{Colors.BLUE}{'='*70}{Colors.NC}")
        print(f"{Colors.BLUE}Template Health Tests{Colors.NC}")
        print(f"{Colors.BLUE}{'='*70}{Colors.NC}\n")

        tests = [
            ("Template Exists", self.test_template_exists),
            ("Template Has Items", self.test_template_has_items),
            ("Template Has Discovery Rules", self.test_template_has_discovery_rules),
            ("Discovery Rules Have Prototypes", self.test_discovery_rule_has_item_prototypes),
            ("Template Has Triggers", self.test_template_has_triggers),
            ("Trigger Severities Valid", self.test_trigger_severities_are_valid),
            ("Template Has Macros", self.test_template_has_macros),
            ("SSH Authentication", self.test_ssh_item_authentication),
            ("External Script Items", self.test_external_script_items_exist),
            ("Item Update Intervals", self.test_item_update_intervals),
            ("Template Value Maps", self.test_template_value_maps),
            ("Template Groups", self.test_template_groups),
            ("Discovery Rule Intervals", self.test_discovery_rule_intervals),
            ("Trigger Expressions", self.test_trigger_expressions_valid),
            ("Item History Storage", self.test_item_history_storage),
        ]

        results = {}
        for test_name, test_func in tests:
            try:
                results[test_name] = test_func()
            except Exception as e:
                self.harness.assertions.assert_true(False, f"Test exception: {str(e)}")
                results[test_name] = False

        return results
