# agentspaces

Workspace orchestration for AI coding agents. Manage isolated workspaces for parallel development with git worktrees, tracked context, and agent integration.

## Features

- **Parallel Development** - Work on multiple features simultaneously without branch switching
- **Isolated Environments** - Each workspace has its own Python venv and dependencies
- **Agent Integration** - Launch Claude Code directly into workspaces with context
- **Project Templates** - Generate documentation optimized for AI agents (CLAUDE.md, TODO.md, ADRs)
- **Workspace Tracking** - Purpose, metadata, and activity tracking per workspace

## Quick Start

### Prerequisites

- Python 3.12+
- Git
- [uv](https://docs.astral.sh/uv/) (Python package manager)

### Installation

```bash
git clone https://github.com/ckrough/agentspaces.git
cd agentspaces
uv sync --all-extras
uv run agentspaces --version
```

### Create a Workspace

```bash
cd ~/projects/my-app
agentspaces workspace create main --purpose "Add user authentication"
# Created: eager-turing at ~/.agentspaces/my-app/eager-turing
```

### Launch an Agent

```bash
agentspaces agent launch eager-turing --use-purpose
# Launches Claude Code with prompt: "Add user authentication"
```

## Usage

### Workspace Commands

```bash
agentspaces workspace create [branch]    # Create from branch (default: HEAD)
agentspaces workspace list               # List all workspaces
agentspaces workspace status [name]      # Show detailed status
agentspaces workspace activate <name>    # Set as active workspace
agentspaces workspace sync [name]        # Sync dependencies
agentspaces workspace remove <name>      # Remove workspace
```

### Agent Commands

```bash
agentspaces agent launch [workspace]     # Launch Claude Code
agentspaces agent launch --use-purpose   # Use workspace purpose as prompt
```

### Documentation Templates

```bash
agentspaces docs list                    # List available templates
agentspaces docs info <template>         # Show template details
agentspaces docs create <template>       # Generate from template
```

Available templates: `readme`, `claude-md`, `todo-md`, `architecture`, `development-standards`, `deployment`, `adr-template`

## Configuration

Workspaces are stored at `~/.agentspaces/<project>/<workspace>/`:

```
~/.agentspaces/my-app/eager-turing/
├── .agentspace/           # Metadata and skills
│   ├── workspace.json
│   └── skills/
├── .venv/                 # Isolated Python environment
└── <project files>        # Git worktree
```

## Architecture

```
[CLI] → [Service] → [Git Worktree] → [Python Env] → [Agent Launch]
```

- **CLI Layer** - Typer commands with Rich output
- **Service Layer** - WorkspaceService orchestration
- **Infrastructure** - Git, uv, and Claude subprocess wrappers

See [docs/design/architecture.md](docs/design/architecture.md) for detailed system design.

## Development

```bash
uv run pytest                    # Run tests
uv run ruff check src/ tests/    # Lint
uv run ruff format src/ tests/   # Format
uv run mypy src/                 # Type check
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.

## License

MIT
