# Cambium NMS Templates

Monitoring templates for Cambium Networks devices on Zabbix, LibreNMS, and other NMS platforms.

**Author:** [Joshaven Potter](https://github.com/joshaven) - Cambium Fiber System Architect

## Quick Start

**Important:** This installer must be run as root to install system dependencies and scripts.

**If you're already root (Proxmox LXC containers, etc.):**
```bash
curl -o- https://raw.githubusercontent.com/cmbmwifi/cambium-nms-templates/refs/heads/main/install.sh | bash
```

**If you're not root, install with sudo:**
```bash
curl -o- https://raw.githubusercontent.com/cmbmwifi/cambium-nms-templates/refs/heads/main/install.sh | sudo bash
```

The interactive menu will guide you through installing the template.

**Note:** Requires `curl`. On Debian-based systems: `apt install curl`

## What's Available

- **Cambium Fiber OLT** - Zabbix template with SSH monitoring
- Additional templates may be added based on community interest

## Requirements

- Zabbix 7.0+ (or your NMS platform)
- SSH access to devices
- **Root access on NMS server** (required for installing dependencies and scripts)
- curl to run the installer
- Python 3.8+ (for external scripts)

## Support and Disclaimer

This project is **built by Cambium Networks engineers** as a best-effort
community tool to assist customers and partners.

**This is not an officially supported Cambium Networks product** and is **not
covered under Cambium Support contracts or SLAs**.

This project provides monitoring templates/scripts only. **Cambium Networks is
not responsible for the installation, administration, availability, security,
or performance of third-party NMS platforms (Zabbix, LibreNMS, etc.), their
databases, operating systems, or hosting infrastructure.** Troubleshooting of
the NMS platform and hosting environment (e.g., OS packages, databases,
permissions, networking, storage) is out of scope.

**Community support** - please use GitHub issues for questions and bug reports.

**Cambium Networks Support (TAC) does not provide support for this project.**
Use of this software is at your own discretion and risk.

## Contributing

Contributions are welcome! See [docs/contributing.md](docs/contributing.md) for development setup and guidelines.

**Using AI assistants?** This project includes `.agentic` configuration to help AI coding tools understand the codebase structure, conventions, and common workflows.

## License

Apache License 2.0 - See [LICENSE](LICENSE) file for details.


