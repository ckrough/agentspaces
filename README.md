# AgentSpaces

[![CI](https://github.com/ckrough/AgentSpaces/actions/workflows/ci.yml/badge.svg)](https://github.com/ckrough/AgentSpaces/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Workspace orchestration tool for AI coding agents.

## Overview

AgentSpaces helps developers working with AI coding agents (Claude Code, Cursor, etc.) by managing isolated workspaces for parallel development. Each workspace is a git worktree with its own environment, tracked purpose, and agent context.

## Features

- **Workspace Management**: Create isolated workspaces from any branch with automatic naming
- **Environment Setup**: Automatic Python venv creation with uv
- **Agent Integration**: Launch AI agents with workspace context
- **Skill Support**: Uses [agentskills.io](https://agentskills.io) standard for portable agent capabilities

## Installation

```bash
# Clone the repository
git clone https://github.com/ckrough/agentspaces.git
cd agentspaces

# Install with uv
uv sync --all-extras

# Verify installation
uv run agentspaces --version
```

## Quick Start

```bash
# Create a workspace from the current branch
as workspace create main --purpose "Refactor authentication"

# List workspaces
as workspace list

# Remove a workspace
as workspace remove eager-turing
```

## Shell Completion

AgentSpaces supports shell completion for bash, zsh, fish, and PowerShell.

```bash
# Install completion (adds to shell config)
as --install-completion

# Or show completion script for manual setup
as --show-completion bash
as --show-completion zsh
as --show-completion fish
```

## Commands

| Command | Description |
|---------|-------------|
| `as workspace create [branch]` | Create workspace from branch |
| `as workspace create --python 3.13` | Specify Python version for venv |
| `as workspace create --no-venv` | Skip virtual environment creation |
| `as workspace list` | List all workspaces |
| `as workspace remove <name>` | Remove workspace and branch |

## How It Works

When you create a workspace, AgentSpaces:

1. Creates a git worktree at `~/.agentspaces/<project>/<name>/`
2. Creates a branch with the workspace name
3. Sets up metadata in `.agentspace/`
4. Auto-detects Python version and creates venv with uv
5. Syncs dependencies from `pyproject.toml` if present
6. (Coming) Creates workspace-context skill for agent discovery

## Development

```bash
# Install dev dependencies
uv sync --all-extras

# Run tests
uv run pytest

# Lint and format
uv run ruff check src/ tests/
uv run ruff format src/ tests/

# Type check
uv run mypy src/
```

## License

MIT
