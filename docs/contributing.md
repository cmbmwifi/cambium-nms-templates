# Contributing Guide

## Getting Started

### Development Environment Setup

**Automated setup** (recommended):

```bash
# Clone the repository
git clone https://github.com/cmbmwifi/cambium-nms-templates.git
cd cambium-nms-templates

# Run the setup script to install development tools
./scripts/setup-dev-environment.sh
```

This installs:
- **PyYAML** - Required for the installer to parse requirements
- **shellcheck** - Bash script linting (catches issues before CI)
- **yamllint** - YAML validation
- **ruff** - Python linting and formatting
- **Git hooks** - Automatic linting on commit, tests on push

**Manual setup**:

If you prefer manual installation or the script doesn't work on your system:

```bash
# Python tools
pip install pyyaml ruff mypy types-requests types-PyYAML yamllint pytest pytest-xdist

# ShellCheck (Debian/Ubuntu)
sudo apt-get install -y shellcheck

# ShellCheck (macOS)
brew install shellcheck

# Install git hooks
cp .git-hooks/pre-commit .git/hooks/pre-commit
cp .git-hooks/pre-push .git/hooks/pre-push
chmod +x .git/hooks/pre-commit .git/hooks/pre-push
```

### Prerequisites

- Python 3.8+
- Docker and Docker Compose (for integration tests)
- Bash shell
- Git

### Clone the Repository

```bash
git clone https://github.com/cmbmwifi/cambium-nms-templates.git
cd cambium-nms-templates
```

## Git Hooks

The development environment includes pre-commit and pre-push hooks that ensure code quality:

### Pre-commit Hook
Runs automatically when you commit, checking:
- Python syntax validation
- Python type checking (mypy)
- Bash syntax and linting (shellcheck)
- YAML validation

This catches issues **before** they're committed, saving you from having to fix them later.

### Pre-push Hook
Runs automatically when you push, executing:
- All linting checks (same as CI)
- Full test suite (~4 minutes)

This ensures your changes pass **the same checks that GitHub Actions runs**, preventing CI failures.

**Bypass hooks** (not recommended):
```bash
git commit --no-verify
git push --no-verify
```

Use `--no-verify` only when you're certain your changes are correct and need to bypass temporarily.

## Making Changes

### Workflow

1. **Create a feature branch**: `git checkout -b feature/your-feature`
2. **Make changes** to templates, scripts, or tests
3. **Test locally** with `./install.sh --local`
4. **Run tests**: `./tests/run_all.sh`
5. **Commit** (triggers linting): `git commit -m "fix: your change"`
6. **Push** (triggers tests): `git push`
7. **Create Pull Request** on GitHub (if contributing to main repository)

## Testing Your Changes

**Always test before pushing.**

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
