---
name: architecture
description: Read when understanding workspaces, agents, or infrastructure. Layered architecture reference.
---

# AgentSpaces Architecture

Workspace orchestration tool for AI coding agents, enabling parallel feature development through isolated git worktrees with tracked context.

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    WORKSPACE CREATION                           │
│  [CLI] → [Service] → [Git Worktree] → [Python Env] → [Skills]   │
└─────────────────────────────────────────────────────────────────┘
                                                        ↓
┌─────────────────────────────────────────────────────────────────┐
│                      WORKSPACE STORAGE                          │
│  ~/.agentspaces/<project>/<workspace>/                          │
│    ├── .agentspace/ (metadata + skills)                         │
│    ├── .venv/ (isolated Python environment)                     │
│    └── <project files> (git worktree)                           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      AGENT INTEGRATION                          │
│  [Workspace Detection] → [Context Loading] → [Claude Code]      │
└─────────────────────────────────────────────────────────────────┘
```

## Architecture Style: Layered Monolith

Single CLI application with clear layer boundaries. Dependencies flow downward only.

**Why this approach:**
- Simple deployment (single `uv` package)
- Clear separation of concerns for testability
- Infrastructure layer wraps all subprocess calls
- Business logic isolated from CLI and external tools

```
┌─────────────────────────────────────────────────────────────────┐
│                     AgentSpaces CLI                             │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    CLI Layer (Typer)                       │ │
│  │         Commands, formatting, user interaction             │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              ↓                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                   Service Layer                            │ │
│  │      WorkspaceService, AgentLauncher (orchestration)       │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              ↓                                  │
│  ┌──────────────────┐  ┌──────────────────┐                     │
│  │ Workspace Module │  │   Agent Module   │                     │
│  │ worktree, env    │  │    launcher      │                     │
│  └──────────────────┘  └──────────────────┘                     │
│                              ↓                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                Infrastructure Layer                        │ │
│  │     git, uv, claude, paths, metadata, naming, skills       │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Tech Stack

### Core (Python 3.12+)

| Component | Choice | Rationale |
|-----------|--------|-----------|
| CLI Framework | Typer | Modern, type-safe, auto-generated help |
| Output | Rich | Terminal tables, panels, colors |
| Validation | Pydantic | Settings, data validation |
| Logging | structlog | Structured JSON logging |
| Templates | Jinja2 | Skill file generation |

### External Dependencies (subprocess)

| Tool | Purpose | Wrapper |
|------|---------|---------|
| `git` | Worktree/branch management | `infrastructure/git.py` |
| `uv` | Python venv and deps | `infrastructure/uv.py` |
| `claude` | AI agent launching | `infrastructure/claude.py` |

### Storage

| Data | Format | Location |
|------|--------|----------|
| Workspace metadata | JSON | `~/.agentspaces/<project>/<workspace>/.agentspace/workspace.json` |
| Active workspace | Plain text | `~/.agentspaces/<project>/.active` |
| Agent skills | Markdown | `~/.agentspaces/<project>/<workspace>/.agentspace/skills/` |
| Python environment | venv | `~/.agentspaces/<project>/<workspace>/.venv/` |

## Project Structure

```
src/agentspaces/
├── __init__.py
├── main.py                     # Entry point
│
├── cli/                        # CLI Layer
│   ├── app.py                  # Main Typer app, global options
│   ├── workspace.py            # Workspace subcommands
│   ├── agent.py                # Agent subcommands
│   ├── context.py              # CLI state (singleton)
│   └── formatters.py           # Rich output utilities
│
├── modules/                    # Domain Modules
│   ├── workspace/
│   │   ├── service.py          # WorkspaceService (orchestration)
│   │   ├── worktree.py         # Higher-level worktree ops
│   │   └── environment.py      # Python environment setup
│   │
│   └── agent/
│       └── launcher.py         # AgentLauncher service
│
└── infrastructure/             # Shared Infrastructure
    ├── git.py                  # Git subprocess wrapper
    ├── uv.py                   # uv subprocess wrapper
    ├── claude.py               # Claude Code subprocess wrapper
    ├── paths.py                # PathResolver (storage locations)
    ├── metadata.py             # Workspace JSON persistence
    ├── naming.py               # Docker-style name generation
    ├── skills.py               # Jinja2 skill generation
    ├── active.py               # Active workspace tracking
    ├── similarity.py           # Fuzzy matching for suggestions
    └── logging.py              # structlog configuration
```

## Key Design Patterns

### Layered Dependencies

Each layer only depends on layers below it:

```
CLI → Service → Module → Infrastructure
```

This enables:
- Testing services without CLI
- Swapping infrastructure implementations
- Clear error propagation paths

### Subprocess Isolation

All external tool calls are isolated in infrastructure wrappers:

```python
# infrastructure/git.py
def worktree_add(
    path: Path,
    branch: str,
    base_branch: str,
    *,
    timeout: float = 30.0,
) -> None:
    """Create a git worktree with a new branch."""
    # All subprocess handling, error wrapping, timeout management
```

Benefits:
- Consistent timeout handling (30s git, 60s uv)
- Structured error types (`GitError`, `UvError`, `ClaudeError`)
- Testable via mocking
- Logging at debug level

### Dependency Injection

Services accept dependencies via constructor:

```python
class WorkspaceService:
    def __init__(self, resolver: PathResolver | None = None) -> None:
        self._resolver = resolver or PathResolver()
```

Enables test isolation without patching globals.

### Immutable Data Classes

Core data structures are frozen dataclasses:

```python
@dataclass(frozen=True)
class WorkspaceInfo:
    name: str
    path: Path
    branch: str
    # ...
```

Benefits:
- Thread-safe by design
- Clear data boundaries
- Prevents accidental mutation

### Graceful Degradation

Non-critical operations don't fail workspace creation:

```python
# Environment setup failure → workspace still created
# Skill generation failure → workspace still created
# Activity tracking failure → agent still launches
```

## Data Flow

### Create Workspace

```
CLI: workspace create --purpose "Add auth"
  │
  ↓
WorkspaceService.create()
  │
  ├─→ worktree.get_repo_info()        # Detect project name
  │
  ├─→ worktree.create_worktree()
  │     ├─→ naming.generate_name()    # "eager-turing"
  │     └─→ git.worktree_add()        # subprocess
  │
  ├─→ environment.setup_environment()
  │     ├─→ uv.venv_create()          # subprocess
  │     └─→ uv.sync()                 # subprocess (if pyproject.toml)
  │
  ├─→ metadata.save_workspace_metadata()  # atomic write
  │
  └─→ skills.generate_workspace_context_skill()  # Jinja2
  │
  ↓
CLI: formatters.print_workspace_created()
```

### Launch Agent

```
CLI: agent launch
  │
  ↓
AgentLauncher.launch_claude()
  │
  ├─→ claude.is_claude_available()    # cached check
  │
  ├─→ Workspace detection:
  │     ├─→ detect_workspace()        # cwd in ~/.agentspaces/?
  │     └─→ get_active()              # fallback to .active file
  │
  ├─→ WorkspaceService.get()          # validate workspace
  │
  ├─→ WorkspaceService.update_activity()
  │
  └─→ claude.launch()                 # interactive subprocess
```

## Workspace Lifecycle

### Creation

1. **Name generation**: Docker-style adjective-noun (89×90 = 8,000+ combinations)
2. **Worktree creation**: `git worktree add -b <name> <path> <base>`
3. **Environment setup**: `uv venv` + `uv sync` (if pyproject.toml exists)
4. **Metadata persistence**: Atomic JSON write with schema versioning
5. **Skill generation**: Jinja2 template → `.agentspace/skills/workspace-context/SKILL.md`

### Storage Layout

```
~/.agentspaces/
├── MyProject/
│   ├── .active                           # "eager-turing"
│   ├── eager-turing/
│   │   ├── .agentspace/
│   │   │   ├── workspace.json            # Metadata
│   │   │   └── skills/
│   │   │       └── workspace-context/
│   │   │           └── SKILL.md          # Agent context
│   │   ├── .venv/                        # Python environment
│   │   └── <project files>               # Git worktree
│   └── jolly-curie/
│       └── ...
└── AnotherProject/
    └── ...
```

### Removal

1. `git worktree remove <path>` (with optional force)
2. `git branch -d <branch>` (delete branch)
3. Metadata directory removed with worktree

## Security Considerations

### Input Validation

```python
# infrastructure/paths.py
NAME_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$")
MAX_NAME_LENGTH = 100
```

All user-provided names validated to prevent:
- Path traversal (`..`, `/`)
- Command injection
- Excessively long paths

### Template Safety

```python
# infrastructure/skills.py
def _sanitize_for_template(value: str) -> str:
    """Sanitize user input for safe template rendering."""
    # Remove HTML tags, escape special characters
```

### Subprocess Safety

- No shell=True (arguments passed as lists)
- Timeouts on all subprocess calls
- Python version format validation before use in commands

## Error Handling

### Exception Hierarchy

```
WorkspaceError (base)
├── WorkspaceNotFoundError
└── WorkspaceExistsError

GitError
├── GitTimeoutError
└── GitNotFoundError

UvError
├── UvTimeoutError
└── UvNotFoundError

ClaudeError
├── ClaudeTimeoutError
└── ClaudeNotFoundError
```

### User-Friendly Messages

```python
# Did-you-mean suggestions using fuzzy matching
WorkspaceNotFoundError: "Workspace 'eager-turng' not found. Did you mean 'eager-turing'?"
```

## Testing Strategy

```
tests/
├── unit/
│   ├── cli/                    # Command parsing, formatters
│   ├── modules/
│   │   ├── workspace/          # Service, worktree, environment
│   │   └── agent/              # Launcher
│   └── infrastructure/         # All wrappers
└── conftest.py                 # Shared fixtures
```

**Coverage target**: 80% on business logic (CLI layer excluded)

**Patterns**:
- Subprocess calls mocked in unit tests
- Dependency injection for service tests
- Fixtures for common test data

## Future Considerations

### Additional Agents

The `modules/agent/` structure supports adding more agents:

```
modules/agent/
├── launcher.py      # AgentLauncher (multi-agent support)
├── claude.py        # Claude-specific logic
├── cursor.py        # Future: Cursor support
└── aider.py         # Future: Aider support
```

### Workspace Templates

Could add project templates:
- FastAPI workspace with standard deps
- Data science workspace with jupyter
- Custom templates from config

### Remote Storage

PathResolver abstraction could support:
- Network-mounted storage
- Cloud sync (optional)
