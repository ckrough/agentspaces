# agentspaces

Workspace orchestration for AI coding agents. Manage isolated workspaces for parallel development with git worktrees and tracked context.

## Features

- **Project Initialization** - Create new projects with templates, documentation, and Python tooling
- **Parallel Development** - Work on multiple features simultaneously without branch switching
- **Isolated Environments** - Each workspace has its own Python venv and dependencies
- **Project Templates** - Generate documentation optimized for AI agents (CLAUDE.md, ADRs, architecture docs)
- **Workspace Tracking** - Purpose, metadata, and timestamps per workspace

## Quick Start

### Prerequisites

- Python 3.13
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

## Usage

### Initialize a New Project

```bash
mkdir my-project && cd my-project
agentspaces project create -n "My Project" -d "Description"

# With Python tooling (pyproject.toml, ruff, mypy, pytest, GitHub Actions)
agentspaces project create --python -n "My CLI" -d "A CLI tool"
```

### Workspace Commands

```bash
agentspaces workspace create [branch]    # Create from branch (default: HEAD)
agentspaces workspace list               # List all workspaces
agentspaces workspace status <name>      # Show detailed status
agentspaces workspace remove <name>      # Remove workspace
```

### Documentation Templates

```bash
agentspaces docs list                    # List available templates
agentspaces docs info <template>         # Show template details
agentspaces docs create <template>       # Generate from template
```

Available templates: `readme`, `claude-md`, `architecture`, `development-standards`, `adr-template`

## Development Cycle Quick Reference

The complete workflow from issue to PR, showing what you do and what the agent does.

### 1. Discovery

**Agent:** Checks ready queue and claims work
```bash
bd ready --json                        # Check available work
bd update <issue-id> --status in_progress   # Claim issue
```
Or creates new issues with `bd create` based on your request

### 2. Planning (MANDATORY - No Code Before Approval)

**You:** Run `/feature-dev` with your change description
*Example: `/feature-dev Add email validation to user registration`*

**Agent:**
- Uses `@code-explorer` to find relevant code
- Asks clarifying questions about approach
- Proposes implementation plan
- Decides if ADR needed (technology choices affecting data storage/processing, significant dependencies, schema changes)
- Runs `@architect-reviewer` to validate design
- Runs `@python-pro` (for Python projects) to review architecture
- Creates tasks with `bd create` for each implementation step
- Gets your approval before coding

### 3. Implementation

**You:** Approve plan, provide feedback on code

**Agent:**
- Updates issue status: `bd update <id> --status in_progress`
- Writes code and tests (TDD for clear requirements, test-after for exploration)
- If bugs discovered: creates linked issues with `bd create` + `bd dep add --type discovered-from`
- If blocker found: switches priorities immediately
- Runs tests: `uv run pytest`

**Coverage target:** 80% on business logic, regression tests for bugs

### 4. Simplification

**Agent:**
- Automatically runs `@simplifier` to review for unnecessary complexity, duplication, naming issues
- Refactors based on feedback before quality gates

### 5. Quality Gates (All Must Pass)

**You:** Request commit or the agent runs automatically

**Agent:** Runs all checks in sequence:
```bash
uv run ruff format src/ tests/         # Format
uv run ruff check src/ tests/          # Lint
uv run bandit -r src/                  # Security scan
uv run mypy src/                       # Type check
uv run pytest                          # Tests
```

### 6. Review (MANDATORY - No Commit Until All Pass)

**You:** Approve changes after review

**Agent:**
- Runs `@code-reviewer` (always) - checks bugs, security, performance
- Runs `@python-pro` (if Python) - validates Python idioms and patterns
- Runs `@verify-app` (if applicable) - E2E verification
- Addresses all feedback before proceeding
- Returns to implementation if reviews fail

### 7. Commit

**You:** Provide final approval for commit

**Agent:**
- Updates docs (README.md, CLAUDE.md, ADRs)
- Exports Beads: `bd export -o .beads/issues.jsonl`
- Creates commit with proper prefix (bug→fix:, feature→feat:, task→task:, chore→chore:)
- Gets your explicit approval
- Commits and closes issue: `bd close <id> --reason "Implemented"`

### 8. Pull Request

**You:** Run `/commit-push-pr`

**Agent (via skill):**
- Pushes commits to remote
- Creates PR with generated summary
- Returns PR URL

---

### Common Workflow Variations

**Quick bug fix:** Skip comprehensive tests and architecture review, but must run @code-reviewer and quality gates

**Prototype:** Skip architecture review and comprehensive tests, but inform you what's being skipped. Security review still required.

**Legacy code:** Match existing patterns even if not ideal. Agent notes when deviating from standards for consistency.

**Discovered blocker:** Agent creates blocker issue, links with `bd dep add --type blocks`, and switches to blocker immediately

## Configuration

Workspaces are stored at `~/.agentspaces/<project>/<workspace>/`:

```
~/.agentspaces/my-app/eager-turing/
├── .agentspace/           # Metadata
│   └── workspace.json
├── .venv/                 # Isolated Python environment
└── <project files>        # Git worktree
```

## Architecture

```
[CLI] → [Service] → [Git Worktree] → [Python Env]
```

- **CLI Layer** - Typer commands with Rich output
- **Service Layer** - WorkspaceService orchestration
- **Infrastructure** - Git and uv subprocess wrappers

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
