#!/bin/sh
# Install dependencies needed by install.sh in the Zabbix web container
apk add --no-cache python3 py3-yaml sshpass openssh-client bash 2>/dev/null || true
