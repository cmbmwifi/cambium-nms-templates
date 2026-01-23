# Versioning and Branch Strategy

## Branch Workflow

This project uses **GitHub Flow** - a simple, production-ready workflow:

1. **`main` branch** - Always production-ready
   - What users download via `curl https://raw.githubusercontent.com/.../install.sh | bash`
   - Protected branch (requires passing tests)
   - Tagged releases: `v1.0.0`, `v1.1.0`, etc.

2. **Feature branches** - For all development work
   ```bash
   git checkout -b feature/new-template
   git checkout -b fix/installer-bug
   git checkout -b docs/update-readme
   ```
   - Created from `main`
   - Merged back to `main` when tests pass
   - Deleted after merge
   - Version tag created on `main` (see Release Tagging below)

3. **No separate development branch** - Keeps workflow simple
   - Feature branches serve as development branches
   - CI validates every change before merge

## Release Tagging

Tags mark stable releases and should be created after merging features to `main`:

```bash
# After merging feature branch(es)
git checkout main
git pull

# Create tag based on changes
git tag -a v1.1.0 -m "Release 1.1.0: Add new templates, improve installer"
git push origin v1.1.0
```

**When to bump the version**:
- **Major** (`v2.0.0`) - Breaking changes to templates or installer API
- **Minor** (`v1.1.0`) - New templates, features, or enhancements
- **Patch** (`v1.0.1`) - Bug fixes, documentation updates

**Tagging workflow**:
1. Merge one or more feature branches to `main`
2. Decide version bump based on changes merged
3. Create and push tag
4. Tag becomes the official release (users can reference specific versions if needed)

**What gets deployed**: When users run `install.sh`, they download from `main`:
- Zabbix templates (YAML), collector scripts (Python), configuration files
- **NOT** test infrastructure (stays in repo only)

## See Also

- [contributing.md](contributing.md) - Complete development workflow and git hooks
- [testing.md](testing.md) - Pre-release validation and CI/CD tests
- [requirements-spec.md](requirements-spec.md) - Template versioning and compatibility
- [README.md](../README.md) - Project overview and quick start
