# Cambium NMS Templates

Monitoring templates for Cambium Networks devices on Zabbix, LibreNMS, and other NMS platforms.

## Quick Start

Run this command on your NMS server:

```bash
curl -o- https://raw.githubusercontent.com/cmbmwifi/cambium-nms-templates/refs/heads/main/install.sh | bash
```

The interactive menu will guide you through installing the template.

## What's Available

- **Cambium Fiber OLT** - Zabbix template with SSH monitoring
- More options may be added upon request

## Requirements

- Zabbix 7.0+ (or your NMS platform)
- SSH access to devices
- Root/sudo access on NMS server
- curl to run the installer
- Python 3.8+ (for external scripts)

## Support and Disclaimer

This project is **built and maintained by Cambium Networks engineering** as a
best-effort tool to assist customers and partners.

**This is not an officially supported Cambium Networks product** and is **not
covered under Cambium Support contracts or SLAs**.

This project provides monitoring templates/scripts only. **Cambium Networks is
not responsible for the installation, administration, availability, security,
or performance of Zabbix, its database, the operating system, or the servers/VMs
running Zabbix.** Troubleshooting of the NMS platform and hosting environment
(e.g., OS packages, MySQL/PostgreSQL, permissions, networking, storage) is out
of scope.

Support is provided on a **best-effort basis** via:
- GitHub issues
- Direct contact with the author [Joshaven Potter](mailto:Joshaven.Potter@CambiumNetworks.com)

Cambium Networks Support (TAC) does not provide support for this project.
Use of this software is at your own discretion.


