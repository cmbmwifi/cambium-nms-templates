"""Test suites for Zabbix integration testing."""

from .test_core_functionality import CoreFunctionalityTests
from .test_template_health import TemplateHealthTests
from .test_graphs import GraphTests
from .test_host_operations import HostOperationsTests
from .test_item_data_collection import ItemDataCollectionTests
from .test_advanced_features import AdvancedFeaturesTests

__all__ = [
    "CoreFunctionalityTests",
    "TemplateHealthTests",
    "GraphTests",
    "HostOperationsTests",
    "ItemDataCollectionTests",
    "AdvancedFeaturesTests",
]

