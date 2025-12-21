# AgentSpaces

Workspace orchestration tool for AI coding agents.

## Overview

AgentSpaces helps developers working with AI coding agents (Claude Code, Cursor, etc.) by managing isolated workspaces for parallel development. Each workspace is a git worktree with its own environment, tracked purpose, and agent context.

**Key benefits:**

- Work on multiple features simultaneously without branch switching
- Each workspace has its own isolated Python environment
- Launch AI agents directly into workspaces with context
- Track workspace purpose for better organization

## Requirements

- Python 3.12+
- Git
- [uv](https://docs.astral.sh/uv/) (Python package manager)

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

The CLI is available as both `agentspaces` and `as` (short alias).

## Quick Start

### Creating Your First Workspace

```bash
# Navigate to any git repository
cd ~/projects/my-app

# Create a workspace from the main branch
as workspace create main --purpose "Add user authentication"

# Output:
#   Purpose: Add user authentication
#   Workspace created: eager-turing
#     Path: ~/.agentspaces/my-app/eager-turing
#     Branch: eager-turing (from main)
#     Python: 3.12.0 (venv created)
#
#   Next steps:
#     cd ~/.agentspaces/my-app/eager-turing
#     as agent launch eager-turing
```

### Working with Workspaces

```bash
# List all workspaces for current project
as workspace list

# Output:
#   Workspaces for my-app
#   NAME          BRANCH        CREATED
#   eager-turing  eager-turing  2 hours ago

# Check detailed status
as workspace status eager-turing

# Set as active workspace (used as default for commands)
as workspace activate eager-turing
```

### Launching an AI Agent

```bash
# Launch Claude Code in a workspace
as agent launch eager-turing

# Or use the workspace purpose as the initial prompt
as agent launch eager-turing --use-purpose

# If you've set an active workspace, just:
as agent launch
```

### Syncing Dependencies

```bash
# Sync dependencies after pyproject.toml changes
as workspace sync eager-turing

# Or sync the active workspace
as workspace sync
```

### Removing a Workspace

```bash
# Remove workspace when done (prompts for confirmation)
as workspace remove eager-turing

# Skip confirmation
as workspace remove eager-turing --yes

# Force remove even if workspace has uncommitted changes
as workspace remove eager-turing --force --yes
```

## Example Workflow: Parallel Feature Development

This walkthrough demonstrates developing two features simultaneously.

```bash
# You're in your project directory
cd ~/projects/my-app

# Create a workspace for authentication feature
as workspace create main --purpose "Implement OAuth login"
# Created: eager-turing

# Create another workspace for API refactoring
as workspace create main --purpose "Refactor REST endpoints"
# Created: clever-hopper

# List your workspaces
as workspace list
# NAME           BRANCH          CREATED
# clever-hopper  clever-hopper   just now
# eager-turing   eager-turing    1 minute ago

# Work on authentication in one terminal
cd ~/.agentspaces/my-app/eager-turing
as agent launch --use-purpose
# Agent starts with prompt: "Implement OAuth login"

# Work on API in another terminal
cd ~/.agentspaces/my-app/clever-hopper
as agent launch --use-purpose
# Agent starts with prompt: "Refactor REST endpoints"

# When done with a feature, clean up
as workspace remove eager-turing --yes
```

## Command Reference

### Global Options

```bash
as --version          # Show version
as --help             # Show help
as --verbose          # Enable debug output
as --quiet            # Suppress info messages
```

### Workspace Commands

| Command | Description |
|---------|-------------|
| `as workspace create [branch]` | Create workspace from branch (default: HEAD) |
| `as workspace list` | List all workspaces for current project |
| `as workspace status [name]` | Show detailed workspace status |
| `as workspace activate <name>` | Set workspace as active (default for commands) |
| `as workspace current` | Show currently active workspace |
| `as workspace sync [name]` | Sync dependencies with uv |
| `as workspace remove <name>` | Remove workspace and its branch |

### Create Options

```bash
as workspace create main                    # From main branch
as workspace create                         # From current HEAD
as workspace create -p "Fix auth bug"       # With purpose description
as workspace create --python 3.13           # Specify Python version
as workspace create --no-venv               # Skip venv creation
```

### List Options

```bash
as workspace list                    # List all (sorted by name)
as workspace list --sort created     # Sort by creation date (newest first)
as workspace list --sort branch      # Sort by branch name
as workspace list -p myproject       # Filter by project name
```

### Remove Options

```bash
as workspace remove <name>           # With confirmation prompt
as workspace remove <name> --yes     # Skip confirmation
as workspace remove <name> --force   # Force remove dirty workspace
```

### Agent Commands

| Command | Description |
|---------|-------------|
| `as agent launch [workspace]` | Launch Claude Code in workspace |

### Launch Options

```bash
as agent launch                           # Auto-detect from current directory
as agent launch eager-turing              # Launch in specific workspace
as agent launch -p "Fix the login bug"    # With initial prompt
as agent launch --use-purpose             # Use workspace purpose as prompt
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

## How It Works

When you create a workspace, AgentSpaces:

1. Creates a git worktree at `~/.agentspaces/<project>/<name>/`
2. Creates a branch with the workspace name
3. Stores metadata in `.agentspace/` directory
4. Auto-detects Python version and creates venv with uv
5. Syncs dependencies from `pyproject.toml` if present

Workspaces are named using memorable adjective-scientist combinations (e.g., "eager-turing", "clever-hopper") for easy reference.

## Contributing

See [CONTRIB.md](CONTRIB.md) for development setup and contribution guidelines.

## License

MIT
