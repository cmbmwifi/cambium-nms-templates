# Contributing Guide

## Getting Started

### Prerequisites

- Python 3.8+
- Docker and Docker Compose (for testing)
- Bash shell

### Clone the Repository

```bash
git clone https://github.com/cmbmwifi/cambium-nms-templates.git
cd cambium-nms-templates
```

## Making Changes

### Templates

Edit files in `templates/<nms>/<product>/`:
- `requirements.yaml` - Define what the template needs
- `template.yaml` - The NMS template configuration
- `*.py` - External scripts the template uses

See [requirements-spec.md](requirements-spec.md) for requirements.yaml format.

### Installer

Modify `install.sh` to change installation behavior, menu logic, or add new features.

### Tests

Add or update tests in `tests/integration/` to verify your changes work correctly.

## Testing Your Changes

**Always test before pushing.**

The `--local` flag makes the installer use files from `~/cambium-nms-templates/` instead of downloading from GitHub. This solves the circular dependency: you can't test without pushing, but you shouldn't push without testing.

### Quick Test

Test your template installs correctly:
```bash
./install.sh --local
```

### Full Test Suite

Run all automated tests:
```bash
./tests/run_all.sh
```

Or test specific components:
```bash
./tests/integration/run_all_zabbix_tests.sh
./tests/integration/run_installer_tests.sh
```

See [testing.md](testing.md) for details.

## Submitting Changes

1. **Ensure tests pass** - Run `./tests/run_all.sh`
2. **Commit your changes** - Use clear commit messages
3. **Push to GitHub** - Changes go live immediately for production users
4. **Verify production** - Test the curl installer fetches correctly

## Adding New Templates

1. **Create template structure:**
   ```
   templates/<nms>/<product>/
   ├── requirements.yaml
   ├── template.yaml
   └── <script>.py
   ```

2. **Define requirements** - See [requirements-spec.md](requirements-spec.md)

3. **Test locally:**
   ```bash
   ./install.sh --local
   ```

4. **Write integration tests** - Verify template behavior

5. **Test across versions** - Ensure compatibility with all supported NMS versions

The installer discovers templates automatically - no code changes needed.

## Guidelines

- Test all changes with `--local` before pushing
- Validate across all supported NMS versions
- Keep tests fast and focused
- Document concepts, not implementation details

## Questions?

- **Testing**: See [testing.md](testing.md)
- **Requirements Format**: See [requirements-spec.md](requirements-spec.md)
- **Project Structure**: See README.md
