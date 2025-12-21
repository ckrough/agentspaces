# Contributing to agentspaces

This guide covers development setup, project architecture, and contribution guidelines.

## Development Setup

### Prerequisites

- Python 3.12+
- Git
- [uv](https://docs.astral.sh/uv/) for Python package management

### Getting Started

```bash
# Clone the repository
git clone https://github.com/ckrough/agentspaces.git
cd agentspaces

# Install all dependencies including dev tools
uv sync --all-extras

# Verify installation
uv run agentspaces --version

# Run tests to confirm setup
uv run pytest
```

### Running the CLI During Development

Always use `uv run` to execute commands:

```bash
uv run agentspaces --help
uv run agentspaces workspace list
```

## Project Structure

```
src/agentspaces/
├── __init__.py              # Package version
├── main.py                  # CLI entry point (app)
├── cli/                     # CLI layer - Typer commands
│   ├── app.py               # Main app, global options
│   ├── workspace.py         # Workspace subcommands
│   ├── agent.py             # Agent subcommands
│   ├── context.py           # CLI context (verbosity state)
│   └── formatters.py        # Rich output formatting
├── modules/                 # Business logic layer
│   ├── workspace/
│   │   ├── service.py       # WorkspaceService - core operations
│   │   ├── worktree.py      # Git worktree operations
│   │   ├── environment.py   # Python venv setup
│   │   └── models.py        # Data models (WorkspaceInfo, etc.)
│   └── agent/
│       └── launcher.py      # Agent launching logic
└── infrastructure/          # Shared utilities
    ├── git.py               # Git subprocess wrapper
    ├── naming.py            # Name generation (adjective-scientist)
    ├── paths.py             # Path resolution
    ├── similarity.py        # String similarity for suggestions
    └── logging.py           # structlog configuration
```

### Architecture Layers

**CLI Layer** (`cli/`): Handles user interaction, argument parsing, and output formatting. Uses Typer for command definitions and Rich for styled output.

**Module Layer** (`modules/`): Contains business logic. Each module (workspace, agent) has its own service class that orchestrates operations. Services use constructor dependency injection for testability.

**Infrastructure Layer** (`infrastructure/`): Shared utilities used across modules. Git operations are performed via subprocess (not a Git library). Logging uses structlog for structured output.

### Data Flow Example

```
User runs: agentspaces workspace create main

1. cli/workspace.py: create() command handler
2. modules/workspace/service.py: WorkspaceService.create()
3. modules/workspace/worktree.py: create_worktree()
4. infrastructure/git.py: Git subprocess calls
5. modules/workspace/environment.py: setup_venv()
6. Return WorkspaceInfo to CLI
7. cli/formatters.py: print_workspace_created()
```

## Testing

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage report
uv run pytest --cov=src --cov-report=term-missing

# Run specific test file
uv run pytest tests/unit/test_naming.py

# Run tests matching a pattern
uv run pytest -k "test_create"

# Run with verbose output
uv run pytest -v
```

### Test Organization

```
tests/
├── conftest.py          # Shared fixtures
├── unit/                # Unit tests (fast, isolated)
│   ├── test_naming.py
│   ├── test_paths.py
│   └── ...
└── integration/         # Integration tests (may use filesystem)
    └── ...
```

### Writing Tests

Use pytest with descriptive names following the pattern `test_<function>_<scenario>_<expected>`:

```python
def test_generate_name_returns_adjective_scientist_format():
    """Names should be formatted as adjective-scientist."""
    name = generate_name()
    parts = name.split("-")
    assert len(parts) == 2


def test_create_workspace_with_invalid_branch_raises_error():
    """Creating a workspace from non-existent branch should fail."""
    with pytest.raises(WorkspaceError, match="branch not found"):
        service.create(base_branch="nonexistent-branch")
```

### Coverage Requirements

- Target: 80% coverage on business logic
- Excluded from coverage: CLI layer, logging config, main entry point
- Run `uv run pytest --cov=src` to check coverage

## Code Quality

### Linting and Formatting

```bash
# Check for lint issues
uv run ruff check src/ tests/

# Auto-fix lint issues
uv run ruff check src/ tests/ --fix

# Format code
uv run ruff format src/ tests/
```

### Type Checking

```bash
# Run mypy with strict mode
uv run mypy src/
```

### Pre-Commit Check

Run all checks before committing:

```bash
uv run ruff check src/ tests/ --fix && \
uv run ruff format src/ tests/ && \
uv run mypy src/ && \
uv run pytest
```

## Code Style

### Python Version

Target Python 3.12+. Use modern Python features:

- Type hints on all function signatures (including `-> None`)
- `collections.abc` types for abstract containers
- Union with `|` syntax: `int | str`
- Pattern matching where appropriate

### Imports

Order: stdlib, third-party, local. Ruff handles sorting automatically.

```python
from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import typer
from rich.console import Console

from agentspaces.infrastructure import git
from agentspaces.modules.workspace.models import WorkspaceInfo
```

### Error Handling

Create meaningful exceptions in each module:

```python
class WorkspaceError(Exception):
    """Base exception for workspace operations."""

class WorkspaceNotFoundError(WorkspaceError):
    """Raised when a workspace doesn't exist."""
```

Chain exceptions with `from`:

```python
try:
    git.checkout(branch)
except git.GitError as e:
    raise WorkspaceError(f"Failed to checkout: {e}") from e
```

### Documentation

Google-style docstrings for public APIs:

```python
def create(
    self,
    base_branch: str,
    purpose: str | None = None,
) -> WorkspaceInfo:
    """Create a new isolated workspace.

    Args:
        base_branch: Branch to create workspace from.
        purpose: Optional description of workspace purpose.

    Returns:
        Information about the created workspace.

    Raises:
        WorkspaceError: If workspace creation fails.
    """
```

## Making Changes

### Adding a New Command

1. Add command function to appropriate CLI module (`cli/workspace.py` or `cli/agent.py`):

```python
@app.command("new-command")
def new_command(
    arg: Annotated[str, typer.Argument(help="Argument description")],
) -> None:
    """Brief description of command.

    Detailed description here.

    \b
    Examples:
        agentspaces workspace new-command foo
        agentspaces workspace new-command bar --option
    """
    try:
        result = _service.new_operation(arg)
        print_success(f"Done: {result}")
    except WorkspaceError as e:
        print_error(str(e))
        raise typer.Exit(1) from e
```

2. Add business logic to service class (`modules/workspace/service.py`)
3. Add tests for both the service method and CLI command
4. Update command reference in README.md

### Adding Infrastructure Utilities

1. Create module in `infrastructure/`
2. Keep it focused on a single concern
3. Add comprehensive unit tests
4. Use from service layer, not directly from CLI

### Example: Adding a New Workspace Feature

This walkthrough adds a "workspace info" command that shows metadata.

**Step 1: Add the service method**

```python
# modules/workspace/service.py
def get_info(self, name: str) -> dict[str, str]:
    """Get workspace metadata.

    Args:
        name: Workspace name.

    Returns:
        Dictionary of metadata key-value pairs.

    Raises:
        WorkspaceNotFoundError: If workspace doesn't exist.
    """
    workspace = self.get(name)
    metadata_file = workspace.path / ".agentspace" / "metadata.json"
    if not metadata_file.exists():
        return {}
    return json.loads(metadata_file.read_text())
```

**Step 2: Add the CLI command**

```python
# cli/workspace.py
@app.command("info")
def info(
    name: Annotated[str, typer.Argument(help="Workspace name")],
) -> None:
    """Show workspace metadata.

    \b
    Examples:
        agentspaces workspace info eager-turing
    """
    try:
        metadata = _service.get_info(name)
    except WorkspaceNotFoundError:
        print_error(f"Workspace not found: {name}")
        raise typer.Exit(1) from None

    if not metadata:
        print_info("No metadata found")
        return

    for key, value in metadata.items():
        print_info(f"{key}: {value}")
```

**Step 3: Add tests**

```python
# tests/unit/test_workspace_service.py
def test_get_info_returns_metadata(tmp_path, service):
    """get_info should return metadata from .agentspace/metadata.json."""
    # Setup
    workspace = service.create("main")
    metadata_file = workspace.path / ".agentspace" / "metadata.json"
    metadata_file.write_text('{"purpose": "Test"}')

    # Test
    result = service.get_info(workspace.name)

    # Verify
    assert result == {"purpose": "Test"}


def test_get_info_nonexistent_workspace_raises(service):
    """get_info should raise for non-existent workspace."""
    with pytest.raises(WorkspaceNotFoundError):
        service.get_info("nonexistent")
```

**Step 4: Run checks**

```bash
uv run ruff check src/ tests/ --fix
uv run mypy src/
uv run pytest -k "test_get_info"
```

## Pull Request Guidelines

1. Create a feature branch: `git checkout -b feature/description`
2. Make focused, incremental changes
3. Run all checks before committing
4. Write clear commit messages
5. Update documentation if adding features
6. Ensure tests pass and coverage is maintained

### Commit Message Format

```
<type>: <description>

<optional body>
```

Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`

Examples:
```
feat: add workspace sync command
fix: handle missing .python-version file
refactor: extract path resolution to infrastructure
docs: update README with new commands
test: add coverage for edge cases in naming
```

## Questions?

Open an issue on GitHub for questions about contributing.
