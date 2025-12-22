# Release Process

This document describes the versioning and release process for agentspaces.

## Version Management

### Version Storage

The application version must be maintained in **two locations** that must stay synchronized:

1. **`src/agentspaces/__init__.py`** (primary source of truth)
   ```python
   __version__ = "0.1.0"
   ```
   - Used by the application at runtime
   - Displayed by `agentspaces --version` command
   - Imported throughout the codebase when version is needed

2. **`pyproject.toml`** (build metadata)
   ```toml
   [project]
   version = "0.1.0"
   ```
   - Used by Hatchling during the build process
   - Published to PyPI package metadata
   - Required for `pip install` and package distribution

### Semantic Versioning

agentspaces follows [Semantic Versioning 2.0.0](https://semver.org/):

```
MAJOR.MINOR.PATCH
```

**Version Increment Rules:**

- **MAJOR** (1.0.0): Breaking changes to CLI commands, API, or data formats
  - Existing workspaces may not work
  - Commands removed or significantly changed
  - Configuration format changed
  - Examples: Removing commands, changing command syntax, incompatible metadata format

- **MINOR** (0.1.0): New features, backward-compatible changes
  - New commands added
  - New flags or options added
  - Enhanced functionality that doesn't break existing usage
  - Examples: Adding new subcommands, new optional flags

- **PATCH** (0.0.1): Bug fixes, documentation updates, internal refactoring
  - No user-facing changes beyond bug fixes
  - Performance improvements
  - Examples: Fixing crashes, correcting error messages, updating docs

**Pre-1.0.0 Versioning:**

- Currently in 0.x.y range (pre-stable)
- MINOR version changes may include breaking changes until 1.0.0
- Document all breaking changes in release notes

## Release Process

### 1. Prepare the Release

**a. Ensure clean working tree:**
```bash
git status
# Should show no uncommitted changes
```

**b. Run full test suite:**
```bash
uv run ruff check src/ tests/ --fix
uv run ruff format src/ tests/
uv run mypy src/
uv run pytest --cov=src
```

All checks must pass before proceeding.

**c. Update version numbers:**

Decide on the new version number based on semantic versioning rules, then update both files:

```bash
# Example: bumping from 0.1.0 to 0.2.0
# Update src/agentspaces/__init__.py
__version__ = "0.2.0"

# Update pyproject.toml
version = "0.2.0"
```

**d. Verify version display:**
```bash
uv run agentspaces --version
# Should output: agentspaces 0.2.0
```

### 2. Create Release Commit

Commit the version bump with a standardized message:

```bash
git add src/agentspaces/__init__.py pyproject.toml
git commit -m "chore: bump version to 0.2.0"
```

**Commit message format:**
```
chore: bump version to X.Y.Z
```

### 3. Create Git Tag

Create an annotated tag matching the version:

```bash
# Create annotated tag with version info
git tag -a v0.2.0 -m "Release version 0.2.0"

# View the tag
git show v0.2.0
```

**Tag naming convention:**
- Format: `vX.Y.Z` (with 'v' prefix)
- Examples: `v0.1.0`, `v0.2.0`, `v1.0.0`
- Use annotated tags (with `-a` flag), not lightweight tags
- Tag message should be: `"Release version X.Y.Z"`

### 4. Push to Remote

Push both the commit and the tag:

```bash
# Push the commit
git push origin main

# Push the tag
git push origin v0.2.0

# Or push all tags at once (use with caution)
git push origin --tags
```

### 5. Build and Publish (Future)

When ready to publish to PyPI:

```bash
# Build the package
uv build

# Publish to PyPI (requires PyPI credentials)
uv publish
```

*Note: PyPI publishing is not yet configured.*

## Verification

After release, verify the version is correct:

```bash
# Check version command
agentspaces --version

# Check git tag
git describe --tags

# Check latest tag
git tag -l --sort=-version:refname | head -n 1
```

## Release Checklist

Use this checklist for each release:

- [ ] All tests passing (`uv run pytest`)
- [ ] Code formatted (`uv run ruff format`)
- [ ] Linting clean (`uv run ruff check`)
- [ ] Type checking passes (`uv run mypy src/`)
- [ ] Version updated in `src/agentspaces/__init__.py`
- [ ] Version updated in `pyproject.toml`
- [ ] Versions match in both files
- [ ] `agentspaces --version` displays correct version
- [ ] Version bump commit created (`chore: bump version to X.Y.Z`)
- [ ] Git tag created (`git tag -a vX.Y.Z -m "Release version X.Y.Z"`)
- [ ] Changes pushed to remote (`git push origin main`)
- [ ] Tag pushed to remote (`git push origin vX.Y.Z`)
- [ ] GitHub release created (optional, future)
- [ ] PyPI package published (optional, future)

## Common Tasks

### Check current version

```bash
# From CLI
agentspaces --version

# From code
python -c "from agentspaces import __version__; print(__version__)"

# From git tags
git describe --tags --abbrev=0
```

### List all versions

```bash
# Show all version tags
git tag -l 'v*' --sort=-version:refname

# Show tags with dates
git tag -l 'v*' --sort=-version:refname --format='%(refname:short) %(creatordate:short)'
```

### Compare versions

```bash
# Show changes between versions
git log v0.1.0..v0.2.0 --oneline

# Show detailed diff
git diff v0.1.0..v0.2.0
```

### Fix version mismatch

If versions get out of sync:

```bash
# Check both locations
grep "__version__" src/agentspaces/__init__.py
grep "^version" pyproject.toml

# Update to match (example)
# Edit both files to match, then:
git add src/agentspaces/__init__.py pyproject.toml
git commit -m "chore: sync version numbers to 0.2.0"
```

### Delete a tag (if needed)

```bash
# Delete local tag
git tag -d v0.2.0

# Delete remote tag
git push origin :refs/tags/v0.2.0
```

## Version History

Track major releases here:

- **v0.1.0** (Current) - Initial release
  - Core workspace management
  - Git worktree integration
  - Basic CLI commands

## Notes

- Never manually edit version in one location without updating the other
- Always use annotated tags (`-a` flag) for releases
- Tag names must match version with 'v' prefix (e.g., `v0.2.0`)
- Test the version command before creating tags
- Keep this document updated with each release
