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
│   ├── project.py             # Project initialization
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
│   ├── skeleton.py            # Project structure definitions
│   ├── resources.py           # Package resource access
│   ├── frontmatter.py         # YAML frontmatter parser
│   └── logging.py             # structlog config
└── templates/                 # Bundled project templates
    ├── skeleton/              # Project skeleton templates
    │   ├── CLAUDE.md          # Agent constitution template
    │   ├── .claude/           # Agent/command templates
    │   └── docs/              # ADR and design templates
    └── languages/             # Language-specific packs
        └── python/            # Python tooling templates
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

## Commands

```bash
# Project initialization
agentspaces project create              # Initialize new project in current dir
agentspaces project create --python     # With Python language pack

# Workspaces
agentspaces workspace create [branch]   # Create workspace
agentspaces workspace list              # List workspaces
agentspaces workspace status <name>     # Show workspace details
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

- Python 3.13
- Type hints on all functions
- Google-style docstrings
- `ruff` for linting/formatting
- `mypy --strict` for type checking
- 80% test coverage target

## Versioning and Releases

### Commit Messages

Use [Conventional Commits](https://www.conventionalcommits.org/) for all commit messages:

```
<type>(<scope>): <description>
```

**Common types:**
- `feat`: New feature (triggers minor version bump)
- `fix`: Bug fix (triggers patch version bump)
- `docs`: Documentation only changes
- `refactor`: Code refactoring without behavior change
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Breaking changes:**
Add `!` after type to trigger major version bump:
```
feat!: change workspace create to require branch argument
```

### CHANGELOG

- **CHANGELOG.md** is automatically updated by semantic-release on each release
- Entries are generated from conventional commit messages
- Unreleased changes are tracked in the `[Unreleased]` section
- Never manually edit the automated sections
- For manual releases, update CHANGELOG.md before tagging

### Release Process

Releases are automated via GitHub Actions when commits are pushed to `main`:
1. Commit with conventional commit message
2. Push to main (or merge PR)
3. GitHub Actions analyzes commits and creates release if needed
4. Version is bumped, CHANGELOG is updated, and tag is created

See [RELEASING.md](RELEASING.md) for full details on versioning and releases.

## Documentation

- [CONTRIBUTING.md](CONTRIBUTING.md) - Development guide
- [RELEASING.md](RELEASING.md) - Version management and release process
- [CHANGELOG.md](CHANGELOG.md) - Project changelog (auto-generated)
- [docs/design/architecture.md](docs/design/architecture.md) - System design
- [docs/adr/](docs/adr/) - Architecture decisions

## Issue Tracking with Beads

Use [Beads](https://github.com/steveyegge/beads) for lightweight issue tracking during development sessions.

```bash
# Start session - see what's ready to work on
bd ready --json

# Create issues
bd create "title" -t <type> -p <priority> -d <task details>
# Types: feature, bug, task, chore
# Priority: 1 (critical) to 4 (low)

# Update status when starting work
bd update <id> --status in_progress

# Close when done
bd close <id> --reason "Completed"

# Track discovered work (links new issue to current work)
bd dep add <new-id> <current-id> --type discovered-from

# End session - sync changes
bd sync
```

### Task Description Standards

When creating Beads issues, include comprehensive standalone context so tasks can be independently executed by an agent without conversation history:

- **Context**: What system/command is involved, relevant source files
- **Goal**: Specific objective of the task
- **Implementation**: Code examples, file paths, specific steps
- **Dependencies**: What other tasks/files are prerequisites
- **Verification**: Commands to confirm task completion

Example:
```bash
bd create "Add validation to user input" -t task -p 2 -d "## Context
The user registration form in src/api/routes/auth.py accepts email without validation.

## Goal
Add email format validation before creating user accounts.

## Implementation
1. Add email-validator to dependencies in pyproject.toml
2. Create validate_email() in src/api/validators.py
3. Call validator in register_user() route handler

## Verification
uv run pytest tests/api/test_auth.py -k email_validation"
```

## Learned Patterns

<!-- Add entries when Claude makes mistakes. Format: When X happens, do Y instead of Z -->
