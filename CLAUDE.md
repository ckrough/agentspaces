# AgentSpaces

Workspace orchestration tool for AI coding agents.

## Quick Reference

```bash
# Run commands with uv
uv run agentspaces --help
uv run pytest
uv run ruff check src/
uv run mypy src/

# Development
uv sync --all-extras          # Install all dependencies
```

## Project Structure

```
src/agentspaces/
├── main.py                    # CLI entry point
├── cli/                       # Typer commands
│   ├── app.py                 # Main app
│   └── workspace.py           # Workspace subcommands
├── modules/
│   └── workspace/             # Workspace management
│       ├── service.py         # Business logic
│       └── worktree.py        # Git worktree operations
└── infrastructure/            # Shared utilities
    ├── git.py                 # Git subprocess wrapper
    ├── naming.py              # Name generation
    ├── paths.py               # Path resolution
    └── logging.py             # structlog config
```

## Architecture

- **CLI Layer** (`cli/`): Typer commands, user interaction
- **Module Layer** (`modules/`): Business logic, services
- **Infrastructure** (`infrastructure/`): Git, storage, logging

### Patterns

- Services use constructor dependency injection
- Git operations via subprocess (not a library)
- JSON files for persistence (in `~/.agentspaces/`)
- structlog for structured logging

## Key Concepts

### Workspaces

A workspace is:
- A git worktree at `~/.agentspaces/<project>/<name>/`
- A branch with the same name as the workspace
- Metadata in `.agentspace/` directory
- Optional Python venv in `.venv/`

### Agent Skills

Uses [agentskills.io](https://agentskills.io) standard:
- `.github/skills/` for project-level skills
- `.agentspace/skills/` for workspace-specific skills
- Auto-discovered by compatible agents

## Commands

```bash
as workspace create [branch]   # Create workspace
as workspace list              # List workspaces
as workspace remove <name>     # Remove workspace
```

## Testing

```bash
uv run pytest                           # All tests
uv run pytest tests/unit/               # Unit tests only
uv run pytest -k "test_naming"          # Specific tests
uv run pytest --cov=src                 # With coverage
```

## Code Quality

```bash
uv run ruff check src/ tests/          # Lint
uv run ruff format src/ tests/         # Format
uv run mypy src/                       # Type check
```

## Conventions

- Python 3.12+
- Type hints on all functions
- Google-style docstrings
- `ruff` for linting/formatting
- `mypy --strict` for type checking
- 80% test coverage target

## Enhancement Backlog

Future improvements from code reviews (Increment 2):

### Python Best Practices
- Use `@dataclass(frozen=True)` for immutable DTOs (`EnvironmentInfo`, `WorktreeCreateResult`, `WorkspaceInfo`)
- Add `@functools.cache` to `is_uv_available()` for performance
- Add `__all__` declarations to define public API in modules
- Use pattern matching for version parsing in `_get_venv_python_version()`
- Consider using walrus operator for cleaner code patterns

### CLI Enhancements
- Add `--verbose` and `--quiet` global flags to `app.py`
- Add examples to help text using `\b` blocks in docstrings
- Add "Next steps:" section to create command output
- Add sorting/filtering options to `list` command (`--sort`, `--all`)
- Add "Did you mean?" suggestions for workspace not found errors
- Consider top-level command aliases (`as create`, `as ls`)
- Document shell completion installation

### Environment Management
- Add `deps_synced` field to `EnvironmentInfo` to track sync success
- Add venv verification after creation (check Python executable exists)
- Make uv timeout configurable via environment variable
- Add public `get_workspace_path()` method to service (avoid `_resolver` access)

### Testing
- Add error path tests for `setup_environment` when uv unavailable
- Add tests for failed dependency sync scenarios
- Add tests for malformed `.python-version` files
