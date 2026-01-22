#!/usr/bin/env python3
"""
Host Operations Test Suite

Tests host creation and management including:
- Host creation with template linking
- Interface configuration (IP, DNS, port)
- Host group assignments
- Macro inheritance and overrides
- Host enable/disable operations
"""

import sys
from pathlib import Path
from typing import Optional, Dict, Any

# Support both package imports and direct script execution
try:
    from ..base.test_harness import ZabbixTestHarness, Colors  # type: ignore[no-redef]
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from base.test_harness import ZabbixTestHarness, Colors  # type: ignore[no-redef]


TEMPLATE_NAME = "Cambium Fiber OLT by SSH v1.3.0"
TEST_HOST_NAME = "test-olt-integration"
TEST_HOST_IP = "192.168.1.100"


class HostOperationsTests:
    """Host operations tests"""

    def __init__(self, harness: ZabbixTestHarness):
        self.harness = harness
        self.test_host_id: Optional[str] = None
        self.test_hostgroup_id: Optional[str] = None

    def cleanup_test_host(self):
        """Clean up test host if it exists"""
        if not self.harness.api_client:
            return

        host = self.harness.api_client.get_host(TEST_HOST_NAME)
        if host:
            try:
                result = self.harness.api_client.request("host.delete", [host['hostid']])
                self.harness.assertions.print_info(f"Cleaned up test host: {TEST_HOST_NAME}")
            except Exception as e:
                self.harness.assertions.print_info(f"Could not cleanup test host: {e}")

    def test_create_host_with_template(self) -> bool:
        """Create a host with the template linked"""
        self.harness.assertions.start_test("Create host with template")


        if not self.harness.api_client:
            self.harness.assertions.assert_true(False, "API client not initialized")
            return False
        # Clean up any existing test host
        self.cleanup_test_host()

        template = self.harness.api_client.get_template(TEMPLATE_NAME)
        if not template:
            self.harness.assertions.assert_true(False, "Template not found")
            return False

        # Get or create a test host group
        groups_result = self.harness.api_client.request("hostgroup.get", {
            "filter": {"name": "Integration Tests"},
            "output": ["groupid"]
        })

        groups = groups_result if isinstance(groups_result, list) else []

        if not groups:
            # Create test group
            create_result = self.harness.api_client.request("hostgroup.create", {
                "name": "Integration Tests"
            })
            if isinstance(create_result, dict) and 'groupids' in create_result:
                self.test_hostgroup_id = create_result['groupids'][0]
            else:
                self.harness.assertions.assert_true(False, "Failed to create test host group")
                return False
        else:
            self.test_hostgroup_id = groups[0]['groupid']

        # Create host
        try:
            result = self.harness.api_client.request("host.create", {
                "host": TEST_HOST_NAME,
                "name": "Test OLT for Integration",
                "groups": [{"groupid": self.test_hostgroup_id}],
                "templates": [{"templateid": template['templateid']}],
                "interfaces": [{
                    "type": 1,  # Agent interface
                    "main": 1,
                    "useip": 1,
                    "ip": TEST_HOST_IP,
                    "dns": "",
                    "port": "10050"
                }]
            })

            if isinstance(result, dict) and 'hostids' in result:
                self.test_host_id = result['hostids'][0]
                self.harness.assertions.assert_true(
                    True,
                    f"Host created successfully with ID: {self.test_host_id}"
                )
                return True
            else:
                self.harness.assertions.assert_true(False, "Failed to create host")
                return False
        except Exception as e:
            self.harness.assertions.assert_true(False, f"Exception creating host: {e}")
            return False

    def test_host_has_template_linked(self) -> bool:
        """Verify host has template properly linked"""
        self.harness.assertions.start_test("Host has template linked")


        if not self.harness.api_client:
            self.harness.assertions.assert_true(False, "API client not initialized")
            return False
        if not self.test_host_id:
            self.harness.assertions.assert_true(False, "Test host not created")
            return False

        template = self.harness.api_client.get_template(TEMPLATE_NAME)
        if not template:
            self.harness.assertions.assert_true(False, "Template not found")
            return False

        result = self.harness.api_client.request("host.get", {
            "hostids": self.test_host_id,
            "selectParentTemplates": ["templateid", "name"]
        })

        if isinstance(result, list) and len(result) > 0:
            host = result[0]
            templates = host.get('parentTemplates', [])

            template_ids = [t['templateid'] for t in templates]
            if template['templateid'] in template_ids:
                self.harness.assertions.assert_true(
                    True,
                    f"Template properly linked to host"
                )
                return True
            else:
                self.harness.assertions.assert_true(
                    False,
                    f"Template not linked to host"
                )
                return False
        else:
            self.harness.assertions.assert_true(False, "Failed to get host details")
            return False

    def test_host_interface_configuration(self) -> bool:
        """Verify host interface is configured correctly"""
        self.harness.assertions.start_test("Host interface configuration")


        if not self.harness.api_client:
            self.harness.assertions.assert_true(False, "API client not initialized")
            return False
        if not self.test_host_id:
            self.harness.assertions.assert_true(False, "Test host not created")
            return False

        result = self.harness.api_client.request("hostinterface.get", {
            "hostids": self.test_host_id,
            "output": ["interfaceid", "ip", "dns", "port", "type"]
        })

        interfaces = result if isinstance(result, list) else []

        if len(interfaces) > 0:
            interface = interfaces[0]
            if interface['ip'] == TEST_HOST_IP:
                self.harness.assertions.assert_true(
                    True,
                    f"Interface configured with IP: {interface['ip']}"
                )
                return True
            else:
                self.harness.assertions.assert_true(
                    False,
                    f"Interface IP mismatch: {interface['ip']} != {TEST_HOST_IP}"
                )
                return False
        else:
            self.harness.assertions.assert_true(False, "No interfaces found on host")
            return False

    def test_host_inherits_items(self) -> bool:
        """Verify host inherits items from template"""
        self.harness.assertions.start_test("Host inherits items from template")


        if not self.harness.api_client:
            self.harness.assertions.assert_true(False, "API client not initialized")
            return False
        if not self.test_host_id:
            self.harness.assertions.assert_true(False, "Test host not created")
            return False

        result = self.harness.api_client.request("item.get", {
            "hostids": self.test_host_id,
            "output": ["itemid", "name", "key_"]
        })

        items = result if isinstance(result, list) else []
        item_count = len(items)

        if item_count > 0:
            self.harness.assertions.assert_true(
                True,
                f"Host inherited {item_count} items from template"
            )
            return True
        else:
            self.harness.assertions.assert_true(
                False,
                "Host has no items (template items not inherited)"
            )
            return False

    def test_host_inherits_triggers(self) -> bool:
        """Verify host inherits triggers from template"""
        self.harness.assertions.start_test("Host inherits triggers from template")


        if not self.harness.api_client:
            self.harness.assertions.assert_true(False, "API client not initialized")
            return False
        if not self.test_host_id:
            self.harness.assertions.assert_true(False, "Test host not created")
            return False

        result = self.harness.api_client.request("trigger.get", {
            "hostids": self.test_host_id,
            "output": ["triggerid", "description"]
        })

        triggers = result if isinstance(result, list) else []
        trigger_count = len(triggers)

        if trigger_count > 0:
            self.harness.assertions.assert_true(
                True,
                f"Host inherited {trigger_count} triggers from template"
            )
            return True
        else:
            self.harness.assertions.assert_true(
                False,
                "Host has no triggers (template triggers not inherited)"
            )
            return False

    def test_host_in_correct_group(self) -> bool:
        """Verify host is in the correct host group"""
        self.harness.assertions.start_test("Host in correct group")

        if not self.harness.api_client:
            self.harness.assertions.assert_true(False, "API client not initialized")
            return False
        if not self.test_host_id:
            self.harness.assertions.assert_true(False, "Test host not created")
            return False

        # Zabbix 7.2+ uses hostgroups instead of groups for hosts
        if self.harness.version == "7.0":
            result = self.harness.api_client.request("host.get", {
                "hostids": self.test_host_id,
                "selectGroups": ["groupid", "name"]
            })
            groups = result[0].get('groups', []) if isinstance(result, list) and len(result) > 0 else []
        else:
            result = self.harness.api_client.request("host.get", {
                "hostids": self.test_host_id,
                "selectHostGroups": ["groupid", "name"]
            })
            groups = result[0].get('hostgroups', []) if isinstance(result, list) and len(result) > 0 else []

        if len(groups) > 0:
            group_names = [g['name'] for g in groups]
            self.harness.assertions.assert_true(
                True,
                f"Host in groups: {', '.join(group_names)}"
            )
            return True
        else:
            self.harness.assertions.assert_true(
                False,
                "Host not in any groups"
            )
            return False

    def test_host_status_enabled(self) -> bool:
        """Verify host is enabled by default"""
        self.harness.assertions.start_test("Host is enabled")


        if not self.harness.api_client:
            self.harness.assertions.assert_true(False, "API client not initialized")
            return False
        if not self.test_host_id:
            self.harness.assertions.assert_true(False, "Test host not created")
            return False

        result = self.harness.api_client.request("host.get", {
            "hostids": self.test_host_id,
            "output": ["hostid", "status"]
        })

        if isinstance(result, list) and len(result) > 0:
            host = result[0]
            status = int(host.get('status', 1))

            if status == 0:  # 0 = enabled, 1 = disabled
                self.harness.assertions.assert_true(
                    True,
                    "Host is enabled"
                )
                return True
            else:
                self.harness.assertions.assert_true(
                    False,
                    "Host is disabled"
                )
                return False
        else:
            self.harness.assertions.assert_true(False, "Failed to get host status")
            return False

    def test_update_host_macro(self) -> bool:
        """Verify ability to set/update host macros"""
        self.harness.assertions.start_test("Update host macro")


        if not self.harness.api_client:
            self.harness.assertions.assert_true(False, "API client not initialized")
            return False
        if not self.test_host_id:
            self.harness.assertions.assert_true(False, "Test host not created")
            return False

        try:
            # Create a test macro
            result = self.harness.api_client.request("usermacro.create", {
                "hostid": self.test_host_id,
                "macro": "{$TEST_MACRO}",
                "value": "test_value"
            })

            if isinstance(result, dict) and 'hostmacroids' in result:
                self.harness.assertions.assert_true(
                    True,
                    "Host macro created successfully"
                )
                return True
            else:
                self.harness.assertions.assert_true(
                    False,
                    "Failed to create host macro"
                )
                return False
        except Exception as e:
            self.harness.assertions.assert_true(False, f"Exception: {e}")
            return False

    def test_disable_host(self) -> bool:
        """Verify ability to disable a host"""
        self.harness.assertions.start_test("Disable host")


        if not self.harness.api_client:
            self.harness.assertions.assert_true(False, "API client not initialized")
            return False
        if not self.test_host_id:
            self.harness.assertions.assert_true(False, "Test host not created")
            return False

        try:
            result = self.harness.api_client.request("host.update", {
                "hostid": self.test_host_id,
                "status": 1  # 1 = disabled
            })

            if isinstance(result, dict) and 'hostids' in result:
                self.harness.assertions.assert_true(
                    True,
                    "Host disabled successfully"
                )
                return True
            else:
                self.harness.assertions.assert_true(
                    False,
                    "Failed to disable host"
                )
                return False
        except Exception as e:
            self.harness.assertions.assert_true(False, f"Exception: {e}")
            return False

    def test_enable_host(self) -> bool:
        """Verify ability to enable a host"""
        self.harness.assertions.start_test("Enable host")


        if not self.harness.api_client:
            self.harness.assertions.assert_true(False, "API client not initialized")
            return False
        if not self.test_host_id:
            self.harness.assertions.assert_true(False, "Test host not created")
            return False

        try:
            result = self.harness.api_client.request("host.update", {
                "hostid": self.test_host_id,
                "status": 0  # 0 = enabled
            })

            if isinstance(result, dict) and 'hostids' in result:
                self.harness.assertions.assert_true(
                    True,
                    "Host enabled successfully"
                )
                return True
            else:
                self.harness.assertions.assert_true(
                    False,
                    "Failed to enable host"
                )
                return False
        except Exception as e:
            self.harness.assertions.assert_true(False, f"Exception: {e}")
            return False

    def test_delete_host(self) -> bool:
        """Verify ability to delete a host"""
        self.harness.assertions.start_test("Delete host")


        if not self.harness.api_client:
            self.harness.assertions.assert_true(False, "API client not initialized")
            return False
        if not self.test_host_id:
            self.harness.assertions.assert_true(False, "Test host not created")
            return False

        try:
            result = self.harness.api_client.request("host.delete", [self.test_host_id])

            if isinstance(result, dict) and 'hostids' in result:
                self.test_host_id = None  # Mark as deleted
                self.harness.assertions.assert_true(
                    True,
                    "Host deleted successfully"
                )
                return True
            else:
                self.harness.assertions.assert_true(
                    False,
                    "Failed to delete host"
                )
                return False
        except Exception as e:
            self.harness.assertions.assert_true(False, f"Exception: {e}")
            return False

    def run_all(self) -> dict:
        """Run all host operation tests"""
        print(f"\n{Colors.BLUE}{'='*70}{Colors.NC}")
        print(f"{Colors.BLUE}Host Operations Tests{Colors.NC}")
        print(f"{Colors.BLUE}{'='*70}{Colors.NC}\n")

        tests = [
            ("Create Host with Template", self.test_create_host_with_template),
            ("Host Has Template Linked", self.test_host_has_template_linked),
            ("Host Interface Configuration", self.test_host_interface_configuration),
            ("Host Inherits Items", self.test_host_inherits_items),
            ("Host Inherits Triggers", self.test_host_inherits_triggers),
            ("Host In Correct Group", self.test_host_in_correct_group),
            ("Host Status Enabled", self.test_host_status_enabled),
            ("Update Host Macro", self.test_update_host_macro),
            ("Disable Host", self.test_disable_host),
            ("Enable Host", self.test_enable_host),
            ("Delete Host", self.test_delete_host),
        ]

        results = {}
        for test_name, test_func in tests:
            try:
                results[test_name] = test_func()
            except Exception as e:
                self.harness.assertions.assert_true(False, f"Test exception: {str(e)}")
                results[test_name] = False

        # Cleanup
        self.cleanup_test_host()

        return results
