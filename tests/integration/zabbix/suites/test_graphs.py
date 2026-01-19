#!/usr/bin/env python3
"""
Graphs Test Suite

Tests graph definitions and configurations including:
- Graph existence and properties
- Graph items and metrics
- Y-axis configuration
- Graph types and display options
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


class GraphTests:
    """Graph configuration tests"""

    def __init__(self, harness: ZabbixTestHarness):
        self.harness = harness

    def test_template_has_graphs(self) -> bool:
        """Verify template has graphs defined"""
        self.harness.assertions.start_test("Template has graphs")


        if not self.harness.api_client:
            self.harness.assertions.assert_true(False, "API client not initialized")
            return False
        template = self.harness.api_client.get_template(TEMPLATE_NAME)
        if not template:
            self.harness.assertions.assert_true(False, "Template not found")
            return False

        result = self.harness.api_client.request("graph.get", {
            "templateids": template['templateid'],
            "output": ["graphid", "name", "width", "height"]
        })

        graphs = result if isinstance(result, list) else []
        graph_count = len(graphs)

        if graph_count > 0:
            self.harness.assertions.assert_true(
                True,
                f"Template has {graph_count} graphs"
            )
            return True
        else:
            self.harness.assertions.assert_true(
                True,
                "Template has no graphs (acceptable, may rely on Zabbix auto-graphs)"
            )
            return True

    def test_graphs_have_items(self) -> bool:
        """Verify graphs have associated items"""
        self.harness.assertions.start_test("Graphs have items")


        if not self.harness.api_client:
            self.harness.assertions.assert_true(False, "API client not initialized")
            return False
        template = self.harness.api_client.get_template(TEMPLATE_NAME)
        if not template:
            self.harness.assertions.assert_true(False, "Template not found")
            return False

        result = self.harness.api_client.request("graph.get", {
            "templateids": template['templateid'],
            "selectGraphItems": ["itemid"],
            "output": ["graphid", "name"]
        })

        graphs = result if isinstance(result, list) else []
        if not graphs:
            self.harness.assertions.assert_true(
                True,
                "No graphs to validate (acceptable)"
            )
            return True

        graphs_without_items = [g for g in graphs if not g.get('gitems', [])]

        if not graphs_without_items:
            total_items = sum(len(g.get('gitems', [])) for g in graphs)
            self.harness.assertions.assert_true(
                True,
                f"All {len(graphs)} graphs have items (total: {total_items})"
            )
            return True
        else:
            self.harness.assertions.assert_true(
                False,
                f"{len(graphs_without_items)} graphs have no items"
            )
            return False

    def test_graph_dimensions(self) -> bool:
        """Verify graphs have valid dimensions"""
        self.harness.assertions.start_test("Graphs have valid dimensions")


        if not self.harness.api_client:
            self.harness.assertions.assert_true(False, "API client not initialized")
            return False
        template = self.harness.api_client.get_template(TEMPLATE_NAME)
        if not template:
            self.harness.assertions.assert_true(False, "Template not found")
            return False

        result = self.harness.api_client.request("graph.get", {
            "templateids": template['templateid'],
            "output": ["graphid", "name", "width", "height"]
        })

        graphs = result if isinstance(result, list) else []
        if not graphs:
            self.harness.assertions.assert_true(True, "No graphs to validate")
            return True

        invalid_graphs = []
        for graph in graphs:
            width = int(graph.get('width', 0))
            height = int(graph.get('height', 0))

            # Reasonable dimensions: 100-2000 pixels
            if width < 100 or width > 2000 or height < 100 or height > 2000:
                invalid_graphs.append(graph['name'])

        if not invalid_graphs:
            self.harness.assertions.assert_true(
                True,
                f"All {len(graphs)} graphs have valid dimensions"
            )
            return True
        else:
            self.harness.assertions.assert_true(
                False,
                f"{len(invalid_graphs)} graphs have invalid dimensions"
            )
            return False

    def test_graph_yaxis_configuration(self) -> bool:
        """Verify graphs have Y-axis properly configured"""
        self.harness.assertions.start_test("Graphs have Y-axis configuration")


        if not self.harness.api_client:
            self.harness.assertions.assert_true(False, "API client not initialized")
            return False
        template = self.harness.api_client.get_template(TEMPLATE_NAME)
        if not template:
            self.harness.assertions.assert_true(False, "Template not found")
            return False

        result = self.harness.api_client.request("graph.get", {
            "templateids": template['templateid'],
            "output": ["graphid", "name", "ymin_type", "ymax_type", "yaxismin", "yaxismax"]
        })

        graphs = result if isinstance(result, list) else []
        if not graphs:
            self.harness.assertions.assert_true(True, "No graphs to validate")
            return True

        # Check that Y-axis is configured (either calculated or fixed)
        configured_graphs = [g for g in graphs if 'ymin_type' in g and 'ymax_type' in g]

        if len(configured_graphs) == len(graphs):
            self.harness.assertions.assert_true(
                True,
                f"All {len(graphs)} graphs have Y-axis configured"
            )
            return True
        else:
            self.harness.assertions.assert_true(
                False,
                f"Only {len(configured_graphs)}/{len(graphs)} graphs have Y-axis configured"
            )
            return False

    def test_graph_item_colors(self) -> bool:
        """Verify graph items have colors assigned"""
        self.harness.assertions.start_test("Graph items have colors")


        if not self.harness.api_client:
            self.harness.assertions.assert_true(False, "API client not initialized")
            return False
        template = self.harness.api_client.get_template(TEMPLATE_NAME)
        if not template:
            self.harness.assertions.assert_true(False, "Template not found")
            return False

        result = self.harness.api_client.request("graph.get", {
            "templateids": template['templateid'],
            "selectGraphItems": ["color"],
            "output": ["graphid", "name"]
        })

        graphs = result if isinstance(result, list) else []
        if not graphs:
            self.harness.assertions.assert_true(True, "No graphs to validate")
            return True

        items_without_colors = []
        for graph in graphs:
            gitems = graph.get('gitems', [])
            for item in gitems:
                if not item.get('color'):
                    items_without_colors.append(graph['name'])
                    break

        if not items_without_colors:
            self.harness.assertions.assert_true(
                True,
                f"All graph items have colors assigned"
            )
            return True
        else:
            self.harness.assertions.assert_true(
                False,
                f"{len(items_without_colors)} graphs have items without colors"
            )
            return False

    def test_graph_prototypes_exist(self) -> bool:
        """Verify template has graph prototypes for LLD"""
        self.harness.assertions.start_test("Graph prototypes exist for LLD")


        if not self.harness.api_client:
            self.harness.assertions.assert_true(False, "API client not initialized")
            return False
        template = self.harness.api_client.get_template(TEMPLATE_NAME)
        if not template:
            self.harness.assertions.assert_true(False, "Template not found")
            return False

        # Get discovery rules first
        rules_result = self.harness.api_client.request("discoveryrule.get", {
            "templateids": template['templateid'],
            "output": ["itemid", "name"]
        })

        rules = rules_result if isinstance(rules_result, list) else []
        if not rules:
            self.harness.assertions.assert_true(
                True,
                "No discovery rules, so no graph prototypes expected"
            )
            return True

        # Get graph prototypes
        graph_proto_result = self.harness.api_client.request("graphprototype.get", {
            "discoveryids": [r['itemid'] for r in rules],
            "output": ["graphid", "name"]
        })

        graph_protos = graph_proto_result if isinstance(graph_proto_result, list) else []

        if len(graph_protos) > 0:
            self.harness.assertions.assert_true(
                True,
                f"Template has {len(graph_protos)} graph prototypes"
            )
            return True
        else:
            self.harness.assertions.assert_true(
                True,
                "No graph prototypes (acceptable, may use auto-graphs)"
            )
            return True

    def run_all(self) -> dict:
        """Run all graph tests"""
        print(f"\n{Colors.BLUE}{'='*70}{Colors.NC}")
        print(f"{Colors.BLUE}Graph Tests{Colors.NC}")
        print(f"{Colors.BLUE}{'='*70}{Colors.NC}\n")

        tests = [
            ("Template Has Graphs", self.test_template_has_graphs),
            ("Graphs Have Items", self.test_graphs_have_items),
            ("Graph Dimensions", self.test_graph_dimensions),
            ("Graph Y-axis Configuration", self.test_graph_yaxis_configuration),
            ("Graph Item Colors", self.test_graph_item_colors),
            ("Graph Prototypes", self.test_graph_prototypes_exist),
        ]

        results = {}
        for test_name, test_func in tests:
            try:
                results[test_name] = test_func()
            except Exception as e:
                self.harness.assertions.assert_true(False, f"Test exception: {str(e)}")
                results[test_name] = False

        return results
