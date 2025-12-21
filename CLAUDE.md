# agentspaces

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
│   ├── workspace.py           # Workspace subcommands
│   └── docs.py                # Design template commands
├── modules/
│   └── workspace/             # Workspace management
│       ├── service.py         # Business logic
│       └── worktree.py        # Git worktree operations
├── infrastructure/            # Shared utilities
│   ├── git.py                 # Git subprocess wrapper
│   ├── naming.py              # Name generation
│   ├── paths.py               # Path resolution
│   ├── design.py              # Template rendering
│   ├── resources.py           # Package resource access
│   ├── frontmatter.py         # YAML frontmatter parser
│   └── logging.py             # structlog config
└── templates/                 # Bundled project templates
    ├── skeleton/              # Project skeleton templates
    │   ├── CLAUDE.md          # Agent constitution template
    │   ├── TODO.md            # Task list template
    │   ├── .claude/           # Agent/command templates
    │   └── docs/              # ADR and design templates
    └── skills/                # Skill templates
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
# Workspaces
agentspaces workspace create [branch]   # Create workspace
agentspaces workspace list              # List workspaces
agentspaces workspace remove <name>     # Remove workspace

# Design templates
agentspaces docs list                   # List available templates
agentspaces docs info <template>        # Show template details
agentspaces docs create <template>      # Generate from template
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

## Documentation

- [TODO.md](TODO.md) - Active task list
- [docs/design/architecture.md](docs/design/architecture.md) - System design
- [docs/adr/](docs/adr/) - Architecture decisions
