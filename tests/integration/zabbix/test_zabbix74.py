#!/usr/bin/env python3
"""
Integration tests for Zabbix 7.4
"""

import argparse
import sys

from zabbix_test_base import ZabbixTestBase


class Zabbix74Test(ZabbixTestBase):
    """Test harness for Zabbix 7.4 integration"""

    def __init__(self):
        super().__init__(
            version="7.4",
            compose_version_file="docker-compose.zabbix74.yml",
            project_name="zabbix_7_4"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Zabbix 7.4 Integration Tests")
    parser.add_argument('--keep', action='store_true', help='Keep Docker stack running after tests')
    parser.add_argument('--skip-startup', action='store_true', help='Skip Docker startup if containers already running')
    parser.add_argument('--setup-only', action='store_true', help='Only start containers, do not run tests')
    parser.add_argument('--teardown-only', action='store_true', help='Only stop containers, do not run tests')
    args = parser.parse_args()

    test = Zabbix74Test()

    if args.setup_only:
        # Infrastructure should already be running, just start this Zabbix version
        test.setup(skip_if_running=True)
        sys.exit(0)
    elif args.teardown_only:
        test.teardown()
        sys.exit(0)
    else:
        test.keep_running = args.keep
        sys.exit(test.run_all_tests(skip_if_running=args.skip_startup))
