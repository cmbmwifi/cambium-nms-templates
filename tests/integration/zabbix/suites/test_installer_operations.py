#!/usr/bin/env python3
"""
Installer Operations Test Suite

Tests installer functionality with Zabbix including:
- flush_hosts option removes old OLT hosts
- flush_template option removes/recreates template
- add_hosts option creates new hosts
"""

import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple

# Support both package imports and direct script execution
try:
    from ..base.test_harness import ZabbixTestHarness, Colors  # type: ignore[no-redef]
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from base.test_harness import ZabbixTestHarness, Colors  # type: ignore[no-redef]


TEMPLATE_NAME = "Cambium Fiber OLT by SSH v1.3.0"


class InstallerOperationsTests:
    """Installer operations test suite"""

    def __init__(self, harness: ZabbixTestHarness):
        self.harness = harness
        self.repo_root = harness.repo_root

    def run_installer_with_env(self, env_vars: dict) -> Tuple[int, str]:
        """Run installer with environment variables inside Docker container"""
        env = {
            "ZABBIX_API_URL": "http://localhost:8080",
            "ZABBIX_API_TOKEN": self.harness.api_token or "",
            "OLT_PASSWORD": self.harness.olt_password,
            **env_vars
        }

        # Get the web container name
        web_container = self.harness.docker.get_container_name("web")

        # Install dependencies (idempotent - safe to run multiple times, run as root)
        subprocess.run(
            ["docker", "exec", "--user", "root", web_container, "sh", "-c",
             "apk add --no-cache python3 py3-yaml sshpass openssh-client bash 2>/dev/null || true"],
            capture_output=True
        )

        # Build docker exec command with environment variables (run as root)
        cmd = ["docker", "exec", "--user", "root"]
        for key, value in env.items():
            cmd.extend(["-e", f"{key}={value}"])
        cmd.extend([
            web_container,
            "/bin/bash", "-c",
            "cd /opt/cambium-nms-templates && ./install.sh --local"
        ])

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )

        return result.returncode, result.stdout + result.stderr

    def test_flush_hosts_removes_old_hosts(self) -> bool:
        """Verify flush_hosts option removes old OLT hosts when re-running installer"""
        self.harness.assertions.start_test("flush_hosts removes old OLT hosts")

        if not self.harness.api_client:
            self.harness.assertions.assert_true(False, "API client not initialized")
            return False

        template = self.harness.api_client.get_template(TEMPLATE_NAME)
        if not template:
            self.harness.assertions.assert_true(False, "Template not found")
            return False

        template_id = template['templateid']

        try:
            # Step 1: Run installer with both OLTs
            env_initial = {
                "OLT_IPS": f"{self.harness.mock_olt_1},{self.harness.mock_olt_2}",
                "FLUSH_TEMPLATE": "false",
                "FLUSH_HOSTS": "false",
                "ADD_HOSTS": "true"
            }

            exit_code, output = self.run_installer_with_env(env_initial)
            if exit_code != 0:
                self.harness.assertions.assert_true(
                    False,
                    f"Initial install with 2 OLTs failed (exit {exit_code})",
                    output[:500]
                )
                return False

            # Step 2: Verify both hosts exist
            hosts_response = self.harness.api_client.request("host.get", {
                "templateids": [template_id],
                "output": ["hostid", "host"],
                "selectInterfaces": ["ip"]
            })

            if not isinstance(hosts_response, list):
                self.harness.assertions.assert_true(False, "Failed to get hosts")
                return False

            initial_host_ips = []
            for host in hosts_response:
                if host.get('interfaces'):
                    initial_host_ips.extend([iface['ip'] for iface in host['interfaces']])

            both_olts_exist = (self.harness.mock_olt_1 in initial_host_ips and
                             self.harness.mock_olt_2 in initial_host_ips)

            if not both_olts_exist:
                self.harness.assertions.assert_true(
                    False,
                    "Both OLT hosts not created in initial install",
                    f"Found IPs: {initial_host_ips}"
                )
                return False

            # Step 3: Re-run installer with only first OLT and flush_hosts=true
            env_flush = {
                "OLT_IPS": self.harness.mock_olt_1,
                "FLUSH_TEMPLATE": "false",
                "FLUSH_HOSTS": "true",
                "ADD_HOSTS": "true"
            }

            exit_code, output = self.run_installer_with_env(env_flush)
            if exit_code != 0:
                self.harness.assertions.assert_true(
                    False,
                    f"Reinstall with flush_hosts failed (exit {exit_code})",
                    output[:500]
                )
                return False

            # Step 4: Verify only first OLT remains
            final_hosts_response = self.harness.api_client.request("host.get", {
                "templateids": [template_id],
                "output": ["hostid", "host"],
                "selectInterfaces": ["ip"]
            })

            if not isinstance(final_hosts_response, list):
                self.harness.assertions.assert_true(False, "Failed to get hosts after flush")
                return False

            final_host_ips = []
            for host in final_hosts_response:
                if host.get('interfaces'):
                    final_host_ips.extend([iface['ip'] for iface in host['interfaces']])

            # Expected: Only mock_olt_1 should remain, mock_olt_2 should be gone
            flush_worked = (self.harness.mock_olt_1 in final_host_ips and
                          self.harness.mock_olt_2 not in final_host_ips)

            self.harness.assertions.assert_true(
                flush_worked,
                f"flush_hosts removed {self.harness.mock_olt_2}, kept {self.harness.mock_olt_1}",
                f"Expected only {self.harness.mock_olt_1}, found: {final_host_ips}"
            )
            return flush_worked

        except Exception as e:
            self.harness.assertions.assert_true(False, f"Test exception: {str(e)}")
            return False

    def test_flush_template_resets_modified_template(self) -> bool:
        """Verify flush_template option removes/recreates template when modified"""
        self.harness.assertions.start_test("flush_template resets modified template")

        if not self.harness.api_client:
            self.harness.assertions.assert_true(False, "API client not initialized")
            return False

        template = self.harness.api_client.get_template(TEMPLATE_NAME)
        if not template:
            self.harness.assertions.assert_true(False, "Template not found")
            return False

        try:
            original_template_id = template['templateid']
            original_name = template['name']
            modified_name = f"{original_name} [MODIFIED-TEST]"

            # Step 1: Create a test host linked to the template BEFORE flush
            test_host_name = f"{self.harness.mock_olt_1}-flush-test"
            groups_result = self.harness.api_client.request("hostgroup.get", {
                "filter": {"name": "Integration Tests"},
                "output": ["groupid"]
            })
            groups = groups_result if isinstance(groups_result, list) else []
            if not groups:
                create_result = self.harness.api_client.request("hostgroup.create", {
                    "name": "Integration Tests"
                })
                test_hostgroup_id = create_result['groupids'][0] if isinstance(create_result, dict) and 'groupids' in create_result else None
            else:
                test_hostgroup_id = groups[0]['groupid']

            host_result = self.harness.api_client.request("host.create", {
                "host": test_host_name,
                "name": "Flush Template Test Host",
                "groups": [{"groupid": test_hostgroup_id}],
                "templates": [{"templateid": original_template_id}],
                "interfaces": [{
                    "type": 1,
                    "main": 1,
                    "useip": 1,
                    "ip": self.harness.mock_olt_1,
                    "dns": "",
                    "port": "10050"
                }]
            })

            if not (isinstance(host_result, dict) and 'hostids' in host_result):
                self.harness.assertions.assert_true(False, "Failed to create test host")
                return False

            test_host_id = host_result['hostids'][0]

            # Step 2: Modify template name via API
            update_result = self.harness.api_client.request("template.update", {
                "templateid": original_template_id,
                "name": modified_name
            })

            if not (isinstance(update_result, dict) and 'templateids' in update_result):
                self.harness.assertions.assert_true(False, "Failed to modify template name")
                return False

            # Verify modification
            modified_template = self.harness.api_client.request("template.get", {
                "templateids": [original_template_id],
                "output": ["templateid", "name"]
            })

            if not (isinstance(modified_template, list) and len(modified_template) > 0):
                self.harness.assertions.assert_true(False, "Failed to get modified template")
                return False

            if modified_template[0]['name'] != modified_name:
                self.harness.assertions.assert_true(
                    False,
                    "Template name not modified correctly"
                )
                return False

            # Step 3: Run installer with flush_template=true
            env_flush = {
                "OLT_IPS": self.harness.mock_olt_1,
                "FLUSH_TEMPLATE": "true",
                "FLUSH_HOSTS": "false",
                "ADD_HOSTS": "false"
            }

            exit_code, output = self.run_installer_with_env(env_flush)
            if exit_code != 0:
                self.harness.assertions.assert_true(
                    False,
                    f"Reinstall with flush_template failed (exit {exit_code})",
                    output[:500]
                )
                # Try to restore template name and cleanup host on error
                try:
                    self.harness.api_client.request("template.update", {
                        "templateid": original_template_id,
                        "name": original_name
                    })
                    self.harness.api_client.request("host.delete", [test_host_id])
                except:
                    pass
                return False

            # Step 4: Verify template name restored to original
            final_template = self.harness.api_client.request("template.get", {
                "filter": {"host": TEMPLATE_NAME},
                "output": ["templateid", "name"]
            })

            if not (isinstance(final_template, list) and len(final_template) > 0):
                self.harness.assertions.assert_true(False, "Template not found after flush")
                # Cleanup test host
                try:
                    self.harness.api_client.request("host.delete", [test_host_id])
                except:
                    pass
                return False

            final_name = final_template[0]['name']
            new_template_id = final_template[0]['templateid']
            template_restored = final_name == original_name and final_name != modified_name

            if not template_restored:
                self.harness.assertions.assert_true(
                    False,
                    f"Template name not restored: Expected '{original_name}', found '{final_name}'"
                )
                # Cleanup test host
                try:
                    self.harness.api_client.request("host.delete", [test_host_id])
                except:
                    pass
                return False

            # Step 5: Check if test host still exists and is linked to new template
            host_check = self.harness.api_client.request("host.get", {
                "hostids": [test_host_id],
                "output": ["hostid", "host"],
                "selectParentTemplates": ["templateid", "name"]
            })

            if not (isinstance(host_check, list) and len(host_check) > 0):
                self.harness.assertions.assert_true(
                    False,
                    "CRITICAL: Host was deleted when template flushed! Existing hosts should be preserved."
                )
                return False

            host_templates = host_check[0].get('parentTemplates', [])
            host_has_new_template = any(t['templateid'] == new_template_id for t in host_templates)

            # Cleanup test host
            try:
                self.harness.api_client.request("host.delete", [test_host_id])
            except:
                pass

            if not host_has_new_template:
                self.harness.assertions.assert_true(
                    False,
                    f"CRITICAL: Host survived but lost template link! Host should be linked to new template. Templates: {[t.get('name') for t in host_templates]}"
                )
                return False

            self.harness.assertions.assert_true(
                True,
                f"flush_template restored name to '{original_name}' AND existing host relinked to new template"
            )
            return True

        except Exception as e:
            self.harness.assertions.assert_true(False, f"Test exception: {str(e)}")
            # Try to restore template name on error
            try:
                if self.harness.api_client:
                    self.harness.api_client.request("template.update", {
                        "templateid": original_template_id,
                        "name": original_name
                    })
            except:
                pass
            return False

    def test_flush_template_on_first_install(self) -> bool:
        """Verify flush_template works safely when no template exists yet"""
        self.harness.assertions.start_test("flush_template works on first install (no existing template)")

        if not self.harness.api_client:
            self.harness.assertions.assert_true(False, "API client not initialized")
            return False

        try:
            # Step 1: Delete template if it exists to simulate first install
            template = self.harness.api_client.get_template(TEMPLATE_NAME)
            if template:
                self.harness.api_client.request("template.delete", [template['templateid']])

            # Step 2: Run installer with flush_template=true on first install
            env_flush = {
                "OLT_IPS": self.harness.mock_olt_1,
                "FLUSH_TEMPLATE": "true",
                "FLUSH_HOSTS": "false",
                "ADD_HOSTS": "false"
            }

            exit_code, output = self.run_installer_with_env(env_flush)
            if exit_code != 0:
                self.harness.assertions.assert_true(
                    False,
                    f"First install with flush_template failed (exit {exit_code})",
                    output[:500]
                )
                return False

            # Step 3: Verify template was created successfully
            final_template = self.harness.api_client.request("template.get", {
                "filter": {"host": TEMPLATE_NAME},
                "output": ["templateid", "name"]
            })

            if not (isinstance(final_template, list) and len(final_template) > 0):
                self.harness.assertions.assert_true(
                    False,
                    "Template not created after first install with flush_template=true"
                )
                return False

            self.harness.assertions.assert_true(
                True,
                "flush_template works safely on first install (no template existed)"
            )
            return True

        except Exception as e:
            self.harness.assertions.assert_true(False, f"Test exception: {str(e)}")
            return False

    def test_add_hosts_preserves_existing(self) -> bool:
        """Verify add_hosts=true with flush_hosts=false preserves existing hosts"""
        self.harness.assertions.start_test("add_hosts preserves existing hosts when flush_hosts=false")

        if not self.harness.api_client:
            self.harness.assertions.assert_true(False, "API client not initialized")
            return False

        template = self.harness.api_client.get_template(TEMPLATE_NAME)
        if not template:
            self.harness.assertions.assert_true(False, "Template not found")
            return False

        template_id = template['templateid']

        try:
            # Step 1: Create initial host (.10)
            env_initial = {
                "OLT_IPS": self.harness.mock_olt_1,
                "FLUSH_TEMPLATE": "false",
                "FLUSH_HOSTS": "false",
                "ADD_HOSTS": "true"
            }

            exit_code, output = self.run_installer_with_env(env_initial)
            if exit_code != 0:
                self.harness.assertions.assert_true(
                    False,
                    f"Initial install with first OLT failed (exit {exit_code})",
                    output[:500]
                )
                return False

            # Step 2: Verify first host exists
            initial_hosts = self.harness.api_client.request("host.get", {
                "templateids": [template_id],
                "output": ["hostid", "host"],
                "selectInterfaces": ["ip"]
            })

            if not isinstance(initial_hosts, list):
                self.harness.assertions.assert_true(False, "Failed to get initial hosts")
                return False

            initial_host_ips = []
            for host in initial_hosts:
                if host.get('interfaces'):
                    initial_host_ips.extend([iface['ip'] for iface in host['interfaces']])

            if self.harness.mock_olt_1 not in initial_host_ips:
                self.harness.assertions.assert_true(
                    False,
                    "First OLT host not created in initial install",
                    f"Found IPs: {initial_host_ips}"
                )
                return False

            # Step 3: Add second host WITHOUT flush (should preserve first host)
            env_add = {
                "OLT_IPS": self.harness.mock_olt_2,
                "FLUSH_TEMPLATE": "false",
                "FLUSH_HOSTS": "false",
                "ADD_HOSTS": "true"
            }

            exit_code, output = self.run_installer_with_env(env_add)
            if exit_code != 0:
                self.harness.assertions.assert_true(
                    False,
                    f"Adding second OLT failed (exit {exit_code})",
                    output[:500]
                )
                return False

            # Step 4: Verify BOTH hosts now exist
            final_hosts = self.harness.api_client.request("host.get", {
                "templateids": [template_id],
                "output": ["hostid", "host"],
                "selectInterfaces": ["ip"]
            })

            if not isinstance(final_hosts, list):
                self.harness.assertions.assert_true(False, "Failed to get final hosts")
                return False

            final_host_ips = []
            for host in final_hosts:
                if host.get('interfaces'):
                    final_host_ips.extend([iface['ip'] for iface in host['interfaces']])

            # Expected: Both OLTs should exist
            both_exist = (self.harness.mock_olt_1 in final_host_ips and
                         self.harness.mock_olt_2 in final_host_ips)

            self.harness.assertions.assert_true(
                both_exist,
                f"add_hosts preserved {self.harness.mock_olt_1} and added {self.harness.mock_olt_2}",
                f"Expected both OLTs, found IPs: {final_host_ips}"
            )
            return both_exist

        except Exception as e:
            self.harness.assertions.assert_true(False, f"Test exception: {str(e)}")
            return False

    def test_flush_both_removes_all_old_hosts(self) -> bool:
        """Verify flush_template + flush_hosts removes ALL old hosts before adding new ones"""
        self.harness.assertions.start_test("flush_template + flush_hosts removes all old hosts")

        if not self.harness.api_client:
            self.harness.assertions.assert_true(False, "API client not initialized")
            return False

        try:
            # Step 1: Install with two OLTs (.10 and .11)
            env_two_olts = {
                "OLT_IPS": f"{self.harness.mock_olt_1},{self.harness.mock_olt_2}",
                "FLUSH_TEMPLATE": "false",
                "FLUSH_HOSTS": "false",
                "ADD_HOSTS": "true"
            }

            exit_code, output = self.run_installer_with_env(env_two_olts)
            if exit_code != 0:
                self.harness.assertions.assert_true(
                    False,
                    f"Initial install with two OLTs failed (exit {exit_code})",
                    output[:500]
                )
                return False

            # Step 2: Run with flush_template=true AND flush_hosts=true, add only .10
            env_flush_both = {
                "OLT_IPS": self.harness.mock_olt_1,  # Only .10
                "FLUSH_TEMPLATE": "true",
                "FLUSH_HOSTS": "true",
                "ADD_HOSTS": "true"
            }

            exit_code, output = self.run_installer_with_env(env_flush_both)
            if exit_code != 0:
                self.harness.assertions.assert_true(
                    False,
                    f"Flush both and reinstall failed (exit {exit_code})",
                    output[:500]
                )
                return False

            # Step 3: Verify only .10 exists (not .11)
            template = self.harness.api_client.get_template(TEMPLATE_NAME)
            if not template:
                self.harness.assertions.assert_true(False, "Template not found after flush")
                return False

            final_hosts = self.harness.api_client.request("host.get", {
                "templateids": [template['templateid']],
                "output": ["hostid", "host"],
                "selectInterfaces": ["ip"]
            })

            if not isinstance(final_hosts, list):
                self.harness.assertions.assert_true(False, "Failed to get final hosts")
                return False

            final_host_ips = []
            for host in final_hosts:
                if host.get('interfaces'):
                    final_host_ips.extend([iface['ip'] for iface in host['interfaces']])

            # Expected: Only .10 should exist, .11 should be gone
            only_olt1 = (self.harness.mock_olt_1 in final_host_ips and
                        self.harness.mock_olt_2 not in final_host_ips)

            self.harness.assertions.assert_true(
                only_olt1,
                f"flush_template + flush_hosts removed old hosts, created only {self.harness.mock_olt_1}",
                f"Expected only .10, found IPs: {final_host_ips}"
            )
            return only_olt1

        except Exception as e:
            self.harness.assertions.assert_true(False, f"Test exception: {str(e)}")
            return False

    def run_all(self) -> dict:
        """Run all installer operation tests"""
        print(f"\n{Colors.BLUE}{'='*70}{Colors.NC}")
        print(f"{Colors.BLUE}Installer Operations Tests{Colors.NC}")
        print(f"{Colors.BLUE}{'='*70}{Colors.NC}\n")

        tests = [
            ("Flush Hosts Removes Old Hosts", self.test_flush_hosts_removes_old_hosts),
            ("Flush Template Resets Modified Template", self.test_flush_template_resets_modified_template),
            ("Flush Template On First Install", self.test_flush_template_on_first_install),
            ("Add Hosts Preserves Existing", self.test_add_hosts_preserves_existing),
            ("Flush Both Removes All Old Hosts", self.test_flush_both_removes_all_old_hosts),
        ]

        results = {}
        for test_name, test_func in tests:
            try:
                results[test_name] = test_func()
            except Exception as e:
                self.harness.assertions.assert_true(False, f"Test exception: {str(e)}")
                results[test_name] = False

        return results
