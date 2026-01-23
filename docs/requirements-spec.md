# Requirements Specification

## Philosophy

A template's `requirements.yaml` file is a declarative contract between the template and the installer. It describes *what* is needed, not *how* to install it. The installer interprets this contract and handles all platform-specific details.

## Design Principles

### Separation of Concerns

**Template Author Responsibility:**
- Define what the template needs (Python packages, macros, inputs)
- Specify conditional logic for workflows
- Document required configuration

**Installer Responsibility:**
- Parse requirements
- Collect user inputs
- Install dependencies
- Configure NMS platform
- Deploy template and scripts

This separation allows templates to evolve independently from installer logic.

### Declarative Configuration

Templates declare requirements; they don't script installation steps. This enables:
- Platform-agnostic template definitions
- Automatic validation before installation
- Interactive and non-interactive modes from the same definition
- Dynamic menu generation without code changes

## Core Concepts

### Metadata

Templates identify themselves and their purpose:
- NMS platform (zabbix, librenms, opennms)
- Product category (cambium-fiber, cnpilot, epmp)
- Version compatibility
- Human-readable description

### Dependencies

Templates declare external dependencies:
- Python packages required by external scripts
- System requirements
- NMS platform version constraints

### Configuration Inputs

Templates request configuration from users:
- Text inputs (IP addresses, credentials)
- Boolean flags (enable features)
- Multi-line inputs (bulk configuration)

**Conditional Logic:** Inputs can be shown conditionally based on other input values, enabling context-aware workflows without complex scripting.

### Platform Integration

Templates specify how they integrate with the NMS:
- Macro definitions and default values
- Whether to automatically create monitored hosts
- Custom hooks for platform-specific logic

## Workflow Theory

1. **Discovery**: Installer reads requirements.yaml
2. **Validation**: Check dependencies and compatibility
3. **Collection**: Gather required inputs (interactive or from environment)
4. **Installation**: Deploy template, configure platform, install scripts
5. **Verification**: Confirm successful installation

## Conditional Inputs

Inputs can have `condition` expressions that reference other input values. This creates dependency chains where the presence of one input controls the visibility of others.

**Use Case Example:**
If a user chooses to add hosts automatically, collect IP addresses. Otherwise, skip that input entirely.

This keeps the user experience clean while supporting both automated and manual workflows.

## Best Practices

- **Minimal Inputs**: Only request what's absolutely necessary
- **Sensible Defaults**: Provide defaults wherever possible
- **Clear Descriptions**: Users should understand what each input does
- **Conditional Complexity**: Use conditionals to hide complexity from users who don't need it

## Extensibility

New NMS platforms, input types, or features can be added to the installer without changing existing requirements files. The schema is versioned to allow backward compatibility.

## See Also

- Example: `templates/zabbix/cambium-fiber/requirements.yaml`
- Implementation: `install.sh` (parsing and execution)
- Development: [contributing.md](contributing.md) - Adding new templates and development workflow
- Testing: [testing.md](testing.md) - Validating template requirements
