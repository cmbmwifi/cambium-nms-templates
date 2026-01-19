#!/usr/bin/env python3
"""
Integration tests for Zabbix 7.0 LTS
"""

import argparse
import sys

from zabbix_test_base import ZabbixTestBase


class Zabbix70Test(ZabbixTestBase):
    """Test harness for Zabbix 7.0 LTS integration"""

    def __init__(self):
        super().__init__(
            version="7.0",
            compose_version_file="docker-compose.zabbix70.yml",
            project_name="zabbix-test-70"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Zabbix 7.0 Integration Tests")
    parser.add_argument('--keep', action='store_true', help='Keep Docker stack running after tests')
    parser.add_argument('--skip-startup', action='store_true', help='Skip Docker startup if containers already running')
    args = parser.parse_args()

    test = Zabbix70Test()
    test.keep_running = args.keep
    sys.exit(test.run_all_tests(skip_if_running=args.skip_startup))
