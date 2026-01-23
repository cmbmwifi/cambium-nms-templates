# Contributing Guide

## Getting Started

### AI Assistant Support

This project includes configuration to help AI coding assistants (GitHub Copilot, Cursor, Codex, etc.) understand the codebase:

- **`.agentic`** - Project structure, conventions, common tasks, and pitfalls
- **`pyproject.toml [tool.agentic]`** - Workflow definitions and quality check commands

AI assistants can reference these files to provide context-aware suggestions that follow project conventions.

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

## Development Workflow

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature
   ```

2. **Make your changes**
   - Templates: `templates/<nms>/<product>/` (see [requirements-spec.md](requirements-spec.md))
   - Installer: `install.sh`
   - Tests: `tests/integration/` or `tests/unit/`

3. **Test your changes**
   ```bash
   # Run all tests
   ./tests/run_all.sh

   # Or run specific test suites
   ./tests/unit/run_all.sh              # Fast unit tests
   ./tests/integration/run_all.sh       # All integration tests
   ./tests/integration/zabbix/run_all.sh    # Zabbix tests only
   ```
   See [testing.md](testing.md) for detailed testing options.

4. **Commit** (triggers pre-commit linting)
   ```bash
   git commit -m "fix: your change"
   ```

5. **Push** (triggers pre-push tests)
   ```bash
   git push
   ```

6. **Tag release** (after merging to `main`)
   ```bash
   git tag -a v1.1.0 -m "Release 1.1.0: description"
   git push origin v1.1.0
   ```
   See [versioning.md](versioning.md) for branch strategy and release guidelines.

## Adding New Templates

1. **Create template structure:**
   ```
   templates/<nms>/<product>/
   ├── requirements.yaml   # Defines installation steps for install.sh
   ├── template.yaml       # Equipment Template to be installed
   └── <script>.py         # Data collector script if needed
   ```

2. **Define requirements** - See [requirements-spec.md](requirements-spec.md)

3. **Test with containers:**
   ```bash
   ./tests/integration/zabbix/run_all.sh
   ```

4. **Write integration tests** - Verify template behavior

5. **Test across versions** - Ensure compatibility with all supported NMS versions

The installer discovers templates automatically - no code changes needed.

## See Also

- [versioning.md](versioning.md) - Branch strategy, release tagging, and version management
- [testing.md](testing.md) - Test architecture, running tests, and debugging
- [requirements-spec.md](requirements-spec.md) - Template requirements format and philosophy
- [README.md](../README.md) - Project overview and quick start
