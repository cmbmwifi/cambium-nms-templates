#!/bin/bash
# Setup development environment for cambium-nms-templates
# Installs linting tools and configures git hooks

set -e

echo "🔧 Setting up development environment..."
echo ""

# Get the root of the git repository
REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo ".")

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python 3 is not installed${NC}"
    exit 1
fi

# Install Python linting and testing tools
echo "📦 Installing Python development tools..."
if pip install pyyaml ruff mypy types-requests types-PyYAML yamllint pytest pytest-xdist; then
    echo -e "${GREEN}✓ Python tools installed${NC}"
else
    echo -e "${RED}✗ Failed to install Python tools${NC}"
    exit 1
fi

# Install ShellCheck (platform-specific)
echo ""
echo "📦 Installing ShellCheck and type checking tools..."
if command -v apt-get &> /dev/null; then
    echo "  Detected apt-get (Debian/Ubuntu)"
    if sudo apt-get install -y shellcheck python3-mypy python3-typeshed 2>/dev/null; then
        echo -e "${GREEN}✓ ShellCheck and type checking tools installed${NC}"
    else
        echo -e "${YELLOW}⚠ Could not install tools via apt-get (may need sudo)${NC}"
    fi
elif command -v brew &> /dev/null; then
    echo "  Detected Homebrew (macOS/Linux)"
    if brew install shellcheck 2>/dev/null; then
        echo -e "${GREEN}✓ ShellCheck installed${NC}"
    else
        echo -e "${YELLOW}⚠ Could not install ShellCheck via Homebrew${NC}"
    fi
    echo "  Note: Install mypy via pip: pip install mypy types-PyYAML"
else
    echo -e "${YELLOW}⚠ No package manager found - install tools manually${NC}"
    echo "  ShellCheck: https://github.com/koalaman/shellcheck#installing"
    echo "  mypy: pip install mypy types-PyYAML"
fi

# Install git hooks
echo ""
echo "🪝 Installing git hooks..."
mkdir -p "$REPO_ROOT/.git/hooks"

if cp "$REPO_ROOT/.git-hooks/pre-commit" "$REPO_ROOT/.git/hooks/pre-commit" && \
   cp "$REPO_ROOT/.git-hooks/pre-push" "$REPO_ROOT/.git/hooks/pre-push"; then
    chmod +x "$REPO_ROOT/.git/hooks/pre-commit"
    chmod +x "$REPO_ROOT/.git/hooks/pre-push"
    chmod +x "$REPO_ROOT/tests/run_all.sh"
    echo -e "${GREEN}✓ Git hooks installed${NC}"
    echo "  - pre-commit: Runs linting checks"
    echo "  - pre-push: Runs all test suites"
else
    echo -e "${RED}✗ Failed to install git hooks${NC}"
    exit 1
fi

# Verify installation
echo ""
echo "🔍 Verifying installation..."
VERIFY_FAILED=0

if command -v ruff &> /dev/null; then
    echo -e "${GREEN}✓${NC} ruff: $(ruff --version)"
else
    echo -e "${RED}✗${NC} ruff not found"
    VERIFY_FAILED=1
fi

if command -v mypy &> /dev/null; then
    echo -e "${GREEN}✓${NC} mypy: $(mypy --version)"
else
    echo -e "${RED}✗${NC} mypy not found"
    VERIFY_FAILED=1
fi

if command -v yamllint &> /dev/null; then
    echo -e "${GREEN}✓${NC} yamllint: $(yamllint --version)"
else
    echo -e "${RED}✗${NC} yamllint not found"
    VERIFY_FAILED=1
fi

if command -v shellcheck &> /dev/null; then
    echo -e "${GREEN}✓${NC} shellcheck: $(shellcheck --version | head -n 2 | tail -n 1)"
else
    echo -e "${YELLOW}⚠${NC} shellcheck not found (optional but recommended)"
fi

if command -v docker &> /dev/null; then
    echo -e "${GREEN}✓${NC} docker: $(docker --version)"
else
    echo -e "${YELLOW}⚠${NC} docker not found (required for integration tests)"
fi

echo ""
if [ $VERIFY_FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ Development environment setup complete!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Make code changes and stage them: git add <files>"
    echo "  2. Commit (triggers linting): git commit -m 'message'"
    echo "  3. Push (triggers tests): git push"
    echo ""
    echo "Manual commands:"
    echo "  - Test hooks: .git/hooks/pre-commit"
    echo "  - Run all tests: ./tests/run_all.sh"
    echo "  - Lint Python: ruff check . && ruff format ."
    echo "  - Bypass hooks: git commit --no-verify"
else
    echo -e "${RED}⚠ Setup completed with errors${NC}"
    echo "Some tools failed to install. Please install them manually."
    exit 1
fi
