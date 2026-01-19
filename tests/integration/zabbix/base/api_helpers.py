#!/usr/bin/env python3
"""
Zabbix API client for integration tests.

Provides a clean interface for making Zabbix API calls with version-specific
authentication handling.
"""

from typing import Any, Dict, List, Optional, Union

try:
    import requests
except ImportError:
    raise ImportError("requests is required. Install with: pip install requests")


class ZabbixAPIClient:
    """
    Zabbix API client with version-aware authentication.

    Automatically handles authentication differences between Zabbix 7.0
    (auth field in payload) and Zabbix 7.2+ (Bearer token in header).
    """

    def __init__(self, base_url: str, api_token: str, version: str):
        """
        Initialize API client.

        Args:
            base_url: Zabbix base URL (e.g., "http://localhost:8080")
            api_token: API authentication token
            version: Zabbix version (e.g., "7.0", "7.2", "7.4")
        """
        self.base_url = base_url.rstrip("/")
        self.api_url = f"{self.base_url}/api_jsonrpc.php"
        self.api_token = api_token
        self.version = version
        self._request_id = 1

    def request(self, method: str, params: Optional[Union[Dict[str, Any], List[Any]]] = None, skip_auth: bool = False) -> Union[Dict[str, Any], List[Any]]:
        """
        Make Zabbix API request.

        Args:
            method: API method name (e.g., "host.get", "template.get")
            params: Method parameters (dict or list depending on the method)
            skip_auth: If True, don't send authentication (needed for apiinfo.version)

        Returns:
            API response result

        Raises:
            RuntimeError: If API request fails
        """
        if params is None:
            params = {}

        self._request_id += 1

        if skip_auth or method == "apiinfo.version":
            # Methods like apiinfo.version must be called without authentication
            response = requests.post(
                self.api_url,
                json={
                    "jsonrpc": "2.0",
                    "method": method,
                    "params": params,
                    "id": self._request_id
                },
                headers={"Content-Type": "application/json"},
                timeout=10
            )
        elif self.version == "7.0":
            # Zabbix 7.0 uses auth field in payload
            response = requests.post(
                self.api_url,
                json={
                    "jsonrpc": "2.0",
                    "method": method,
                    "params": params,
                    "auth": self.api_token,
                    "id": self._request_id
                },
                headers={"Content-Type": "application/json"},
                timeout=10
            )
        else:
            # Zabbix 7.2+ uses Bearer token in header
            response = requests.post(
                self.api_url,
                json={
                    "jsonrpc": "2.0",
                    "method": method,
                    "params": params,
                    "id": self._request_id
                },
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_token}"
                },
                timeout=10
            )

        result = response.json()

        if "error" in result:
            error_data = result["error"]
            raise RuntimeError(f"API error: {error_data.get('message')} - {error_data.get('data')}")

        return result.get("result", {})

    def get_template(self, template_name: str) -> Optional[Dict[str, Any]]:
        """
        Get template by name.

        Args:
            template_name: Template name to search for

        Returns:
            Template dict or None if not found
        """
        result = self.request("template.get", {"filter": {"host": template_name}})
        if isinstance(result, list) and len(result) > 0:
            return result[0]
        return None

    def get_host(self, identifier: str) -> Optional[Dict[str, Any]]:
        """
        Get host by IP or hostname.

        Args:
            identifier: IP address or hostname

        Returns:
            Host dict or None if not found
        """
        search_by = "ip" if "." in identifier else "host"

        if search_by == "ip":
            result = self.request("host.get", {
                "filter": {"ip": identifier},
                "output": ["hostid", "host", "name"],
                "selectInterfaces": ["ip"]
            })
        else:
            result = self.request("host.get", {
                "filter": {"host": identifier},
                "output": ["hostid", "host", "name"]
            })

        if isinstance(result, list) and len(result) > 0:
            return result[0]
        return None

    def get_items(self, hostid: str, **filters: Any) -> list:
        """
        Get items for a host with optional filters.

        Args:
            hostid: Host ID
            **filters: Additional filter parameters

        Returns:
            List of item dicts
        """
        params: Dict[str, Any] = {
            "hostids": [hostid],
            "output": "extend"
        }
        if filters:
            params["filter"] = filters

        result = self.request("item.get", params)
        return result if isinstance(result, list) else []

    def get_items_with_errors(self, hostid: str) -> list:
        """
        Get items in unsupported state (with errors).

        Args:
            hostid: Host ID

        Returns:
            List of item dicts with errors
        """
        result = self.request("item.get", {
            "hostids": [hostid],
            "output": ["itemid", "name", "key_", "state", "error"],
            "filter": {"state": 1}  # State 1 = not supported
        })
        return result if isinstance(result, list) else []

    def get_triggers(self, hostid: str) -> list:
        """
        Get triggers for a host.

        Args:
            hostid: Host ID

        Returns:
            List of trigger dicts
        """
        result = self.request("trigger.get", {
            "hostids": [hostid],
            "output": "extend"
        })
        return result if isinstance(result, list) else []

    def get_active_problems(self, hostid: str) -> list:
        """
        Get active problems for a host.

        Args:
            hostid: Host ID

        Returns:
            List of problem dicts
        """
        result = self.request("problem.get", {
            "hostids": [hostid],
            "output": ["eventid", "name", "severity"],
            "recent": True
        })
        return result if isinstance(result, list) else []

    def get_discovery_rules(self, hostid: str) -> list:
        """
        Get discovery rules for a host.

        Args:
            hostid: Host ID

        Returns:
            List of discovery rule dicts
        """
        result = self.request("discoveryrule.get", {
            "hostids": [hostid],
            "output": ["itemid", "name", "state", "error"],
            "selectHosts": ["host"]
        })
        return result if isinstance(result, list) else []

    def get_graphs(self, hostid: str) -> list:
        """
        Get graphs for a host.

        Args:
            hostid: Host ID

        Returns:
            List of graph dicts
        """
        result = self.request("graph.get", {
            "hostids": [hostid],
            "output": ["graphid", "name"]
        })
        return result if isinstance(result, list) else []

    def get_graph_prototypes(self, discoveryid: str) -> list:
        """
        Get graph prototypes for a discovery rule.

        Args:
            discoveryid: Discovery rule ID

        Returns:
            List of graph prototype dicts
        """
        result = self.request("graphprototype.get", {
            "discoveryids": [discoveryid],
            "output": ["graphid", "name"]
        })
        return result if isinstance(result, list) else []
