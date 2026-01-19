#!/usr/bin/env python3
"""
Integration tests for Zabbix 7.2
"""

import argparse
import sys

from zabbix_test_base import ZabbixTestBase


class Zabbix72Test(ZabbixTestBase):
    """Test harness for Zabbix 7.2 integration"""

    def __init__(self):
        super().__init__(
            version="7.2",
            compose_version_file="docker-compose.zabbix72.yml",
            project_name="zabbix-test-72"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Zabbix 7.2 Integration Tests")
    parser.add_argument('--keep', action='store_true', help='Keep Docker stack running after tests')
    parser.add_argument('--skip-startup', action='store_true', help='Skip Docker startup if containers already running')
    args = parser.parse_args()

    test = Zabbix72Test()
    test.keep_running = args.keep
    sys.exit(test.run_all_tests(skip_if_running=args.skip_startup))
